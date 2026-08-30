import json
import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem

from components.main_window.shortcut_tree import DraggableShortcutTree
from handlers.json_handler import JsonExportImportHandler
from managers.shortcuts.shortcut_manager import ShortcutManager
from models.model import init_db
from services.shortcuts.shortcut_table_service import render_shortcut_tree_item
from ui.main_window.task_actions import MainWindowTaskActionsMixin


def test_legacy_shortcut_schema_migrates_to_root_entries():
    connection = sqlite3.connect(":memory:")
    connection.execute("""
        CREATE TABLE shortcut_entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            shortcut_path TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'todo',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            action_type TEXT NOT NULL DEFAULT 'open'
        )
    """)
    connection.execute(
        "INSERT INTO shortcut_entries (id, title, shortcut_path, created_at, updated_at) "
        "VALUES ('root', 'Root', '/tmp/root', '2026-01-01', '2026-01-01')"
    )
    manager = ShortcutManager(connection=connection)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(shortcut_entries)")
    }
    assert {'parent_id', 'order_index'} <= columns
    assert manager.get_by_id('root')['parent_id'] is None
    connection.close()


def test_shortcut_hierarchy_crud_and_parent_validation():
    connection = sqlite3.connect(":memory:")
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Root', '/tmp/root')
    root = manager.get_all()[0]
    assert manager.create('todo', 'Child', '/tmp/child', parent_id=root['id'])
    child = manager.get_children(root['id'])[0]
    assert child['parent_id'] == root['id']
    assert not manager.create('todo', 'Grandchild', '/tmp/grandchild', parent_id=child['id'])
    assert not manager.update(root['id'], parent_id=child['id'])
    assert manager.update(child['id'], parent_id=None)
    assert manager.get_by_id(child['id'])['parent_id'] is None
    connection.close()


def test_tree_widget_starts_expanded_and_keeps_child_items():
    app = QApplication.instance() or QApplication([])
    tree = DraggableShortcutTree()
    tree.setColumnCount(7)
    root = QTreeWidgetItem(tree)
    render_shortcut_tree_item(
        tree, root,
        {'id': 'root', 'title': 'Root', 'shortcut_path': '/tmp/root',
         'action_type': 'open', 'tags': '', 'parent_id': None, 'created_at': '-'}
    )
    child = QTreeWidgetItem(root)
    render_shortcut_tree_item(
        tree, child,
        {'id': 'child', 'title': 'Child', 'shortcut_path': '/tmp/child',
         'action_type': 'open', 'tags': '', 'parent_id': 'root', 'created_at': '-'}
    )
    root.setExpanded(True)
    assert tree.topLevelItemCount() == 1
    assert tree.rowCount() == 2
    root.setExpanded(False)
    assert tree.rowCount() == 1
    assert tree.find_item_by_id('child') is child
    tree.deleteLater()
    app.processEvents()


def test_force_delete_workspace_lock_error_shows_recovery_steps_without_paths():
    raw_message = (
        "Unable to delete workspace directory after stopping its project. "
        "A process may still be using 'C:\\private\\workspace\\.venv\\Lib\\site-packages\\charset_normalizer\\cd.pyd'."
    )

    message = MainWindowTaskActionsMixin._format_force_delete_workspace_failure(raw_message)

    assert '\u5173\u95ed\u8be5\u5de5\u4f5c\u533a\u7684\u7ec8\u7aef' in message
    assert '\u7ba1\u7406\u5458\u8eab\u4efd\u91cd\u65b0\u6253\u5f00\u672c\u7a0b\u5e8f' in message
    assert 'C:\\private' not in message
    assert 'cd.pyd' not in message


