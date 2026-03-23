"""
Task Manager - PyQt6 主界面
现代化的任务管理器界面
"""

import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QDialog, QLineEdit, QTextEdit, 
                             QLabel, QComboBox, QCheckBox, QDateEdit, QGroupBox, QSplitter,
                             QMenuBar, QMenu, QStatusBar, QToolBar, QAbstractItemView)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QAction, QIcon, QColor
from datetime import datetime, date
from data_manager import DataManager, TaskType
from models import DailyTask, TodoTask, EntertainmentTask
import config


class TaskManagerMainWindow(QMainWindow):
    """任务管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建三个标签页
        self.create_daily_tab()
        self.create_todo_tab()
        self.create_entertainment_tab()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        import_action = QAction('导入数据', self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        add_daily_action = QAction('添加每日任务', self)
        add_daily_action.triggered.connect(self.add_daily_task)
        edit_menu.addAction(add_daily_action)
        
        add_todo_action = QAction('添加待办事项', self)
        add_todo_action.triggered.connect(self.add_todo_task)
        edit_menu.addAction(add_todo_action)
        
        add_entertainment_action = QAction('添加娱乐任务', self)
        add_entertainment_action.triggered.connect(self.add_entertainment_task)
        edit_menu.addAction(add_entertainment_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        stats_action = QAction('统计信息', self)
        stats_action.triggered.connect(self.show_statistics)
        tools_menu.addAction(stats_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar('工具栏')
        
        # 每日任务工具
        toolbar.addAction('添加每日', self.add_daily_task)
        toolbar.addAction('随机每日', self.random_daily_task)
        
        toolbar.addSeparator()
        
        # 待办事项工具
        toolbar.addAction('添加待办', self.add_todo_task)
        toolbar.addAction('随机待办', self.random_todo_task)
        
        toolbar.addSeparator()
        
        # 娱乐任务工具
        toolbar.addAction('添加娱乐', self.add_entertainment_task)
        toolbar.addAction('随机娱乐', self.random_entertainment_task)
    
    def create_daily_tab(self):
        """创建每日任务标签页"""
        daily_widget = QWidget()
        daily_layout = QVBoxLayout(daily_widget)
        
        # 控制按钮区域
        daily_control_layout = QHBoxLayout()
        
        self.add_daily_btn = QPushButton('添加任务')
        self.add_daily_btn.clicked.connect(self.add_daily_task)
        daily_control_layout.addWidget(self.add_daily_btn)
        
        self.edit_daily_btn = QPushButton('编辑任务')
        self.edit_daily_btn.clicked.connect(self.edit_daily_task)
        daily_control_layout.addWidget(self.edit_daily_btn)
        
        self.delete_daily_btn = QPushButton('删除任务')
        self.delete_daily_btn.clicked.connect(self.delete_daily_task)
        daily_control_layout.addWidget(self.delete_daily_btn)
        
        self.random_daily_btn = QPushButton('随机抽取')
        self.random_daily_btn.clicked.connect(self.random_daily_task)
        daily_control_layout.addWidget(self.random_daily_btn)
        
        # 筛选下拉框
        daily_control_layout.addStretch()
        
        # 星期筛选
        daily_control_layout.addWidget(QLabel('星期:'))
        self.daily_weekday_combo = QComboBox()
        self.daily_weekday_combo.addItems(['全部', '每天'] + ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
        # 设置默认值为今天是星期几
        today_weekday_index = datetime.now().weekday()  # 0是星期一，6是星期日
        weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        if 0 <= today_weekday_index <= 6:
            today_name = weekday_names[today_weekday_index]
            index = self.daily_weekday_combo.findText(today_name)
            if index >= 0:
                self.daily_weekday_combo.setCurrentIndex(index)
        self.daily_weekday_combo.currentTextChanged.connect(self.load_daily_tasks)
        daily_control_layout.addWidget(self.daily_weekday_combo)
        
        # 状态筛选
        daily_control_layout.addWidget(QLabel('状态:'))
        self.daily_status_combo = QComboBox()
        self.daily_status_combo.addItems(['全部', '进行中', '已完成'])
        self.daily_status_combo.currentTextChanged.connect(self.load_daily_tasks)
        daily_control_layout.addWidget(self.daily_status_combo)
        
        daily_layout.addLayout(daily_control_layout)
        
        # 任务表格
        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(5)
        self.daily_table.setHorizontalHeaderLabels(['状态', '标题', '星期', '描述', '创建日期'])
        self.daily_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.daily_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.daily_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.daily_table.cellDoubleClicked.connect(self.edit_daily_task)
        
        daily_layout.addWidget(self.daily_table)
        self.tab_widget.addTab(daily_widget, '每日必做')
    
    def create_todo_tab(self):
        """创建待办事项标签页"""
        todo_widget = QWidget()
        todo_layout = QVBoxLayout(todo_widget)
        
        # 控制按钮区域
        todo_control_layout = QHBoxLayout()
        
        self.add_todo_btn = QPushButton('添加任务')
        self.add_todo_btn.clicked.connect(self.add_todo_task)
        todo_control_layout.addWidget(self.add_todo_btn)
        
        self.edit_todo_btn = QPushButton('编辑任务')
        self.edit_todo_btn.clicked.connect(self.edit_todo_task)
        todo_control_layout.addWidget(self.edit_todo_btn)
        
        self.delete_todo_btn = QPushButton('删除任务')
        self.delete_todo_btn.clicked.connect(self.delete_todo_task)
        todo_control_layout.addWidget(self.delete_todo_btn)
        
        self.random_todo_btn = QPushButton('随机抽取')
        self.random_todo_btn.clicked.connect(self.random_todo_task)
        todo_control_layout.addWidget(self.random_todo_btn)
        
        # 状态筛选下拉框
        todo_control_layout.addStretch()
        todo_control_layout.addWidget(QLabel('状态:'))
        self.todo_status_combo = QComboBox()
        self.todo_status_combo.addItems(['全部', '进行中', '已完成', '已过期'])
        self.todo_status_combo.currentTextChanged.connect(self.load_todo_tasks)
        todo_control_layout.addWidget(self.todo_status_combo)
        
        todo_layout.addLayout(todo_control_layout)
        
        # 任务表格
        self.todo_table = QTableWidget()
        self.todo_table.setColumnCount(6)
        self.todo_table.setHorizontalHeaderLabels(['状态', '标题', '截止日期', '紧急程度', '描述', '创建日期'])
        self.todo_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.todo_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.todo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.todo_table.cellDoubleClicked.connect(self.edit_todo_task)
        
        todo_layout.addWidget(self.todo_table)
        self.tab_widget.addTab(todo_widget, '待办事项')
    
    def create_entertainment_tab(self):
        """创建娱乐任务标签页"""
        entertainment_widget = QWidget()
        entertainment_layout = QVBoxLayout(entertainment_widget)
        
        # 控制按钮区域
        entertainment_control_layout = QHBoxLayout()
        
        self.add_entertainment_btn = QPushButton('添加任务')
        self.add_entertainment_btn.clicked.connect(self.add_entertainment_task)
        entertainment_control_layout.addWidget(self.add_entertainment_btn)
        
        self.edit_entertainment_btn = QPushButton('编辑任务')
        self.edit_entertainment_btn.clicked.connect(self.edit_entertainment_task)
        entertainment_control_layout.addWidget(self.edit_entertainment_btn)
        
        self.delete_entertainment_btn = QPushButton('删除任务')
        self.delete_entertainment_btn.clicked.connect(self.delete_entertainment_task)
        entertainment_control_layout.addWidget(self.delete_entertainment_btn)
        
        self.random_entertainment_btn = QPushButton('随机抽取')
        self.random_entertainment_btn.clicked.connect(self.random_entertainment_task)
        entertainment_control_layout.addWidget(self.random_entertainment_btn)
        
        # 状态筛选下拉框
        entertainment_control_layout.addStretch()
        entertainment_control_layout.addWidget(QLabel('状态:'))
        self.entertainment_status_combo = QComboBox()
        self.entertainment_status_combo.addItems(['全部', '进行中', '已完成'])
        self.entertainment_status_combo.currentTextChanged.connect(self.load_entertainment_tasks)
        entertainment_control_layout.addWidget(self.entertainment_status_combo)
        
        entertainment_layout.addLayout(entertainment_control_layout)
        
        # 任务表格
        self.entertainment_table = QTableWidget()
        self.entertainment_table.setColumnCount(5)
        self.entertainment_table.setHorizontalHeaderLabels(['状态', '标题', '类别', '描述', '创建日期'])
        self.entertainment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entertainment_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.entertainment_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.entertainment_table.cellDoubleClicked.connect(self.edit_entertainment_task)
        
        entertainment_layout.addWidget(self.entertainment_table)
        self.tab_widget.addTab(entertainment_widget, '娱乐任务')
    
    def load_data(self):
        """加载所有数据"""
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()
        self.update_status_bar()
    
    def load_daily_tasks(self):
        """加载每日任务"""
        # 获取筛选条件
        weekday = self.daily_weekday_combo.currentText()
        if weekday == '全部':
            weekday_filter = 'all'
        elif weekday == '每天':
            weekday_filter = 'daily'  # 对应数据库中week_day为空的情况
        else:
            weekday_filter = weekday
        
        status = self.daily_status_combo.currentText()
        if status == '全部':
            status_filter = 'all'
        elif status == '进行中':
            status_filter = 'pending'
        else:  # '已完成'
            status_filter = 'completed'
        
        tasks = self.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)
        
        self.daily_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            # 状态
            status_item = QTableWidgetItem('✓' if task.completed else '○')
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.daily_table.setItem(row, 0, status_item)
            
            # 标题
            self.daily_table.setItem(row, 1, QTableWidgetItem(task.title))
            
            # 星期
            weekday = task.week_day if task.week_day else '每天'
            self.daily_table.setItem(row, 2, QTableWidgetItem(weekday))
            
            # 描述
            self.daily_table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
            
            # 创建日期
            self.daily_table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
            
            # 存储任务ID用于后续操作
            status_item.setData(Qt.ItemDataRole.UserRole, task.id)
        
        self.update_status_bar()
    
    def load_todo_tasks(self):
        """加载待办事项"""
        # 获取筛选条件
        status = self.todo_status_combo.currentText()
        if status == '全部':
            status_filter = 'all'
        elif status == '进行中':
            status_filter = 'pending'
        else:  # '已完成'
            status_filter = 'completed'
        
        tasks = self.data_manager.get_todo_tasks(status=status_filter)
        
        self.todo_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            # 状态
            status_item = QTableWidgetItem('✓' if task.completed else '○')
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.todo_table.setItem(row, 0, status_item)
            
            # 标题
            self.todo_table.setItem(row, 1, QTableWidgetItem(task.title))
            
            # 截止日期
            deadline = task.deadline if task.deadline else '无'
            self.todo_table.setItem(row, 2, QTableWidgetItem(deadline))
            
            # 紧急程度
            self.todo_table.setItem(row, 3, QTableWidgetItem(str(task.urgency_score)))
            
            # 描述
            self.todo_table.setItem(row, 4, QTableWidgetItem(task.description or '-'))
            
            # 创建日期
            self.todo_table.setItem(row, 5, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
            
            # 存储任务ID用于后续操作
            status_item.setData(Qt.ItemDataRole.UserRole, task.id)
        
        self.update_status_bar()
    
    def load_entertainment_tasks(self):
        """加载娱乐任务"""
        # 获取筛选条件
        status = self.entertainment_status_combo.currentText()
        if status == '全部':
            status_filter = 'all'
        elif status == '进行中':
            status_filter = 'pending'
        else:  # '已完成'
            status_filter = 'completed'
        
        tasks = self.data_manager.get_entertainment_tasks(status=status_filter)
        
        self.entertainment_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            # 状态
            status_item = QTableWidgetItem('✓' if task.completed else '○')
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.entertainment_table.setItem(row, 0, status_item)
            
            # 标题
            self.entertainment_table.setItem(row, 1, QTableWidgetItem(task.title))
            
            # 类别
            self.entertainment_table.setItem(row, 2, QTableWidgetItem(task.fun_category))
            
            # 描述
            self.entertainment_table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
            
            # 创建日期
            self.entertainment_table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
            
            # 存储任务ID用于后续操作
            status_item.setData(Qt.ItemDataRole.UserRole, task.id)
        
        self.update_status_bar()
    
    def add_daily_task(self):
        """添加每日任务"""
        dialog = TaskEditDialog(TaskType.DAILY, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_daily_task(
                title=data['title'],
                description=data['description'],
                week_day=data['weekday'],
                completed=data['completed']
            )
            self.load_daily_tasks()
            self.status_bar.showMessage('每日任务添加成功')
    
    def edit_daily_task(self):
        """编辑每日任务"""
        current_row = self.daily_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        item = self.daily_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_daily_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.DAILY, self, task)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_daily_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    week_day=data['weekday'],
                    completed=data['completed']
                )
                self.load_daily_tasks()
                self.status_bar.showMessage('每日任务更新成功')
    
    def delete_daily_task(self):
        """删除每日任务"""
        current_row = self.daily_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        reply = QMessageBox.question(self, '确认', '确定要删除这个任务吗？', 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            item = self.daily_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_daily_task(task_id)
            self.load_daily_tasks()
            self.status_bar.showMessage('每日任务删除成功')
    
    def add_todo_task(self):
        """添加待办事项"""
        dialog = TaskEditDialog(TaskType.TODO, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_todo_task(
                title=data['title'],
                description=data['description'],
                deadline=data['deadline'] if data.get('deadline') else '',
                completed=data['completed']
            )
            self.load_todo_tasks()
            self.status_bar.showMessage('待办事项添加成功')
    
    def edit_todo_task(self):
        """编辑待办事项"""
        current_row = self.todo_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        item = self.todo_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_todo_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.TODO, self, task)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_todo_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    deadline=data['deadline'] if data.get('deadline') else '',
                    completed=data['completed']
                )
                self.load_todo_tasks()
                self.status_bar.showMessage('待办事项更新成功')
    
    def delete_todo_task(self):
        """删除待办事项"""
        current_row = self.todo_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        reply = QMessageBox.question(self, '确认', '确定要删除这个任务吗？', 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            item = self.todo_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_todo_task(task_id)
            self.load_todo_tasks()
            self.status_bar.showMessage('待办事项删除成功')
    
    def add_entertainment_task(self):
        """添加娱乐任务"""
        dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_entertainment_task(
                title=data['title'],
                description=data['description'],
                fun_category=data['fun_category'],
                completed=data['completed']
            )
            self.load_entertainment_tasks()
            self.status_bar.showMessage('娱乐任务添加成功')
    
    def edit_entertainment_task(self):
        """编辑娱乐任务"""
        current_row = self.entertainment_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        item = self.entertainment_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_entertainment_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self, task)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_entertainment_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    fun_category=data['fun_category'],
                    completed=data['completed']
                )
                self.load_entertainment_tasks()
                self.status_bar.showMessage('娱乐任务更新成功')
    
    def delete_entertainment_task(self):
        """删除娱乐任务"""
        current_row = self.entertainment_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, '警告', '请先选择一个任务')
            return
        
        reply = QMessageBox.question(self, '确认', '确定要删除这个任务吗？', 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            item = self.entertainment_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_entertainment_task(task_id)
            self.load_entertainment_tasks()
            self.status_bar.showMessage('娱乐任务删除成功')
    
    def random_daily_task(self):
        """随机抽取每日任务（根据当前筛选条件）"""
        # 获取当前筛选条件
        weekday = self.daily_weekday_combo.currentText()
        if weekday == '全部':
            weekday_filter = 'all'
        elif weekday == '每天':
            weekday_filter = 'daily'
        else:
            weekday_filter = weekday
        
        status = self.daily_status_combo.currentText()
        if status == '全部':
            status_filter = 'all'
        elif status == '进行中':
            status_filter = 'pending'
        else:  # '已完成'
            status_filter = 'completed'
        
        # 根据当前筛选条件获取任务
        tasks = self.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)
        pending_tasks = [t for t in tasks if not t.completed]
        
        if not pending_tasks:
            if not tasks:
                QMessageBox.information(self, '提示', '没有符合条件的每日任务')
            else:
                QMessageBox.information(self, '提示', '没有未完成的符合条件的每日任务')
            return
        
        import random
        task = random.choice(pending_tasks)
        weekday_display = task.week_day if task.week_day else '每天'
        QMessageBox.information(self, '随机抽取', f'建议处理任务：\n\n标题：{task.title}\n星期：{weekday_display}')
    
    def random_todo_task(self):
        """随机抽取待办事项（按权重）"""
        tasks = self.data_manager.get_todo_tasks()
        pending_tasks = [t for t in tasks if not t.completed]
        
        if not pending_tasks:
            QMessageBox.information(self, '提示', '没有未完成的待办事项')
            return
        
        # 按紧急度权重随机选择
        weights = [max(1, t.urgency_score) for t in pending_tasks]
        import random
        total_weight = sum(weights)
        
        if total_weight <= 0:
            task = random.choice(pending_tasks)
        else:
            rand_val = random.uniform(0, total_weight)
            cum_weight = 0
            for i, w in enumerate(weights):
                cum_weight += w
                if rand_val <= cum_weight:
                    task = pending_tasks[i]
                    break
            else:
                task = pending_tasks[-1]  # 防止索引越界
        
        QMessageBox.information(self, '随机抽取', 
                               f'建议处理任务：\n\n标题：{task.title}\n截止日期：{task.deadline or "无"}\n紧急度：{task.urgency_score}')
    
    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        tasks = self.data_manager.get_entertainment_tasks()
        pending_tasks = [t for t in tasks if not t.completed]
        
        if not pending_tasks:
            QMessageBox.information(self, '提示', '没有未完成的娱乐任务')
            return
        
        import random
        task = random.choice(pending_tasks)
        QMessageBox.information(self, '随机抽取', f'建议娱乐：\n\n{task.title}')
    
    def export_data(self):
        """导出数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(self, '导出数据', 'tasks_export.json', 'JSON Files (*.json)')
        if filepath:
            success = self.data_manager.export_to_json(filepath)
            if success:
                QMessageBox.information(self, '成功', '数据导出成功')
            else:
                QMessageBox.critical(self, '错误', '数据导出失败')
    
    def import_data(self):
        """导入数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(self, '导入数据', '', 'JSON Files (*.json)')
        if filepath:
            reply = QMessageBox.question(self, '确认', '导入数据将会覆盖现有数据，确定继续？', 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                success = self.data_manager.import_from_json(filepath)
                if success:
                    self.load_data()  # 重新加载数据
                    QMessageBox.information(self, '成功', '数据导入成功')
                else:
                    QMessageBox.critical(self, '错误', '数据导入失败')
    
    def show_statistics(self):
        """显示统计信息"""
        stats = self.data_manager.get_statistics()
        
        msg = f"""统计信息：
        
