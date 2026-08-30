"""Git worktree lifecycle for reusable agent shortcut children.

The service deliberately keeps Git commands out of Qt widgets.  A workspace is
either active for one feature or idle and reusable; it is never a permanent
record for every feature branch.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from datetime import datetime
import os
import re
import shutil
import socket
import stat
import string
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.shortcuts.shortcut_table_service import build_agent_command
from services.shortcuts.terminal_service import (
    AGENT_TERMINAL_GROUP,
    SCRIPT_TERMINAL_GROUP,
    launch_terminal_tab,
)


class GitWorktreeError(RuntimeError):
    """A safe, user-displayable Git workspace failure."""


class _BaseRefSyncResult(str):
    """A base ref that remains string-compatible while carrying sync feedback."""

    def __new__(cls, value: str, warning: str = "") -> "_BaseRefSyncResult":
        result = str.__new__(cls, value)
        result.warning = warning
        return result


class GitWorktreeService:
    """Manage an elastic pool of per-agent Git worktrees."""

    POOL_SIZE_CONFIG_KEY = "agent_workspace_warm_pool_size"
    DEFAULT_POOL_SIZE = 2
    ACTIVE_LIMIT_CONFIG_KEY = "agent_workspace_active_limit"
    DEFAULT_ACTIVE_LIMIT = 2  # 0 explicitly means unlimited concurrent children.
    MERGE_INSTRUCTION_CONFIG_KEY = "agent_workspace_merge_instruction"
    PROXY_POOL_SUBSCRIPTION_CONFIG_KEY = "agent_workspace_proxy_pool_subscription"
    PROXY_POOL_HYSTERIA_EXECUTABLE_CONFIG_KEY = "agent_workspace_proxy_pool_hysteria_executable"
    PROXY_POOL_CONNECT_TIMEOUT_SECONDS = 8
    MERGE_PROVIDER_CONFIG_KEY = "agent_workspace_merge_provider"
    DEFAULT_MERGE_PROVIDER = "codex"
    DEFAULT_MERGE_INSTRUCTION = (
        "请将功能分支 {branch} 合并到本地基线分支 {base_branch}。"
        "先检查状态、差异和冲突，必要时运行测试；确认无误后完成合并并报告结果。"
        "不要强推或删除远程分支。"
    )
    _MERGE_TEMPLATE_FIELDS = frozenset((
        "branch", "base_branch", "repository_root", "worktree_path",
    ))

    def __init__(self, data_manager: Any) -> None:
        self._data_manager = data_manager
        self._shortcuts = data_manager.shortcut_manager

    @staticmethod
    def _clean_feature_name(feature_name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", feature_name.strip()).strip(".-")
        return cleaned[:48] or "feature"

    @staticmethod
    def _run(command: Sequence[str], cwd: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
        """Run a short Git command without Windows pipe reader threads.

        ``capture_output=True`` makes Python create ``_readerthread`` workers
        on Windows.  Some embedded/GUI-launched Python 3.12 environments can
        close those pipe handles early, producing an unhandled ``Invalid
        handle`` traceback after Git has already completed.  Git command
        output is small, so a temporary file is a reliable equivalent.
        """
        try:
            with tempfile.TemporaryFile(mode="w+b") as output:
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
                raw_result = subprocess.run(
                    list(command), cwd=cwd, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=output, check=False,
                    creationflags=creationflags,
                )
                output.seek(0)
                output_text = output.read().decode("utf-8", errors="replace")
            result = subprocess.CompletedProcess(
                list(command), raw_result.returncode, stdout=output_text, stderr="",
            )
        except OSError as error:
            raise GitWorktreeError("无法启动 Git；请确认 Git 已安装并已加入 PATH。") from error
        if check and result.returncode != 0:
            message = (result.stderr or result.stdout or "Git 操作失败").strip()
            raise GitWorktreeError(message)
        return result

    def _git(self, repository_root: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return self._run(["git", "-C", repository_root, *arguments], check=check)

    def discover_repository(self, path: str) -> str:
        """Return the canonical repository root, including linked worktrees."""
        if not path:
            raise GitWorktreeError("快捷入口没有路径，无法识别 Git 仓库。")
        candidate = os.path.abspath(os.path.expanduser(path))
        # A normal parent shortcut may point straight at run.bat/launch.py.
        # Git -C accepts directories only, so resolve that common form to the
        # script's directory before asking Git for the actual repository root.
        if os.path.isfile(candidate) or os.path.splitext(os.path.basename(candidate))[1]:
            candidate = os.path.dirname(candidate)
        result = self._git(candidate, "rev-parse", "--show-toplevel")
        root = result.stdout.strip()
        if not root:
            raise GitWorktreeError("该快捷入口不是 Git 工作目录。")
        return os.path.normcase(os.path.normpath(root))

    @staticmethod
    def _parent_launch_script(repository_root: str, shortcut_path: str) -> str:
        """Return the parent shortcut's script as a repo-relative launcher."""
        candidate = os.path.realpath(os.path.abspath(os.path.expanduser(shortcut_path or "")))
        if not os.path.isfile(candidate):
            return ""
        root = os.path.realpath(repository_root)
        try:
            if os.path.commonpath([root, candidate]) != root:
                return ""
        except ValueError:
            return ""
        return os.path.relpath(candidate, root)

    def configure_repository(
        self,
        parent_shortcut_id: str,
        launch_script: str = "",
        base_ref: Optional[str] = None,
        remote_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        parent = self._shortcuts.get_by_id(parent_shortcut_id)
        if not parent or parent.get("parent_id"):
            raise GitWorktreeError("只能将顶级快捷入口配置为仓库入口。")
        repository_root = self.discover_repository(parent.get("shortcut_path", ""))
        existing = self._shortcuts.get_repository_profile(parent_shortcut_id)
        configured_remote = existing.get("remote_name", "origin") if existing else "origin"
        selected_remote = (remote_name or configured_remote or "origin").strip()
        selected_base_ref = (
            (existing.get("base_ref", "") or "")
            if base_ref is None and existing else (base_ref or "").strip()
        )
        selected_script = launch_script.strip()
        if not selected_script:
            selected_script = self._parent_launch_script(
                repository_root, parent.get("shortcut_path", ""),
            )
        if not selected_script and existing:
            selected_script = existing.get("launch_script", "")
        if not selected_script:
            selected_script = self._find_default_launch_script(repository_root)
        if not selected_script:
            raise GitWorktreeError(
                "仓库根目录未找到默认启动脚本（launch.bat、launch.py 或 launch.sh）。"
            )
        if existing and self._shortcuts.has_agent_workspaces(parent_shortcut_id):
            old_root = os.path.normcase(os.path.normpath(existing["repository_root"]))
            changed_git_settings = (
                old_root != repository_root
                or existing.get("remote_name", "origin") != selected_remote
                or (existing.get("base_ref", "") or "") != selected_base_ref
            )
            if changed_git_settings:
                raise GitWorktreeError(
                    "该仓库仍有智能体工作区；请先归还或删除全部工作区，"
                    "再修改仓库根目录、远程或基线分支。"
                )
        self._git(repository_root, "remote", "get-url", selected_remote)
        self._resolve_launch_script(repository_root, selected_script)
        self._shortcuts.save_repository_profile(
            parent_shortcut_id, repository_root, selected_remote, selected_base_ref, selected_script,
        )
        return self._shortcuts.get_repository_profile(parent_shortcut_id) or {}

    def _profile(self, parent_shortcut_id: str) -> Dict[str, Any]:
        # Reconcile on each lifecycle action. This makes a parent shortcut
        # pointing to run.bat authoritative even if an older profile saved a
        # guessed launch.py/launch.bat value before file-entry support existed.
        return self.configure_repository(parent_shortcut_id)

    def get_repository_profile(self, parent_shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Expose saved parent settings for the UI without exposing the repository."""
        return self._shortcuts.get_repository_profile(parent_shortcut_id)

    def get_workspace(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Return workspace metadata when this shortcut is an agent child."""
        return self._shortcuts.get_agent_workspace(shortcut_id)

    def get_proxy_pool_subscription(self) -> str:
        return str(self._data_manager.get_config(self.PROXY_POOL_SUBSCRIPTION_CONFIG_KEY, "") or "").strip()

    def set_proxy_pool_subscription(self, subscription_url: str) -> None:
        self._data_manager.set_config(self.PROXY_POOL_SUBSCRIPTION_CONFIG_KEY, (subscription_url or "").strip())

    def get_proxy_pool_hysteria_executable(self) -> str:
        return str(self._data_manager.get_config(self.PROXY_POOL_HYSTERIA_EXECUTABLE_CONFIG_KEY, "") or "").strip()

    def set_proxy_pool_hysteria_executable(self, executable: str) -> None:
        self._data_manager.set_config(
            self.PROXY_POOL_HYSTERIA_EXECUTABLE_CONFIG_KEY, (executable or "").strip(),
        )

    def _sync_and_base_ref(self, profile: Dict[str, Any]) -> _BaseRefSyncResult:
        """Sync directly first, then try subscription proxy nodes on network failure."""
        repository_root = profile["repository_root"]
        remote_name = profile.get("remote_name") or "origin"
        fetch, fetch_warning = self._fetch_remote(repository_root, remote_name)
        base_ref = self._resolve_available_base_ref(repository_root, remote_name, profile)
        if fetch.returncode == 0:
            if base_ref:
                return _BaseRefSyncResult(base_ref, fetch_warning)
            raise GitWorktreeError(
                "Remote sync succeeded, but no usable base branch was found. "
                "Specify a base branch in the repository settings."
            )
        details = (fetch.stderr or fetch.stdout or "Git fetch failed").strip()
        if base_ref:
            warning = (
                "Unable to update remote '{}'; created the workspace from local cached base '{}'. "
                "It may not contain the latest remote commits.{}".format(
                    remote_name, base_ref, "\n" + fetch_warning if fetch_warning else "",
                )
            )
            if details:
                warning += "\nGit: " + " ".join(details.splitlines()[:2])
            return _BaseRefSyncResult(base_ref, warning)
        raise GitWorktreeError(
            "Unable to update remote '{}' and no usable local base branch is available. "
            "Check the network or Git proxy, or configure an existing local base branch.\n{}".format(
                remote_name, details,
            )
        )

    def _fetch_remote(self, repository_root: str, remote_name: str) -> Tuple[subprocess.CompletedProcess, str]:
        """Fetch directly first; proxy nodes are a connection-failure fallback only."""
        direct = self._git(
            repository_root,
            "-c", "http.connectTimeout={}".format(self.PROXY_POOL_CONNECT_TIMEOUT_SECONDS),
            "-c", "http.lowSpeedLimit=1",
            "-c", "http.lowSpeedTime=15",
            "fetch", "--prune", remote_name,
            check=False,
        )
        if direct.returncode == 0 or not self._is_connectivity_failure(direct):
            return direct, ""
        proxied, proxy_warning = self._fetch_via_proxy_pool(repository_root, remote_name)
        if proxied is not None:
            return proxied, proxy_warning
        return direct, proxy_warning

    @staticmethod
    def _is_connectivity_failure(result: subprocess.CompletedProcess) -> bool:
        details = "{}\n{}".format(result.stdout or "", result.stderr or "").lower()
        markers = (
            "unable to access", "failed to connect", "could not connect", "connection timed out",
            "connection refused", "could not resolve host", "network is unreachable", "proxy error",
            "recv failure", "send failure", "ssl connection timeout",
        )
        return any(marker in details for marker in markers)

    def _fetch_via_proxy_pool(
        self, repository_root: str, remote_name: str,
    ) -> Tuple[Optional[subprocess.CompletedProcess], str]:
        """Try every Hysteria 2 node in the configured subscription once."""
        subscription_url = self.get_proxy_pool_subscription()
        if not subscription_url:
            return None, "Direct connection failed; no proxy-pool subscription is configured."
        executable = self.get_proxy_pool_hysteria_executable() or shutil.which("hysteria") or ""
        if not executable or not os.path.isfile(executable):
            return None, "Direct connection failed; install Hysteria 2 or configure its executable path before using the proxy pool."
        try:
            nodes = self._load_hysteria_subscription(subscription_url)
        except Exception as error:
            return None, "Direct connection failed; unable to load the proxy subscription: {}".format(error)
        if not nodes:
            return None, "Direct connection failed; the proxy subscription contains no Hysteria 2 nodes."

        failures = []
        for index, node in enumerate(nodes, start=1):
            process = None
            config_path = ""
            try:
                process, config_path, proxy_url = self._start_hysteria_proxy(executable, node)
                proxied = self._git(
                    repository_root,
                    "-c", "http.proxy={}".format(proxy_url),
                    "-c", "https.proxy={}".format(proxy_url),
                    "-c", "http.connectTimeout={}".format(self.PROXY_POOL_CONNECT_TIMEOUT_SECONDS),
                    "-c", "http.lowSpeedLimit=1",
                    "-c", "http.lowSpeedTime=15",
                    "fetch", "--prune", remote_name,
                    check=False,
                )
                if proxied.returncode == 0:
                    return proxied, "Direct connection failed; remote sync succeeded through proxy node {} of {}.".format(index, len(nodes))
                failures.append("node {}: {}".format(index, self._compact_git_error(proxied)))
            except Exception as error:
                failures.append("node {}: {}".format(index, error))
            finally:
                self._stop_proxy_process(process)
                if config_path:
                    try:
                        os.remove(config_path)
                    except OSError:
                        pass
        summary = "; ".join(failures[:3])
        if len(failures) > 3:
            summary += "; {} more nodes failed".format(len(failures) - 3)
        return None, "Direct connection failed; all {} proxy nodes failed. {}".format(len(nodes), summary)

    @staticmethod
    def _compact_git_error(result: subprocess.CompletedProcess) -> str:
        details = (result.stderr or result.stdout or "Git fetch failed").strip()
        return " ".join(details.splitlines()[:2])[:300]

    @staticmethod
    def _load_hysteria_subscription(subscription_url: str) -> List[str]:
        request = Request(subscription_url, headers={"User-Agent": "TaskManager-PyQt/1.0"})
        with urlopen(request, timeout=15) as response:
            payload = response.read()
        return GitWorktreeService._parse_hysteria_subscription(
            payload.decode("utf-8", errors="replace"),
        )

    @staticmethod
    def _parse_hysteria_subscription(payload: str) -> List[str]:
        raw = (payload or "").strip()
        compact = "".join(raw.split())
        try:
            decoded = base64.b64decode(compact + "=" * (-len(compact) % 4), validate=True)
            raw = decoded.decode("utf-8", errors="replace")
        except (ValueError, UnicodeError):
            pass
        return [
            line.strip() for line in raw.splitlines()
            if line.strip().lower().startswith(("hysteria2://", "hy2://"))
        ]

    @staticmethod
    def _hysteria_client_config(node_uri: str, listen_port: int) -> str:
        """Create a client config that preserves every option in the share URI."""
        parsed = urlsplit(node_uri)
        if parsed.scheme.lower() not in ("hysteria2", "hy2") or not parsed.hostname:
            raise GitWorktreeError("Invalid Hysteria 2 proxy node.")
        quote = lambda value: '"{}"'.format(str(value).replace('\\', '\\\\').replace('"', '\\"'))
        return "\n".join((
            "server: " + quote(node_uri),
            "http:",
            "  listen: " + quote("127.0.0.1:{}".format(listen_port)),
            "",
        ))

    @staticmethod
    def _unused_local_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return int(listener.getsockname()[1])

    def _start_hysteria_proxy(self, executable: str, node_uri: str) -> Tuple[subprocess.Popen, str, str]:
        port = self._unused_local_port()
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yaml", delete=False) as config:
            config.write(self._hysteria_client_config(node_uri, port))
            config_path = config.name
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                [executable, "client", "-c", config_path],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            deadline = time.monotonic() + self.PROXY_POOL_CONNECT_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise GitWorktreeError("Hysteria 2 exited before its local proxy started.")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.2)
                    if probe.connect_ex(("127.0.0.1", port)) == 0:
                        return process, config_path, "http://127.0.0.1:{}".format(port)
                time.sleep(0.1)
            raise GitWorktreeError("Timed out while starting the local Hysteria 2 proxy.")
        except Exception:
            self._stop_proxy_process(locals().get("process"))
            try:
                os.remove(config_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _stop_proxy_process(process: Optional[subprocess.Popen]) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def _resolve_available_base_ref(
        self, repository_root: str, remote_name: str, profile: Dict[str, Any],
    ) -> str:
        """Return a locally resolvable configured/default base ref, if any."""
        requested = (profile.get("base_ref") or "").strip()
        candidates = [requested] if requested else []
        if not requested:
            head = self._git(
                repository_root, "symbolic-ref", "--quiet", "--short",
                "refs/remotes/{}/HEAD".format(remote_name), check=False,
            )
            if head.returncode == 0 and head.stdout.strip():
                candidates.append(head.stdout.strip())
            candidates.extend(("{}/main".format(remote_name), "main", "master"))
            local_head = self._git(
                repository_root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False,
            )
            if local_head.returncode == 0 and local_head.stdout.strip():
                candidates.append(local_head.stdout.strip())

        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            exists = self._git(
                repository_root, "rev-parse", "--verify", "--quiet", candidate, check=False,
            )
            if exists.returncode == 0:
                return self._prefer_local_base(repository_root, remote_name, candidate)
        return ""

    def _prefer_local_base(
        self, repository_root: str, remote_name: str, remote_ref: str,
    ) -> str:
        """Use the local base branch when it already contains remote latest."""
        prefix = "{}/".format(remote_name)
        if not remote_ref.startswith(prefix):
            return remote_ref
        local_ref = remote_ref[len(prefix):]
        local_exists = self._git(
            repository_root, "show-ref", "--verify", "--quiet",
            "refs/heads/{}".format(local_ref), check=False,
        )
        if local_exists.returncode != 0:
            return remote_ref
        remote_is_in_local = self._git(
            repository_root, "merge-base", "--is-ancestor", remote_ref, local_ref,
            check=False,
        )
        return local_ref if remote_is_in_local.returncode == 0 else remote_ref

    @staticmethod
    def _find_default_launch_script(repository_root: str) -> str:
        """Find the conventional project launcher once, from the parent repo."""
        for candidate in ("launch.bat", "launch.py", "launch.sh"):
            if os.path.isfile(os.path.join(repository_root, candidate)):
                return candidate
        return ""

    @staticmethod
    def _clean_repository_name(repository_root: str) -> str:
        """Make the parent repository directory name safe for Windows paths."""
        repo_name = os.path.basename(os.path.normpath(repository_root)) or "repository"
        cleaned = re.sub(r'[<>:"/\|?*\x00-\x1f]+', "-", repo_name).strip(". ")
        return cleaned[:200] or "repository"

    @classmethod
    def _workspace_path(cls, repository_root: str, agent_number: int) -> str:
        """Place a numbered worktree beside, never inside, its parent repository."""
        timestamp = datetime.now().strftime("%d%H%M%S")
        return os.path.join(
            os.path.dirname(repository_root),
            "{}-{}-{}".format(
                agent_number, cls._clean_repository_name(repository_root), timestamp,
            ),
        )

    def _new_branch_name(self, feature_name: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "agent/{}/{}-{}".format(self._clean_feature_name(feature_name), stamp, uuid.uuid4().hex[:6])

    def _resolve_launch_script(self, worktree_path: str, launch_script: str) -> str:
        if not launch_script:
            raise GitWorktreeError("该仓库尚未设置本地启动脚本。")
        root = os.path.realpath(worktree_path)
        script = launch_script
        if not os.path.isabs(script):
            script = os.path.join(root, script)
        script = os.path.realpath(script)
        try:
            is_inside = os.path.commonpath([root, script]) == root
        except ValueError:
            is_inside = False
        if not is_inside or not os.path.isfile(script):
            raise GitWorktreeError("启动脚本不存在，或不在该智能体工作区内。")
        return script

    def get_warm_pool_size(self) -> int:
        value = self._data_manager.get_config(self.POOL_SIZE_CONFIG_KEY, str(self.DEFAULT_POOL_SIZE))
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return self.DEFAULT_POOL_SIZE

    def set_warm_pool_size(self, size: int) -> None:
        self._data_manager.set_config(self.POOL_SIZE_CONFIG_KEY, str(max(0, int(size))))

    def get_active_workspace_limit(self) -> int:
        """Return the active-child cap; zero explicitly means no cap."""
        value = self._data_manager.get_config(
            self.ACTIVE_LIMIT_CONFIG_KEY, str(self.DEFAULT_ACTIVE_LIMIT),
        )
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return self.DEFAULT_ACTIVE_LIMIT

    def set_active_workspace_limit(self, size: int) -> None:
        self._data_manager.set_config(
            self.ACTIVE_LIMIT_CONFIG_KEY, str(max(0, int(size))),
        )

    def get_merge_provider(self) -> str:
        provider = str(self._data_manager.get_config(
            self.MERGE_PROVIDER_CONFIG_KEY, self.DEFAULT_MERGE_PROVIDER,
        ) or "").strip().lower()
        return provider if provider in ("codex", "claude") else self.DEFAULT_MERGE_PROVIDER

    def set_merge_provider(self, provider: str) -> None:
        provider = (provider or "").strip().lower()
        if provider not in ("codex", "claude"):
            raise GitWorktreeError("合并智能体只能选择 Codex 或 Claude Code。")
        self._data_manager.set_config(self.MERGE_PROVIDER_CONFIG_KEY, provider)

    def get_merge_instruction(self) -> str:
        instruction = self._data_manager.get_config(
            self.MERGE_INSTRUCTION_CONFIG_KEY, self.DEFAULT_MERGE_INSTRUCTION,
        )
        return str(instruction or self.DEFAULT_MERGE_INSTRUCTION)

    def set_merge_instruction(self, instruction: str) -> None:
        instruction = (instruction or "").strip()
        if not instruction:
            raise GitWorktreeError("合并指令不能为空；如需默认内容，请使用“恢复默认合并指令”。")
        self._validate_merge_instruction(instruction)
        self._data_manager.set_config(self.MERGE_INSTRUCTION_CONFIG_KEY, instruction)

    def reset_merge_instruction(self) -> str:
        self._data_manager.set_config(
            self.MERGE_INSTRUCTION_CONFIG_KEY, self.DEFAULT_MERGE_INSTRUCTION,
        )
        return self.DEFAULT_MERGE_INSTRUCTION

    def _validate_merge_instruction(self, instruction: str) -> None:
        """Reject malformed/unknown placeholders before a terminal is opened."""
        try:
            fields = [name for _, name, _, _ in string.Formatter().parse(instruction) if name]
        except ValueError as error:
            raise GitWorktreeError("合并指令中的占位符格式无效。") from error
        unknown = set(fields) - self._MERGE_TEMPLATE_FIELDS
        if unknown:
            raise GitWorktreeError(
                "合并指令只支持占位符：{branch}、{base_branch}、{repository_root}、{worktree_path}。"
            )

    def launch_merge_agent(self, shortcut_id: str) -> Dict[str, str]:
        """Open the selected local agent in the parent checkout to perform a merge.

        The application does not run ``git merge`` here.  The agent receives a
        concise, user-editable instruction and works in the parent checkout,
        where the integration branch belongs.  Recycling remains an explicit
        later safety check after the merge is complete.
        """
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace or workspace.get("state") != "active":
            raise GitWorktreeError("只能为处于开发状态的智能体工作区启动合并。")
        profile = self._profile(workspace["parent_shortcut_id"])
        base_branch = self._sync_and_base_ref(profile)
        sync_warning = base_branch.warning
        branch = workspace.get("branch_name", "").strip()
        if not branch:
            raise GitWorktreeError("该工作区没有可合并的功能分支。")
        template = self.get_merge_instruction()
        self._validate_merge_instruction(template)
        instruction = template.format(
            branch=branch,
            base_branch=base_branch,
            repository_root=profile["repository_root"],
            worktree_path=workspace["worktree_path"],
        )
        provider = self.get_merge_provider()
        command = build_agent_command(provider)
        if not command:
            name = "Codex" if provider == "codex" else "Claude Code"
            raise GitWorktreeError("未找到 {} 命令行工具；请安装后重启应用再试。".format(name))
        command = list(command) + [instruction]
        name = "Codex" if provider == "codex" else "Claude Code"
        launch_terminal_tab(
            command, profile["repository_root"], AGENT_TERMINAL_GROUP,
            title="{} 合并 - {}".format(name, branch),
        )
        return {
            "provider": provider,
            "instruction": instruction,
            "base_branch": base_branch,
            "branch": branch,
            "sync_warning": sync_warning,
        }

    def create_or_reuse_workspace(
        self, parent_shortcut_id: str, feature_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a ready-to-run child with no input, or activate an idle one."""
        feature_name = (feature_name or "").strip()
        if not feature_name:
            feature_name = "智能体-{}".format(datetime.now().strftime("%Y%m%d-%H%M%S"))
        profile = self._profile(parent_shortcut_id)
        active_limit = self.get_active_workspace_limit()
        active_count = self._shortcuts.count_active_agent_workspaces(parent_shortcut_id)
        if active_limit and active_count >= active_limit:
            raise GitWorktreeError(
                "该父项目的同时开发子类已达上限（{}/{}）。"
                "请先归还、删除一个子类，或提高上限。".format(active_count, active_limit)
            )
        base_ref_result = self._sync_and_base_ref(profile)
        base_ref = str(base_ref_result)
        sync_warning = base_ref_result.warning
        branch_name = self._new_branch_name(feature_name)
        agent_number = self._shortcuts.count_agent_workspaces(parent_shortcut_id) + 1
        # Keep the display title independent from the on-disk worktree name.
        title = "\U0001f916 \u5b50\u7c7b {}".format(agent_number)
        idle_workspaces = self._shortcuts.get_idle_agent_workspaces(parent_shortcut_id)
        for workspace in idle_workspaces:
            path = workspace["worktree_path"]
            if not os.path.isdir(path):
                self._shortcuts.remove_agent_workspace(workspace["shortcut_id"])
                continue
            status = self._git(path, "status", "--porcelain").stdout.strip()
            if status:
                continue
            self._git(path, "switch", "-c", branch_name, base_ref)
            self._shortcuts.update_agent_workspace(
                workspace["shortcut_id"], branch_name=branch_name, base_ref=base_ref,
                state="active", feature_name=feature_name, runtime_state="stopped",
            )
            self._shortcuts.update(workspace["shortcut_id"], title=title)
            result = self._shortcuts.get_by_id(workspace["shortcut_id"])
            result["workspace_reused"] = True
            result["sync_warning"] = sync_warning
            return result

        worktree_path = self._workspace_path(profile["repository_root"], agent_number)
        self._git(profile["repository_root"], "worktree", "add", "-b", branch_name, worktree_path, base_ref)
        try:
            result = self._shortcuts.create_agent_workspace(
                parent_shortcut_id, title, worktree_path, branch_name, base_ref, feature_name,
            )
        except Exception:
            self._git(profile["repository_root"], "worktree", "remove", worktree_path, check=False)
            raise
        result["workspace_reused"] = False
        result["sync_warning"] = sync_warning
        return result

    def workspace_status(self, shortcut_id: str) -> Dict[str, Any]:
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            raise GitWorktreeError("选中的快捷入口不是智能体工作区。")
        path = workspace["worktree_path"]
        branch = self._git(path, "branch", "--show-current").stdout.strip()
        dirty = bool(self._git(path, "status", "--porcelain").stdout.strip())
        return dict(workspace, branch_name=branch or workspace.get("branch_name", ""), dirty=dirty)

    @staticmethod
    def _branch_name_from_ref(ref: str) -> str:
        """Normalize a configured Git ref to its local branch name."""
        ref = (ref or "").strip()
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/"):]
        if ref.startswith("refs/remotes/"):
            ref = ref[len("refs/remotes/"):]
        if "/" in ref and ref.split("/", 1)[0] in {"origin", "upstream"}:
            return ref.split("/", 1)[1]
        return ref

    def get_non_main_branches(self, parent_shortcut_id: str) -> Dict[str, Any]:
        """List local branches eligible for the cleanup action."""
        parent = self._shortcuts.get_by_id(parent_shortcut_id)
        if not parent:
            raise GitWorktreeError("\u627e\u4e0d\u5230\u5bf9\u5e94\u7684\u5feb\u6377\u5165\u53e3\u3002")
        profile = self._shortcuts.get_repository_profile(parent_shortcut_id) or {}
        repository_root = profile.get("repository_root") or self.discover_repository(
            parent.get("shortcut_path", "")
        )
        configured_base = self._branch_name_from_ref(profile.get("base_ref", ""))
        protected = {"main", "master"}
        if configured_base:
            protected.add(configured_base)

        branches_result = self._git(
            repository_root, "for-each-ref", "--format=%(refname:short)",
            "refs/heads/",
        )
        branches = [line.strip() for line in branches_result.stdout.splitlines() if line.strip()]

        # Remote refs are intentionally read-only here.  They are surfaced to
        # explain why `git branch -a` can show more names than this local-only
        # cleanup action, but they are never deletion candidates.
        remote_name = (profile.get("remote_name") or "origin").strip() or "origin"
        remote_result = self._git(
            repository_root, "for-each-ref", "--format=%(refname:short)",
            "refs/remotes/{}/".format(remote_name), check=False,
        )
        remote_branches = []
        remote_prefix = remote_name + "/"
        for ref in remote_result.stdout.splitlines():
            ref = ref.strip()
            if not ref.startswith(remote_prefix):
                continue
            branch = ref[len(remote_prefix):]
            if branch == "HEAD" or branch in protected:
                continue
            remote_branches.append(branch)

        # A branch checked out in the primary checkout or a linked worktree
        # cannot be deleted by Git. Parse worktree porcelain output once so
        # the UI can explain why such branches were left untouched.
        worktree_result = self._git(
            repository_root, "worktree", "list", "--porcelain", check=False,
        )
        worktrees = []
        current_worktree = {}
        for line in worktree_result.stdout.splitlines() + [""]:
            if not line.strip():
                if current_worktree:
                    worktrees.append(current_worktree)
                    current_worktree = {}
                continue
            if line.startswith("worktree "):
                current_worktree["worktree_path"] = line[len("worktree "):].strip()
            elif line.startswith("branch refs/heads/"):
                current_worktree["branch"] = line[len("branch refs/heads/"):].strip()

        workspace_by_path = {}
        workspace_by_branch = {}
        for child in self._shortcuts.get_children(parent_shortcut_id):
            workspace = self._shortcuts.get_agent_workspace(child.get("id"))
            if not workspace or not workspace.get("branch_name"):
                continue
            metadata = {
                "shortcut_id": workspace.get("shortcut_id", child.get("id")),
                "branch": workspace["branch_name"],
                "worktree_path": workspace.get("worktree_path", ""),
                "runtime_state": workspace.get("runtime_state", "stopped"),
                "feature_name": workspace.get("feature_name", ""),
            }
            normalized_path = os.path.normcase(
                os.path.normpath(os.path.abspath(metadata["worktree_path"]))
            ) if metadata["worktree_path"] else ""
            if normalized_path:
                workspace_by_path[normalized_path] = metadata
            workspace_by_branch.setdefault(metadata["branch"], []).append(metadata)

        branch_usage = {}
        for worktree in worktrees:
            branch = worktree.get("branch")
            if not branch:
                continue
            normalized_path = os.path.normcase(
                os.path.normpath(os.path.abspath(worktree.get("worktree_path", "")))
            )
            metadata = workspace_by_path.get(normalized_path)
            if metadata is None:
                matching = workspace_by_branch.get(branch, [])
                metadata = matching[0] if matching else None
            usage = dict(metadata or {})
            usage.update({
                "branch": branch,
                "worktree_path": worktree.get("worktree_path", ""),
                "is_agent_workspace": metadata is not None,
                "is_registered_worktree": True,
                "is_primary_worktree": normalized_path == os.path.normcase(
                    os.path.normpath(os.path.abspath(repository_root))
                ),
            })
            branch_usage.setdefault(branch, []).append(usage)

        # The runtime marker is authoritative for a project that was launched
        # from this application.  A terminal/process can remain active even
        # when Git's worktree registration is temporarily stale or the path
        # was created by an older application version.  Keep those branches in
        # the usage map as well, otherwise the UI loses the red warning and the
        # force-stop button exactly when it is most useful.
        for branch, metadata_entries in workspace_by_branch.items():
            if branch in branch_usage:
                continue
            if not any(entry.get("runtime_state") == "running" for entry in metadata_entries):
                continue
            for metadata in metadata_entries:
                usage = dict(metadata)
                usage.update({
                    "branch": branch,
                    "is_agent_workspace": True,
                    "is_registered_worktree": False,
                })
                branch_usage.setdefault(branch, []).append(usage)

        local_candidates = [branch for branch in branches if branch not in protected]
        remote_candidates = sorted(set(remote_branches))
        # Preserve local-branch ordering, then append remote-only names.  A
        # single checkbox represents both refs when the same name exists in
        # local and remote repositories.
        candidates = local_candidates + [
            branch for branch in remote_candidates if branch not in local_candidates
        ]
        checked_out = set(branch_usage)
        return {
            "repository_root": repository_root,
            "remote_name": remote_name,
            "protected_branches": sorted(protected),
            "branches": candidates,
            "local_non_main_branches": local_candidates,
            "remote_non_main_branches": remote_candidates,
            "checked_out": sorted(branch for branch in local_candidates if branch in checked_out),
            "branch_usage": {
                branch: branch_usage[branch] for branch in local_candidates if branch in branch_usage
            },
        }

    def cleanup_non_main_branches(
        self, parent_shortcut_id: str, branches: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Delete selected non-main branches from both local and remote refs."""
        details = self.get_non_main_branches(parent_shortcut_id)
        requested = set(branches) if branches is not None else set(details["branches"])
        requested &= set(details["branches"])
        local_branches = set(details["local_non_main_branches"])
        remote_branches = set(details["remote_non_main_branches"])
        checked_out = set(details["checked_out"])
        deleted = []
        deleted_remote = []
        skipped = []
        for branch in details["branches"]:
            if branch not in requested:
                continue
            local_exists = branch in local_branches
            remote_exists = branch in remote_branches
            if local_exists and branch in checked_out:
                skipped.append({
                    "branch": branch,
                    "reason": "\u5206\u652f\u5f53\u524d\u6b63\u88ab\u5de5\u4f5c\u533a\u4f7f\u7528\uff0c\u672a\u5220\u9664\u672c\u5730\u6216\u8fdc\u7a0b\u5206\u652f",
                })
                continue
            if local_exists:
                local_result = self._git(
                    details["repository_root"], "branch", "-D", branch, check=False,
                )
                if local_result.returncode != 0:
                    reason = (local_result.stdout or local_result.stderr or "Git \u672c\u5730\u5206\u652f\u5220\u9664\u5931\u8d25").strip()
                    skipped.append({"branch": branch, "reason": reason})
                    continue
                deleted.append(branch)
            if remote_exists:
                remote_result = self._git(
                    details["repository_root"], "push", details["remote_name"],
                    "--delete", branch, check=False,
                )
                if remote_result.returncode == 0:
                    deleted_remote.append(branch)
                else:
                    reason = (remote_result.stdout or remote_result.stderr or "Git \u8fdc\u7a0b\u5206\u652f\u5220\u9664\u5931\u8d25").strip()
                    skipped.append({"branch": branch, "reason": reason})
        return dict(
            details, deleted=deleted, deleted_local=deleted,
            deleted_remote=deleted_remote, skipped=skipped,
        )

    def release_non_main_branch_worktrees(
        self, parent_shortcut_id: str, branch_name: str,
    ) -> Dict[str, Any]:
        """Remove linked worktrees that block later local branch deletion.

        This is deliberately a two-step destructive flow: release the Git
        worktree first, then let the existing branch-cleanup confirmation delete
        the still-present local branch.  Remote refs are never touched.
        """
        branch_name = (branch_name or "").strip()
        details = self.get_non_main_branches(parent_shortcut_id)
        if branch_name not in details["branches"]:
            raise GitWorktreeError("\u53ea\u80fd\u89e3\u9664\u975e\u4e3b\u5206\u652f\u7684\u5de5\u4f5c\u533a\u5360\u7528\u3002")

        usages = details.get("branch_usage", {}).get(branch_name, [])
        if any(usage.get("is_primary_worktree") for usage in usages):
            raise GitWorktreeError(
                "\u8be5\u5206\u652f\u6b63\u88ab\u4e3b\u4ed3\u5e93\u68c0\u51fa\uff1b\u8bf7\u5148\u5728\u4e3b\u4ed3\u5e93\u5207\u6362\u5230\u53d7\u4fdd\u62a4\u5206\u652f\u540e\u518d\u89e3\u9664\u3002"
            )

        # Stop only the project processes owned by managed workspaces.  Unknown
        # Git worktrees have no reliable process ownership marker, but Git can
        # still remove them with --force when no external process locks files.
        terminated_processes = 0
        managed_shortcut_ids = []
        for usage in usages:
            shortcut_id = usage.get("shortcut_id")
            if not shortcut_id or shortcut_id in managed_shortcut_ids:
                continue
            workspace = self._shortcuts.get_agent_workspace(shortcut_id)
            if not workspace:
                continue
            if workspace.get("runtime_state") == "running":
                stopped = self.force_stop_workspace_project(shortcut_id)
                terminated_processes += stopped.get("terminated_processes", 0)
            managed_shortcut_ids.append(shortcut_id)

        registered_usages = [
            usage for usage in usages if usage.get("is_registered_worktree")
        ]
        released_worktrees = []
        for usage in registered_usages:
            worktree_path = usage.get("worktree_path", "")
            result = self._git(
                details["repository_root"], "worktree", "remove", "--force",
                worktree_path, check=False,
            )
            if result.returncode != 0:
                message = (result.stderr or result.stdout or "Git \u5de5\u4f5c\u533a\u5220\u9664\u5931\u8d25").strip()
                raise GitWorktreeError(
                    "\u65e0\u6cd5\u89e3\u9664\u5de5\u4f5c\u533a\u5360\u7528 '{}': {}".format(worktree_path, message)
                )
            released_worktrees.append(worktree_path)

        released_paths = {
            os.path.normcase(os.path.normpath(os.path.abspath(path)))
            for path in released_worktrees
        }
        removed_shortcut_ids = []
        for shortcut_id in managed_shortcut_ids:
            workspace = self._shortcuts.get_agent_workspace(shortcut_id)
            if not workspace:
                continue
            workspace_path = os.path.normcase(
                os.path.normpath(os.path.abspath(workspace.get("worktree_path", "")))
            )
            if workspace_path in released_paths and self._shortcuts.remove_agent_workspace(shortcut_id):
                removed_shortcut_ids.append(shortcut_id)

        return {
            "branch": branch_name,
            "released_worktrees": released_worktrees,
            "removed_shortcuts": len(removed_shortcut_ids),
            "removed_shortcut_ids": removed_shortcut_ids,
            "terminated_processes": terminated_processes,
        }

    def launch_workspace_project(self, shortcut_id: str) -> None:
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            raise GitWorktreeError("选中的快捷入口不是智能体工作区。")
        profile = self._profile(workspace["parent_shortcut_id"])
        script = self._resolve_launch_script(workspace["worktree_path"], profile.get("launch_script", ""))
        extension = os.path.splitext(script)[1].lower()
        if os.name == "nt" and extension in (".bat", ".cmd"):
            command = ["cmd.exe", "/d", "/k", "call", script]
        elif os.name == "nt" and extension == ".ps1":
            command = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", script]
        elif extension == ".py":
            command = [sys.executable, script]
        else:
            command = [script]
        launch_terminal_tab(
            command, workspace["worktree_path"], SCRIPT_TERMINAL_GROUP,
            title="{} - {}".format(workspace.get("feature_name") or "Agent", os.path.basename(script)),
            wrap_in_cmd=False,
        )
        self._shortcuts.update_agent_workspace(shortcut_id, runtime_state="running")

    def mark_workspace_project_stopped(self, shortcut_id: str) -> None:
        """Record explicit terminal shutdown before a destructive lifecycle action."""
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            raise GitWorktreeError("选中的快捷入口不是智能体工作区。")
        self._shortcuts.update_agent_workspace(shortcut_id, runtime_state="stopped")

    @staticmethod
    def _powershell_encoded_command(command: str) -> str:
        return base64.b64encode(command.encode("utf-16le")).decode("ascii")

    def force_stop_workspace_project(self, shortcut_id: str) -> Dict[str, int]:
        """Force-stop the launched script and its child process tree on Windows.

        Windows Terminal does not expose the process ID of a tab it creates.
        The launch script path is therefore used as the stable ownership marker:
        every supported workspace launch command includes that exact path.
        """
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            raise GitWorktreeError("选中的快捷入口不是智能体工作区。")
        if os.name != "nt":
            raise GitWorktreeError("强制关闭本地项目当前仅支持 Windows。")

        profile = self._profile(workspace["parent_shortcut_id"])
        script = self._resolve_launch_script(
            workspace["worktree_path"], profile.get("launch_script", ""),
        )
        # The script path is data, not executable PowerShell text.  Doubling
        # single quotes keeps it a single literal inside the encoded command.
        script_literal = script.replace("'", "''")
        workspace_literal = workspace["worktree_path"].replace("'", "''")
        query = (
            "$ErrorActionPreference = 'Stop'; "
            "$scriptPath = '{}'; "
            "$workspacePath = '{}'; "
            "Get-CimInstance Win32_Process | Where-Object {{ "
            "($_.CommandLine -and ("
            "$_.CommandLine.IndexOf($scriptPath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 "
            "-or $_.CommandLine.IndexOf($workspacePath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0)) "
            "-or ($_.ExecutablePath -and $_.ExecutablePath.IndexOf($workspacePath, "
            "[System.StringComparison]::OrdinalIgnoreCase) -ge 0) "
            "}} | Select-Object -ExpandProperty ProcessId"
        ).format(script_literal, workspace_literal)
        result = self._run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
            self._powershell_encoded_command(query),
        ])
        process_ids = []
        for value in result.stdout.splitlines():
            try:
                process_id = int(value.strip())
            except ValueError:
                continue
            if process_id and process_id != os.getpid() and process_id not in process_ids:
                process_ids.append(process_id)

        for process_id in process_ids:
            # /T is essential for launch scripts that start a server process.
            # A process may exit between discovery and taskkill, so its failure
            # is deliberately non-fatal.
            self._run(["taskkill", "/PID", str(process_id), "/T", "/F"], check=False)

        self._shortcuts.update_agent_workspace(shortcut_id, runtime_state="stopped")
        return {"terminated_processes": len(process_ids)}

    @staticmethod
    def _dirty_workspace_error(status: str, action: str) -> GitWorktreeError:
        """Show the actual Git entries that prevent a lifecycle action."""
        changes = status.strip().splitlines()
        visible_changes = changes[:30]
        details = "\n".join(visible_changes)
        if len(changes) > len(visible_changes):
            details += "\n…还有 {} 项未显示".format(len(changes) - len(visible_changes))
        return GitWorktreeError(
            "工作区仍有未提交或未跟踪文件，不能{}：\n{}"
            "\n（M=修改，A=新增，D=删除，??=未跟踪）".format(action, details)
        )

    def recycle_merged_workspace(self, shortcut_id: str) -> Dict[str, Any]:
        """Return a clean, merged branch to the reusable pool without force deletion."""
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            raise GitWorktreeError("选中的快捷入口不是智能体工作区。")
        if workspace.get("state") != "active":
            raise GitWorktreeError("该工作区当前不处于开发状态。")
        if workspace.get("runtime_state") == "running":
            raise GitWorktreeError("请先关闭该子类启动的本地项目，并标记项目已停止。")
        profile = self._profile(workspace["parent_shortcut_id"])
        base_ref = str(self._sync_and_base_ref(profile))
        path = workspace["worktree_path"]
        status = self._git(path, "status", "--porcelain").stdout
        if status.strip():
            raise self._dirty_workspace_error(status, "回收")
        branch_name = workspace.get("branch_name", "")
        if not branch_name:
            raise GitWorktreeError("工作区缺少功能分支信息，不能安全回收。")
        merged = self._git(path, "merge-base", "--is-ancestor", branch_name, base_ref, check=False)
        if merged.returncode != 0:
            raise GitWorktreeError("尚未确认该功能分支已合并到基线分支。")
        self._git(path, "switch", "--detach", base_ref)
        # ``branch -d`` judges merge state against the repository's current
        # HEAD, which may be unrelated to the configured integration branch.
        # The explicit is-ancestor check above is the authoritative guard, so
        # deletion is now safe even when the parent checkout is on another ref.
        self._git(profile["repository_root"], "branch", "-D", branch_name)
        now = datetime.now().isoformat()
        self._shortcuts.update_agent_workspace(
            shortcut_id, branch_name="", base_ref=base_ref, state="idle",
            feature_name="", runtime_state="stopped", last_recycled_at=now,
        )
        self._shortcuts.update(shortcut_id, title="🤖 空闲工作区")
        removed = self._trim_idle_pool(workspace["parent_shortcut_id"])
        return {"recycled": True, "removed_idle_workspaces": removed}

    def validate_workspace_removal(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Preflight a permanent workspace deletion without mutating anything.

        Deleting an agent child is stricter than returning one to the idle pool:
        its feature branch must already be integrated into the configured base
        branch. A failed preflight leaves the worktree, branch, shortcut entry,
        and metadata untouched.
        """
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            return None
        if workspace.get("runtime_state") == "running":
            raise GitWorktreeError("è¯·åå³é­è¯¥å­ç±»å¯å¨çæ¬å°é¡¹ç®ï¼å¹¶æ è®°é¡¹ç®å·²åæ­¢ã")
        if workspace.get("state") != "active":
            raise GitWorktreeError("è¯¥å·¥ä½åºå½åä¸å¤äºå¼åç¶æã")

        profile = self._profile(workspace["parent_shortcut_id"])
        base_ref = str(self._sync_and_base_ref(profile))
        branch_name = workspace.get("branch_name", "")
        if not branch_name:
            raise GitWorktreeError("å·¥ä½åºç¼ºå°åè½åæ¯ä¿¡æ¯ï¼æ æ³å®å¨å é¤ã")
        merged = self._git(
            profile["repository_root"], "merge-base", "--is-ancestor",
            branch_name, base_ref, check=False,
        )
        if merged.returncode != 0:
            raise GitWorktreeError(
                "功能分支尚未合并到基线分支 {}，无法删除工作区。"
                .format(base_ref)
            )

        path = workspace["worktree_path"]
        if not os.path.isdir(path):
            raise GitWorktreeError("工作区目录不存在，无法安全删除。")

        # ``git worktree remove`` only accepts paths still registered by the
        # parent repository. A prior interrupted cleanup can leave an ordinary
        # Git checkout at the saved path; calling ``worktree remove`` then
        # fails with ``is not a working tree`` and leaves the shortcut stuck.
        # Treat this as a recoverable orphan, but verify its Git state first so
        # cleanup cannot discard local work from an unrelated checkout.
        registration = self._git(
            profile["repository_root"], "worktree", "list", "--porcelain",
        ).stdout
        normalized_path = os.path.normcase(os.path.normpath(os.path.abspath(path)))
        registered_paths = {
            os.path.normcase(os.path.normpath(os.path.abspath(line[9:].strip())))
            for line in registration.splitlines()
            if line.startswith("worktree ")
        }
        is_registered = normalized_path in registered_paths

        status = self._git(path, "status", "--porcelain").stdout
        if status.strip():
            raise self._dirty_workspace_error(status, "删除")
        if not is_registered:
            current_branch = self._git(path, "branch", "--show-current").stdout.strip()
            if current_branch and current_branch != branch_name:
                raise GitWorktreeError(
                    "该目录已不属于父仓库管理的工作区，且当前检出的是其他分支；"
                    "为避免误删，未执行删除。"
                )
        return dict(workspace, _profile=profile, _base_ref=base_ref,
                    _orphaned_worktree=not is_registered)


    def remove_workspace(self, shortcut_id: str) -> None:
        """Permanently delete a merged worktree, branch, and shortcut entry.

        Git must remove the worktree directory before deleting its checked-out
        branch. The application shortcut and metadata are removed only after
        both Git operations have succeeded.
        """
        workspace = self.validate_workspace_removal(shortcut_id)
        if not workspace:
            return
        path = workspace["worktree_path"]
        profile = workspace["_profile"]
        branch_name = workspace["branch_name"]

        if workspace.get("_orphaned_worktree"):
            # The path is a clean Git checkout but no longer a worktree owned
            # by the configured parent. It cannot be removed through Git's
            # worktree command, so delete only this validated recorded path and
            # prune any stale administrative records before branch cleanup.
            def _remove_readonly(func, target, _exc_info):
                # Files in a cloned ``.git/objects`` directory are commonly
                # read-only on Windows. Make only the failing entry writable,
                # then retry the same operation.
                os.chmod(target, stat.S_IWRITE)
                func(target)

            try:
                shutil.rmtree(path, onerror=_remove_readonly)
            except OSError as error:
                raise GitWorktreeError(
                    "无法删除已失效的智能体工作区目录：{}".format(error)
                ) from error
            self._git(profile["repository_root"], "worktree", "prune", check=False)
        else:
            self._git(profile["repository_root"], "worktree", "remove", path)
        # 前面的校验已确认功能分支属于配置的合并基线分支。这里使用
        # ``-D`` 而不是 ``-d``，因为父仓库当前检出的分支可能不同（例如
        # 配置的合并目标是 ``release``，但当前检出的是 ``main``）。
        # 上面的祖先关系校验已经提供安全保障；如果使用 ``-d``，这种情况下
        # 可能会把已经合并的子类功能分支遗留下来。
        branch_result = self._git(
            profile["repository_root"], "branch", "-D", branch_name, check=False,
        )
        if branch_result.returncode != 0:
            branch_exists = self._git(
                profile["repository_root"], "show-ref", "--verify", "--quiet",
                "refs/heads/{}".format(branch_name), check=False,
            ).returncode == 0
            if branch_exists:
                raise GitWorktreeError(
                    "已合并的功能分支无法删除 '{}': {}".format(
                        branch_name, branch_result.stdout.strip(),
                    )
                )
        if not self._shortcuts.remove_agent_workspace(shortcut_id):
            raise GitWorktreeError("Git 工作区已删除，但本地快捷入口记录删除失败。")


    @staticmethod
    def _find_windows_locking_processes(path: str) -> List[int]:
        """Return process IDs holding the exact Windows resource at *path*.

        Restart Manager accepts individual paths, not recursive directory
        searches.  Registering only an arbitrary first batch of files from a
        virtual environment can miss a later extension module such as
        ``charset_normalizer\\cd.pyd``.  Callers therefore pass the exact path
        reported by ``shutil.rmtree`` when deletion fails.
        """
        if os.name != "nt":
            return []

        class _RMUniqueProcess(ctypes.Structure):
            _fields_ = [
                ("dwProcessId", wintypes.DWORD),
                ("ProcessStartTime", wintypes.FILETIME),
            ]

        class _RMProcessInfo(ctypes.Structure):
            _fields_ = [
                ("Process", _RMUniqueProcess),
                ("strAppName", wintypes.WCHAR * 256),
                ("strServiceShortName", wintypes.WCHAR * 64),
                ("ApplicationType", wintypes.DWORD),
                ("AppStatus", wintypes.DWORD),
                ("TSSessionId", wintypes.DWORD),
                ("bRestartable", wintypes.BOOL),
            ]

        try:
            rm = ctypes.WinDLL("Rstrtmgr")
        except OSError:
            return []
        rm.RmStartSession.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, wintypes.LPWSTR]
        rm.RmStartSession.restype = wintypes.DWORD
        rm.RmRegisterResources.argtypes = [
            wintypes.DWORD, wintypes.UINT, ctypes.POINTER(wintypes.LPCWSTR),
            wintypes.UINT, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(wintypes.LPCWSTR),
        ]
        rm.RmRegisterResources.restype = wintypes.DWORD
        rm.RmGetList.argtypes = [
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(_RMProcessInfo), ctypes.POINTER(wintypes.DWORD),
        ]
        rm.RmGetList.restype = wintypes.DWORD
        rm.RmEndSession.argtypes = [wintypes.DWORD]
        rm.RmEndSession.restype = wintypes.DWORD
        session = wintypes.DWORD()
        session_key = ctypes.create_unicode_buffer(33)
        absolute = os.path.abspath(path)
        resource_array = (wintypes.LPCWSTR * 1)(absolute)
        result = rm.RmStartSession(ctypes.byref(session), 0, session_key)
        if result != 0:
            return []
        try:
            result = rm.RmRegisterResources(
                session, 1, resource_array, 0, None, 0, None,
            )
            if result != 0:
                return []
            needed = wintypes.DWORD(0)
            count = wintypes.DWORD(0)
            reboot_reason = wintypes.DWORD(0)
            result = rm.RmGetList(
                session, ctypes.byref(needed), ctypes.byref(count), None,
                ctypes.byref(reboot_reason),
            )
            if result != 234 or not needed.value:
                return []
            processes = (_RMProcessInfo * needed.value)()
            count.value = needed.value
            result = rm.RmGetList(
                session, ctypes.byref(needed), ctypes.byref(count), processes,
                ctypes.byref(reboot_reason),
            )
            if result != 0:
                return []
            return list(dict.fromkeys(
                int(processes[index].Process.dwProcessId)
                for index in range(count.value)
                if processes[index].Process.dwProcessId
            ))
        finally:
            rm.RmEndSession(session)

    def _stop_windows_file_lockers(self, path: str) -> int:
        """Terminate processes holding workspace files, excluding this app."""
        terminated = 0
        for process_id in self._find_windows_locking_processes(path):
            if process_id == os.getpid():
                continue
            result = self._run(
                ["taskkill", "/PID", str(process_id), "/T", "/F"], check=False,
            )
            if result.returncode == 0:
                terminated += 1
        return terminated

    @staticmethod
    def _schedule_windows_delete(path: str) -> bool:
        """Schedule a locked file/directory for deletion at the next reboot."""
        if os.name != "nt":
            return False
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            move_file_ex = kernel32.MoveFileExW
            move_file_ex.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            move_file_ex.restype = wintypes.BOOL
        except OSError:
            return False

        absolute = os.path.abspath(path)
        entries = []
        if os.path.isdir(absolute):
            for root, directories, files in os.walk(absolute, topdown=False):
                entries.extend(os.path.join(root, name) for name in files)
                entries.extend(os.path.join(root, name) for name in directories)
        entries.append(absolute)
        scheduled = False
        for entry in entries:
            if os.path.exists(entry) and move_file_ex(entry, None, 0x00000004):
                scheduled = True
        return scheduled

    @staticmethod
    def _is_windows_lock_error(error: BaseException) -> bool:
        """Whether *error* is a Windows sharing/access violation."""
        return (
            getattr(error, "winerror", None) in (5, 32, 33)
            or getattr(error, "errno", None) == 13
        )

    def _remove_directory_with_readonly_retry(
        self, path: str, defer_on_failure: bool = False,
    ) -> bool:
        """Remove a workspace directory, releasing exact Windows file locks.

        A virtual environment commonly contains far more than 128 files, so a
        broad folder scan is not dependable for locating the process that has a
        native module mapped.  ``rmtree`` exposes the exact entry that failed;
        on a sharing violation, query Restart Manager for that entry, terminate
        its process tree, and retry it immediately before retrying the complete
        directory removal.
        """
        def _make_writable(target: str) -> None:
            try:
                os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass

        lock_targets = {os.path.abspath(path)}

        def _remove_readonly(func, target, exc_info):
            _make_writable(target)
            error = exc_info[1]
            if os.name == "nt" and self._is_windows_lock_error(error):
                exact_target = os.path.abspath(target)
                lock_targets.add(exact_target)
                # ``target`` is the actual locked file (for example the venv's
                # charset_normalizer\cd.pyd), unlike the workspace root which
                # may contain thousands of unrelated files.
                if self._stop_windows_file_lockers(exact_target):
                    # taskkill returning does not guarantee that a mapped .pyd
                    # has been released by the kernel yet.
                    time.sleep(0.15)
            func(target)

        last_error = None
        for attempt in range(5):
            try:
                if os.name == "nt":
                    # First release any known exact failure targets from a prior
                    # attempt.  The root path also covers a process that holds
                    # the directory itself rather than an individual file.
                    for lock_target in tuple(lock_targets):
                        self._stop_windows_file_lockers(lock_target)
                if not os.path.exists(path):
                    return False
                # Git-created files can carry the read-only attribute. Clear it
                # before each retry; this is harmless for normal files.
                for root, directories, files in os.walk(path, topdown=False):
                    for name in files + directories:
                        _make_writable(os.path.join(root, name))
                shutil.rmtree(path, onerror=_remove_readonly)
                return False
            except OSError as error:
                last_error = error
                if not self._is_windows_lock_error(error):
                    break
                time.sleep(0.4 * (attempt + 1))
        if defer_on_failure and self._schedule_windows_delete(path):
            return True
        raise GitWorktreeError(
            "Unable to delete workspace directory after stopping its project. "
            "A process may still be using '{}'; close the project/terminal and retry. ({})".format(
                path, last_error,
            )
        ) from last_error

    def force_remove_workspace(self, shortcut_id: str) -> Dict[str, Any]:
        """Permanently remove a workspace without requiring branch integration.

        This intentionally discards unmerged commits and uncommitted files.
        The UI must obtain an explicit destructive confirmation first.
        """
        workspace = self._shortcuts.get_agent_workspace(shortcut_id)
        if not workspace:
            return {"removed": False, "reason": "not_found"}
        # Do not trust the persisted runtime marker: Windows Terminal or a
        # child Python process can survive after the marker was set to stopped.
        # Force deletion is explicitly destructive, so stop matching processes
        # automatically instead of asking the user to repeat the operation.

        profile = self._shortcuts.get_repository_profile(workspace["parent_shortcut_id"])
        if not profile:
            raise GitWorktreeError("Parent repository configuration was not found.")
        repository_root = profile["repository_root"]
        path = workspace["worktree_path"]
        branch_name = (workspace.get("branch_name") or "").strip()
        cleanup_scheduled = False

        # The runtime marker can be stale when Windows Terminal or a child
        # Python process survived the UI. Stop matching processes even when the
        # marker says "stopped", otherwise files in a virtualenv can remain
        # locked and rmtree fails with WinError 5.
        if os.name == "nt":
            try:
                self.force_stop_workspace_project(shortcut_id)
            except GitWorktreeError:
                # A missing launcher should not prevent cleanup; the directory
                # removal below will still provide the precise lock error.
                pass

        registration = self._git(
            repository_root, "worktree", "list", "--porcelain",
        ).stdout
        normalized_path = os.path.normcase(os.path.normpath(os.path.abspath(path)))
        is_registered = any(
            normalized_path == os.path.normcase(os.path.normpath(os.path.abspath(line[9:].strip())))
            for line in registration.splitlines()
            if line.startswith("worktree ")
        )
        if is_registered:
            remove_result = self._git(
                repository_root, "worktree", "remove", "--force", path, check=False,
            )
            if remove_result.returncode != 0 and os.path.isdir(path):
                cleanup_scheduled = self._remove_directory_with_readonly_retry(
                    path, defer_on_failure=True,
                )
                self._git(repository_root, "worktree", "prune", check=False)
        elif os.path.isdir(path):
            # Handles stale metadata or a separately-cloned checkout that is
            # no longer registered in the parent repository.
            cleanup_scheduled = self._remove_directory_with_readonly_retry(
                path, defer_on_failure=True,
            )
            self._git(repository_root, "worktree", "prune", check=False)

        if branch_name:
            # -D is deliberate: force deletion explicitly discards an
            # unmerged feature branch. Missing branches are already cleaned up.
            branch_result = self._git(
                repository_root, "branch", "-D", branch_name, check=False,
            )
            if branch_result.returncode != 0:
                branch_exists = self._git(
                    repository_root, "show-ref", "--verify", "--quiet",
                    "refs/heads/{}".format(branch_name), check=False,
                ).returncode == 0
                if branch_exists:
                    raise GitWorktreeError(
                        "Force deletion could not remove branch '{}': {}".format(
                            branch_name, branch_result.stdout.strip(),
                        )
                    )
        if not self._shortcuts.remove_agent_workspace(shortcut_id):
            raise GitWorktreeError(
                "Git workspace was deleted, but the shortcut record could not be removed."
            )
        return {
            "removed": True,
            "forced": True,
            "cleanup_scheduled": cleanup_scheduled,
        }


    def _trim_idle_pool(self, parent_shortcut_id: str) -> int:
        idle_workspaces = self._shortcuts.get_idle_agent_workspaces(parent_shortcut_id)
        overflow = max(0, len(idle_workspaces) - self.get_warm_pool_size())
        removed = 0
        for workspace in idle_workspaces[:overflow]:
            profile = self._profile(parent_shortcut_id)
            result = self._git(profile["repository_root"], "worktree", "remove", workspace["worktree_path"], check=False)
            if result.returncode == 0 and self._shortcuts.remove_agent_workspace(workspace["shortcut_id"]):
                removed += 1
        return removed
