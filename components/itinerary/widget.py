"""行程浮动窗口及数据加载协调。"""

import json
import logging
from datetime import datetime

from PyQt6.QtCore import QPoint, QSettings, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from components.itinerary.constants import DAY_BUTTON_HEIGHT, KEY_TO_STATUS, WEEKDAY_NAMES
from components.itinerary.factory import ItineraryComponentFactory
from components.itinerary.payload import parse_task_payload
from managers.tasks.priority import DEFAULT_PRIORITY, get_priority_label

logger = logging.getLogger(__name__)


class ItineraryWidget(QWidget):
    """展示和管理一周行程的浮动窗口。"""

    def __init__(self, data_manager, main_window=None):
        super().__init__(None)
        self.data_manager, self.main_window = data_manager, main_window
        self._dragging, self._drag_position, self._current_day = False, QPoint(), 0
        self._day_views = []
        self._settings = QSettings('TaskManager', 'Itinerary')
        self._init_ui()
        self._load_position()
        self._load_itinerary_data()

    def _init_ui(self):
        self.setWindowTitle('行程规划')
        self.setMinimumSize(560, 720)
        self.setMaximumSize(680, 960)
        self.resize(600, 780)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        self.setStyleSheet('ItineraryWidget { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E0E0E0; }')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        title = QHBoxLayout()
        label = QLabel('行程规划')
        label.setStyleSheet('font-size: 15px; font-weight: bold; color: #2C3E50;')
        title.addWidget(label)
        title.addStretch()
        minimize_button = QPushButton('−')
        minimize_button.setFixedSize(24, 24)
        minimize_button.setToolTip('隐藏行程（Alt+Q）')
        minimize_button.clicked.connect(self._hide_window)
        minimize_button.setStyleSheet('QPushButton { background-color: transparent; color: #7F8C8D; border: none; font-size: 18px; } QPushButton:hover { background-color: #D5DBDB; color: #2C3E50; border-radius: 4px; }')
        title.addWidget(minimize_button)
        layout.addLayout(title)
        day_layout = QHBoxLayout()
        day_layout.setSpacing(4)
        self.day_buttons = []
        for index, name in enumerate(WEEKDAY_NAMES):
            button = QPushButton(name)
            button.setFixedHeight(DAY_BUTTON_HEIGHT)
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, day=index: self._switch_day(day))
            button.setStyleSheet('QPushButton { background-color: #ECF0F1; color: #2C3E50; border: none; border-radius: 6px; font-size: 13px; } QPushButton:hover { background-color: #D5DBDB; } QPushButton:checked { background-color: #3498DB; color: white; font-weight: bold; }')
            self.day_buttons.append(button)
            day_layout.addWidget(button)
        layout.addLayout(day_layout)
        self.content_stack = QWidget()
        content = QVBoxLayout(self.content_stack)
        content.setContentsMargins(0, 0, 0, 0)
        for day in range(7):
            view = ItineraryComponentFactory.create_day_view(day, self.data_manager, self.main_window)
            view.task_dropped.connect(self._on_task_dropped)
            view.setVisible(day == 0)
            self._day_views.append(view)
            content.addWidget(view)
        layout.addWidget(self.content_stack, 1)
        tip = QLabel('拖拽主界面任务到小时槽；时段和小时均可折叠；状态点击沿用主界面状态切换。')
        tip.setStyleSheet('color: #95A5A6; font-size: 11px;')
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.day_buttons[0].setChecked(True)

    def _switch_day(self, day_index):
        self._current_day = day_index
        for index, view in enumerate(self._day_views):
            view.setVisible(index == day_index)
            self.day_buttons[index].setChecked(index == day_index)

    def _on_task_dropped(self, task_id, task_type, day, hour):
        logger.info('任务拖入行程', extra={'trace_id': task_id, 'task_type': task_type, 'day': day, 'hour': hour})

    def _hide_window(self):
        """Hide the window while keeping the loaded itinerary alive."""
        self._save_position()
        self.hide()

    def closeEvent(self, event):
        """Intercept close requests so the itinerary is never destroyed."""
        self._hide_window()
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, _event):
        self._dragging = False
        self._save_position()

    def _save_position(self):
        self._settings.setValue('itinerary/pos_x', self.x())
        self._settings.setValue('itinerary/pos_y', self.y())

    def _load_position(self):
        x, y = self._settings.value('itinerary/pos_x', None), self._settings.value('itinerary/pos_y', None)
        if x is not None and y is not None:
            position = QPoint(int(x), int(y))
            screen = QApplication.screenAt(position) or QApplication.primaryScreen()
            if screen and screen.availableGeometry().adjusted(-80, -80, 80, 80).contains(position):
                self.move(position)

    def has_saved_position(self):
        x, y = self._settings.value('itinerary/pos_x', None), self._settings.value('itinerary/pos_y', None)
        if x is None or y is None:
            return False
        position = QPoint(int(x), int(y))
        screen = QApplication.screenAt(position) or QApplication.primaryScreen()
        return bool(screen and screen.availableGeometry().adjusted(-80, -80, 80, 80).contains(position))

    def refresh_itinerary_data(self):
        """Rebuild displayed rows so retained windows use current task state."""
        for view in self._day_views:
            for block in view.blocks:
                for slot in block.hour_slots:
                    slot.clear_displayed_tasks()
        self._load_itinerary_data()

    def _load_itinerary_data(self):
        if self.data_manager is None:
            return
        for record in self.data_manager.get_itinerary_tasks():
            slot = self._day_views[max(0, min(6, (record.day_of_week or 1) - 1))].get_slot(max(0, min(23, record.hour or 0)))
            if slot:
                slot.add_task(self._build_task_data(record), persist=False)
        self.auto_navigate_to_current_time()

    def auto_navigate_to_current_time(self, now=None):
        """Prefer the latest overdue pending slot; otherwise use the current hour."""
        now = now or datetime.now()
        target = self._find_latest_unfinished_slot_before(now.weekday(), now.hour)
        if target is None:
            target = self._find_slot(now.weekday(), now.hour)

        self._collapse_all()
        if target is None:
            return

        day_index, block, slot = target
        self._switch_day(day_index)
        if block.collapsed:
            block._toggle_collapse()
        if slot.collapsed:
            slot._toggle_collapse()

    def _find_latest_unfinished_slot_before(self, current_day, current_hour):
        """Return the latest pending slot before the current time this week."""
        for day_index in range(current_day, -1, -1):
            view = self._day_views[day_index]
            for block in reversed(view.blocks):
                for slot in reversed(block.hour_slots):
                    if day_index == current_day and slot.hour >= current_hour:
                        continue
                    if any(self._is_unfinished(row.task_data) for row in slot.task_rows):
                        return day_index, block, slot
        return None

    def _find_slot(self, day_index, hour):
        view = self._day_views[day_index]
        for block in view.blocks:
            slot = block.get_slot(hour)
            if slot is not None:
                return day_index, block, slot
        return None

    @staticmethod
    def _is_unfinished(task_data):
        status_key = task_data.get('status_key')
        return status_key == 'pending' if status_key is not None else task_data.get('status', '○') == '○'

    def _collapse_all(self):
        for view in self._day_views:
            for block in view.blocks:
                if not block.collapsed:
                    block._toggle_collapse()
                for slot in block.hour_slots:
                    if not slot.collapsed:
                        slot._toggle_collapse()

    def _build_task_data(self, record):
        snapshot = parse_task_payload(record.description or '{}')
        source = self._get_source_task(record.task_type, record.task_id)
        if source is not None:
            priority_key = getattr(source, 'priority', None) or snapshot.get('priority_key') or DEFAULT_PRIORITY
            status_key = getattr(source, 'status', None) or snapshot.get('status_key') or 'pending'
            return {'itinerary_id': record.id, 'task_id': record.task_id or '', 'task_type': record.task_type or '', 'status': KEY_TO_STATUS.get(status_key, '○'), 'status_key': status_key, 'title': getattr(source, 'title', '') or record.title or '未命名任务', 'tags': getattr(source, 'tags', '') or '', 'priority': get_priority_label(priority_key), 'priority_key': priority_key}
        snapshot.update({'itinerary_id': record.id, 'task_id': record.task_id or snapshot.get('task_id', ''), 'task_type': record.task_type or snapshot.get('task_type', ''), 'title': record.title or snapshot.get('title', '未命名任务'), 'priority_key': snapshot.get('priority_key') or DEFAULT_PRIORITY})
        snapshot.setdefault('status', '○')
        snapshot.setdefault('tags', '')
        snapshot.setdefault('priority', get_priority_label(snapshot['priority_key']))
        return snapshot

    def _get_source_task(self, task_type, task_id):
        getters = {'daily': getattr(self.data_manager, 'get_daily_task_by_id', None), 'todo': getattr(self.data_manager, 'get_todo_task_by_id', None), 'entertainment': getattr(self.data_manager, 'get_entertainment_task_by_id', None)}
        getter = getters.get(task_type)
        return getter(task_id) if task_id and callable(getter) else None

    @staticmethod
    def _parse_task_payload(raw):
        return parse_task_payload(raw)
