from unittest.mock import patch

from services.shortcuts.vscode_workspace_service import VSCodeWorkspaceService


class _DataManager:
    def __init__(self, value="0"):
        self.value = value
        self.saved = []

    def get_config(self, key, default):
        return self.value if self.value is not None else default

    def set_config(self, key, value):
        self.value = value
        self.saved.append((key, value))


def test_vscode_workspace_setting_is_persistent():
    data_manager = _DataManager()
    service = VSCodeWorkspaceService(data_manager)

    assert service.is_enabled() is False
    service.set_enabled(True)
    assert service.is_enabled() is True
    assert data_manager.saved == [(service.CONFIG_KEY, "1")]


def test_add_folder_to_active_workspace_uses_code_add(tmp_path):
    data_manager = _DataManager("1")
    service = VSCodeWorkspaceService(data_manager)
    executable = str(tmp_path / "code.cmd")

    with patch.object(service, "_resolve_code_command", return_value=executable), \
         patch("services.shortcuts.vscode_workspace_service.subprocess.Popen") as popen:
        result = service.add_folder_to_workspace(str(tmp_path))

    assert result["folder"] == str(tmp_path)
    args, kwargs = popen.call_args
    assert args[0] == [executable, "--add", str(tmp_path)]
    assert kwargs["cwd"] == str(tmp_path)


def test_remove_folder_from_active_workspace_uses_code_remove(tmp_path):
    service = VSCodeWorkspaceService(_DataManager("0"))

    with patch.object(service, "_resolve_code_command", return_value="code"), \
         patch("services.shortcuts.vscode_workspace_service.subprocess.Popen") as popen:
        result = service.remove_folder_from_workspace(str(tmp_path))

    assert result["folder"] == str(tmp_path)
    assert popen.call_args.args[0] == ["code", "--remove", str(tmp_path)]


def test_file_shortcut_adds_its_parent_folder(tmp_path):
    file_path = tmp_path / "launch.py"
    file_path.write_text("print('ok')", encoding="utf-8")
    service = VSCodeWorkspaceService(_DataManager("1"))

    with patch.object(service, "_resolve_code_command", return_value="code"), \
         patch("services.shortcuts.vscode_workspace_service.subprocess.Popen") as popen:
        service.add_folder_to_workspace(str(file_path))

    assert popen.call_args.args[0] == ["code", "--add", str(tmp_path)]
