"""Tests for itinerary visibility and automatic navigation behavior."""

import os
from datetime import datetime
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import sip
from PyQt6.QtGui import QCloseEvent
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

    itinerary.showMinimized()
    app.processEvents()
    assert itinerary.isMinimized()

    host.show_itinerary()
    app.processEvents()

    assert itinerary.isVisible()
    assert not itinerary.isMinimized()
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
