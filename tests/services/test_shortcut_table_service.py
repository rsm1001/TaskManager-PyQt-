"""快捷入口终端启动与表格渲染的回归测试。"""

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidget

import config.config as config
from services import shortcut_table_service


def test_codex_bypass_command_uses_supported_flag(monkeypatch):
    """启用放权开关时使用 Codex 支持的参数。"""
    monkeypatch.setattr(shortcut_table_service, "_get_codex_path", lambda: "codex.exe")
    monkeypatch.setattr(shortcut_table_service, "_is_codex_skip_permissions_enabled", lambda: True)

    assert shortcut_table_service._build_codex_command() == [
        "codex.exe",
        config.CODEX_DANGEROUS_SKIP_PERMISSIONS_FLAG,
    ]


def test_codex_terminal_uses_cwd_for_directory_with_cmd_metacharacters(monkeypatch):
    """目录中的 CMD 元字符不能进入命令文本。"""
    target_dir = os.path.abspath("R&D")
    monkeypatch.setattr(shortcut_table_service.os.path, "isfile", lambda _path: False)
    monkeypatch.setattr(shortcut_table_service, "_build_codex_command", lambda: ["codex.exe", "--test"])

    with patch.object(shortcut_table_service.subprocess, "Popen") as popen:
        shortcut_table_service._open_codex_in_terminal(target_dir)

    args, kwargs = popen.call_args
    assert args[0] == ["cmd.exe", "/k", "codex.exe", "--test"]
    assert kwargs["cwd"] == target_dir
    assert all("cd /d" not in value for value in args[0])


def test_script_shortcut_launches_claude_with_argument_list(monkeypatch):
    """脚本快捷入口不能将 Python 列表字符串传入 CMD。"""
    script_path = os.path.abspath(os.path.join("R&D", "run.cmd"))
    launched = []
    monkeypatch.setattr(shortcut_table_service, "_build_claude_command", lambda: ["claude.exe", "--test"])
    monkeypatch.setattr(
        shortcut_table_service,
        "_launch_terminal",
        lambda directory, command: launched.append((directory, command)),
    )

    shortcut_table_service._open_shortcut_path(script_path, "script")

    assert launched == [(os.path.dirname(script_path), ["claude.exe", "--test"])]


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
