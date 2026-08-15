"""终端分组与标签页启动服务。

Windows 优先使用 Windows Terminal 的命名窗口和标签页：
- agents 组承载 Claude Code 与 Codex；
- scripts 组承载程序脚本。

当 Windows Terminal 不存在时，自动回退到原生 CMD/系统终端，保证旧环境仍可启动。
本模块只负责进程启动，不依赖 PyQt，便于单元测试和后续替换终端实现。
"""

import logging
import os
import shutil
import subprocess
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

AGENT_TERMINAL_GROUP = "agents"
SCRIPT_TERMINAL_GROUP = "scripts"

# Windows Terminal 的命名窗口 ID。命名窗口可以让不同次 wt.exe 调用复用同一个窗口，
# 但仍通过 new-tab 创建独立标签页。
TERMINAL_WINDOW_IDS = {
    AGENT_TERMINAL_GROUP: "TaskManager-Agents",
    SCRIPT_TERMINAL_GROUP: "TaskManager-Scripts",
}

PopenFactory = Callable[..., object]


def get_windows_terminal_path() -> Optional[str]:
    """查找 Windows Terminal 的 wt.exe；找不到时返回 None。"""
    if os.name != "nt":
        return None

    for command_name in ("wt.exe", "wt"):
        path = shutil.which(command_name)
        if path:
            return path

    # 从资源管理器启动时 PATH 可能未包含 WindowsApps，显式探测系统别名目录。
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidate = os.path.join(local_appdata, "Microsoft", "WindowsApps", "wt.exe")
        if os.path.isfile(candidate):
            return candidate

    return None


def _normalise_title(title: Optional[str], working_directory: str) -> str:
    if title and title.strip():
        return title.strip()
    folder_name = os.path.basename(os.path.normpath(working_directory))
    return folder_name or "TaskManager"


def build_windows_terminal_command(
    command: List[str],
    working_directory: str,
    group: str,
    title: Optional[str] = None,
    terminal_path: Optional[str] = None,
) -> Optional[List[str]]:
    """构造一个复用分组窗口并新建标签页的 wt.exe 命令。"""
    terminal_path = terminal_path or get_windows_terminal_path()
    window_id = TERMINAL_WINDOW_IDS.get(group)
    if not terminal_path or not window_id:
        return None

    return [
        terminal_path,
        "--window",
        window_id,
        "new-tab",
        "--title",
        _normalise_title(title, working_directory),
        "--startingDirectory",
        working_directory,
        *command,
    ]


def launch_terminal_tab(
    command: List[str],
    working_directory: str,
    group: str,
    title: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    popen: Optional[PopenFactory] = None,
    wrap_in_cmd: bool = True,
) -> object:
    """在指定分组的 Windows Terminal 标签页中启动命令。

    没有 Windows Terminal 时回退到原生 CMD 新窗口（Windows）或当前终端（POSIX）。
    ``popen`` 参数仅用于测试，生产环境默认使用 ``subprocess.Popen``。
    """
    popen = popen or subprocess.Popen
    working_directory = os.path.abspath(working_directory)
    terminal_payload = command
    if os.name == "nt" and wrap_in_cmd:
        # Keep agent tabs as real CMD sessions so interactive CLI state remains
        # visible after the CLI exits and the user can continue typing there.
        terminal_payload = ["cmd.exe", "/d", "/k", *command]
    wt_command = build_windows_terminal_command(
        terminal_payload,
        working_directory,
        group,
        title=title,
    )

    if wt_command:
        logger.info(
            "在 Windows Terminal 分组窗口中启动标签页 group=%s cwd=%s command=%s",
            group,
            working_directory,
            command,
        )
        kwargs = {"cwd": working_directory}
        if env is not None:
            kwargs["env"] = env
        return popen(wt_command, **kwargs)

    logger.info(
        "未找到 Windows Terminal，回退到原生终端 group=%s cwd=%s command=%s",
        group,
        working_directory,
        command,
    )
    if os.name == "nt":
        fallback_command = ["cmd.exe", "/k", *command] if wrap_in_cmd else command
        kwargs = {
            "cwd": working_directory,
            "creationflags": getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        }
        if env is not None:
            kwargs["env"] = env
        return popen(fallback_command, **kwargs)

    kwargs = {"cwd": working_directory}
    if env is not None:
        kwargs["env"] = env
    return popen(command, **kwargs)
