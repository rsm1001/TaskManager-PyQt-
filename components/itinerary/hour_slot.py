"""行程小时槽及其持久化交互。"""

import json
import logging

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMessageBox, QPushButton, QStyle, QVBoxLayout, QWidget

from components.itinerary.constants import HOUR_HEADER_HEIGHT
from components.itinerary.factory import ItineraryComponentFactory
from components.itinerary.payload import parse_task_payload
from components.itinerary.task_row import ItineraryTaskRow
from managers.tasks.priority import DEFAULT_PRIORITY, PRIORITY_BG_COLORS

logger = logging.getLogger(__name__)


class HourSlotWidget(QFrame):
    """支持投放、状态同步及持久化的单小时容器。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, hour: int, day_index: int, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.hour, self.day_index = hour, day_index
        self.data_manager, self.main_window = data_manager, main_window
        self.collapsed, self.task_rows, self._pending_restore = True, [], None
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        self._apply_normal_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(3)
        header_box = QWidget()
        header_box.setFixedHeight(HOUR_HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_box)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        self.header = QPushButton()
        self.header.clicked.connect(self._toggle_collapse)
        self.header.setStyleSheet('QPushButton { background-color: #ECF0F1; color: #2C3E50; border: none; border-radius: 4px; font-size: 12px; text-align: left; padding-left: 8px; } QPushButton:hover { background-color: #D5DBDB; }')
        header_layout.addWidget(self.header, 1)
        self.clear_unfinished_btn = self._make_clear_button(
            QStyle.StandardPixmap.SP_BrowserReload,
            '移除本小时未完成任务',
            self._remove_unfinished,
        )
        self.clear_all_btn = self._make_clear_button(
            QStyle.StandardPixmap.SP_TrashIcon,
            '移除本小时全部任务',
            self._remove_all,
        )
        header_layout.addWidget(self.clear_unfinished_btn)
        header_layout.addWidget(self.clear_all_btn)
        layout.addWidget(header_box)
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(4, 2, 4, 2)
        self.task_layout.setSpacing(4)
        layout.addWidget(self.task_container)
        self.task_container.setVisible(False)
        self._update_header()

    def _make_clear_button(self, standard_icon, tooltip, callback):
        button = QPushButton()
        button.setFixedSize(24, HOUR_HEADER_HEIGHT)
        button.setIcon(self.style().standardIcon(standard_icon))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        button.setStyleSheet('QPushButton { background-color: transparent; color: #7F8C8D; border: none; font-size: 12px; } QPushButton:hover { background-color: #E74C3C; color: white; border-radius: 3px; }')
        return button

    def _apply_normal_style(self):
        self.setStyleSheet('HourSlotWidget { background-color: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 4px; } HourSlotWidget:hover { background-color: #F0F8FF; border: 1px solid #3498DB; }')

    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.task_container.setVisible(not self.collapsed)
        self._update_header()

    def _update_header(self):
        arrow = '▸' if self.collapsed else '▾'
        suffix = f'  {len(self.task_rows)} 项' if self.task_rows else ''
        self.header.setText(f'{arrow} {self.hour:02d}:00{suffix}')

    def add_task(self, task_data: dict, persist: bool = True):
        if persist:
            task_data = self._persist_task(task_data)
        row = ItineraryComponentFactory.create_task_row(task_data, self)
        row.deleted.connect(self._delete_task_row)
        row.status_toggled.connect(self._toggle_task_status)
        row.drag_started.connect(self._on_task_drag_started)
        row.launch_requested.connect(self._launch_task)
        row.shortcut_dropped.connect(self._bind_shortcut_to_task)
        self.task_rows.append(row)
        self.task_layout.addWidget(row)
        self.collapsed = False
        self.task_container.setVisible(True)
        self._update_header()
        if self.main_window and task_data.get('itinerary_id'):
            self.main_window.refresh_arranged_cache()

    def clear_displayed_tasks(self):
        """Remove row widgets without changing persisted itinerary records."""
        for row in list(self.task_rows):
            row.setParent(None)
            row.deleteLater()
        self.task_rows.clear()
        self.collapsed = True
        self.task_container.setVisible(False)
        self._update_header()

    def _launch_task(self, row: ItineraryTaskRow):
        task_data = row.task_data
        shortcut_id = task_data.get('shortcut_id')
        if not shortcut_id:
            return
        launcher = getattr(self.main_window, 'launch_shortcut_from_itinerary', None)
        if callable(launcher):
            launcher(shortcut_id)
            return
        parent = self.parent()
        while parent is not None:
            launcher = getattr(parent, 'launch_shortcut_from_itinerary', None)
            if callable(launcher):
                launcher(shortcut_id)
                return
            parent = parent.parent()

    def _bind_shortcut_to_task(self, row: ItineraryTaskRow, shortcut_data: dict):
        shortcut_id = shortcut_data.get('task_id', '')
        if not shortcut_id:
            return
        row.set_shortcut_binding({
            'shortcut_id': shortcut_id,
            'shortcut_title': shortcut_data.get('title', ''),
            'shortcut_path': shortcut_data.get('shortcut_path', ''),
            'shortcut_action_type': shortcut_data.get('action_type', 'open'),
        })
        self._update_persisted_snapshot(row.task_data)
        logger.info('Shortcut bound to itinerary task', extra={
            'trace_id': row.task_data.get('itinerary_id'),
            'shortcut_id': shortcut_id,
        })

    def _on_task_drag_started(self, task_data: dict, _source_slot):
        self._pending_restore = task_data
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == task_data.get('itinerary_id'):
                row.hide()
                self._update_header()
                break

    def _show_and_remove_row(self, itinerary_id: str):
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == itinerary_id:
                row.show()
                self.task_rows.remove(row)
                row.setParent(None)
                row.deleteLater()
                self._update_header()
                return

    def _restore_pending(self):
        if self._pending_restore is False:
            self._pending_restore = None
            return
        if not self._pending_restore:
            return
        task_data, self._pending_restore = self._pending_restore, None
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == task_data.get('itinerary_id'):
                row.show()
                self._update_header()
                return
        self.add_task(task_data, persist=False)

    def _persist_task(self, task_data: dict) -> dict:
        if self.data_manager is None or task_data.get('itinerary_id'):
            return task_data
        record = self.data_manager.create_itinerary_task(title=task_data.get('title') or '未命名任务', day_of_week=self.day_index + 1, hour=self.hour, task_id=task_data.get('task_id', ''), task_type=task_data.get('task_type', ''), description=json.dumps(task_data, ensure_ascii=False), color=PRIORITY_BG_COLORS.get(task_data.get('priority_key'), PRIORITY_BG_COLORS[DEFAULT_PRIORITY]))
        saved = dict(task_data)
        saved['itinerary_id'] = record.id
        logger.info('行程任务已保存', extra={'trace_id': saved.get('itinerary_id'), 'day': self.day_index + 1, 'hour': self.hour})
        return saved

    def _delete_task_row(self, row: ItineraryTaskRow):
        itinerary_id = row.task_data.get('itinerary_id')
        if itinerary_id and self.data_manager is not None:
            self.data_manager.delete_itinerary_task(itinerary_id)
            logger.info('行程任务已删除', extra={'trace_id': itinerary_id})
        if row in self.task_rows:
            self.task_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        if self.main_window:
            self.main_window.refresh_arranged_cache()
        if not self.task_rows:
            self.collapsed = True
            self.task_container.setVisible(False)
        self._update_header()

    def _toggle_task_status(self, row: ItineraryTaskRow):
        task_id, task_type = row.task_data.get('task_id', ''), row.task_data.get('task_type', '')
        toggles = {'daily': getattr(self.data_manager, 'toggle_daily_task_completion', None), 'todo': getattr(self.data_manager, 'toggle_todo_task_completion', None), 'entertainment': getattr(self.data_manager, 'toggle_entertainment_task_completion', None)} if self.data_manager else {}
        toggle = toggles.get(task_type)
        if not task_id or not callable(toggle):
            return
        if not toggle(task_id):
            QMessageBox.warning(self, '提示', '任务状态切换失败')
            return
        row.set_status({'○': '✓', '✓': '✕', '✕': '○'}.get(row.task_data.get('status', '○'), '○'))
        self._update_persisted_snapshot(row.task_data)
        self._refresh_main_table(task_type)

    def _update_persisted_snapshot(self, task_data: dict):
        itinerary_id = task_data.get('itinerary_id')
        if itinerary_id and self.data_manager is not None:
            self.data_manager.update_itinerary_task(itinerary_id, title=task_data.get('title') or '未命名任务', description=json.dumps(task_data, ensure_ascii=False), color=PRIORITY_BG_COLORS.get(task_data.get('priority_key'), PRIORITY_BG_COLORS[DEFAULT_PRIORITY]))

    def _refresh_main_table(self, task_type: str):
        loader = getattr(self.main_window, f'load_{task_type}_tasks', None) if self.main_window else None
        if callable(loader):
            loader()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/task-data'):
            event.acceptProposedAction()
            self.setStyleSheet('HourSlotWidget { background-color: #E8F5E9; border: 2px dashed #27AE60; border-radius: 4px; }')

    def dragLeaveEvent(self, event):
        self._apply_normal_style()

    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        if not event.mimeData().hasFormat('application/task-data'):
            return
        try:
            task_data = parse_task_payload(bytes(event.mimeData().data('application/task-data')).decode('utf-8'))
        except UnicodeDecodeError:
            logger.warning('行程投放数据无效', extra={'trace_id': 'itinerary-drop'})
            return
        if not task_data:
            return
        if task_data.get('task_type') == 'shortcut':
            QMessageBox.information(self, '提示', '请将快捷入口拖放到已有行程任务上进行绑定')
            event.acceptProposedAction()
            return
        itinerary_id = task_data.get('itinerary_id')
        if itinerary_id and self.data_manager is not None:
            self.data_manager.update_itinerary_task(itinerary_id, day_of_week=self.day_index + 1, hour=self.hour)
            source_slot = self._find_source_slot(itinerary_id)
            if source_slot and source_slot != self:
                source_slot._pending_restore = False
                source_slot._show_and_remove_row(itinerary_id)
            self.add_task(task_data, persist=False)
            if self.main_window:
                self.main_window.refresh_arranged_cache()
            event.acceptProposedAction()
            return
        task_id, task_type = task_data.get('task_id', ''), task_data.get('task_type', '')
        if self.data_manager and self.data_manager.has_itinerary_task_ref_for_day(task_id, task_type, self.day_index + 1):
            QMessageBox.information(self, '提示', '该任务已安排到本周的行程')
            event.acceptProposedAction()
            return
        self.add_task(task_data)
        self.task_dropped.emit(task_id, task_type, 0, self.hour)
        event.acceptProposedAction()

    def _find_source_slot(self, itinerary_id: str):
        parent = self.parent()
        while parent is not None and not hasattr(parent, 'blocks'):
            parent = parent.parent()
        for block in getattr(parent, 'blocks', []):
            for slot in block.hour_slots:
                if any(row.task_data.get('itinerary_id') == itinerary_id for row in slot.task_rows):
                    return slot
        return None

    def _remove_unfinished(self):
        for row in list(self.task_rows):
            if row.task_data.get('status') == '○':
                self._delete_task_row(row)

    def _remove_all(self):
        self.clear_all()

    def clear_all(self):
        for row in list(self.task_rows):
            self._delete_task_row(row)
