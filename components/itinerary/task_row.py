"""行程任务行组件。"""

import json

from PyQt6.QtCore import QByteArray, QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QPainter, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from components.itinerary.constants import STATUS_TO_KEY, TASK_ROW_HEIGHT
from components.itinerary.payload import parse_task_payload
from managers.tasks.priority import DEFAULT_PRIORITY, LABEL_TO_KEY, PRIORITY_BG_COLORS, PRIORITY_TEXT_COLORS


class ItineraryTaskRow(QFrame):
    """小时槽中展示和拖拽的单条任务。"""

    deleted = pyqtSignal(object)
    status_toggled = pyqtSignal(object)
    drag_started = pyqtSignal(object, object)
    launch_requested = pyqtSignal(object)
    shortcut_dropped = pyqtSignal(object, object)

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self._drag_start_pos = None
        self._dragging = False
        self._init_ui()
        self._render()

    def _init_ui(self):
        self.setFixedHeight(TASK_ROW_HEIGHT)
        self.setAcceptDrops(True)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 3, 6, 3)
        self.layout.setSpacing(6)
        self.status_btn = QPushButton()
        self.status_btn.setFixedSize(24, 24)
        self.status_btn.clicked.connect(lambda: self.status_toggled.emit(self))
        self.layout.addWidget(self.status_btn)
        self.title_label = QLabel()
        self.title_label.setMinimumWidth(120)
        self.title_label.setStyleSheet('font-size: 12px; font-weight: bold;')
        self.layout.addWidget(self.title_label, 1)
        self.tags_label = QLabel()
        self.tags_label.setMinimumWidth(80)
        self.tags_label.setStyleSheet('font-size: 11px;')
        self.layout.addWidget(self.tags_label)
        self.priority_label = QLabel()
        self.priority_label.setFixedWidth(44)
        self.priority_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.priority_label.setStyleSheet('font-size: 11px; font-weight: bold;')
        self.layout.addWidget(self.priority_label)
        self.launch_btn = QPushButton('\u542f\u52a8')
        self.launch_btn.setFixedSize(42, 20)
        self.launch_btn.setToolTip('\u542f\u52a8\u7ed1\u5b9a\u7684\u5feb\u6377\u5165\u53e3\u5e76\u9690\u85cf\u884c\u7a0b\u7a97\u53e3')
        self.launch_btn.clicked.connect(lambda: self.launch_requested.emit(self))
        self.launch_btn.setStyleSheet(
            'QPushButton { background: #E8F5E9; color: #2E7D32; border: 1px solid #66BB6A; '
            'border-radius: 3px; font-size: 11px; } QPushButton:hover { background: #C8E6C9; }'
        )
        self.launch_btn.setVisible(self._has_shortcut_binding())
        self.layout.addWidget(self.launch_btn)
        self.delete_btn = QPushButton('×')
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self))
        self.delete_btn.setStyleSheet('QPushButton { background: transparent; color: #E74C3C; border: none; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #E74C3C; color: white; border-radius: 3px; }')
        self.layout.addWidget(self.delete_btn)

    def _render(self):
        priority_key = self.task_data.get('priority_key') or LABEL_TO_KEY.get(self.task_data.get('priority', ''), DEFAULT_PRIORITY)
        background = PRIORITY_BG_COLORS.get(priority_key, PRIORITY_BG_COLORS[DEFAULT_PRIORITY])
        foreground = PRIORITY_TEXT_COLORS.get(priority_key, PRIORITY_TEXT_COLORS[DEFAULT_PRIORITY])
        self.setStyleSheet(f'ItineraryTaskRow {{ background-color: {background}; border: 1px solid {foreground}; border-radius: 5px; }} QLabel {{ color: {foreground}; }}')
        self.status_btn.setText(self.task_data.get('status') or '○')
        self.status_btn.setStyleSheet(f'QPushButton {{ background: transparent; color: {foreground}; border: none; font-size: 14px; font-weight: bold; }} QPushButton:hover {{ background: rgba(255, 255, 255, 90); border-radius: 12px; }}')
        self.title_label.setText(self.task_data.get('title') or '未命名任务')
        tags = self.task_data.get('tags') or '-'
        self.tags_label.setText(tags if tags != '-' else '')
        self.priority_label.setText(self.task_data.get('priority') or '普通')
        self.launch_btn.setVisible(self._has_shortcut_binding())

    def set_status(self, status: str):
        self.task_data['status'] = status
        self.task_data['status_key'] = STATUS_TO_KEY.get(status, 'pending')
        self._render()

    def _has_shortcut_binding(self):
        return bool(self.task_data.get('shortcut_id'))

    def set_shortcut_binding(self, shortcut_data: dict):
        self.task_data.update(shortcut_data)
        self._render()

    @staticmethod
    def _get_shortcut_payload(event):
        if not event.mimeData().hasFormat('application/task-data'):
            return None
        try:
            task_data = parse_task_payload(bytes(event.mimeData().data('application/task-data')).decode('utf-8'))
        except UnicodeDecodeError:
            return None
        return task_data if task_data.get('task_type') == 'shortcut' else None

    def dragEnterEvent(self, event):
        if self._get_shortcut_payload(event):
            event.acceptProposedAction()
            self.setStyleSheet('ItineraryTaskRow { background-color: #E8F5E9; border: 2px dashed #27AE60; border-radius: 5px; }')
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._render()
        event.accept()

    def dropEvent(self, event):
        shortcut_data = self._get_shortcut_payload(event)
        self._render()
        if not shortcut_data:
            event.ignore()
            return
        self.shortcut_dropped.emit(self, shortcut_data)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is None or self._dragging:
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 10:
            return
        self._dragging = True
        source_slot = self.parent()
        self.drag_started.emit(self.task_data, source_slot)
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData('application/task-data', QByteArray(json.dumps(self.task_data, ensure_ascii=False).encode('utf-8')))
        drag.setMimeData(mime_data)
        pixmap = QPixmap(140, 28)
        pixmap.fill(QColor(PRIORITY_BG_COLORS.get(self.task_data.get('priority_key'), '#E3F2FD')))
        painter = QPainter(pixmap)
        painter.setPen(QColor(PRIORITY_TEXT_COLORS.get(self.task_data.get('priority_key'), '#0D47A1')))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.task_data.get('title', '')[:12])
        painter.end()
        drag.setPixmap(pixmap)
        drag.exec(Qt.DropAction.CopyAction)
        restore = getattr(source_slot, '_restore_pending', None)
        if callable(restore):
            restore()
        self._drag_start_pos = None
        self._dragging = False

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)
