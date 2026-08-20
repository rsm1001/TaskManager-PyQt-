"""Tree widget used by the shortcut tab."""

import json
from typing import Iterable, List, Optional

from PyQt6.QtCore import QByteArray, QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem


class DraggableShortcutTree(QTreeWidget):
    """Two-level shortcut tree with the legacy table signal helpers.

    The compatibility helpers keep the rest of the main window small while
    the actual hierarchy is represented by QTreeWidgetItem parent/child nodes.
    """

    cellClicked = pyqtSignal(int, int)
    cellDoubleClicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_type = 'shortcut'
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(False)
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        self.cellClicked.emit(self.visible_index(item), column)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        self.cellDoubleClicked.emit(self.visible_index(item), column)

    def iter_items(self, include_hidden: bool = True) -> Iterable[QTreeWidgetItem]:
        for index in range(self.topLevelItemCount()):
            root = self.topLevelItem(index)
            yield root
            if include_hidden:
                for child_index in range(root.childCount()):
                    yield root.child(child_index)
            elif root.isExpanded():
                for child_index in range(root.childCount()):
                    yield root.child(child_index)

    def visible_items(self) -> List[QTreeWidgetItem]:
        return list(self.iter_items(include_hidden=False))

    def visible_index(self, target: QTreeWidgetItem) -> int:
        try:
            return self.visible_items().index(target)
        except ValueError:
            return -1

    def item_at_row(self, row: int) -> Optional[QTreeWidgetItem]:
        items = self.visible_items()
        return items[row] if 0 <= row < len(items) else None

    # Compatibility with QTableWidget call sites.
    def rowCount(self) -> int:
        return len(self.visible_items())

    def currentRow(self) -> int:
        item = self.currentItem()
        return self.visible_index(item) if item is not None else -1

    def cellWidget(self, row: int, column: int):
        item = self.item_at_row(row)
        return self.itemWidget(item, column) if item is not None else None

    def selectRow(self, row: int) -> None:
        item = self.item_at_row(row)
        if item is not None:
            self.setCurrentItem(item)
            item.setSelected(True)
            self.scrollToItem(item)

    def find_item_by_id(self, shortcut_id: str) -> Optional[QTreeWidgetItem]:
        for item in self.iter_items():
            if item.data(0, Qt.ItemDataRole.UserRole) == shortcut_id:
                return item
        return None

    def selected_shortcut_items(self) -> List[QTreeWidgetItem]:
        return [item for item in self.selectedItems() if item is not None]

    def startDrag(self, supportedActions) -> None:
        items = self.selected_shortcut_items()
        if not items:
            return
        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole + 1) or {}
        shortcut_id = data.get('id')
        if not shortcut_id:
            return
        payload_data = {
            'task_id': shortcut_id,
            'task_type': 'shortcut',
            'status': '?',
            'title': data.get('title', item.text(0)),
            'tags': data.get('tags', ''),
            'priority': 'normal',
            'priority_key': 'normal',
            'shortcut_path': data.get('shortcut_path', ''),
            'action_type': data.get('action_type', 'open'),
            'parent_id': data.get('parent_id'),
        }
        mime_data = QMimeData()
        mime_data.setData(
            'application/task-data',
            QByteArray(json.dumps(payload_data, ensure_ascii=False).encode('utf-8')),
        )
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(supportedActions)