def test_workspace_name_uses_workspace_launcher_instead_of_opening_its_directory(monkeypatch):
    app = QApplication.instance() or QApplication([])
    tree = DraggableShortcutTree()
    tree.setColumnCount(7)
    item = QTreeWidgetItem(tree)
    launched = []
    opened = []
    monkeypatch.setattr(
        'services.shortcuts.shortcut_table_service._open_shortcut_path',
        lambda *args: opened.append(args) or True,
    )
    render_shortcut_tree_item(
        tree, item,
        {'id': 'workspace', 'title': 'Child', 'shortcut_path': '/tmp/worktree',
         'action_type': 'open', 'category': 'workspace', 'tags': '',
         'parent_id': 'root', 'created_at': '-'},
        on_workspace_launch_callback=lambda data: launched.append(data['id']),
    )

    tree.itemWidget(item, 0).click()

    assert launched == ['workspace']
    assert opened == []
    tree.deleteLater()
    app.processEvents()


def test_workspace_open_action_uses_workspace_launcher_before_refreshing_history():
    app = QApplication.instance() or QApplication([])
    events = []

    class WorkspaceService:
        def get_workspace(self, shortcut_id):
            events.append(('get_workspace', shortcut_id))
            return {'id': shortcut_id}

        def launch_workspace_project(self, shortcut_id):
            events.append(('launch_workspace_project', shortcut_id))

    class ShortcutService:
        def open_shortcut(self, shortcut_id):
            events.append(('open_shortcut', shortcut_id))

    class Window(MainWindowTaskActionsMixin):
        def __init__(self):
            self.shortcuts_table = DraggableShortcutTree()
            item = QTreeWidgetItem(self.shortcuts_table)
            item.setData(0, Qt.ItemDataRole.UserRole, 'workspace')
            item.setData(
                0, Qt.ItemDataRole.UserRole + 1,
                {'id': 'workspace', 'category': 'workspace'},
            )
            self.shortcuts_table.setCurrentItem(item)

        def _workspace_service(self):
            return WorkspaceService()

        def _shortcut_service(self):
            return ShortcutService()

        def load_shortcuts_history(self):
            events.append(('load_history', None))

        def _update_history_limit_label(self):
            events.append(('update_history_limit', None))

    window = Window()
    window.open_shortcut()

    assert events == [
        ('launch_workspace_project', 'workspace'),
        ('load_history', None),
        ('update_history_limit', None),
    ]
    window.shortcuts_table.deleteLater()
    app.processEvents()


def test_json_roundtrip_preserves_parent_relationship(tmp_path):
    db_path = str(tmp_path / "shortcuts.db")
    export_path = str(tmp_path / "shortcuts.json")
    connection = sqlite3.connect(db_path)
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Root', '/tmp/root')
    root = manager.get_all()[0]
    assert manager.create('todo', 'Child', '/tmp/child', parent_id=root['id'])

    engine, session_factory = init_db(db_path, run_migration=True)
    session = session_factory()
    handler = JsonExportImportHandler(session, manager)
    assert handler.export_to_json(export_path)
    with open(export_path, encoding='utf-8') as stream:
        exported = json.load(stream)
    assert any(item.get('parent_id') == root['id'] for item in exported['shortcuts'])

    assert handler.import_from_json(export_path)
    assert len(manager.get_tree()) == 2
    assert len(manager.get_children(root['id'])) == 1

    session.close()
    engine.dispose()
    connection.close()


def test_json_import_failure_restores_existing_data(tmp_path):
    db_path = str(tmp_path / "rollback.db")
    bad_path = str(tmp_path / "invalid.json")
    connection = sqlite3.connect(db_path)
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Existing', '/tmp/existing')
    existing = manager.get_all()[0]

    engine, session_factory = init_db(db_path, run_migration=True)
    session = session_factory()
    handler = JsonExportImportHandler(session, manager)
    with open(bad_path, 'w', encoding='utf-8') as stream:
        json.dump({
            'todo': [
                {'id': 'duplicate', 'title': 'one'},
                {'id': 'duplicate', 'title': 'two'},
            ],
            'shortcuts': [
                {'id': 'new', 'title': 'New', 'shortcut_path': '/tmp/new'},
            ],
        }, stream)

    assert handler.import_from_json(bad_path) is False
    assert manager.get_by_id(existing['id']) is not None

    session.close()
    engine.dispose()
    connection.close()


