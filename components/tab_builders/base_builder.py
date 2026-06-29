"""
Tab 页面构建器基类
封装 Tab 页面通用组件：
- 控制按钮行（添加 / 编辑 / 删除 / 随机 / 批量操作等）
- 状态 / 时段筛选下拉框
- 通用 QTableWidget 配置
"""

import logging
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QWidget,
)

import config.config as config

from components.tab_filters import (
    _init_time_period_combo,
    wrap_edit_handler,
)

logger = logging.getLogger(__name__)


class BaseTabBuilder:
    """Tab 页面构建器基类，集中通用 UI 装配片段。

    Why:
        每日 / 待办 / 娱乐三个任务 Tab 共享相同的"控制按钮 + 筛选 + 表格"结构，
        这里把可复用片段抽出来，避免各 Builder 重复代码。
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

    # -------------------- 子类需实现的钩子 --------------------
    def build(self) -> QWidget:
        """构建并返回 Tab 页面根容器，子类需重写"""
        raise NotImplementedError("子类必须实现 build() 方法")

    # -------------------- 通用控件构建工具 --------------------
    def add_control_button(self, layout, attr_name: str, label: str, slot) -> QPushButton:
        """添加一个按钮并绑定到主窗口的指定属性 + 点击信号

        Args:
            layout: 目标布局
            attr_name: 在主窗口上的属性名
            label: 按钮显示文本
            slot: 点击信号绑定的处理函数

        Returns:
            创建好的按钮实例
        """
        btn = QPushButton(label)
        if callable(slot):
            btn.clicked.connect(slot)
        setattr(self.parent_window, attr_name, btn)
        layout.addWidget(btn)
        return btn

    def build_weekday_filter(self, layout, attr_name: str, reload_slot) -> QComboBox:
        """构建"星期"筛选下拉框，默认选中当天

        Args:
            layout: 目标布局
            attr_name: 在主窗口上的属性名
            reload_slot: 选项变更时触发的重新加载函数

        Returns:
            创建好的下拉框实例
        """
        layout.addWidget(QLabel('星期:'))
        combo = QComboBox()
        combo.addItems(config.WEEKDAY_FILTER_OPTIONS)
        # 默认选中当天
        idx = datetime.now().weekday()
        if 0 <= idx <= 6:
            today_name = config.WEEKDAY_NAMES[idx]
            pos = combo.findText(today_name)
            if pos >= 0:
                combo.setCurrentIndex(pos)
        if callable(reload_slot):
            combo.currentTextChanged.connect(reload_slot)
        setattr(self.parent_window, attr_name, combo)
        layout.addWidget(combo)
        return combo

    def build_status_filter(self, layout, attr_name: str,
                            statuses: list, default_text: str,
                            reload_slot) -> QComboBox:
        """构建"状态"筛选下拉框

        Args:
            layout: 目标布局
            attr_name: 在主窗口上的属性名
            statuses: 状态文案列表，如 ['全部', '进行中', '已完成']
            default_text: 默认选中项文案
            reload_slot: 选项变更时触发的重新加载函数

        Returns:
            创建好的下拉框实例
        """
        layout.addWidget(QLabel('状态:'))
        combo = QComboBox()
        combo.addItems(statuses)
        combo.setCurrentText(default_text)
        if callable(reload_slot):
            combo.currentTextChanged.connect(reload_slot)
        setattr(self.parent_window, attr_name, combo)
        layout.addWidget(combo)
        return combo

    def build_time_period_filter(self, layout, attr_name: str, task_type: str,
                                 reload_slot) -> QComboBox:
        """构建"时段"筛选下拉框，封装哨兵初始化逻辑

        Args:
            layout: 目标布局
            attr_name: 在主窗口上的属性名
            task_type: 任务大类
            reload_slot: 选项变更时触发的重新加载函数

        Returns:
            创建好的下拉框实例
        """
        layout.addWidget(QLabel('时段:'))
        combo = QComboBox()
        setattr(self.parent_window, attr_name, combo)
        # 先绑定属性，再初始化 items（_init 内部通过属性访问）
        _init_time_period_combo(self.parent_window, task_type)
        if callable(reload_slot):
            combo.currentTextChanged.connect(reload_slot)
        layout.addWidget(combo)
        return combo

    def make_table(self, attr_name: str, headers: list,
                   column_count: int = None,
                   edit_handler=None, click_handler=None) -> QTableWidget:
        """构造并配置一个标准 QTableWidget

        Args:
            attr_name: 在主窗口上的属性名
            headers: 表头文案列表
            column_count: 列数；None 则使用 len(headers)
            edit_handler: 双击编辑处理函数（自动包成"非状态列才生效"）
            click_handler: 单击单元格处理函数（如切状态）

        Returns:
            配置好的表格实例
        """
        table = QTableWidget()
        table.setColumnCount(column_count if column_count else len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        if callable(edit_handler):
            table.cellDoubleClicked.connect(wrap_edit_handler(edit_handler))
        if callable(click_handler):
            table.cellClicked.connect(click_handler)

        setattr(self.parent_window, attr_name, table)
        return table
