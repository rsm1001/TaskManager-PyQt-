"""
可拖拽任务表格组件
支持将任务行拖拽为 MIME 数据，供行程面板等接收
"""

import json

from PyQt6.QtWidgets import QTableWidget, QAbstractItemView, QPushButton
from PyQt6.QtCore import Qt, QMimeData, QByteArray
from PyQt6.QtGui import QDrag

from managers.tasks.priority import DEFAULT_PRIORITY, LABEL_TO_KEY


class DraggableTaskTable(QTableWidget):
    """
    支持拖拽的任务表格。

    拖拽时携带 task_id 与 task_type，供行程面板等外部控件接收。
    任务类型通过外部属性 ``task_type`` 注入（如 ``'daily'`` / ``'todo'`` / ``'entertainment'``）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_type = ""
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def startDrag(self, supportedActions):
        """
        重写 startDrag，将当前选中行的 task_id 打包为自定义 MIME 数据。
        使用 JSON，避免标题或标签中包含分隔符导致解析错误。
        """
        selected = self.selectedItems()
        if not selected:
            return

        # 获取第一行的 task_id（存储在第 0 列的 UserRole 中）
        row = selected[0].row()
        item = self.item(row, 0)
        button = None
        if self.task_type == 'shortcut':
            cell = self.cellWidget(row, 0)
            button = getattr(cell, 'button', None) or (cell.findChild(QPushButton) if cell else None)
            task_id = button.property('task_id') if button else None
            title = button.text() if button else self._cell_text(row, 0)
        else:
            if item is None:
                return
            task_id = item.data(Qt.ItemDataRole.UserRole)
            title = self._cell_text(row, 1)
        if not task_id:
            return

        # 不同任务表的标签/优先级列不同，按任务类型取。
        tags_col, priority_col = {
            "daily": (4, 8),
            "todo": (5, 9),
            "entertainment": (4, 8),
            "shortcut": (4, -1),
        }.get(self.task_type, (4, 8))
        priority = self._cell_text(row, priority_col) if priority_col >= 0 else "normal"

        mime_data = QMimeData()
        payload_data = {
            "task_id": task_id,
            "task_type": self.task_type,
            "status": self._cell_text(row, 0) if self.task_type != "shortcut" else "\u25cb",
            "title": title,
            "tags": self._cell_text(row, tags_col),
            "priority": priority,
            "priority_key": LABEL_TO_KEY.get(priority, DEFAULT_PRIORITY),
        }
        if self.task_type == "shortcut":
            payload_data.update({
                "shortcut_path": button.property("shortcut_path") if button else self._cell_text(row, 5),
                "action_type": button.property("action_type") if button else "open",
            })
        payload = json.dumps(payload_data, ensure_ascii=False)
        mime_data.setData("application/task-data", QByteArray(payload.encode("utf-8")))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(supportedActions)

    def _cell_text(self, row: int, column: int) -> str:
        """读取单元格文本，越界或空单元格返回空串。"""
        if column >= self.columnCount():
            return ""
        item = self.item(row, column)
        return item.text() if item else ""
