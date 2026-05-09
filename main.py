"""
Task Manager - PyQt6 主界面
现代化的任务管理器界面
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QTabWidget, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QDialog, QLineEdit, QTextEdit,
                             QLabel, QComboBox, QCheckBox, QDateEdit, QGroupBox, QSplitter,
                             QMenuBar, QMenu, QStatusBar, QAbstractItemView)
from dialogs.json_examples_dialog import JsonExamplesDialog
from dialogs.trash_dialog import TrashDialog
from dialogs.shortcut_edit_dialog import ShortcutEditDialog
from services.random_task_service import (
    pick_random_daily_task,
    pick_random_todo_task,
    pick_random_entertainment_task,
)
from PyQt6.QtCore import Qt, QDate
from datetime import date
from managers.data_manager import DataManager, TaskType
from models.model import DailyTask, TodoTask, EntertainmentTask
from ui.task_edit_dialog import TaskEditDialog
import config.config
from components.ui_components import create_daily_tab_ui, create_todo_tab_ui, create_entertainment_tab_ui, create_shortcuts_tab_ui
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
    sort_todo_table_by_column, load_shortcuts_to_table
)
from managers.data_manager import TaskType


class TaskManagerMainWindow(QMainWindow):
    """任务管理器主窗口"""

    def __init__(self):
        super().__init__()
        # 延迟初始化目录(避免导入时副作用)
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

        # 创建三个标签页 + 快捷入口标签页
        self.create_daily_tab()
        self.create_todo_tab()
        self.create_entertainment_tab()
        self.create_shortcuts_tab()

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

    def create_shortcuts_tab(self):
        """创建快捷入口标签页"""
        shortcuts_widget = create_shortcuts_tab_ui(self)
        self.tab_widget.addTab(shortcuts_widget, '快捷入口')

    def load_data(self):
        """加载所有数据"""
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()
        self.load_shortcuts()
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
        """根据列进行排序(支持正序和倒序)"""
        sort_todo_table_by_column(self, column)

    def load_entertainment_tasks(self):
        """加载娱乐任务"""
        load_entertainment_tasks_to_table(self)

    def toggle_entertainment_task_status(self, row, column):
        """切换娱乐任务状态"""
        toggle_entertainment_task_status(self, row, column)

    def update_task_row_style(self, table, row, is_completed):
        """更新任务行样式(根据完成状态)"""
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
            '确定要重置今日已完成的每日任务吗?',
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

    # ==================== 快捷入口相关方法 ====================

    def load_shortcuts(self):
        """加载快捷入口"""
        load_shortcuts_to_table(self)

    def add_shortcut(self):
        """添加快捷入口"""
        dialog = ShortcutEditDialog(self, data_manager=self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, '警告', '请输入快捷入口名称')
                return
            if not data['shortcut_path']:
                QMessageBox.warning(self, '警告', '请拖拽文件或文件夹到对话框中')
                return
            # 默认添加到待办分类
            self.data_manager.create_shortcut('todo', data['title'], data['shortcut_path'])
            self.load_shortcuts()
            show_task_added_confirmation('shortcut', self)
            self.status_bar.showMessage('快捷入口添加成功')

    def edit_shortcut(self):
        """编辑选中的快捷入口"""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        btn = self.shortcuts_table.cellWidget(row, 0)
        if btn is None:
            return
        shortcut_id = btn.property('task_id')
        if not shortcut_id:
            return

        # 获取当前数据
        shortcuts = self.data_manager.get_all_shortcuts()
        shortcut_data = None
        for s in shortcuts:
            if s['id'] == shortcut_id:
                shortcut_data = s
                break
        if not shortcut_data:
            return

        dialog = ShortcutEditDialog(
            self,
            data_manager=self.data_manager,
            initial_title=shortcut_data['title'],
            initial_path=shortcut_data['shortcut_path']
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, '警告', '请输入快捷入口名称')
                return
            self.data_manager.update_shortcut(
                shortcut_id,
                title=data['title'],
                shortcut_path=data['shortcut_path']
            )
            self.load_shortcuts()
            show_task_updated_confirmation('shortcut', self)
            self.status_bar.showMessage('快捷入口更新成功')

    def delete_shortcut(self):
        """删除选中的快捷入口（不经过垃圾桶）"""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        btn = self.shortcuts_table.cellWidget(row, 0)
        if btn is None:
            return
        shortcut_id = btn.property('task_id')
        if not shortcut_id:
            return
        reply = confirm_task_deletion()
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.delete_shortcut(shortcut_id)
            self.load_shortcuts()
            show_task_deleted_confirmation('shortcut', self)
            self.status_bar.showMessage('快捷入口删除成功')

    def open_shortcut(self):
        """打开选中的快捷入口（直接打开文件或文件夹）"""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        btn = self.shortcuts_table.cellWidget(row, 0)
        if btn is None:
            return
        shortcut_path = btn.toolTip() if btn.toolTip() else ''
        if not shortcut_path:
            item = self.shortcuts_table.item(row, 2)
            if item:
                shortcut_path = item.text()
        if shortcut_path and shortcut_path != '-':
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            import os
            if os.path.isfile(shortcut_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(shortcut_path))
            elif os.path.isdir(shortcut_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(shortcut_path))

    def on_shortcuts_cell_clicked(self, row, col):
        """快捷入口表格单击处理（列0时直接打开）"""
        if col == 0:
            btn = self.shortcuts_table.cellWidget(row, 0)
            if btn:
                btn.click()  # 触发按钮点击 = 直接打开

    def random_daily_task(self):
        """随机抽取每日任务(根据当前筛选条件)"""
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
        else:
            status_filter = 'completed'

        task = pick_random_daily_task(self.data_manager, weekday_filter, status_filter)
        if task is None:
            tasks = self.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)
            if not tasks:
                inform_no_suitable_tasks('没有符合条件的每日任务')
            else:
                inform_no_pending_tasks('daily')
            return
        show_random_daily_task_dialog(task)

    def random_todo_task(self):
        """随机抽取待办事项(按权重)"""
        task = pick_random_todo_task(self.data_manager)
        if task is None:
            inform_no_pending_tasks('todo')
            return
        show_random_todo_task_dialog(task)

    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        task = pick_random_entertainment_task(self.data_manager)
        if task is None:
            inform_no_pending_tasks('entertainment')
            return
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


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = TaskManagerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()