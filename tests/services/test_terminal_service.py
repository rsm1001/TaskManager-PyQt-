"""Tests for the grouped Windows Terminal launcher."""

from unittest.mock import Mock

from services.shortcuts import terminal_service


def test_build_windows_terminal_command_uses_named_window_and_new_tab(tmp_path, monkeypatch):
    monkeypatch.setattr(terminal_service, "get_windows_terminal_path", lambda: "wt.exe")

    command = terminal_service.build_windows_terminal_command(
        ["claude.exe", "--flag"],
        str(tmp_path),
        terminal_service.AGENT_TERMINAL_GROUP,
        title="Claude - project",
    )

    assert command == [
        "wt.exe",
        "--window",
        "TaskManager-Agents",
        "new-tab",
        "--title",
        "Claude - project",
        "--startingDirectory",
        str(tmp_path),
        "claude.exe",
        "--flag",
    ]


def test_launch_terminal_tab_keeps_agent_and_script_groups_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(terminal_service, "get_windows_terminal_path", lambda: "wt.exe")
    popen = Mock()

    terminal_service.launch_terminal_tab(
        ["claude.exe"],
        str(tmp_path),
        terminal_service.AGENT_TERMINAL_GROUP,
        title="Claude",
        popen=popen,
    )
    terminal_service.launch_terminal_tab(
        ["python.exe", "job.py"],
        str(tmp_path),
        terminal_service.SCRIPT_TERMINAL_GROUP,
        title="Script",
        popen=popen,
    )

    agent_command = popen.call_args_list[0].args[0]
    script_command = popen.call_args_list[1].args[0]
    assert agent_command[2] == "TaskManager-Agents"
    assert script_command[2] == "TaskManager-Scripts"
    assert agent_command[3] == "new-tab"
    assert script_command[3] == "new-tab"
    assert agent_command[-4:] == ["cmd.exe", "/d", "/k", "claude.exe"]
    assert script_command[-2:] == ["python.exe", "job.py"]


def test_windows_fallback_keeps_legacy_cmd_launch_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(terminal_service, "get_windows_terminal_path", lambda: None)
    popen = Mock()

    terminal_service.launch_terminal_tab(
        ["claude.exe"],
        str(tmp_path),
        terminal_service.AGENT_TERMINAL_GROUP,
        popen=popen,
    )

    assert popen.call_args.args[0] == ["cmd.exe", "/k", "claude.exe"]
    assert popen.call_args.kwargs["cwd"] == str(tmp_path)
