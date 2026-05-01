"""
Task Manager - PyQt6 主界面
现代化的任务管理器界面
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QDialog, QLineEdit, QTextEdit, 
                             QLabel, QComboBox, QCheckBox, QDateEdit, QGroupBox, QSplitter,
                             QMenuBar, QMenu, QStatusBar, QToolBar, QAbstractItemView)
from dialogs.json_examples_dialog import JsonExamplesDialog
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QAction, QIcon, QColor
from datetime import datetime, date
from managers.data_manager import DataManager, TaskType
from models.model import DailyTask, TodoTask, EntertainmentTask
from ui.task_edit_dialog import TaskEditDialog
import config.config
from components.ui_components import create_daily_tab_ui, create_todo_tab_ui, create_entertainment_tab_ui
from utils.ui_messages import (show_statistics_dialog, show_about_dialog, show_random_daily_task_dialog, 
                        show_random_todo_task_dialog, show_random_entertainment_task_dialog,
                        show_task_added_confirmation, show_task_updated_confirmation, 
                        show_task_deleted_confirmation, confirm_task_deletion, confirm_data_import,
                        show_import_success, show_import_failure, show_export_success, show_export_failure,
                        warn_no_task_selected, inform_no_suitable_tasks, inform_no_pending_tasks,
                        update_task_row_style)
from components.ui_elements import create_menu_bar, create_toolbar
from services.table_operations import (
    load_daily_tasks_to_table, load_todo_tasks_to_table, load_entertainment_tasks_to_table,
    toggle_daily_task_status, toggle_todo_task_status, toggle_entertainment_task_status,
    sort_todo_table_by_column
)
from managers.data_manager import TaskType


class TaskManagerMainWindow(QMainWindow):
    """任务管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        # 延迟初始化目录（避免导入时副作用）
        config.config.ensure_directories()
        self.data_manager = DataManager()
        self.current_tag_filter = ""  # 当前标签筛选
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(config.config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.config.WINDOW_WIDTH, config.config.WINDOW_HEIGHT)
        
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
        create_menu_bar(self)
    
    def create_toolbar(self):
        """创建工具栏"""
        create_toolbar(self)
    
    def create_daily_tab(self):
        """创建每日任务标签页"""
        daily_widget = create_daily_tab_ui(self)
        self.tab_widget.addTab(daily_widget, '每日必做')
    
    def create_todo_tab(self):
        """创建待办事项标签页"""
        todo_widget = create_todo_tab_ui(self)
        self.tab_widget.addTab(todo_widget, '待办事项')
    
    def create_entertainment_tab(self):
        """创建娱乐任务标签页"""
        entertainment_widget = create_entertainment_tab_ui(self)
        self.tab_widget.addTab(entertainment_widget, '娱乐任务')
    
    def load_data(self):
        """加载所有数据"""
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()
        self.update_status_bar()
    
    def load_daily_tasks(self):
        """加载每日任务"""
        load_daily_tasks_to_table(self)
    
    def toggle_daily_task_status(self, row, column):
        """切换每日任务状态"""
        toggle_daily_task_status(self, row, column)
    
    def load_todo_tasks(self):
        """加载待办事项"""
        load_todo_tasks_to_table(self)
    
    def toggle_todo_task_status(self, row, column):
        """切换待办事项状态"""
        toggle_todo_task_status(self, row, column)
    
    def sort_todo_table_by_column(self, column):
        """根据列进行排序（支持正序和倒序）"""
        sort_todo_table_by_column(self, column)
    
    def load_entertainment_tasks(self):
        """加载娱乐任务"""
        load_entertainment_tasks_to_table(self)
    
    def toggle_entertainment_task_status(self, row, column):
        """切换娱乐任务状态"""
        toggle_entertainment_task_status(self, row, column)
    
    def update_task_row_style(self, table, row, is_completed):
        """更新任务行样式（根据完成状态）"""
        from utils.ui_messages import update_task_row_style as update_style
        update_style(table, row, is_completed)
    
    def add_daily_task(self):
        """添加每日任务"""
        dialog = TaskEditDialog(TaskType.DAILY, self, data_manager=self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_daily_task(
                title=data['title'],
                description=data['description'],
                week_day=data['weekday'],
                completed=data['completed'],
                status=data.get('status', 'pending'),
                tags=data.get('tags', '')
            )
            self.load_daily_tasks()
            show_task_added_confirmation('daily', self)
            self.status_bar.showMessage('每日任务添加成功')
    
    def edit_daily_task(self):
        """编辑每日任务"""
        current_row = self.daily_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        item = self.daily_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_daily_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.DAILY, self, task, data_manager=self.data_manager)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_daily_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    week_day=data['weekday'],
                    completed=data['completed'],
                    status=data.get('status', 'pending'),
                    tags=data.get('tags', '')
                )
                self.load_daily_tasks()
                show_task_updated_confirmation('daily', self)
                self.status_bar.showMessage('每日任务更新成功')
    
    def delete_daily_task(self):
        """删除每日任务"""
        current_row = self.daily_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        reply = confirm_task_deletion()
        if reply == QMessageBox.StandardButton.Yes:
            item = self.daily_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_daily_task(task_id)
            self.load_daily_tasks()
            show_task_deleted_confirmation('daily', self)
            self.status_bar.showMessage('每日任务删除成功')
    
    def reset_today_daily_tasks(self):
        """手动重置今日已完成的每日任务"""
        reply = QMessageBox.question(
            self,
            '确认',
            '确定要重置今日已完成的每日任务吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.reset_daily_tasks()
            self.load_daily_tasks()
            self.update_status_bar()
            self.status_bar.showMessage('今日任务已重置')
    
    def add_todo_task(self):
        """添加待办事项"""
        dialog = TaskEditDialog(TaskType.TODO, self, data_manager=self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_todo_task(
                title=data['title'],
                description=data['description'],
                deadline=data['deadline'] if data.get('deadline') else '',
                completed=data['completed'],
                status=data.get('status', 'pending'),
                tags=data.get('tags', '')
            )
            self.load_todo_tasks()
            show_task_added_confirmation('todo', self)
            self.status_bar.showMessage('待办事项添加成功')
    
    def edit_todo_task(self):
        """编辑待办事项"""
        current_row = self.todo_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        item = self.todo_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_todo_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.TODO, self, task, data_manager=self.data_manager)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_todo_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    deadline=data['deadline'] if data.get('deadline') else '',
                    completed=data['completed'],
                    status=data.get('status', 'pending'),
                    tags=data.get('tags', '')
                )
                self.load_todo_tasks()
                show_task_updated_confirmation('todo', self)
                self.status_bar.showMessage('待办事项更新成功')
    
    def delete_todo_task(self):
        """删除待办事项"""
        current_row = self.todo_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        reply = confirm_task_deletion()
        if reply == QMessageBox.StandardButton.Yes:
            item = self.todo_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_todo_task(task_id)
            self.load_todo_tasks()
            show_task_deleted_confirmation('todo', self)
            self.status_bar.showMessage('待办事项删除成功')
    
    def add_entertainment_task(self):
        """添加娱乐任务"""
        dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self, data_manager=self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.data_manager.create_entertainment_task(
                title=data['title'],
                description=data['description'],
                fun_category=data['fun_category'],
                completed=data['completed'],
                status=data.get('status', 'pending'),
                tags=data.get('tags', '')
            )
            self.load_entertainment_tasks()
            show_task_added_confirmation('entertainment', self)
            self.status_bar.showMessage('娱乐任务添加成功')
    
    def edit_entertainment_task(self):
        """编辑娱乐任务"""
        current_row = self.entertainment_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        item = self.entertainment_table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.data_manager.get_entertainment_task_by_id(task_id)
        
        if task:
            dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self, task, data_manager=self.data_manager)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self.data_manager.update_entertainment_task(
                    task_id=task_id,
                    title=data['title'],
                    description=data['description'],
                    fun_category=data['fun_category'],
                    completed=data['completed'],
                    status=data.get('status', 'pending'),
                    tags=data.get('tags', '')
                )
                self.load_entertainment_tasks()
                show_task_updated_confirmation('entertainment', self)
                self.status_bar.showMessage('娱乐任务更新成功')
    
    def delete_entertainment_task(self):
        """删除娱乐任务"""
        current_row = self.entertainment_table.currentRow()
        if current_row < 0:
            warn_no_task_selected()
            return
        
        reply = confirm_task_deletion()
        if reply == QMessageBox.StandardButton.Yes:
            item = self.entertainment_table.item(current_row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            self.data_manager.delete_entertainment_task(task_id)
            self.load_entertainment_tasks()
            show_task_deleted_confirmation('entertainment', self)
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
                inform_no_suitable_tasks('没有符合条件的每日任务')
            else:
                inform_no_pending_tasks('daily')
            return
        
        import random
        task = random.choice(pending_tasks)
        show_random_daily_task_dialog(task)
    
    def random_todo_task(self):
        """随机抽取待办事项（按权重）"""
        tasks = self.data_manager.get_todo_tasks()
        pending_tasks = [t for t in tasks if not t.completed]
        
        if not pending_tasks:
            inform_no_pending_tasks('todo')
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
        
        show_random_todo_task_dialog(task)
    
    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        tasks = self.data_manager.get_entertainment_tasks()
        pending_tasks = [t for t in tasks if not t.completed]
        
        if not pending_tasks:
            inform_no_pending_tasks('entertainment')
            return
        
        import random
        task = random.choice(pending_tasks)
        show_random_entertainment_task_dialog(task)
    
    def export_data(self):
        """导出数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(self, '导出数据', 'tasks_export.json', 'JSON Files (*.json)')
        if filepath:
            success = self.data_manager.export_to_json(filepath)
            if success:
                show_export_success()
            else:
                show_export_failure()
    
    def import_data(self):
        """导入数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(self, '导入数据', '', 'JSON Files (*.json)')
        if filepath:
            reply = confirm_data_import()
            if reply == QMessageBox.StandardButton.Yes:
                success = self.data_manager.import_from_json(filepath)
                if success:
                    self.load_data()  # 重新加载数据
                    show_import_success()
                    self.status_bar.showMessage('数据导入成功')
                else:
                    show_import_failure()
                    self.status_bar.showMessage('数据导入失败')
    
    def show_statistics(self):
        """显示统计信息"""
        stats = self.data_manager.get_statistics()
        show_statistics_dialog(stats)
    
    def show_json_examples(self):
        """显示JSON导入示例"""
        dialog = JsonExamplesDialog(self)
        dialog.exec()
    
    def show_about(self):
        """显示关于信息"""
        show_about_dialog()
    
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
    
    def open_trash_dialog(self):
        """打开垃圾桶对话框"""
        dialog = TrashDialog(self, self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新所有标签页
            self.load_data()


class TrashDialog(QDialog):
    """垃圾桶对话框 - 查看和恢复已删除任务"""
    
    TYPE_LABELS = {
        'daily': '每日任务',
        'todo': '待办事项',
        'entertainment': '娱乐任务',
    }
    
    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle('垃圾桶')
        self.setModal(True)
        self.resize(700, 500)
        self._init_ui()
        self._load_trashed()
    
    def _init_ui(self):
        """初始化对话框UI"""
        layout = QVBoxLayout(self)
        
        # 顶部筛选区
        top_layout = QHBoxLayout()
        
        # 类型筛选
        top_layout.addWidget(QLabel('类型:'))
        self.type_combo = QComboBox()
        self.type_combo.addItem('全部')
        self.type_combo.addItem('每日任务')
        self.type_combo.addItem('待办事项')
        self.type_combo.addItem('娱乐任务')
        self.type_combo.currentTextChanged.connect(self._load_trashed)
        top_layout.addWidget(self.type_combo)
        
        top_layout.addSpacing(20)
        
        # 搜索框
        top_layout.addWidget(QLabel('搜索:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索标题/描述...')
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_input)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # 任务列表
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        self.trash_table = QTableWidget()
        self.trash_table.setColumnCount(5)
        self.trash_table.setHorizontalHeaderLabels(['类型', '标题', '描述', '删除时间', '操作'])
        self.trash_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.trash_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.trash_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.trash_table)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        restore_btn = QPushButton('恢复选中')
        restore_btn.clicked.connect(self._restore_selected)
        btn_layout.addWidget(restore_btn)
        
        delete_btn = QPushButton('彻底删除')
        delete_btn.clicked.connect(self._purge_selected)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        clear_btn = QPushButton('清空垃圾桶')
        clear_btn.clicked.connect(self._purge_all)
        btn_layout.addWidget(clear_btn)
        
        cancel_btn = QPushButton('关闭')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _get_filter_type(self):
        """获取当前筛选类型"""
        text = self.type_combo.currentText()
        if text == '每日任务':
            return 'daily'
        elif text == '待办事项':
            return 'todo'
        elif text == '娱乐任务':
            return 'entertainment'
        return None
    
    def _load_trashed(self):
        """加载垃圾桶中的任务"""
        filter_type = self._get_filter_type()
        rows = self.data_manager.get_trashed_tasks(task_type=filter_type)
        
        self.trash_table.setRowCount(len(rows))
        for row, (trash_id, task_type, task_id, data_json, deleted_at) in enumerate(rows):
            data = json.loads(data_json)
            
            # 类型
            type_item = QTableWidgetItem(self.TYPE_LABELS.get(task_type, task_type))
            type_item.setData(Qt.ItemDataRole.UserRole, trash_id)
            self.trash_table.setItem(row, 0, type_item)
            
            # 标题
            self.trash_table.setItem(row, 1, QTableWidgetItem(data.get('title', '')))
            
            # 描述
            desc = data.get('description', '')
            if len(desc) > 30:
                desc = desc[:30] + '...'
            self.trash_table.setItem(row, 2, QTableWidgetItem(desc or '-'))
            
            # 删除时间
            try:
                dt = datetime.fromisoformat(deleted_at)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                time_str = deleted_at
            self.trash_table.setItem(row, 3, QTableWidgetItem(time_str))
            
            # 操作提示
            op_item = QTableWidgetItem('双击恢复')
            op_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.trash_table.setItem(row, 4, op_item)
        
        # 双击恢复
        self.trash_table.cellDoubleClicked.connect(self._on_double_click)
    
    def _on_search_changed(self, text):
        """搜索框内容变化，实时过滤表格"""
        keyword = text.strip().lower()
        for row in range(self.trash_table.rowCount()):
            if not keyword:
                self.trash_table.setRowHidden(row, False)
                continue
            # 搜索标题(1)和描述(2)列
            match = False
            for col in [1, 2]:
                item = self.trash_table.item(row, col)
                if item and keyword in item.text().lower():
                    match = True
                    break
            self.trash_table.setRowHidden(row, not match)
    
    def _on_double_click(self, row, column):
        """双击恢复任务"""
        item = self.trash_table.item(row, 0)
        if item:
            trash_id = item.data(Qt.ItemDataRole.UserRole)
            self._do_restore(trash_id)
    
    def _restore_selected(self):
        """恢复选中的任务"""
        row = self.trash_table.currentRow()
        if row < 0:
            QMessageBox.information(self, '提示', '请先选中要恢复的任务')
            return
        item = self.trash_table.item(row, 0)
        if item:
            trash_id = item.data(Qt.ItemDataRole.UserRole)
            self._do_restore(trash_id)
    
    def _do_restore(self, trash_id):
        """执行恢复操作"""
        success = self.data_manager.restore_trashed_task(trash_id)
        if success:
            QMessageBox.information(self, '成功', '任务已恢复')
            self._load_trashed()
            self.accept()  # 通知主窗口刷新
        else:
            QMessageBox.warning(self, '失败', '恢复失败，任务可能已不存在')
    
    def _purge_selected(self):
        """彻底删除选中的任务"""
        row = self.trash_table.currentRow()
        if row < 0:
            QMessageBox.information(self, '提示', '请先选中要删除的任务')
            return
        
        reply = QMessageBox.question(
            self, '确认',
            '彻底删除后无法恢复，确定要删除吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            item = self.trash_table.item(row, 0)
            if item:
                trash_id = item.data(Qt.ItemDataRole.UserRole)
                self.data_manager.purge_trashed_task(trash_id)
                self._load_trashed()
    
    def _purge_all(self):
        """清空垃圾桶"""
        reply = QMessageBox.question(
            self, '确认',
            '清空垃圾桶后所有任务都无法恢复，确定要清空吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            filter_type = self._get_filter_type()
            self.data_manager.purge_all_trashed(task_type=filter_type)
            self._load_trashed()





def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = TaskManagerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()