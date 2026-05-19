"""
批量编辑标签对话框 - 批量为选中任务添加/移除标签
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QWidget, QGridLayout,
                             QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt


class BatchTagEditDialog(QDialog):
    """批量编辑标签对话框"""

    def __init__(self, parent, data_manager, task_type, current_tags: set):
        super().__init__(parent)
        self.data_manager = data_manager
        self.task_type = task_type  # 'daily' / 'todo' / 'entertainment'
        self.current_tags = current_tags
        self.add_tags = set()
        self.remove_tags = set()
        self.checkboxes = {}  # tag -> QCheckBox
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f'批量编辑标签 - {self._get_type_name()}')
        self.setModal(True)
        self.resize(450, 350)

        layout = QVBoxLayout(self)

        # 说明文字
        layout.addWidget(QLabel(
            f'当前选中任务共涉及 {len(self.current_tags)} 个标签。\n'
            '勾选添加或移除标签后点击确定。'
        ))

        # 加载所有可用标签
        all_tags = set()
        if self.data_manager:
            category = self.task_type
            category_tags = self.data_manager.get_all_tags(category)
            all_tags.update(category_tags)
        all_tags.update(self.current_tags)

        # 标签列表（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        grid = QGridLayout()

        row, col = 0, 0
        num_cols = 2
        for tag in sorted(all_tags):
            cb = QCheckBox(tag)
            # 已有标签默认不选中（移除模式）
            in_current = tag in self.current_tags
            cb.setChecked(in_current)
            cb.stateChanged.connect(self._on_state_changed)
            self.checkboxes[tag] = cb
            grid.addWidget(cb, row, col)
            col += 1
            if col >= num_cols:
                col = 0
                row += 1

        # 如果没有标签
        if not all_tags:
            grid.addWidget(QLabel('暂无可用标签，请在任务中添加'), 0, 0, 1, 2)

        scroll_widget.setLayout(grid)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # 图例说明
        hint_layout = QHBoxLayout()
        hint_layout.addWidget(QLabel('勾选=添加到任务；取消勾选=从任务移除'))
        hint_layout.addStretch()
        layout.addLayout(hint_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _get_type_name(self):
        names = {'daily': '每日任务', 'todo': '待办事项', 'entertainment': '娱乐任务'}
        return names.get(self.task_type, self.task_type)

    def _on_state_changed(self, state):
        """记录复选框状态变化"""
        sender = self.sender()
        if not sender:
            return
        tag = sender.text()
        if state == Qt.CheckState.Checked.value:
            self.add_tags.add(tag)
        else:
            self.remove_tags.add(tag)

    def _on_ok(self):
        """确定：检查是否有变更"""
        if not self.add_tags and not self.remove_tags:
            QMessageBox.information(self, '提示', '请至少选择一个标签操作')
            return
        self.accept()

    def get_result(self):
        """返回 (要添加的标签集合, 要移除的标签集合)"""
        return self.add_tags, self.remove_tags
