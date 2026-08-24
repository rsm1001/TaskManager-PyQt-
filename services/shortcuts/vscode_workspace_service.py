"""Small adapter for adding shortcut folders to the active VS Code window."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any, Dict, Optional

import config.config as app_config

logger = logging.getLogger(__name__)


class VSCodeWorkspaceError(RuntimeError):
    """A user-displayable VS Code integration failure."""


class VSCodeWorkspaceService:
    """Persist the opt-in switch and invoke VS Code's ``code --add`` CLI."""

    CONFIG_KEY = app_config.VSCODE_ADD_TO_WORKSPACE_KEY
    DEFAULT_ENABLED = app_config.VSCODE_ADD_TO_WORKSPACE_DEFAULT

    def __init__(self, data_manager: Any) -> None:
        self._data_manager = data_manager

    def is_enabled(self) -> bool:
        value = self._data_manager.get_config(
            self.CONFIG_KEY, "1" if self.DEFAULT_ENABLED else "0",
        )
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def set_enabled(self, enabled: bool) -> None:
        self._data_manager.set_config(
            self.CONFIG_KEY, "1" if bool(enabled) else "0",
        )

    @staticmethod
    def _resolve_code_command() -> Optional[str]:
        """Find the VS Code CLI, including common Windows install locations."""
        for command in ("code", "code.cmd"):
            resolved = shutil.which(command)
            if resolved:
                return resolved

        if os.name != "nt":
            return None

        candidates = []
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                os.path.join(local_app_data, "Programs", "Microsoft VS Code", "bin", "code.cmd")
            )
        for program_files_key in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            program_files = os.environ.get(program_files_key)
            if program_files:
                candidates.append(
                    os.path.join(program_files, "Microsoft VS Code", "bin", "code.cmd")
                )
        portable_root = os.environ.get("VSCODE_PORTABLE")
        if portable_root:
            candidates.append(os.path.join(portable_root, "bin", "code.cmd"))

        return next((path for path in candidates if os.path.isfile(path)), None)

    @staticmethod
    def _folder_for_path(path: str) -> str:
        candidate = os.path.abspath(os.path.expanduser(str(path or "").strip()))
        if os.path.isdir(candidate):
            return candidate
        if os.path.isfile(candidate):
            return os.path.dirname(candidate)
        raise VSCodeWorkspaceError("快捷入口路径不是现有文件夹，无法加入 VS Code 工作区。")

    def add_folder_to_workspace_if_enabled(self, path: str) -> Optional[Dict[str, str]]:
        """Add a folder only when the persisted opt-in switch is enabled."""
        if not self.is_enabled():
            return None
        return self.add_folder_to_workspace(path)

    def add_folder_to_workspace(self, path: str) -> Dict[str, str]:
        """Add a shortcut's directory to the currently active VS Code window."""
        return self._run_workspace_command("--add", path)

    def remove_folder_from_workspace(self, path: str) -> Dict[str, str]:
        """Remove a shortcut's directory from the currently active VS Code window."""
        return self._run_workspace_command("--remove", path)

    def _run_workspace_command(self, option: str, path: str) -> Dict[str, str]:
        folder = self._folder_for_path(path)
        executable = self._resolve_code_command()
        if not executable:
            raise VSCodeWorkspaceError(
                "未找到 VS Code 命令行工具 code；请在 VS Code 中安装/启用 shell command 后重试。"
            )

        command = [executable, option, folder]
        try:
            popen_kwargs = {
                "cwd": folder,
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "close_fds": os.name != "nt",
            }
            # Do not let the Windows command shim briefly create a console
            # window and steal focus from the task manager.
            if os.name == "nt":
                popen_kwargs["creationflags"] = getattr(
                    subprocess, "CREATE_NO_WINDOW", 0,
                )
            subprocess.Popen(command, **popen_kwargs)
        except OSError as error:
            raise VSCodeWorkspaceError("启动 VS Code 命令行失败：{}".format(error)) from error

        operation = "Added" if option == "--add" else "Removed"
        logger.info("%s shortcut folder %s VS Code workspace: %s", operation, option, folder)
        return {"folder": folder, "executable": executable}