每日任务：{stats['daily']['total']} 个 ({stats['daily']['completed']} 已完成)
待办事项：{stats['todo']['total']} 个 ({stats['todo']['completed']} 已完成, {stats['todo']['expired']} 已过期)
娱乐任务：{stats['entertainment']['total']} 个 ({stats['entertainment']['completed']} 已完成)
        
总计：{stats['daily']['total'] + stats['todo']['total'] + stats['entertainment']['total']} 个任务
已完成：{stats['daily']['completed'] + stats['todo']['completed'] + stats['entertainment']['completed']} 个"""
        
        QMessageBox.information(self, '统计信息', msg)
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, '关于', '''任务管理系统 v1.0

功能：
- 每日必做任务管理（支持按星期分类）
- 待办事项管理（带截止日期和紧急程度）
- 娱乐任务管理
- SQLite数据库存储
- 数据导入导出（JSON格式）
- 每日自动重置
- 带权重的随机选择
- 现代化图形界面

作者：AI Assistant
日期：2026年''')
    
    def update_status_bar(self):
        """更新状态栏"""
        stats = self.data_manager.get_statistics()
        msg = f"每日: {stats['daily']['completed']}/{stats['daily']['total']} 完成 | "
        msg += f"待办: {stats['todo']['completed']}/{stats['todo']['total']} 完成 ({stats['todo']['expired']} 过期) | "
        msg += f"娱乐: {stats['entertainment']['completed']}/{stats['entertainment']['total']} 完成"
        self.status_bar.showMessage(msg)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.data_manager.close_session()
        event.accept()


class TaskEditDialog(QDialog):
    """任务编辑对话框"""
    
    def __init__(self, task_type: TaskType, parent=None, task=None):
        super().__init__(parent)
        self.task_type = task_type
        self.task = task
        self.init_ui()
        if task:
            self.load_task_data()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{'编辑' if self.task else '添加'}{self.get_task_type_name()}")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('标题:'))
        self.title_edit = QLineEdit()
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # 描述
        layout.addWidget(QLabel('描述:'))
        self.desc_edit = QTextEdit()
        layout.addWidget(self.desc_edit)
        
        # 任务特定字段
        if self.task_type == TaskType.DAILY:
            weekday_layout = QHBoxLayout()
            weekday_layout.addWidget(QLabel('星期:'))
            self.weekday_combo = QComboBox()
            self.weekday_combo.addItems(['每天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'])
            weekday_layout.addWidget(self.weekday_combo)
            layout.addLayout(weekday_layout)
        elif self.task_type == TaskType.TODO:
            deadline_layout = QHBoxLayout()
            deadline_layout.addWidget(QLabel('截止日期:'))
            self.deadline_date = QDateEdit()
            self.deadline_date.setDisplayFormat('yyyy-MM-dd')
            self.deadline_date.setCalendarPopup(True)
            deadline_layout.addWidget(self.deadline_date)
            layout.addLayout(deadline_layout)
        elif self.task_type == TaskType.ENTERTAINMENT:
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel('类别:'))
            self.category_combo = QComboBox()
            self.category_combo.addItems(['general', 'games', 'movies', 'sports', 'reading', 'music', 'other'])
            category_layout.addWidget(self.category_combo)
            layout.addLayout(category_layout)
        
        # 完成状态
        status_layout = QHBoxLayout()
        self.completed_check = QCheckBox('已完成')
        status_layout.addWidget(self.completed_check)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_task_type_name(self):
        """获取任务类型名称"""
        if self.task_type == TaskType.DAILY:
            return '每日任务'
        elif self.task_type == TaskType.TODO:
            return '待办事项'
        else:
            return '娱乐任务'
    
    def load_task_data(self):
        """加载任务数据到表单"""
        if self.task:
            self.title_edit.setText(self.task.title)
            self.desc_edit.setPlainText(self.task.description or '')
            self.completed_check.setChecked(self.task.completed)
            
            if self.task_type == TaskType.DAILY:
                weekday = self.task.week_day if self.task.week_day else '每天'
                index = self.weekday_combo.findText(weekday)
                if index >= 0:
                    self.weekday_combo.setCurrentIndex(index)
            elif self.task_type == TaskType.TODO:
                if self.task.deadline:
                    try:
                        deadline_date = QDate.fromString(self.task.deadline, 'yyyy-MM-dd')
                        self.deadline_date.setDate(deadline_date)
                    except:
                        pass
            elif self.task_type == TaskType.ENTERTAINMENT:
                index = self.category_combo.findText(self.task.fun_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
    
    def get_data(self):
        """获取表单数据"""
        data = {
            'title': self.title_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'completed': self.completed_check.isChecked()
        }
        
        if self.task_type == TaskType.DAILY:
            weekday = self.weekday_combo.currentText()
            data['weekday'] = '' if weekday == '每天' else weekday
        elif self.task_type == TaskType.TODO:
            if self.deadline_date.date() != QDate(2000, 1, 1):  # 检查是否设置了日期
                data['deadline'] = self.deadline_date.date().toString('yyyy-MM-dd')
            else:
                data['deadline'] = ''
        elif self.task_type == TaskType.ENTERTAINMENT:
            data['fun_category'] = self.category_combo.currentText()
        
        return data


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = TaskManagerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()