def test_individual_child_restore_keeps_existing_parent():
    connection = sqlite3.connect(":memory:")
    manager = ShortcutManager(connection=connection)
    manager.create('todo', 'Root', '/tmp/root')
    root = manager.get_all()[0]
    manager.create('todo', 'Child', '/tmp/child', parent_id=root['id'])
    child = manager.get_children(root['id'])[0]

    from services.domain.trash_restoration_service import TrashRestorationService
    service = TrashRestorationService(None, manager, None, None, None, None, None)
    manager.delete_tree(child['id'])
    assert service._restore_shortcut('trash-id', child)
    assert manager.get_by_id(child['id'])['parent_id'] == root['id']
    connection.close()


def test_restored_repository_shortcut_keeps_its_git_profile():
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    manager.create('todo', 'Repository', '/tmp/repository')
    root = manager.get_all()[0]
    manager.save_repository_profile(
        root['id'], '/tmp/repository', 'origin', 'origin/main', 'launch.py',
    )
    deleted = manager.delete_tree(root['id'])
    assert deleted[0]['_repository_profile']['launch_script'] == 'launch.py'

    from services.domain.trash_restoration_service import TrashRestorationService
    service = TrashRestorationService(None, manager, None, None, None, None, None)
    assert service._restore_shortcut('trash-id', deleted[0])

    profile = manager.get_repository_profile(root['id'])
    assert profile['repository_root'] == '/tmp/repository'
    assert profile['base_ref'] == 'origin/main'
    assert profile['launch_script'] == 'launch.py'
    connection.close()


def test_json_replacement_clears_agent_workspace_metadata(tmp_path):
    db_path = str(tmp_path / 'shortcuts.db')
    export_path = str(tmp_path / 'shortcuts.json')
    connection = sqlite3.connect(db_path)
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', '/tmp/repository')
    root = manager.get_all()[0]
    manager.save_repository_profile(root['id'], '/tmp/repository', launch_script='launch.py')
    workspace = manager.create_agent_workspace(
        root['id'], 'Agent', '/tmp/worktree', 'agent/test', 'origin/main', 'test',
    )

    engine, session_factory = init_db(db_path, run_migration=True)
    session = session_factory()
    handler = JsonExportImportHandler(session, manager)
    assert handler.export_to_json(export_path)
    assert handler.import_from_json(export_path)

    assert manager.get_repository_profile(root['id']) is None
    assert manager.get_agent_workspace(workspace['id']) is None
    session.close()
    engine.dispose()
    connection.close()


def test_agent_workspace_rejects_generic_path_or_parent_changes():
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', '/tmp/repository')
    root = manager.get_all()[0]
    workspace = manager.create_agent_workspace(
        root['id'], 'Agent', '/tmp/worktree', 'agent/test', 'origin/main', 'test',
    )

    assert not manager.update(workspace['id'], shortcut_path='/tmp/other-worktree')
    assert not manager.update(workspace['id'], parent_id=None)
    current = manager.get_by_id(workspace['id'])
    metadata = manager.get_agent_workspace(workspace['id'])
    assert current['shortcut_path'] == metadata['worktree_path'] == '/tmp/worktree'
    assert current['parent_id'] == metadata['parent_shortcut_id'] == root['id']
    connection.close()


