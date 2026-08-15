"""行程浮动窗口及数据加载协调。"""

import json
import logging
from datetime import datetime

from PyQt6.QtCore import QPoint, QSettings, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

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
        tip = QLabel('拖拽主界面任务到小时槽；将快捷入口拖到已有行程任务上绑定；状态点击沿用主界面状态切换。')
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

    def launch_shortcut_from_itinerary(self, shortcut_id: str):
        """Launch a shortcut bound to an itinerary row after hiding this window."""
        if not shortcut_id or self.data_manager is None:
            return
        shortcuts = self.data_manager.get_all_shortcuts()
        if not any(item.get('id') == shortcut_id for item in shortcuts):
            QMessageBox.warning(self.main_window or self, '\u542f\u52a8\u5931\u8d25', '\u5173\u8054\u7684\u5feb\u6377\u5165\u53e3\u4e0d\u5b58\u5728\uff0c\u53ef\u80fd\u5df2\u88ab\u5220\u9664\u3002')
            return
        # Hide the always-on-top itinerary before launching the external program.
        self._hide_window()
        QApplication.processEvents()
        service_factory = getattr(self.data_manager, '_service_factory', None)
        service = service_factory.get_shortcut_operation_service() if service_factory else None
        result = service.open_shortcut(shortcut_id) if service else {'success': False, 'message': '\u5feb\u6377\u5165\u53e3\u670d\u52a1\u4e0d\u53ef\u7528'}
        if result.get('success'):
            self._refresh_shortcut_history()
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()
        QMessageBox.warning(self.main_window or self, '\u542f\u52a8\u5931\u8d25', result.get('message', '\u5feb\u6377\u5165\u53e3\u542f\u52a8\u5931\u8d25'))

    def _refresh_shortcut_history(self):
        """Keep the main-window shortcut history current after itinerary launches."""
        if self.main_window is None:
            return
        for method_name in ('load_shortcuts_history', '_update_history_limit_label'):
            method = getattr(self.main_window, method_name, None)
            if callable(method):
                method()

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
            if record.task_type == 'shortcut':
                logger.info('Ignoring obsolete standalone shortcut itinerary record', extra={'trace_id': record.id})
                continue
            slot = self._day_views[max(0, min(6, (record.day_of_week or 1) - 1))].get_slot(max(0, min(23, record.hour or 0)))
            if slot:
                slot.add_task(self._build_task_data(record), persist=False)
        self.auto_navigate_to_current_time()

    def auto_navigate_to_current_time(self, now=None):
        """Open today's earliest unfinished slot, or the current hour."""
        now = now or datetime.now()
        target = self._find_earliest_unfinished_slot(now.weekday())
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

    def _find_earliest_unfinished_slot(self, day_index):
        """Return the first pending slot in chronological order for one day."""
        view = self._day_views[day_index]
        for block in view.blocks:
            for slot in block.hour_slots:
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
        if task_data.get('task_type') == 'shortcut':
            return False
        status_key = task_data.get('status_key')
        return status_key == 'pending' if status_key is not None else task_data.get('status', '\u25cb') == '\u25cb'

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
            task_data = {
                'itinerary_id': record.id,
                'task_id': record.task_id or '',
                'task_type': record.task_type or '',
                'status': KEY_TO_STATUS.get(status_key, '\u25cb'),
                'status_key': status_key,
                'title': getattr(source, 'title', '') or record.title or '\u672a\u547d\u540d\u4efb\u52a1',
                'tags': getattr(source, 'tags', '') or '',
                'priority': get_priority_label(priority_key),
                'priority_key': priority_key,
            }
            return self._apply_shortcut_binding(task_data, snapshot)
        snapshot.update({
            'itinerary_id': record.id,
            'task_id': record.task_id or snapshot.get('task_id', ''),
            'task_type': record.task_type or snapshot.get('task_type', ''),
            'title': record.title or snapshot.get('title', '\u672a\u547d\u540d\u4efb\u52a1'),
            'priority_key': snapshot.get('priority_key') or DEFAULT_PRIORITY,
        })
        snapshot.setdefault('status', '\u25cb')
        snapshot.setdefault('tags', '')
        snapshot.setdefault('priority', get_priority_label(snapshot['priority_key']))
        return self._apply_shortcut_binding(snapshot, snapshot)

    def _apply_shortcut_binding(self, task_data, snapshot):
        shortcut_id = snapshot.get('shortcut_id', '')
        if not shortcut_id:
            return task_data
        shortcut = self._get_shortcut_by_id(shortcut_id)
        task_data.update({
            'shortcut_id': shortcut_id,
            'shortcut_title': (shortcut or {}).get('title', snapshot.get('shortcut_title', '')),
            'shortcut_path': (shortcut or {}).get('shortcut_path', snapshot.get('shortcut_path', '')),
            'shortcut_action_type': (shortcut or {}).get('action_type', snapshot.get('shortcut_action_type', 'open')),
        })
        return task_data

    def _get_shortcut_by_id(self, shortcut_id):
        if not shortcut_id or self.data_manager is None:
            return None
        return next((item for item in self.data_manager.get_all_shortcuts() if item.get('id') == shortcut_id), None)

    def _get_source_task(self, task_type, task_id):
        if not task_id or self.data_manager is None:
            return None
        getters = {'daily': getattr(self.data_manager, 'get_daily_task_by_id', None), 'todo': getattr(self.data_manager, 'get_todo_task_by_id', None), 'entertainment': getattr(self.data_manager, 'get_entertainment_task_by_id', None)}
        getter = getters.get(task_type)
        return getter(task_id) if callable(getter) else None

    @staticmethod
    def _parse_task_payload(raw):
        return parse_task_payload(raw)
