"""任务编辑对话框的子任务组件。"""

import json
import uuid
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class SubtaskEditor(QGroupBox):
    """封装子任务的编辑、展示和序列化。"""

    def __init__(self, parent: QWidget = None):
        super().__init__("子任务", parent)
        self._subtasks: List[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("检查项列表"))
        header.addStretch()
        self._progress_label = QLabel("已完成 0/0")
        header.addWidget(self._progress_label)
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(220)
        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._list_host)
        layout.addWidget(self._scroll)

        add_row = QHBoxLayout()
        self._new_edit = QLineEdit()
        self._new_edit.setPlaceholderText("新子任务内容，回车添加")
        self._new_edit.returnPressed.connect(self._add_subtask)
        self._new_edit.textChanged.connect(self._on_text_changed)
        add_row.addWidget(self._new_edit)
        self._add_button = QPushButton("添加")
        self._add_button.setEnabled(False)
        self._add_button.clicked.connect(self._add_subtask)
        add_row.addWidget(self._add_button)
        layout.addLayout(add_row)
        self._render()

    def load_serialized(self, raw: str) -> None:
        """加载持久化的子任务列表，忽略不合法条目。"""
        try:
            parsed = json.loads(raw or "[]")
        except (TypeError, ValueError):
            parsed = []
        if not isinstance(parsed, list):
            parsed = []
        self._subtasks = [
            {
                "id": str(item.get("id") or uuid.uuid4()),
                "title": str(item.get("title", "")),
                "completed": bool(item.get("completed", False)),
            }
            for item in parsed
            if isinstance(item, dict)
        ]
        self._render()

    def to_serialized(self) -> str:
        """返回用于存储的子任务 JSON。"""
        return json.dumps(self._subtasks, ensure_ascii=False)

    def _on_text_changed(self, text: str) -> None:
        self._add_button.setEnabled(bool(text.strip()))

    def _add_subtask(self) -> None:
        title = self._new_edit.text().strip()
        if not title:
            return
        self._subtasks.append({"id": str(uuid.uuid4()), "title": title, "completed": False})
        self._new_edit.clear()
        self._render()
        self._new_edit.setFocus()

    def _delete_subtask(self, index: int) -> None:
        if 0 <= index < len(self._subtasks):
            del self._subtasks[index]
            self._render()

    def _set_completed(self, index: int, checked: bool) -> None:
        if 0 <= index < len(self._subtasks):
            self._subtasks[index]["completed"] = checked
            self._update_progress()

    def _save_title(self, index: int, text: str) -> None:
        if not 0 <= index < len(self._subtasks):
            return
        title = text.strip()
        if title:
            self._subtasks[index]["title"] = title
        else:
            self._render()

    def _render(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()
        if not self._subtasks:
            empty = QLabel("暂无子任务，点击下方添加")
            empty.setStyleSheet("color: gray;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, empty)
        else:
            for index, subtask in enumerate(self._subtasks):
                self._list_layout.insertWidget(
                    self._list_layout.count() - 1,
                    self._create_row(index, subtask),
                )
        self._update_progress()

    def _create_row(self, index: int, subtask: dict) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 2, 2, 2)
        checkbox = QCheckBox()
        checkbox.setChecked(bool(subtask.get("completed")))
        checkbox.stateChanged.connect(
            lambda state, i=index: self._set_completed(i, state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(checkbox)
        title_edit = QLineEdit(subtask.get("title", ""))
        title_edit.editingFinished.connect(
            lambda i=index, edit=title_edit: self._save_title(i, edit.text())
        )
        layout.addWidget(title_edit, 1)
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(lambda _checked=False, i=index: self._delete_subtask(i))
        layout.addWidget(delete_button)
        return row

    def _update_progress(self) -> None:
        total = len(self._subtasks)
        done = sum(1 for item in self._subtasks if item.get("completed"))
        self._progress_label.setText(f"已完成 {done}/{total}")