def test_root_deletion_preflights_every_workspace_before_removing_any():
    from types import SimpleNamespace
    from unittest.mock import Mock, patch
    from PyQt6.QtWidgets import QMessageBox
    from services.application.task_operations.shortcut_operations import ShortcutOperations

    root = {'id': 'root', 'parent_id': None}
    child_a = {'id': 'child-a', 'parent_id': 'root'}
    child_b = {'id': 'child-b', 'parent_id': 'root'}

    class WorkspaceService:
        def __init__(self):
            self.validated = []
            self.removed = []

        def get_workspace(self, shortcut_id):
            return {'shortcut_id': shortcut_id} if shortcut_id.startswith('child-') else None

        def validate_workspace_removal(self, shortcut_id):
            self.validated.append(shortcut_id)
            if shortcut_id == 'child-b':
                raise RuntimeError('child-b is dirty')

        def remove_workspace(self, shortcut_id):
            self.removed.append(shortcut_id)

    workspace_service = WorkspaceService()
    data_manager = SimpleNamespace(
        _service_factory=SimpleNamespace(get_git_worktree_service=lambda: workspace_service),
        get_shortcut_children=Mock(return_value=[child_a, child_b]),
        delete_shortcut=Mock(),
    )
    window = SimpleNamespace(
        shortcuts_table=SimpleNamespace(selected_shortcut_items=lambda: [object()]),
        data_manager=data_manager,
    )
    operations = ShortcutOperations(window)
    operations._item_data = lambda _item: root

    with patch(
        'services.application.task_operations.shortcut_operations.confirm_batch_deletion',
        return_value=QMessageBox.StandardButton.Yes,
    ), patch('services.application.task_operations.shortcut_operations.QMessageBox.warning'):
        operations.delete_shortcut()

    assert workspace_service.validated == ['child-a', 'child-b']
    assert workspace_service.removed == []
    data_manager.delete_shortcut.assert_not_called()


def test_task_handler_exposes_child_shortcut_delegation():
    from unittest.mock import Mock
    from services.application.window_task_operations import TaskOperationHandler

    handler = TaskOperationHandler.__new__(TaskOperationHandler)
    handler._shortcut_ops = Mock()
    handler.add_child_shortcut('root-id')
    handler._shortcut_ops.add_child_shortcut.assert_called_once_with('root-id')


def test_shortcut_tag_filter_preserves_internal_spaces():
    connection = sqlite3.connect(":memory:")
    manager = ShortcutManager(connection=connection)
    manager.create('todo', 'Tagged', '/tmp/tagged', tags='project files,work')
    manager.create('todo', 'Other', '/tmp/other', tags='project,work')
    matches = manager.get_all(tag='project files')
    assert [item['title'] for item in matches] == ['Tagged']
    connection.close()


def test_add_child_shortcut_uses_parent_returned_by_dialog():
    from types import SimpleNamespace
    from unittest.mock import Mock, patch
    from services.application.task_operations.shortcut_operations import ShortcutOperations

    root_a = {'id': 'a', 'title': 'A', 'parent_id': None}
    root_b = {'id': 'b', 'title': 'B', 'parent_id': None}
    data_manager = Mock()
    data_manager.get_all_shortcuts.return_value = [root_a, root_b]
    data_manager.create_shortcut.return_value = True
    window = SimpleNamespace(
        data_manager=data_manager,
        shortcuts_table=Mock(),
        status_bar=Mock(),
        load_shortcuts=Mock(),
        update_status_bar=Mock(),
        shortcut_tag_filter=Mock(),
    )
    window.shortcuts_table.currentItem.return_value = None
    operations = ShortcutOperations(window)

    class FakeDialog:
        class DialogCode:
            Accepted = 1

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return self.DialogCode.Accepted

        def get_data(self):
            return {
                'title': 'Child',
                'shortcut_path': '/tmp/child',
                'tags': '',
                'action_type': 'open',
                'parent_id': 'b',
            }

    with patch(
        'services.application.task_operations.shortcut_operations.ShortcutEditDialog',
        FakeDialog,
    ), patch('services.application.task_operations.shortcut_operations.os.path.exists', return_value=True),          patch('services.application.task_operations.shortcut_operations.show_task_added_confirmation'):
        operations.add_child_shortcut('a')

    assert data_manager.create_shortcut.call_args.kwargs['parent_id'] == 'b'
