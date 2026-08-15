from unittest.mock import patch

from services.shortcuts import shortcut_operation_service
from services.shortcuts.shortcut_operation_service import ShortcutOperationService


class _DataManager:
    def get_all_shortcuts(self):
        return [{
            'id': 'shortcut-script',
            'title': 'PowerShell script',
            'shortcut_path': r'C:\work\launch.ps1',
            'action_type': 'script',
        }]

    def add_or_update_history(self, *args):
        return True


def test_shortcut_operation_service_uses_shared_script_launcher():
    service = ShortcutOperationService(_DataManager())

    with patch('services.shortcuts.shortcut_table_service._open_shortcut_path') as launcher:
        result = service.open_shortcut('shortcut-script')

    assert result['success'] is True
    launcher.assert_called_once_with(r'C:\work\launch.ps1', 'script')



def test_shortcut_operation_service_runs_posix_scripts_through_bash(monkeypatch):
    service = ShortcutOperationService(_DataManager())
    monkeypatch.setattr(shortcut_operation_service.sys, 'platform', 'linux')

    with patch.object(shortcut_operation_service.subprocess, 'Popen') as popen, \
         patch('services.shortcuts.shortcut_table_service._open_shortcut_path') as shared_launcher:
        service._open_shortcut_path('/tmp/launch.sh', 'script')

    popen.assert_called_once_with(['bash', '/tmp/launch.sh'], cwd='/tmp')
    shared_launcher.assert_not_called()



def test_shortcut_operation_service_reports_rejected_os_open():
    class OpenDataManager(_DataManager):
        def get_all_shortcuts(self):
            return [{
                'id': 'shortcut-open',
                'title': 'Unregistered file',
                'shortcut_path': r'C:\work\unknown.file',
                'action_type': 'open',
            }]

        def __init__(self):
            self.history_calls = 0

        def add_or_update_history(self, *args):
            self.history_calls += 1
            return True

    data_manager = OpenDataManager()
    service = ShortcutOperationService(data_manager)
    with patch('services.shortcuts.shortcut_table_service._open_shortcut_path', return_value=False):
        result = service.open_shortcut('shortcut-open')

    assert result['success'] is False
    assert 'The operating system rejected' in result['message']
    assert data_manager.history_calls == 0
