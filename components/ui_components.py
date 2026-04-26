"""
UI Components Module for Task Manager - PyQt6
负责处理所有用户界面创建相关的功能
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QLabel, QComboBox, QGroupBox, QSplitter,
                             QAbstractItemView)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime, date
from PyQt6.QtGui import QColor
import config.config as config
from components.tag_filter_bar import TagFilterBar
from managers.data_manager import TaskType


def create_daily_tab_ui(parent_window):
    """创建每日任务标签页"""
    daily_widget = QWidget()
    daily_layout = QVBoxLayout(daily_widget)
    
    # 【新增】标签分类栏（位于控制按钮下方、表格上方）
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
    
    parent_window.random_daily_btn = QPushButton('随机抽取')
    parent_window.random_daily_btn.clicked.connect(parent_window.random_daily_task)
    daily_control_layout.addWidget(parent_window.random_daily_btn)
    
    # 筛选下拉框
    daily_control_layout.addStretch()
    
    # 星期筛选
    daily_control_layout.addWidget(QLabel('星期:'))
    parent_window.daily_weekday_combo = QComboBox()
    parent_window.daily_weekday_combo.addItems(config.WEEKDAY_FILTER_OPTIONS)
    # 设置默认值为今天是星期几
    today_weekday_index = datetime.now().weekday()  # 0是星期一，6是星期日
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
    parent_window.daily_status_combo.setCurrentText('进行中')  # 默认选择"进行中"
    parent_window.daily_status_combo.currentTextChanged.connect(parent_window.load_daily_tasks)
    daily_control_layout.addWidget(parent_window.daily_status_combo)
    
    daily_layout.addLayout(daily_control_layout)
    
    # 任务表格
    parent_window.daily_table = QTableWidget()
    parent_window.daily_table.setColumnCount(6)
    parent_window.daily_table.setHorizontalHeaderLabels(['状态', '标题', '星期', '标签', '描述', '创建日期'])
    parent_window.daily_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.daily_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    parent_window.daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.daily_table.cellDoubleClicked.connect(parent_window.edit_daily_task)
    parent_window.daily_table.cellClicked.connect(parent_window.toggle_daily_task_status)
    
    daily_layout.addWidget(parent_window.daily_table)
    return daily_widget


def create_todo_tab_ui(parent_window):
    """创建待办事项标签页"""
    todo_widget = QWidget()
    todo_layout = QVBoxLayout(todo_widget)
    
    # 【新增】标签分类栏
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
    
    # 状态筛选下拉框
    todo_control_layout.addStretch()
    todo_control_layout.addWidget(QLabel('状态:'))
    parent_window.todo_status_combo = QComboBox()
    parent_window.todo_status_combo.addItems(['全部', '进行中', '已完成', '已过期', '暂弃'])
    parent_window.todo_status_combo.setCurrentText('进行中')  # 默认选择"进行中"
    parent_window.todo_status_combo.currentTextChanged.connect(parent_window.load_todo_tasks)
    todo_control_layout.addWidget(parent_window.todo_status_combo)
    
    todo_layout.addLayout(todo_control_layout)
    
    # 任务表格
    parent_window.todo_table = QTableWidget()
    parent_window.todo_table.setColumnCount(7)
    parent_window.todo_table.setHorizontalHeaderLabels(['状态', '标题', '截止日期', '紧急程度', '标签', '描述', '创建日期'])
    parent_window.todo_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.todo_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    parent_window.todo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.todo_table.cellDoubleClicked.connect(parent_window.edit_todo_task)
    
    # 启用表头点击排序功能
    parent_window.todo_table.horizontalHeader().sectionClicked.connect(parent_window.sort_todo_table_by_column)
    
    # 添加排序状态跟踪变量
    parent_window.todo_sort_column = -1  # 当前排序列(-1表示未排序)
    parent_window.todo_sort_order = Qt.SortOrder.AscendingOrder  # 排序顺序(升序)
    
    # 再次绑定事件以确保响应
    parent_window.todo_table.horizontalHeader().sectionClicked.connect(parent_window.sort_todo_table_by_column)
    
    parent_window.todo_table.cellClicked.connect(parent_window.toggle_todo_task_status)
    
    todo_layout.addWidget(parent_window.todo_table)
    return todo_widget


def create_entertainment_tab_ui(parent_window):
    """创建娱乐任务标签页"""
    entertainment_widget = QWidget()
    entertainment_layout = QVBoxLayout(entertainment_widget)
    
    # 【新增】标签分类栏
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
    
    # 状态筛选下拉框
    entertainment_control_layout.addStretch()
    entertainment_control_layout.addWidget(QLabel('状态:'))
    parent_window.entertainment_status_combo = QComboBox()
    parent_window.entertainment_status_combo.addItems(['全部', '进行中', '已完成', '暂弃'])
    parent_window.entertainment_status_combo.setCurrentText('进行中')  # 默认选择"进行中"
    parent_window.entertainment_status_combo.currentTextChanged.connect(parent_window.load_entertainment_tasks)
    entertainment_control_layout.addWidget(parent_window.entertainment_status_combo)
    
    entertainment_layout.addLayout(entertainment_control_layout)
    
    # 任务表格
    parent_window.entertainment_table = QTableWidget()
    parent_window.entertainment_table.setColumnCount(6)
    parent_window.entertainment_table.setHorizontalHeaderLabels(['状态', '标题', '类别', '标签', '描述', '创建日期'])
    parent_window.entertainment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    parent_window.entertainment_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    parent_window.entertainment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    parent_window.entertainment_table.cellDoubleClicked.connect(parent_window.edit_entertainment_task)
    parent_window.entertainment_table.cellClicked.connect(parent_window.toggle_entertainment_task_status)
    
    entertainment_layout.addWidget(parent_window.entertainment_table)
    return entertainment_widget


def on_tag_filter_clicked(parent_window, tag: str, task_type: str):
    """标签筛选点击处理"""
    parent_window.current_tag_filter = tag
    if task_type == 'daily':
        parent_window.load_daily_tasks()
    elif task_type == 'todo':
        parent_window.load_todo_tasks()
    elif task_type == 'entertainment':
        parent_window.load_entertainment_tasks()