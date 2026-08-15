"""Tests for itinerary visibility and automatic navigation behavior."""

import json
import os
from datetime import datetime
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import sip
from PyQt6.QtCore import QByteArray, QMimeData, QPointF, Qt
from PyQt6.QtGui import QCloseEvent, QDropEvent
from PyQt6.QtWidgets import QApplication

from components.itinerary.widget import ItineraryWidget
from ui.main_window.tools import MainWindowToolsMixin


def _app():
    return QApplication.instance() or QApplication([])


def _task(task_id, status_key="pending"):
    status = "○" if status_key == "pending" else "✓"
    return {
        "itinerary_id": task_id,
        "status": status,
        "status_key": status_key,
        "title": task_id,
        "priority": "普通",
        "priority_key": "normal",
    }


def test_auto_navigation_prefers_today_earliest_unfinished_slot():
    app = _app()
    widget = ItineraryWidget(data_manager=None)
    # Monday is earlier in the week, but the navigation rule only considers today.
    widget._day_views[0].get_slot(8).add_task(_task("monday-pending"), persist=False)
    widget._day_views[1].get_slot(9).add_task(_task("today-earliest-pending"), persist=False)
    widget._day_views[1].get_slot(12).add_task(_task("today-later-pending"), persist=False)
    widget._day_views[1].get_slot(11).add_task(_task("completed", "completed"), persist=False)

    widget.auto_navigate_to_current_time(datetime(2026, 7, 28, 13, 30))

    target_slot = widget._day_views[1].get_slot(9)
    target_block = next(block for block in widget._day_views[1].blocks if target_slot in block.hour_slots)
    assert widget._current_day == 1
    assert not target_block.collapsed
    assert not target_slot.collapsed
    assert all(
        block.collapsed
        for day_view in widget._day_views
        for block in day_view.blocks
        if block is not target_block
    )
    assert all(
        slot.collapsed
        for day_view in widget._day_views
        for block in day_view.blocks
        for slot in block.hour_slots
        if slot is not target_slot
    )
    widget.deleteLater()
    app.processEvents()


def test_auto_navigation_uses_current_hour_when_no_unfinished_tasks_exist():
    app = _app()
    widget = ItineraryWidget(data_manager=None)

    widget.auto_navigate_to_current_time(datetime(2026, 7, 28, 13, 30))

    target_slot = widget._day_views[1].get_slot(13)
    target_block = next(block for block in widget._day_views[1].blocks if target_slot in block.hour_slots)
    assert widget._current_day == 1
    assert not target_block.collapsed
    assert not target_slot.collapsed
    assert all(
        slot.collapsed
        for day_view in widget._day_views
        for block in day_view.blocks
        for slot in block.hour_slots
        if slot is not target_slot
    )
    widget.deleteLater()
    app.processEvents()


def test_close_hides_itinerary_without_destroying_it():
    app = _app()
    widget = ItineraryWidget(data_manager=None)
    widget.show()
    app.processEvents()

    widget.close()
    app.processEvents()

    assert not widget.isVisible()
    assert not sip.isdeleted(widget)
    widget.deleteLater()


class _CloseDataManager:
    def __init__(self):
        self.closed = False

    def close_session(self):
        self.closed = True


class _CloseHost(MainWindowToolsMixin):
    def __init__(self, itinerary):
        self._itinerary_widget = itinerary
        self.data_manager = _CloseDataManager()


def test_main_window_close_hides_visible_itinerary_before_exiting():
    app = _app()
    itinerary = ItineraryWidget(data_manager=None)
    itinerary.show()
    app.processEvents()
    host = _CloseHost(itinerary)

    event = QCloseEvent()
    host.closeEvent(event)

    assert event.isAccepted()
    assert host.data_manager.closed
    assert not itinerary.isVisible()
    itinerary.deleteLater()
    app.processEvents()


class _RefreshDataManager:
    def __init__(self):
        self.source = SimpleNamespace(
            status="pending", priority="normal", title="source task", tags=""
        )
        self.record = SimpleNamespace(
            id="itinerary-1",
            day_of_week=2,
            hour=9,
            task_id="task-1",
            task_type="todo",
            title="stored task",
            description="{}",
        )

    def get_itinerary_tasks(self):
        return [self.record]

    def get_todo_task_by_id(self, task_id):
        return self.source if task_id == self.record.task_id else None


