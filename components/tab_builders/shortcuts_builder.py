"""
快捷入口 Tab 构建器
包含两个子 Tab：「快捷入口」与「历史记录」
"""

import logging

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from components.main_window.tab_filters import on_shortcut_tag_filter_clicked
from components.main_window.tag_filter_bar import TagFilterBar
from managers.application.data_manager import TaskType

logger = logging.getLogger(__name__)


class ShortcutsTabBuilder:
    """构建"快捷入口"标签页（双子 Tab：快捷入口 / 历史记录）

    与 BaseTabBuilder 不同，本页结构独特（双子 Tab + 自定义表格列宽），
    因此未继承 BaseTabBuilder 而是独立实现。
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def build(self) -> QWidget:
        win = self.parent_window
        root = QWidget()
        root_layout = QVBoxLayout(root)

        win.shortcuts_tab_widget = QTabWidget()
        root_layout.addWidget(win.shortcuts_tab_widget)

        entries_widget = self._build_entries_widget()
        history_widget = self._build_history_widget()

        win.shortcuts_tab_widget.addTab(entries_widget, '快捷入口')
        win.shortcuts_tab_widget.addTab(history_widget, '历史记录')

        logger.info("[Tab 构建] 快捷入口 Tab（含历史子 Tab）装配完成")
        return root

    # ---------------- 子 Tab 1：快捷入口 ----------------
    def _build_entries_widget(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标签分类栏
        win.shortcut_tag_filter = TagFilterBar(parent=win, data_manager=win.data_manager)
        win.shortcut_tag_filter.set_task_type(TaskType.SHORTCUT)
        win.shortcut_tag_filter.tagClicked.connect(
            lambda tag: on_shortcut_tag_filter_clicked(win, tag)
        )
        layout.addWidget(win.shortcut_tag_filter)

        # 控制按钮行
        control = QHBoxLayout()
        self._add_btn(control, 'add_shortcut_btn', '添加快捷入口', win.add_shortcut)
        self._add_btn(control, 'edit_shortcut_btn', '编辑', win.edit_shortcut)
        self._add_btn(control, 'delete_shortcut_btn', '删除', win.delete_shortcut)
        self._add_btn(control, 'open_shortcut_btn', '打开', win.open_shortcut)
        control.addStretch()

        # Claude 启动放权开关
        win.claude_skip_perm_checkbox = QCheckBox('放权启动 Claude')
        win.claude_skip_perm_checkbox.setToolTip(
            '勾选后，通过"快捷入口"和"历史记录"中的 Terminal 按钮启动 Claude 时，\n'
            '会自动带上 --dangerously-skip-permissions 参数（放权所有工具调用）。\n'
            '状态会持久化保存，下次启动仍然生效。'
        )
        win.claude_skip_perm_checkbox.stateChanged.connect(
            win.on_claude_skip_permission_toggled
        )
        control.addWidget(win.claude_skip_perm_checkbox)

        # Codex 启动放权开关
        win.codex_skip_perm_checkbox = QCheckBox('放权启动 Codex')
        win.codex_skip_perm_checkbox.setToolTip(
            '勾选后，通过"快捷入口"和"历史记录"中的 Codex 按钮启动 Codex 时，\n'
            '会自动带上 --dangerously-skip-permissions 参数（放权所有工具调用）。\n'
            '状态会持久化保存，下次启动仍然生效。'
        )
        win.codex_skip_perm_checkbox.stateChanged.connect(
            win.on_codex_skip_permission_toggled
        )
        control.addWidget(win.codex_skip_perm_checkbox)
        layout.addLayout(control)

        # 快捷入口表格（自定义列宽）
        win.shortcuts_table = self._make_shortcuts_table()
        layout.addWidget(win.shortcuts_table)
        return widget

    def _make_shortcuts_table(self) -> QTableWidget:
        win = self.parent_window
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(['名称', 'claude', 'Codex', '类型', '标签', '路径', '创建日期'])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 45)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 45)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 80)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 130)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.cellDoubleClicked.connect(win.edit_shortcut)
        table.cellClicked.connect(win.on_shortcuts_cell_clicked)
        return table

    # ---------------- 子 Tab 2：历史记录 ----------------
    def _build_history_widget(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 控制按钮行
        control = QHBoxLayout()
        self._add_btn(control, 'history_limit_btn', '设置缓存数量', win.set_history_limit)
        self._add_btn(control, 'clear_history_btn', '清空历史', win.clear_history)

        limit = win.data_manager.get_history_limit()
        win.history_limit_label = QLabel(f'当前缓存: {limit} 条')
        control.addWidget(win.history_limit_label)
        control.addStretch()
        layout.addLayout(control)

        # 历史记录表格（自定义列宽）
        win.shortcut_history_table = self._make_history_table()
        layout.addWidget(win.shortcut_history_table)
        return widget

    def _make_history_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(['名称', 'claude', 'Codex', '★', '路径', '最后打开', '操作'])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 45)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 45)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 35)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 130)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 100)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        return table

    def _add_btn(self, layout, attr_name: str, label: str, slot) -> QPushButton:
        """添加按钮 + 绑定信号 + 注册到主窗口属性

        Args:
            layout: 目标布局
            attr_name: 主窗口上的属性名
            label: 按钮文本
            slot: 点击处理函数

        Returns:
            创建好的按钮实例
        """
        btn = QPushButton(label)
        if callable(slot):
            btn.clicked.connect(slot)
        setattr(self.parent_window, attr_name, btn)
        layout.addWidget(btn)
        return btn
