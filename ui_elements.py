"""
Task Manager UI Components Module
处理菜单栏、工具栏等UI元素创建功能
"""

from PyQt6.QtWidgets import QMenuBar, QMenu, QStatusBar, QToolBar
from PyQt6.QtGui import QAction
from dialogs.json_examples_dialog import JsonExamplesDialog


def create_menu_bar(window):
    """创建菜单栏"""
    menubar = window.menuBar()
    
    # 文件菜单
    file_menu = menubar.addMenu('文件')
    
    export_action = QAction('导出数据', window)
    export_action.triggered.connect(window.export_data)
    file_menu.addAction(export_action)
    
    import_action = QAction('导入数据', window)
    import_action.triggered.connect(window.import_data)
    file_menu.addAction(import_action)
    
    file_menu.addSeparator()
    
    exit_action = QAction('退出', window)
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)
    
    # 编辑菜单
    edit_menu = menubar.addMenu('编辑')
    
    add_daily_action = QAction('添加每日任务', window)
    add_daily_action.triggered.connect(window.add_daily_task)
    edit_menu.addAction(add_daily_action)
    
    add_todo_action = QAction('添加待办事项', window)
    add_todo_action.triggered.connect(window.add_todo_task)
    edit_menu.addAction(add_todo_action)
    
    add_entertainment_action = QAction('添加娱乐任务', window)
    add_entertainment_action.triggered.connect(window.add_entertainment_task)
    edit_menu.addAction(add_entertainment_action)
    
    # 工具菜单
    tools_menu = menubar.addMenu('工具')
    
    stats_action = QAction('统计信息', window)
    stats_action.triggered.connect(window.show_statistics)
    tools_menu.addAction(stats_action)
    
    # 帮助菜单
    help_menu = menubar.addMenu('帮助')
    
    json_examples_action = QAction('JSON导入示例', window)
    json_examples_action.triggered.connect(window.show_json_examples)
    help_menu.addAction(json_examples_action)
    
    about_action = QAction('关于', window)
    about_action.triggered.connect(window.show_about)
    help_menu.addAction(about_action)


def create_toolbar(window):
    """创建工具栏"""
    toolbar = window.addToolBar('工具栏')
    
    # 每日任务工具
    toolbar.addAction('添加每日', window.add_daily_task)
    toolbar.addAction('随机每日', window.random_daily_task)
    
    toolbar.addSeparator()
    
    # 待办事项工具
    toolbar.addAction('添加待办', window.add_todo_task)
    toolbar.addAction('随机待办', window.random_todo_task)
    
    toolbar.addSeparator()
    
    # 娱乐任务工具
    toolbar.addAction('添加娱乐', window.add_entertainment_task)
    toolbar.addAction('随机娱乐', window.random_entertainment_task)