class _ShowHost(MainWindowToolsMixin):
    def __init__(self, data_manager, itinerary):
        self.data_manager = data_manager
        self._itinerary_widget = itinerary
        self._itinerary_positioned = True

    def _refresh_arranged_cache(self):
        pass


def test_show_itinerary_restores_a_minimized_itinerary_instead_of_hiding_it():
    app = _app()
    data_manager = _RefreshDataManager()
    itinerary = ItineraryWidget(data_manager=data_manager)
    host = _ShowHost(data_manager, itinerary)

    slot = itinerary._day_views[1].get_slot(9)
    old_row = slot.task_rows[0]
    itinerary.showMinimized()
    app.processEvents()
    assert itinerary.isMinimized()

    data_manager.source.status = "completed"
    host.show_itinerary()
    app.processEvents()

    assert itinerary.isVisible()
    assert not itinerary.isMinimized()
    assert len(slot.task_rows) == 1
    assert slot.task_rows[0] is not old_row
    assert slot.task_rows[0].task_data["status_key"] == "completed"
    itinerary.deleteLater()
    app.processEvents()


def test_reopening_hidden_itinerary_refreshes_task_status_rows():
    app = _app()
    data_manager = _RefreshDataManager()
    itinerary = ItineraryWidget(data_manager=data_manager)
    slot = itinerary._day_views[1].get_slot(9)
    old_row = slot.task_rows[0]
    assert old_row.task_data["status_key"] == "pending"

    itinerary.show()
    app.processEvents()
    itinerary.hide()
    data_manager.source.status = "completed"

    host = _ShowHost(data_manager, itinerary)
    host.show_itinerary()
    app.processEvents()

    assert itinerary.isVisible()
    assert len(slot.task_rows) == 1
    assert slot.task_rows[0] is not old_row
    assert slot.task_rows[0].task_data["status_key"] == "completed"
    itinerary.deleteLater()
    app.processEvents()


class _ShortcutService:
    def __init__(self):
        self.opened = []

    def open_shortcut(self, shortcut_id):
        self.opened.append(shortcut_id)
        return {'success': True}


class _ShortcutFactory:
    def __init__(self, service):
        self.service = service

    def get_shortcut_operation_service(self):
        return self.service


class _ShortcutDataManager:
    def __init__(self, service):
        self._service_factory = _ShortcutFactory(service)
        self.itinerary_updates = []

    def get_itinerary_tasks(self):
        return []

    def update_itinerary_task(self, itinerary_id, **kwargs):
        self.itinerary_updates.append((itinerary_id, kwargs))
        return True

    def get_all_shortcuts(self):
        return [{
            'id': 'shortcut-1',
            'title': 'Launch me',
            'shortcut_path': 'C:/launch-me.ps1',
            'action_type': 'script',
            'tags': 'test',
        }]


