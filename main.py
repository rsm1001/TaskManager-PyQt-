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


class TaskManagerMainWindow(QMainWindow):
    """任务管理器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
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
    
    def toggle_daily_task_status(self, row, column):
        """切换每日任务状态"""
        if column == 0:  # 状态列
            item = self.daily_table.item(row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                # 切换状态
                task = self.data_manager.get_daily_task_by_id(task_id)
                if task:
                    new_status = not task.completed
                    self.data_manager.update_daily_task(task_id=task_id, completed=new_status)
                    
                    # 重新加载任务以确保数据一致性
                    self.load_daily_tasks()
                    
                    # 清除选中状态
                    self.daily_table.clearSelection()
    
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
    
    def toggle_todo_task_status(self, row, column):
        """切换待办事项状态"""
        if column == 0:  # 状态列
            item = self.todo_table.item(row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                # 切换状态
                task = self.data_manager.get_todo_task_by_id(task_id)
                if task:
                    new_status = not task.completed
                    self.data_manager.update_todo_task(task_id=task_id, completed=new_status)
                    
                    # 重新加载任务以确保数据一致性
                    self.load_todo_tasks()
                    
                    # 清除选中状态
                    self.todo_table.clearSelection()
    
    def sort_todo_table_by_column(self, column):
        """根据列进行排序（支持正序和倒序）"""
        # 如果点击的是同一列，则切换排序顺序（升序->降序->原始顺序）
        if self.todo_sort_column == column:
            if self.todo_sort_order == Qt.SortOrder.AscendingOrder:
                self.todo_sort_order = Qt.SortOrder.DescendingOrder
            elif self.todo_sort_order == Qt.SortOrder.DescendingOrder:
                # 第三次点击恢复原始顺序（不排序）
                self.todo_sort_column = -1
                self.todo_sort_order = Qt.SortOrder.AscendingOrder
                self.load_todo_tasks()  # 重新加载原始数据
                return
        else:
            # 如果点击的是不同列，开始新列的升序排序
            self.todo_sort_column = column
            self.todo_sort_order = Qt.SortOrder.AscendingOrder

        # 获取当前筛选状态
        status = self.todo_status_combo.currentText()
        if status == '全部':
            status_filter = 'all'
        elif status == '进行中':
            status_filter = 'pending'
        else:  # '已完成' 或 '已过期'
            status_filter = 'completed'

        tasks = self.data_manager.get_todo_tasks(status=status_filter)
        
        # 根据列进行排序
        if column == 0:  # 状态列
            tasks.sort(key=lambda x: x.completed, reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))
        elif column == 1:  # 标题列
            tasks.sort(key=lambda x: x.title.lower(), reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))
        elif column == 2:  # 截止日期列
            # 处理可能的空截止日期
            tasks.sort(key=lambda x: (x.deadline or ''), reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))
        elif column == 3:  # 紧急程度列
            tasks.sort(key=lambda x: x.urgency_score, reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))
        elif column == 4:  # 描述列
            tasks.sort(key=lambda x: (x.description or '').lower(), reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))
        elif column == 5:  # 创建日期列
            tasks.sort(key=lambda x: x.created_at, reverse=(self.todo_sort_order == Qt.SortOrder.DescendingOrder))

        # 更新表格显示
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
    
    def toggle_entertainment_task_status(self, row, column):
        """切换娱乐任务状态"""
        if column == 0:  # 状态列
            item = self.entertainment_table.item(row, 0)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                # 切换状态
                task = self.data_manager.get_entertainment_task_by_id(task_id)
                if task:
                    new_status = not task.completed
                    self.data_manager.update_entertainment_task(task_id=task_id, completed=new_status)
                    
                    # 重新加载任务以确保数据一致性
                    self.load_entertainment_tasks()
                    
                    # 清除选中状态
                    self.entertainment_table.clearSelection()
    
    def update_task_row_style(self, table, row, is_completed):
        """更新任务行样式（根据完成状态）"""
        from utils.ui_messages import update_task_row_style as update_style
        update_style(table, row, is_completed)
    
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
            self.status_bar.showMessage(show_task_added_confirmation('daily'))
    
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
                self.status_bar.showMessage(show_task_updated_confirmation('daily'))
    
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
            self.status_bar.showMessage(show_task_deleted_confirmation('daily'))
    
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
            self.status_bar.showMessage(show_task_added_confirmation('todo'))
    
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
                self.status_bar.showMessage(show_task_updated_confirmation('todo'))
    
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
            self.status_bar.showMessage(show_task_deleted_confirmation('todo'))
    
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
            self.status_bar.showMessage(show_task_added_confirmation('entertainment'))
    
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
                self.status_bar.showMessage(show_task_updated_confirmation('entertainment'))
    
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
            self.status_bar.showMessage(show_task_deleted_confirmation('entertainment'))
    
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





def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = TaskManagerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()