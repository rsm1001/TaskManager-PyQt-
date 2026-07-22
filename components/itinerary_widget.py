"""
行程面板组件
可拖拽的浮动窗口，展示7天行程规划，支持24小时时间轴和任务拖拽
"""

import json
import logging

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QMimeData, QByteArray, QSettings
from PyQt6.QtGui import QColor, QDrag, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsDropShadowEffect, QMessageBox,
    QApplication
)

from managers.priority import (
    DEFAULT_PRIORITY,
    LABEL_TO_KEY,
    PRIORITY_BG_COLORS,
    PRIORITY_TEXT_COLORS,
    get_priority_label,
)

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
WEEKDAY_FULL = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
HOUR_BLOCKS = [(0, '凌晨'), (4, '早晨'), (8, '上午'), (12, '下午'), (16, '傍晚'), (20, '晚上')]
BLOCK_COLORS = {
    '凌晨': '#1A1A2E',
    '早晨': '#E8B4B8',
    '上午': '#A8D8EA',
    '下午': '#F9F9C5',
    '傍晚': '#FFB6B9',
    '晚上': '#6C5B7B',
}
STATUS_TO_KEY = {'○': 'pending', '✓': 'completed', '✗': 'abandoned'}
KEY_TO_STATUS = {'pending': '○', 'completed': '✓', 'abandoned': '✗'}
BLOCK_HEADER_HEIGHT = 30
HOUR_HEADER_HEIGHT = 28
TASK_ROW_HEIGHT = 34
DAY_BUTTON_HEIGHT = 36


class ItineraryTaskRow(QFrame):
    """行程小时内的单行任务。"""

    deleted = pyqtSignal(object)
    status_toggled = pyqtSignal(object)
    drag_started = pyqtSignal(object, object)  # (task_data, source_slot)

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self._init_ui()
        self._render()

    def _init_ui(self):
        self.setFixedHeight(TASK_ROW_HEIGHT)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 3, 6, 3)
        self.layout.setSpacing(6)

        self.status_btn = QPushButton()
        self.status_btn.setFixedSize(24, 24)
        self.status_btn.clicked.connect(lambda: self.status_toggled.emit(self))
        self.layout.addWidget(self.status_btn)

        self.title_label = QLabel()
        self.title_label.setMinimumWidth(120)
        self.title_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.layout.addWidget(self.title_label, 1)

        self.tags_label = QLabel()
        self.tags_label.setMinimumWidth(80)
        self.tags_label.setStyleSheet("font-size: 11px;")
        self.layout.addWidget(self.tags_label)

        self.priority_label = QLabel()
        self.priority_label.setFixedWidth(44)
        self.priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.priority_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.layout.addWidget(self.priority_label)

        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self))
        self.delete_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #E74C3C; border: none; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #E74C3C; color: white; border-radius: 3px; }
        """)
        self.layout.addWidget(self.delete_btn)

    def _render(self):
        priority_key = self.task_data.get('priority_key') or LABEL_TO_KEY.get(
            self.task_data.get('priority', ''), DEFAULT_PRIORITY
        )
        bg = PRIORITY_BG_COLORS.get(priority_key, PRIORITY_BG_COLORS[DEFAULT_PRIORITY])
        fg = PRIORITY_TEXT_COLORS.get(priority_key, PRIORITY_TEXT_COLORS[DEFAULT_PRIORITY])
        status = self.task_data.get('status') or '○'
        tags = self.task_data.get('tags') or '-'
        priority = self.task_data.get('priority') or '普通'

        self.setStyleSheet(f"""
            ItineraryTaskRow {{ background-color: {bg}; border: 1px solid {fg}; border-radius: 5px; }}
            QLabel {{ color: {fg}; }}
        """)
        self.status_btn.setText(status)
        self.status_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {fg}; border: none; font-size: 14px; font-weight: bold; }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 90); border-radius: 12px; }}
        """)
        self.title_label.setText(self.task_data.get('title') or '未命名任务')
        self.tags_label.setText(tags if tags != '-' else '')
        self.priority_label.setText(priority)

    def set_status(self, status: str):
        """更新行程内状态显示。"""
        self.task_data['status'] = status
        self.task_data['status_key'] = STATUS_TO_KEY.get(status, 'pending')
        self._render()

    def mousePressEvent(self, event):
        """支持行程内任务继续拖拽。"""
        if event.button() == Qt.MouseButton.LeftButton:
            source_slot = self.parent()
            self.drag_started.emit(self.task_data, source_slot)
            drag = QDrag(self)
            mime_data = QMimeData()
            payload = json.dumps(self.task_data, ensure_ascii=False)
            mime_data.setData('application/task-data', QByteArray(payload.encode('utf-8')))
            drag.setMimeData(mime_data)
            pixmap = QPixmap(140, 28)
            bg_color = PRIORITY_BG_COLORS.get(
                self.task_data.get('priority_key'), '#E3F2FD'
            )
            fg_color = PRIORITY_TEXT_COLORS.get(
                self.task_data.get('priority_key'), '#0D47A1'
            )
            pixmap.fill(QColor(bg_color))
            painter = QPainter(pixmap)
            painter.setPen(QColor(fg_color))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.task_data.get('title', '')[:12])
            painter.end()
            drag.setPixmap(pixmap)
            drag.exec(Qt.DropAction.CopyAction)
            # drag.exec 结束后：放置成功则源槽位的 _pending_restore 已由 dropEvent 清除
            # 放置失败（或取消）则恢复源槽位的任务行
            if isinstance(source_slot, HourSlotWidget):
                source_slot._restore_pending()
        else:
            super().mousePressEvent(event)


