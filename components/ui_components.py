"""
UI Components Module for Task Manager - PyQt6
负责处理所有用户界面创建相关的功能
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QPushButton, QLabel, QComboBox, QGroupBox, QSplitter,
                             QAbstractItemView, QLineEdit)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime, date
from PyQt6.QtGui import QColor
import config.config as config
from components.tag_filter_bar import TagFilterBar
from managers.data_manager import TaskType
from services.table_operations import load_search_results_to_table
import os


def on_tag_filter_clicked(parent_window, tag: str, task_type: str):
    """标签筛选点击处理"""
    attr_name = 'current_tag_filter'
    setattr(parent_window, attr_name, tag)

    if task_type == 'daily':
        parent_window.load_daily_tasks()
    elif task_type == 'todo':
        parent_window.load_todo_tasks()
    elif task_type == 'entertainment':
        parent_window.load_entertainment_tasks()


def _wrap_edit_handler(handler):
    """包装编辑事件处理器，拦截对状态栏(列0)的双击"""
    def wrapper(row, col):
        if col != 0:
            handler()
    return wrapper


def create_daily_tab_ui(parent_window):
    """创建每日任务标签页"""
    daily_widget = QWidget()
    daily_layout = QVBoxLayout(daily_widget)

    # 标签分类栏
    parent_window.daily_tag_filter = TagFilterBar(parent=parent_window, data_manager=parent_window.data_manager)
    parent_window.daily_tag_filter.set_task_type(TaskType.DAILY)
    parent_window.daily_tag_filter.tagClicked.connect(lambda tag: on_tag_filter_clicked(parent_window, tag, 'daily'))
    daily_layout.addWidget(parent_window.daily_tag_filter)

    # 控制按钮区域
    daily_control_layout = QHBoxLayout()

    parent_window.add_daily_btn = QPushButton('添加任务')
    parent_window.add_daily_btn.clicked.connect(parent_window.add_daily_task)
    daily_control_layout.addWidget(parent_window.add_daily_btn)

    parent_window.edit_daily_btn = QPushButton('编辑任务')
    parent_window.edit_daily_btn.clicked.connect(parent_window.edit_daily_task)
    daily_control_layout.addWidget(parent_window.edit_daily_btn)

    parent_window.delete_daily_btn = QPushButton('删除任务')
    parent_window.delete_daily_btn.clicked.connect(parent_window.delete_daily_task)
    daily_control_layout.addWidget(parent_window.delete_daily_btn)

    parent_window.reset_today_btn = QPushButton('重置今日')
    parent_window.reset_today_btn.clicked.connect(parent_window.reset_today_daily_tasks)
    daily_control_layout.addWidget(parent_window.reset_today_btn)

    parent_window.random_daily_btn = QPushButton('随机抽取')
    parent_window.random_daily_btn.clicked.connect(parent_window.random_daily_task)
    daily_control_layout.addWidget(parent_window.random_daily_btn)

    parent_window.batch_status_daily_btn = QPushButton('批量改状态')
    parent_window.batch_status_daily_btn.clicked.connect(parent_window.batch_edit_daily_status)
    daily_control_layout.addWidget(parent_window.batch_status_daily_btn)

    parent_window.batch_tags_daily_btn = QPushButton('批量编辑标签')
    parent_window.batch_tags_daily_btn.clicked.connect(parent_window.batch_edit_daily_tags)
    daily_control_layout.addWidget(parent_window.batch_tags_daily_btn)

    # 筛选下拉框
    daily_control_layout.addStretch()

    # 星期筛选
    daily_control_layout.addWidget(QLabel('星期:'))
    parent_window.daily_weekday_combo = QComboBox()
    parent_window.daily_weekday_combo.addItems(config.WEEKDAY_FILTER_OPTIONS)
    today_weekday_index = datetime.now().weekday()
    if 0 <= today_weekday_index <= 6:
        today_name = config.WEEKDAY_NAMES[today_weekday_index]
        index = parent_window.daily_weekday_combo.findText(today_name)
        if index >= 0:
            parent_window.daily_weekday_combo.setCurrentIndex(index)
    parent_window.daily_weekday_combo.currentTextChanged.connect(parent_window.load_daily_tasks)
    daily_control_layout.addWidget(parent_window.daily_weekday_combo)

    # 状态筛选
    daily_control_layout.addWidget(QLabel('状态:'))
    parent_window.daily_status_combo = QComboBox()
    parent_window.daily_status_combo.addItems(['全部', '进行中', '已完成', '暂弃'])
    parent_window.daily_status_combo.setCurrentText('进行中')
    parent_window.daily_status_combo.currentTextChanged.connect(parent_window.load_daily_tasks)
    daily_control_layout.addWidget(parent_window.daily_status_combo)

    daily_layout.addLayout(daily_control_layout)

    # 任务表格
    parent_window.daily_table = QTableWidget()
    parent_window.daily_table.setColumnCount(8)
    parent_window.daily_table.setHorizontalHeaderLabels(['状态', '标题', '分类', '星期', '标签', '描述', '创建日期', '优先级'])
    parent_window.daily_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.daily_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    parent_window.daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.daily_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    parent_window.daily_table.cellDoubleClicked.connect(_wrap_edit_handler(parent_window.edit_daily_task))
    parent_window.daily_table.cellClicked.connect(parent_window.toggle_daily_task_status)

    daily_layout.addWidget(parent_window.daily_table)
    return daily_widget


def create_todo_tab_ui(parent_window):
    """创建待办事项标签页"""
    todo_widget = QWidget()
    todo_layout = QVBoxLayout(todo_widget)

    # 标签分类栏
    parent_window.todo_tag_filter = TagFilterBar(parent=parent_window, data_manager=parent_window.data_manager)
    parent_window.todo_tag_filter.set_task_type(TaskType.TODO)
    parent_window.todo_tag_filter.tagClicked.connect(lambda tag: on_tag_filter_clicked(parent_window, tag, 'todo'))
    todo_layout.addWidget(parent_window.todo_tag_filter)

    # 控制按钮区域
    todo_control_layout = QHBoxLayout()

    parent_window.add_todo_btn = QPushButton('添加任务')
    parent_window.add_todo_btn.clicked.connect(parent_window.add_todo_task)
    todo_control_layout.addWidget(parent_window.add_todo_btn)

    parent_window.edit_todo_btn = QPushButton('编辑任务')
    parent_window.edit_todo_btn.clicked.connect(parent_window.edit_todo_task)
    todo_control_layout.addWidget(parent_window.edit_todo_btn)

    parent_window.delete_todo_btn = QPushButton('删除任务')
    parent_window.delete_todo_btn.clicked.connect(parent_window.delete_todo_task)
    todo_control_layout.addWidget(parent_window.delete_todo_btn)

    parent_window.random_todo_btn = QPushButton('随机抽取')
    parent_window.random_todo_btn.clicked.connect(parent_window.random_todo_task)
    todo_control_layout.addWidget(parent_window.random_todo_btn)

    parent_window.batch_status_todo_btn = QPushButton('批量改状态')
    parent_window.batch_status_todo_btn.clicked.connect(parent_window.batch_edit_todo_status)
    todo_control_layout.addWidget(parent_window.batch_status_todo_btn)

    parent_window.batch_tags_todo_btn = QPushButton('批量编辑标签')
    parent_window.batch_tags_todo_btn.clicked.connect(parent_window.batch_edit_todo_tags)
    todo_control_layout.addWidget(parent_window.batch_tags_todo_btn)

    # 状态筛选下拉框
    todo_control_layout.addStretch()
    todo_control_layout.addWidget(QLabel('状态:'))
    parent_window.todo_status_combo = QComboBox()
    parent_window.todo_status_combo.addItems(['全部', '进行中', '已完成', '已过期', '暂弃'])
    parent_window.todo_status_combo.setCurrentText('进行中')
    parent_window.todo_status_combo.currentTextChanged.connect(parent_window.load_todo_tasks)
    todo_control_layout.addWidget(parent_window.todo_status_combo)

    todo_layout.addLayout(todo_control_layout)

    # 任务表格
    parent_window.todo_table = QTableWidget()
    parent_window.todo_table.setColumnCount(9)
    parent_window.todo_table.setHorizontalHeaderLabels(['状态', '标题', '截止日期', '分类', '紧急程度', '标签', '描述', '创建日期', '优先级'])
    parent_window.todo_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.todo_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    parent_window.todo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.todo_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    parent_window.todo_table.cellDoubleClicked.connect(_wrap_edit_handler(parent_window.edit_todo_task))
    parent_window.todo_table.horizontalHeader().sectionClicked.connect(parent_window.sort_todo_table_by_column)
    parent_window.todo_sort_column = -1
    parent_window.todo_sort_order = Qt.SortOrder.AscendingOrder
    parent_window.todo_table.horizontalHeader().sectionClicked.connect(parent_window.sort_todo_table_by_column)
    parent_window.todo_table.cellClicked.connect(parent_window.toggle_todo_task_status)

    todo_layout.addWidget(parent_window.todo_table)
    return todo_widget


def create_entertainment_tab_ui(parent_window):
    """创建娱乐任务标签页"""
    entertainment_widget = QWidget()
    entertainment_layout = QVBoxLayout(entertainment_widget)

    # 标签分类栏
    parent_window.entertainment_tag_filter = TagFilterBar(parent=parent_window, data_manager=parent_window.data_manager)
    parent_window.entertainment_tag_filter.set_task_type(TaskType.ENTERTAINMENT)
    parent_window.entertainment_tag_filter.tagClicked.connect(lambda tag: on_tag_filter_clicked(parent_window, tag, 'entertainment'))
    entertainment_layout.addWidget(parent_window.entertainment_tag_filter)

    # 控制按钮区域
    entertainment_control_layout = QHBoxLayout()

    parent_window.add_entertainment_btn = QPushButton('添加任务')
    parent_window.add_entertainment_btn.clicked.connect(parent_window.add_entertainment_task)
    entertainment_control_layout.addWidget(parent_window.add_entertainment_btn)

    parent_window.edit_entertainment_btn = QPushButton('编辑任务')
    parent_window.edit_entertainment_btn.clicked.connect(parent_window.edit_entertainment_task)
    entertainment_control_layout.addWidget(parent_window.edit_entertainment_btn)

    parent_window.delete_entertainment_btn = QPushButton('删除任务')
    parent_window.delete_entertainment_btn.clicked.connect(parent_window.delete_entertainment_task)
    entertainment_control_layout.addWidget(parent_window.delete_entertainment_btn)

    parent_window.random_entertainment_btn = QPushButton('随机抽取')
    parent_window.random_entertainment_btn.clicked.connect(parent_window.random_entertainment_task)
    entertainment_control_layout.addWidget(parent_window.random_entertainment_btn)

    parent_window.batch_status_entertainment_btn = QPushButton('批量改状态')
    parent_window.batch_status_entertainment_btn.clicked.connect(parent_window.batch_edit_entertainment_status)
    entertainment_control_layout.addWidget(parent_window.batch_status_entertainment_btn)

    parent_window.batch_tags_entertainment_btn = QPushButton('批量编辑标签')
    parent_window.batch_tags_entertainment_btn.clicked.connect(parent_window.batch_edit_entertainment_tags)
    entertainment_control_layout.addWidget(parent_window.batch_tags_entertainment_btn)

    # 状态筛选下拉框
    entertainment_control_layout.addStretch()
    entertainment_control_layout.addWidget(QLabel('状态:'))
    parent_window.entertainment_status_combo = QComboBox()
    parent_window.entertainment_status_combo.addItems(['全部', '进行中', '已完成', '暂弃'])
    parent_window.entertainment_status_combo.setCurrentText('进行中')
    parent_window.entertainment_status_combo.currentTextChanged.connect(parent_window.load_entertainment_tasks)
    entertainment_control_layout.addWidget(parent_window.entertainment_status_combo)

    entertainment_layout.addLayout(entertainment_control_layout)

    # 任务表格
    parent_window.entertainment_table = QTableWidget()
    parent_window.entertainment_table.setColumnCount(8)
    parent_window.entertainment_table.setHorizontalHeaderLabels(['状态', '标题', '类别', '分类', '标签', '描述', '创建日期', '优先级'])
    parent_window.entertainment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.entertainment_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    parent_window.entertainment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.entertainment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    parent_window.entertainment_table.cellDoubleClicked.connect(_wrap_edit_handler(parent_window.edit_entertainment_task))
    parent_window.entertainment_table.cellClicked.connect(parent_window.toggle_entertainment_task_status)

    entertainment_layout.addWidget(parent_window.entertainment_table)
    return entertainment_widget


def create_shortcuts_tab_ui(parent_window):
    """创建快捷入口标签页（独立Tab）"""
    shortcuts_widget = QWidget()
    shortcuts_layout = QVBoxLayout(shortcuts_widget)

    # 标签分类栏
    from managers.tag_manager import TagManager
    parent_window.shortcut_tag_filter = TagFilterBar(parent=parent_window, data_manager=parent_window.data_manager)
    # 临时设置一个假的 task_type 用于快捷入口
    class ShortcutTaskType:
        value = "shortcut"
    parent_window.shortcut_tag_filter.set_task_type(ShortcutTaskType())
    parent_window.shortcut_tag_filter.tagClicked.connect(lambda tag: on_shortcut_tag_filter_clicked(parent_window, tag))
    shortcuts_layout.addWidget(parent_window.shortcut_tag_filter)

    # 控制按钮区域
    control_layout = QHBoxLayout()

    parent_window.add_shortcut_btn = QPushButton('添加快捷入口')
    parent_window.add_shortcut_btn.clicked.connect(parent_window.add_shortcut)
    control_layout.addWidget(parent_window.add_shortcut_btn)

    parent_window.edit_shortcut_btn = QPushButton('编辑')
    parent_window.edit_shortcut_btn.clicked.connect(parent_window.edit_shortcut)
    control_layout.addWidget(parent_window.edit_shortcut_btn)

    parent_window.delete_shortcut_btn = QPushButton('删除')
    parent_window.delete_shortcut_btn.clicked.connect(parent_window.delete_shortcut)
    control_layout.addWidget(parent_window.delete_shortcut_btn)

    parent_window.open_shortcut_btn = QPushButton('打开')
    parent_window.open_shortcut_btn.clicked.connect(parent_window.open_shortcut)
    control_layout.addWidget(parent_window.open_shortcut_btn)

    control_layout.addStretch()

    shortcuts_layout.addLayout(control_layout)

    # 快捷入口表格
    parent_window.shortcuts_table = QTableWidget()
    parent_window.shortcuts_table.setColumnCount(6)
    parent_window.shortcuts_table.setHorizontalHeaderLabels(['名称', 'Terminal', '类型', '标签', '路径', '创建日期'])
    parent_window.shortcuts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.shortcuts_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
    parent_window.shortcuts_table.horizontalHeader().resizeSection(2, 80)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    parent_window.shortcuts_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
    parent_window.shortcuts_table.horizontalHeader().resizeSection(5, 130)
    parent_window.shortcuts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    parent_window.shortcuts_table.cellDoubleClicked.connect(parent_window.edit_shortcut)
    parent_window.shortcuts_table.cellClicked.connect(parent_window.on_shortcuts_cell_clicked)

    shortcuts_layout.addWidget(parent_window.shortcuts_table)
    return shortcuts_widget


def on_shortcut_tag_filter_clicked(parent_window, tag: str):
    """快捷入口标签筛选点击处理"""
    parent_window.current_shortcut_tag_filter = tag
    parent_window.load_shortcuts()


def create_search_tab_ui(parent_window):
    """创建全局搜索标签页"""
    search_widget = QWidget()
    search_layout = QVBoxLayout(search_widget)

    # 搜索框区域
    search_control_layout = QHBoxLayout()

    search_control_layout.addWidget(QLabel('搜索:'))
    parent_window.search_input = QLineEdit()
    parent_window.search_input.setPlaceholderText('输入关键词搜索所有任务...')
    parent_window.search_input.setMinimumWidth(300)
    parent_window.search_input.textChanged.connect(parent_window.on_search_text_changed)
    search_control_layout.addWidget(parent_window.search_input)

    parent_window.search_clear_btn = QPushButton('清除')
    parent_window.search_clear_btn.clicked.connect(parent_window.on_search_clear)
    search_control_layout.addWidget(parent_window.search_clear_btn)

    search_control_layout.addStretch()

    # 搜索结果数量标签
    parent_window.search_status_label = QLabel('请输入关键词搜索')
    search_control_layout.addWidget(parent_window.search_status_label)

    search_layout.addLayout(search_control_layout)

    # 搜索结果表格
    parent_window.search_results_table = QTableWidget()
    parent_window.search_results_table.setColumnCount(8)
    parent_window.search_results_table.setHorizontalHeaderLabels(
        ['类型', '状态', '标题', '分类', '标签', '描述', '创建日期', '优先级']
    )
    parent_window.search_results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.search_results_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    parent_window.search_results_table.horizontalHeader().resizeSection(0, 80)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
    parent_window.search_results_table.horizontalHeader().resizeSection(1, 60)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
    parent_window.search_results_table.horizontalHeader().resizeSection(6, 100)
    parent_window.search_results_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
    parent_window.search_results_table.horizontalHeader().resizeSection(7, 70)
    parent_window.search_results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    parent_window.search_results_table.cellDoubleClicked.connect(parent_window.on_search_result_double_click)

    search_layout.addWidget(parent_window.search_results_table)

    # 说明标签
    hint_label = QLabel('提示: 双击结果行可跳转到对应任务')
    hint_label.setStyleSheet("color: gray; font-size: 12px;")
    search_layout.addWidget(hint_label)

    return search_widget
