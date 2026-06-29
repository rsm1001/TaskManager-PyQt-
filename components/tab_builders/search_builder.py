"""
全局搜索 Tab 构建器
"""

import logging

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class SearchTabBuilder:
    """构建"全局搜索"标签页

    结构：搜索框 + 清除按钮 + 结果统计标签 → 搜索结果表（自定义列宽） → 提示
    """

    HEADERS = ['类型', '状态', '星期', '标题', '分类', '标签',
               '用时(分钟)', '描述', '创建日期', '优先级']

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def build(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 搜索框区域
        control = QHBoxLayout()
        control.addWidget(QLabel('搜索:'))
        win.search_input = QLineEdit()
        win.search_input.setPlaceholderText('输入关键词搜索所有任务...')
        win.search_input.setMinimumWidth(300)
        win.search_input.textChanged.connect(win.on_search_text_changed)
        control.addWidget(win.search_input)

        win.search_clear_btn = QPushButton('清除')
        win.search_clear_btn.clicked.connect(win.on_search_clear)
        control.addWidget(win.search_clear_btn)

        control.addStretch()
        win.search_status_label = QLabel('请输入关键词搜索')
        control.addWidget(win.search_status_label)
        layout.addLayout(control)

        # 搜索结果表格
        win.search_results_table = self._make_table()
        layout.addWidget(win.search_results_table)

        # 底部提示
        hint = QLabel('提示: 双击结果行可跳转到对应任务')
        hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint)

        logger.info("[Tab 构建] 全局搜索 Tab 装配完成")
        return widget

    def _make_table(self) -> QTableWidget:
        win = self.parent_window
        table = QTableWidget()
        table.setColumnCount(len(self.HEADERS))
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # 搜索表的列宽布局较精细：固定 + 拉伸混合
        header = table.horizontalHeader()
        modes = [
            (QHeaderView.ResizeMode.Fixed, 80),
            (QHeaderView.ResizeMode.Fixed, 60),
            (QHeaderView.ResizeMode.Fixed, 70),
            (QHeaderView.ResizeMode.Stretch, 0),
            (QHeaderView.ResizeMode.ResizeToContents, 0),
            (QHeaderView.ResizeMode.ResizeToContents, 0),
            (QHeaderView.ResizeMode.ResizeToContents, 80),
            (QHeaderView.ResizeMode.Stretch, 0),
            (QHeaderView.ResizeMode.Fixed, 100),
            (QHeaderView.ResizeMode.Fixed, 70),
        ]
        for col, (mode, width) in enumerate(modes):
            header.setSectionResizeMode(col, mode)
            if mode == QHeaderView.ResizeMode.Fixed and width > 0:
                header.resizeSection(col, width)

        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.cellDoubleClicked.connect(win.on_search_result_double_click)
        return table