class HourSlotWidget(QFrame):
    """单个小时容器，支持折叠和多个任务。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, hour: int, day_index: int, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.hour = hour
        self.day_index = day_index
        self.data_manager = data_manager
        self.main_window = main_window
        self.collapsed = True
        self.task_rows = []
        self._pending_restore: dict | None = None  # {(task_data)}  拖拽失败待恢复
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            HourSlotWidget { background-color: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 4px; }
            HourSlotWidget:hover { background-color: #F0F8FF; border: 1px solid #3498DB; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(3)

        self.header = QPushButton()
        self.header.setFixedHeight(HOUR_HEADER_HEIGHT)
        self.header.clicked.connect(self._toggle_collapse)
        self.header.setStyleSheet("""
            QPushButton { background-color: #ECF0F1; color: #2C3E50; border: none; border-radius: 4px; font-size: 12px; text-align: left; padding-left: 8px; }
            QPushButton:hover { background-color: #D5DBDB; }
        """)
        layout.addWidget(self.header)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(4, 2, 4, 2)
        self.task_layout.setSpacing(4)
        layout.addWidget(self.task_container)
        self.task_container.setVisible(False)
        self._update_header()

    def _toggle_collapse(self):
        """切换小时折叠状态。"""
        self.collapsed = not self.collapsed
        self.task_container.setVisible(not self.collapsed)
        self._update_header()

    def _update_header(self):
        arrow = '▶' if self.collapsed else '▼'
        count = len(self.task_rows)
        suffix = f"  {count} 项" if count else ""
        self.header.setText(f"{arrow} {self.hour:02d}:00{suffix}")

    def add_task(self, task_data: dict, persist: bool = True):
        """追加一个任务行。"""
        if persist:
            task_data = self._persist_task(task_data)
        row = ItineraryTaskRow(task_data, self)
        row.deleted.connect(self._delete_task_row)
        row.status_toggled.connect(self._toggle_task_status)
        row.drag_started.connect(self._on_task_drag_started)
        self.task_rows.append(row)
        self.task_layout.addWidget(row)
        self.collapsed = False
        self.task_container.setVisible(True)
        self._update_header()
        # 刷新主窗口已安排缓存
        if self.main_window and task_data.get('itinerary_id'):
            self.main_window.refresh_arranged_cache()

    def _on_task_drag_started(self, task_data: dict, _source_slot):
        """任务行开始拖拽：隐藏行。"""
        self._pending_restore = task_data
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == task_data.get('itinerary_id'):
                row.hide()
                self._update_header()
                break

    def _show_and_remove_row(self, itinerary_id: str):
        """显示被隐藏的行并从列表中移除（拖拽成功时调用）。"""
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == itinerary_id:
                row.show()
                self.task_rows.remove(row)
                row.setParent(None)
                row.deleteLater()
                self._update_header()
                return

    def _restore_pending(self):
        """拖拽失败时恢复任务行；成功时此方法不执行任何操作。"""
        if self._pending_restore is False:
            # 拖拽成功（dropEvent 已处理），源行已移走，无需恢复
            self._pending_restore = None
            return
        if not self._pending_restore:
            # None = 无待恢复任务
            return
        td = self._pending_restore
        self._pending_restore = None
        for row in self.task_rows:
            if row.task_data.get('itinerary_id') == td.get('itinerary_id'):
                row.show()
                self._update_header()
                return
        # 行已不存在则重建
        row = ItineraryTaskRow(td, self)
        row.deleted.connect(self._delete_task_row)
        row.status_toggled.connect(self._toggle_task_status)
        row.drag_started.connect(self._on_task_drag_started)
        self.task_rows.append(row)
        self.task_layout.addWidget(row)
        self._update_header()

    def _persist_task(self, task_data: dict) -> dict:
        """保存行程任务，返回带 itinerary_id 的任务数据。"""
        if self.data_manager is None or task_data.get('itinerary_id'):
            return task_data
        record = self.data_manager.create_itinerary_task(
            title=task_data.get('title') or '未命名任务',
            day_of_week=self.day_index + 1,
            hour=self.hour,
            task_id=task_data.get('task_id', ''),
            task_type=task_data.get('task_type', ''),
            description=json.dumps(task_data, ensure_ascii=False),
            color=PRIORITY_BG_COLORS.get(task_data.get('priority_key'), PRIORITY_BG_COLORS[DEFAULT_PRIORITY]),
        )
        task_data = dict(task_data)
        task_data['itinerary_id'] = record.id
        return task_data

    def _delete_task_row(self, row: ItineraryTaskRow):
        """删除任务行。"""
        itinerary_id = row.task_data.get('itinerary_id')
        if itinerary_id and self.data_manager is not None:
            self.data_manager.delete_itinerary_task(itinerary_id)
        if row in self.task_rows:
            self.task_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        # 刷新主窗口已安排缓存
        if self.main_window:
            self.main_window.refresh_arranged_cache()
        if not self.task_rows:
            self.collapsed = True
            self.task_container.setVisible(False)
        self._update_header()

    def _toggle_task_status(self, row: ItineraryTaskRow):
        """沿用主界面的任务状态切换。"""
        task_id = row.task_data.get('task_id', '')
        task_type = row.task_data.get('task_type', '')
        if not task_id or not task_type or self.data_manager is None:
            return
        toggles = {
            'daily': self.data_manager.toggle_daily_task_completion,
            'todo': self.data_manager.toggle_todo_task_completion,
            'entertainment': self.data_manager.toggle_entertainment_task_completion,
        }
        toggle = toggles.get(task_type)
        if not toggle:
            return
        if not toggle(task_id):
            QMessageBox.warning(self, '提示', '任务状态切换失败')
            return
        next_status = {'○': '✓', '✓': '✗', '✗': '○'}.get(row.task_data.get('status', '○'), '○')
        row.set_status(next_status)
        self._update_persisted_snapshot(row.task_data)
        self._refresh_main_table(task_type)

    def _update_persisted_snapshot(self, task_data: dict):
        """更新行程任务快照。"""
        itinerary_id = task_data.get('itinerary_id')
        if itinerary_id and self.data_manager is not None:
            self.data_manager.update_itinerary_task(
                itinerary_id,
                title=task_data.get('title') or '未命名任务',
                description=json.dumps(task_data, ensure_ascii=False),
                color=PRIORITY_BG_COLORS.get(task_data.get('priority_key'), PRIORITY_BG_COLORS[DEFAULT_PRIORITY]),
            )

    def _refresh_main_table(self, task_type: str):
        """刷新主界面对应表格。"""
        if self.main_window is None:
            return
        loaders = {
            'daily': getattr(self.main_window, 'load_daily_tasks', None),
            'todo': getattr(self.main_window, 'load_todo_tasks', None),
            'entertainment': getattr(self.main_window, 'load_entertainment_tasks', None),
        }
        loader = loaders.get(task_type)
        if callable(loader):
            loader()

    def dragEnterEvent(self, event):
        """拖拽进入事件。"""
        if event.mimeData().hasFormat('application/task-data'):
            event.acceptProposedAction()
            self.setStyleSheet("""
                HourSlotWidget { background-color: #E8F5E9; border: 2px dashed #27AE60; border-radius: 4px; }
            """)

    def dragLeaveEvent(self, event):
        """拖拽离开事件。"""
        self.setStyleSheet("""
            HourSlotWidget { background-color: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 4px; }
            HourSlotWidget:hover { background-color: #F0F8FF; border: 1px solid #3498DB; }
        """)

    def dropEvent(self, event):
        """放置事件。"""
        self.dragLeaveEvent(event)
        mime = event.mimeData()
        if not mime.hasFormat('application/task-data'):
            return
        raw = bytes(mime.data('application/task-data')).decode('utf-8')
        task_data = _parse_task_payload(raw)
        if not task_data:
            return
        itinerary_id = task_data.get('itinerary_id')
        task_id = task_data.get('task_id', '')
        task_type = task_data.get('task_type', '')

        if itinerary_id and self.data_manager is not None:
            # 情况1：行程内任务移动到新槽位
            self.data_manager.update_itinerary_task(
                itinerary_id,
                day_of_week=self.day_index + 1,
                hour=self.hour,
            )
            task_data['day_of_week'] = self.day_index + 1
            task_data['hour'] = self.hour
            # 源槽位：从列表移除
            source_slot = self._find_source_slot(task_data)
            if source_slot and source_slot != self:
                source_slot._pending_restore = False
                source_slot._show_and_remove_row(itinerary_id)
            # 目标槽位：添加任务行
            self.add_task(task_data, persist=False)
            if self.main_window:
                self.main_window.refresh_arranged_cache()
            event.acceptProposedAction()
            return

        # 情况2：外部任务（主界面任务）添加到行程
        # 每个周几独立去重：同一任务可在不同星期各安排一次，但不能在同一星期重复安排
        if self.data_manager and self.data_manager.has_itinerary_task_ref_for_day(
            task_id, task_type, self.day_index + 1
        ):
            QMessageBox.information(self, '提示', '该任务已安排到本周的行程')
            event.acceptProposedAction()
            return
        self.add_task(task_data)
        self.task_dropped.emit(task_id, task_type, 0, self.hour)
        event.acceptProposedAction()

    def _find_source_slot(self, task_data) -> "HourSlotWidget | None":
        """根据 itinerary_id 找到源槽位。"""
        it_id = task_data.get('itinerary_id')
        if not it_id:
            return None
        for block in self._parent_day_view().blocks:
            for slot in block.hour_slots:
                if any(r.task_data.get('itinerary_id') == it_id for r in slot.task_rows):
                    return slot
        return None

    def _parent_day_view(self) -> "DayViewWidget | None":
        """获取所属 DayViewWidget。"""
        from PyQt6.QtWidgets import QWidget
        parent = self.parent()
        while parent and not isinstance(parent, DayViewWidget):
            parent = parent.parent()
        return parent

    def clear_all(self):
        """清除本小时所有任务。"""
        for row in list(self.task_rows):
            self._delete_task_row(row)


class HourBlockWidget(QFrame):
    """4小时块控件（可折叠）。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, start_hour: int, block_name: str, day_index: int, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.start_hour = start_hour
        self.block_name = block_name
        self.day_index = day_index
        self.data_manager = data_manager
        self.main_window = main_window
        self.collapsed = True
        self.hour_slots = []
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = QPushButton()
        self.header.setFixedHeight(BLOCK_HEADER_HEIGHT)
        self.header.clicked.connect(self._toggle_collapse)
        self.header.setStyleSheet(f"""
            QPushButton {{ background-color: {BLOCK_COLORS.get(self.block_name, '#3498DB')}; color: white; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; text-align: left; padding-left: 10px; }}
            QPushButton:hover {{ background-color: {BLOCK_COLORS.get(self.block_name, '#3498DB')}DD; }}
        """)
        self.main_layout.addWidget(self.header)

        self.slots_container = QWidget()
        slots_layout = QVBoxLayout(self.slots_container)
        slots_layout.setContentsMargins(4, 4, 4, 4)
        slots_layout.setSpacing(3)
        for hour in range(self.start_hour, self.start_hour + 4):
            slot = HourSlotWidget(hour, self.day_index, self.data_manager, self.main_window)
            slot.task_dropped.connect(self._on_slot_task_dropped)
            self.hour_slots.append(slot)
            slots_layout.addWidget(slot)
        self.main_layout.addWidget(self.slots_container)
        self.slots_container.setVisible(False)
        self._update_header()

    def _on_slot_task_dropped(self, task_id: str, task_type: str, _day: int, hour: int):
        """转发槽位的 task_dropped 信号。"""
        self.task_dropped.emit(task_id, task_type, 0, hour)

    def _toggle_collapse(self):
        """切换4小时块折叠状态。"""
        self.collapsed = not self.collapsed
        self.slots_container.setVisible(not self.collapsed)
        self._update_header()

    def _update_header(self):
        arrow = '▶' if self.collapsed else '▼'
        self.header.setText(f"{arrow} {self.block_name} ({self.start_hour:02d}:00-{(self.start_hour + 4):02d}:00)")

    def get_slot(self, hour: int):
        """获取指定小时的槽位。"""
        for slot in self.hour_slots:
            if slot.hour == hour:
                return slot
        return None


class DayViewWidget(QWidget):
    """单日视图控件。"""

    task_dropped = pyqtSignal(str, str, int, int)

    def __init__(self, day_index: int, data_manager=None, main_window=None, parent=None):
        super().__init__(parent)
        self.day_index = day_index
        self.data_manager = data_manager
        self.main_window = main_window
        self.blocks = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel(WEEKDAY_FULL[self.day_index])
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        for start_hour, block_name in HOUR_BLOCKS:
            block = HourBlockWidget(start_hour, block_name, self.day_index, self.data_manager, self.main_window)
            block.task_dropped.connect(self._on_task_dropped)
            self.blocks.append(block)
            container_layout.addWidget(block)

        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _on_task_dropped(self, task_id: str, task_type: str, _day: int, hour: int):
        """转发任务放置信号。"""
        self.task_dropped.emit(task_id, task_type, self.day_index, hour)

    def get_slot(self, hour: int):
        """获取指定小时的槽位。"""
        for block in self.blocks:
            slot = block.get_slot(hour)
            if slot:
                return slot
        return None

    def clear_all(self):
        """清除所有任务。"""
        for block in self.blocks:
            for slot in block.hour_slots:
                slot.clear_all()


class ItineraryWidget(QWidget):
    """行程面板浮动窗口。"""

    def __init__(self, data_manager, main_window=None):
        super().__init__(None)
        self.data_manager = data_manager
        self.main_window = main_window
        self._dragging = False
        self._drag_position = QPoint()
        self._current_day = 0
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
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.setStyleSheet("""
            ItineraryWidget { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E0E0E0; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title_layout = QHBoxLayout()
        self.title_label = QLabel('📅 行程规划')
        self.title_label.setStyleSheet('font-size: 15px; font-weight: bold; color: #2C3E50;')
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.minimize_btn = QPushButton('−')
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.setToolTip('最小化（隐藏但不关闭）')
        self.minimize_btn.clicked.connect(self.hide)
        self.minimize_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #7F8C8D; border: none; font-size: 16px; }
            QPushButton:hover { background-color: #F39C12; color: white; border-radius: 4px; }
        """)
        title_layout.addWidget(self.minimize_btn)

        self.close_btn = QPushButton('×')
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setToolTip('关闭并销毁')
        self.close_btn.clicked.connect(self._on_close)
        self.close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #7F8C8D; border: none; font-size: 18px; }
            QPushButton:hover { background-color: #E74C3C; color: white; border-radius: 4px; }
        """)
        title_layout.addWidget(self.close_btn)
        layout.addLayout(title_layout)

        day_layout = QHBoxLayout()
        day_layout.setSpacing(4)
        self.day_buttons = []
        for i, name in enumerate(WEEKDAY_NAMES):
            btn = QPushButton(name)
            btn.setFixedHeight(DAY_BUTTON_HEIGHT)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._switch_day(idx))
            btn.setStyleSheet("""
                QPushButton { background-color: #ECF0F1; color: #2C3E50; border: none; border-radius: 6px; font-size: 13px; }
                QPushButton:hover { background-color: #D5DBDB; }
                QPushButton:checked { background-color: #3498DB; color: white; font-weight: bold; }
            """)
            self.day_buttons.append(btn)
            day_layout.addWidget(btn)
        layout.addLayout(day_layout)

        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        for i in range(7):
            day_view = DayViewWidget(i, self.data_manager, self.main_window)
            day_view.task_dropped.connect(self._on_task_dropped)
            day_view.setVisible(i == 0)
            self._day_views.append(day_view)
            self.content_layout.addWidget(day_view)
        layout.addWidget(self.content_stack, 1)

        tip = QLabel('拖拽主界面任务到小时槽；4小时块和每小时均可折叠；状态点击沿用主界面状态切换')
        tip.setStyleSheet('color: #95A5A6; font-size: 11px;')
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.day_buttons[0].setChecked(True)

    def _switch_day(self, day_index: int):
        """切换显示的日期。"""
        self._current_day = day_index
        for i, view in enumerate(self._day_views):
            view.setVisible(i == day_index)
        for i, btn in enumerate(self.day_buttons):
            btn.setChecked(i == day_index)

    def _on_task_dropped(self, task_id: str, task_type: str, day: int, hour: int):
        """处理任务放置。"""
        logger.info('任务拖入行程: %s (%s) -> %s %s:00', task_id, task_type, WEEKDAY_FULL[day], hour)

    def _on_close(self):
        """关闭并销毁。"""
        self._save_position()
        self.deleteLater()

    def mousePressEvent(self, event):
        """鼠标按下事件（用于拖拽窗口）。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件（用于拖拽窗口）。"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件。"""
        self._dragging = False
        self._save_position()

    def _save_position(self):
        """保存窗口位置到 QSettings。"""
        self._settings.setValue('itinerary/pos_x', self.x())
        self._settings.setValue('itinerary/pos_y', self.y())

    def _load_position(self):
        """从 QSettings 恢复窗口位置。"""
        x = self._settings.value('itinerary/pos_x', None)
        y = self._settings.value('itinerary/pos_y', None)
        if x is None or y is None:
            return
        pos = QPoint(int(x), int(y))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        if screen and screen.availableGeometry().adjusted(-80, -80, 80, 80).contains(pos):
            self.move(pos)

    def has_saved_position(self) -> bool:
        """是否已有可用的保存位置。"""
        x = self._settings.value('itinerary/pos_x', None)
        y = self._settings.value('itinerary/pos_y', None)
        if x is None or y is None:
            return False
        pos = QPoint(int(x), int(y))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        return bool(screen and screen.availableGeometry().adjusted(-80, -80, 80, 80).contains(pos))

    def _load_itinerary_data(self):
        """从数据库加载行程数据。"""
        if self.data_manager is None:
            return
        for record in self.data_manager.get_itinerary_tasks():
            day_index = max(0, min(6, (record.day_of_week or 1) - 1))
            hour = max(0, min(23, record.hour or 0))
            slot = self._day_views[day_index].get_slot(hour)
            if slot:
                slot.add_task(self._build_task_data(record), persist=False)

    def _build_task_data(self, record) -> dict:
        """从行程记录构建显示数据，优先使用原任务最新数据。"""
        snapshot = _parse_task_payload(record.description or "{}")
        source = self._get_source_task(record.task_type, record.task_id)
        if source is not None:
            priority_key = getattr(source, 'priority', None) or snapshot.get('priority_key') or DEFAULT_PRIORITY
            status_key = getattr(source, 'status', None) or snapshot.get('status_key') or 'pending'
            return {
                'itinerary_id': record.id,
                'task_id': record.task_id or '',
                'task_type': record.task_type or '',
                'status': KEY_TO_STATUS.get(status_key, '○'),
                'status_key': status_key,
                'title': getattr(source, 'title', '') or record.title or '未命名任务',
                'tags': getattr(source, 'tags', '') or '',
                'priority': get_priority_label(priority_key),
                'priority_key': priority_key,
            }
        snapshot.update({
            'itinerary_id': record.id,
            'task_id': record.task_id or snapshot.get('task_id', ''),
            'task_type': record.task_type or snapshot.get('task_type', ''),
            'title': record.title or snapshot.get('title', '未命名任务'),
            'priority_key': snapshot.get('priority_key') or DEFAULT_PRIORITY,
        })
        snapshot.setdefault('status', '○')
        snapshot.setdefault('tags', '')
        snapshot.setdefault('priority', get_priority_label(snapshot['priority_key']))
        return snapshot

    def _get_source_task(self, task_type: str, task_id: str):
        """获取行程关联的原任务。"""
        if not task_id:
            return None
        getters = {
            'daily': self.data_manager.get_daily_task_by_id,
            'todo': self.data_manager.get_todo_task_by_id,
            'entertainment': self.data_manager.get_entertainment_task_by_id,
        }
        getter = getters.get(task_type)
        return getter(task_id) if getter else None


def _parse_task_payload(raw: str) -> dict:
    """解析拖拽任务数据，兼容旧版分隔符格式。"""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data.setdefault('status', '○')
            data.setdefault('priority_key', LABEL_TO_KEY.get(data.get('priority', ''), DEFAULT_PRIORITY))
            return data
    except (ValueError, TypeError):
        pass

    parts = raw.split('|')
    if len(parts) < 2:
        return {}
    priority = parts[5] if len(parts) > 5 else '普通'
    return {
        'task_id': parts[0],
        'task_type': parts[1],
        'status': parts[2] if len(parts) > 2 else '○',
        'title': parts[3] if len(parts) > 3 else f"任务 {parts[0][:8]}...",
        'tags': parts[4] if len(parts) > 4 else '',
        'priority': priority,
        'priority_key': LABEL_TO_KEY.get(priority, DEFAULT_PRIORITY),
    }