def test_shortcut_drop_binds_existing_itinerary_task_without_creating_a_row():
    app = _app()
    service = _ShortcutService()
    data_manager = _ShortcutDataManager(service)
    widget = ItineraryWidget(data_manager=data_manager)
    slot = widget._day_views[0].get_slot(9)
    task_data = {
        'itinerary_id': 'itinerary-task-1',
        'task_id': 'todo-1',
        'task_type': 'todo',
        'status': chr(0x25cb),
        'status_key': 'pending',
        'title': 'Existing task',
        'tags': 'work',
        'priority': 'normal',
        'priority_key': 'normal',
    }
    slot.add_task(task_data, persist=False)
    row = slot.task_rows[0]

    shortcut_payload = {
        'task_id': 'shortcut-1',
        'task_type': 'shortcut',
        'title': 'Launch me',
        'shortcut_path': 'C:/launch-me.ps1',
        'action_type': 'script',
    }
    mime_data = QMimeData()
    mime_data.setData('application/task-data', QByteArray(json.dumps(shortcut_payload).encode('utf-8')))
    row.dropEvent(QDropEvent(
        QPointF(1, 1),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    ))

    assert len(slot.task_rows) == 1
    assert row.task_data['task_type'] == 'todo'
    assert row.task_data['shortcut_id'] == 'shortcut-1'
    assert row.task_data['shortcut_path'] == 'C:/launch-me.ps1'
    assert not row.status_btn.isHidden()
    assert not row.launch_btn.isHidden()
    assert widget._is_unfinished(row.task_data) is True
    assert data_manager.itinerary_updates[0][0] == 'itinerary-task-1'
    persisted = data_manager.itinerary_updates[0][1]['description']
    assert 'shortcut-1' in persisted
    restored = widget._build_task_data(SimpleNamespace(
        id='itinerary-task-1',
        task_id='todo-1',
        task_type='todo',
        title='Existing task',
        description=persisted,
    ))
    assert restored['shortcut_id'] == 'shortcut-1'
    assert restored['shortcut_path'] == 'C:/launch-me.ps1'

    widget.show()
    app.processEvents()
    row.launch_btn.click()
    app.processEvents()
    assert service.opened == ['shortcut-1']
    assert not widget.isVisible()

    widget.deleteLater()
    app.processEvents()



def test_shortcut_drop_to_an_empty_hour_slot_is_rejected(monkeypatch):
    app = _app()
    widget = ItineraryWidget(data_manager=_ShortcutDataManager(_ShortcutService()))
    slot = widget._day_views[0].get_slot(10)
    mime_data = QMimeData()
    mime_data.setData('application/task-data', QByteArray(json.dumps({
        'task_id': 'shortcut-1',
        'task_type': 'shortcut',
        'title': 'Launch me',
    }).encode('utf-8')))

    with monkeypatch.context() as patcher:
        patcher.setattr('components.itinerary.hour_slot.QMessageBox.information', lambda *args: None)
        slot.dropEvent(QDropEvent(
            QPointF(1, 1),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ))

    assert slot.task_rows == []
    widget.deleteLater()
    app.processEvents()

def test_itinerary_shortcut_launch_refreshes_history_after_hiding():
    app = _app()
    service = _ShortcutService()
    data_manager = _ShortcutDataManager(service)
    widget = ItineraryWidget(data_manager=data_manager)

    class Host:
        def __init__(self):
            self.history_refreshes = 0
            self.limit_refreshes = 0

        def load_shortcuts_history(self):
            self.history_refreshes += 1

        def _update_history_limit_label(self):
            self.limit_refreshes += 1

    host = Host()
    widget.main_window = host
    widget.show()
    app.processEvents()
    widget.launch_shortcut_from_itinerary('shortcut-1')
    app.processEvents()

    assert service.opened == ['shortcut-1']
    assert not widget.isVisible()
    assert host.history_refreshes == 1
    assert host.limit_refreshes == 1

    widget.deleteLater()
    app.processEvents()



def test_itinerary_shortcut_launch_failure_restores_itinerary_without_history_refresh(monkeypatch):
    app = _app()

    class FailedService(_ShortcutService):
        def open_shortcut(self, shortcut_id):
            self.opened.append(shortcut_id)
            return {'success': False, 'message': 'OS rejected launch'}

    service = FailedService()
    widget = ItineraryWidget(data_manager=_ShortcutDataManager(service))

    class Host:
        def __init__(self):
            self.history_refreshes = 0
            self.limit_refreshes = 0

        def load_shortcuts_history(self):
            self.history_refreshes += 1

        def _update_history_limit_label(self):
            self.limit_refreshes += 1

    widget.main_window = Host()
    widget.show()
    app.processEvents()
    with monkeypatch.context() as patcher:
        patcher.setattr('components.itinerary.widget.QMessageBox.warning', lambda *args: None)
        widget.launch_shortcut_from_itinerary('shortcut-1')
    app.processEvents()

    assert service.opened == ['shortcut-1']
    assert widget.isVisible()
    assert widget.main_window.history_refreshes == 0
    assert widget.main_window.limit_refreshes == 0

    widget.deleteLater()
    app.processEvents()
