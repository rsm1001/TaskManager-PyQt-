"""快捷入口终端启动与表格渲染的回归测试。"""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidget

import config.config as config
from services.shortcuts import shortcut_table_service
import services.shortcuts.terminal_service as terminal_service


def test_cli_path_uses_windows_npm_shim_when_path_is_missing(monkeypatch, tmp_path):
    """Desktop-launched processes may miss npm from PATH but still have APPDATA."""
    npm_directory = tmp_path / "Roaming" / "npm"
    npm_directory.mkdir(parents=True)
    codex_shim = npm_directory / "codex.cmd"
    codex_shim.write_text("@echo off", encoding="utf-8")

    monkeypatch.setattr(shortcut_table_service.shutil, "which", lambda _command: None)
    monkeypatch.setenv("APPDATA", str(npm_directory.parent))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert shortcut_table_service._get_codex_path() == str(codex_shim)


def test_missing_codex_does_not_open_terminal(monkeypatch, tmp_path):
    """A missing CLI should produce an actionable UI message, not CMD's vague error."""
    monkeypatch.setattr(shortcut_table_service, "_build_codex_command", lambda: None)

    with patch.object(shortcut_table_service.QMessageBox, "warning") as warning, \
         patch.object(shortcut_table_service.subprocess, "Popen") as popen:
        shortcut_table_service._open_codex_in_terminal(str(tmp_path))

    warning.assert_called_once()
    assert "Codex" in warning.call_args.args[1]
    popen.assert_not_called()


def test_codex_bypass_command_uses_supported_flag(monkeypatch):
    """启用放权开关时使用 Codex 支持的参数。"""
    monkeypatch.setattr(shortcut_table_service, "_get_codex_path", lambda: "codex.exe")
    monkeypatch.setattr(shortcut_table_service, "_is_codex_skip_permissions_enabled", lambda: True)

    assert shortcut_table_service._build_codex_command() == [
        "codex.exe",
        config.CODEX_DANGEROUS_SKIP_PERMISSIONS_FLAG,
    ]


def test_codex_terminal_uses_cwd_for_directory_with_cmd_metacharacters(monkeypatch, tmp_path):
    """目录中的 CMD 元字符不能进入命令文本。"""
    target_dir = tmp_path / "R&D"
    target_dir.mkdir()
    target_dir = str(target_dir)
    monkeypatch.setattr(shortcut_table_service.os.path, "isfile", lambda _path: False)
    monkeypatch.setattr(terminal_service, "get_windows_terminal_path", lambda: None)
    monkeypatch.setattr(shortcut_table_service, "_build_codex_command", lambda: ["codex.exe", "--test"])

    with patch.object(shortcut_table_service.subprocess, "Popen") as popen:
        shortcut_table_service._open_codex_in_terminal(target_dir)

    args, kwargs = popen.call_args
    assert args[0] == ["cmd.exe", "/k", "codex.exe", "--test"]
    assert kwargs["cwd"] == target_dir
    assert all("cd /d" not in value for value in args[0])


def test_codex_terminal_uses_parent_for_missing_script_shortcut(monkeypatch, tmp_path):
    """A missing script must not be passed to CreateProcess as its working directory."""
    script_path = tmp_path / "start.bat"
    monkeypatch.setattr(shortcut_table_service, "_build_codex_command", lambda: ["codex.exe"])

    with patch.object(shortcut_table_service.subprocess, "Popen") as popen:
        shortcut_table_service._open_codex_in_terminal(str(script_path))

    assert popen.call_args.kwargs["cwd"] == str(tmp_path)


def test_terminal_uses_nearest_existing_parent_for_missing_directory(tmp_path):
    """A stale shortcut directory must not be passed to subprocess as cwd."""
    missing_directory = tmp_path / "missing-project" / "nested"

    assert shortcut_table_service._get_existing_terminal_directory(str(missing_directory)) == str(tmp_path)


def test_script_shortcut_runs_batch_file_in_its_directory(monkeypatch):
    """Script shortcuts must run the selected batch file rather than Claude."""
    script_path = os.path.abspath(os.path.join("R&D", "run.cmd"))
    monkeypatch.setattr(terminal_service, "get_windows_terminal_path", lambda: None)
    with patch.object(shortcut_table_service.subprocess, "Popen") as popen:
        shortcut_table_service._open_shortcut_path(script_path, "script")

    args, kwargs = popen.call_args
    assert args[0] == ["cmd.exe", "/d", "/c", "call", script_path]
    assert kwargs["cwd"] == os.path.dirname(script_path)


def test_script_environment_makes_current_python_discoverable():
    environment = shortcut_table_service._get_script_environment()
    python_directory = os.path.dirname(sys.executable)
    path_key = next(key for key in environment if key.upper() == 'PATH')

    assert python_directory in environment[path_key].split(os.pathsep)


def test_shortcut_row_keeps_path_and_created_at_in_separate_columns():
    """路径与创建日期不能互相覆盖。"""
    app = QApplication.instance() or QApplication([])
    table = QTableWidget(1, 7)
    shortcut_table_service.render_shortcut_row(
        table,
        0,
        {
            "id": "shortcut-1",
            "title": "工作目录",
            "shortcut_path": r"C:\Work\R&D",
            "task_type": "shortcut",
            "tags": "工作",
            "created_at": "2026-07-26T10:30:00",
        },
    )

    assert table.item(0, 5).text() == r"C:\Work\R&D"
    assert table.item(0, 6).text() == "2026-07-26 10:30"
    table.deleteLater()
    app.processEvents()



def test_open_shortcut_path_returns_false_when_os_rejects_open(monkeypatch):
    monkeypatch.setattr(shortcut_table_service.os.path, 'isfile', lambda _path: False)
    monkeypatch.setattr(shortcut_table_service.os.path, 'isdir', lambda _path: False)
    monkeypatch.setattr(shortcut_table_service.QDesktopServices, 'openUrl', lambda _url: False)

    assert shortcut_table_service._open_shortcut_path('/tmp/unhandled.path', 'open') is False
