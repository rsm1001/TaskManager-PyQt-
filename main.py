"""
Task Manager - PyQt6 主界面
现代化的任务管理器界面
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QDialog, QMessageBox, QStatusBar
from PyQt6.QtCore import Qt
from dialogs.json_examples_dialog import JsonExamplesDialog
from dialogs.trash_dialog import TrashDialog
from managers.data_manager import DataManager, TaskType
from components.ui_components import (
    create_daily_tab_ui,
    create_todo_tab_ui,
    create_entertainment_tab_ui,
    create_shortcuts_tab_ui,
    create_search_tab_ui,
)
from components.ui_elements import create_menu_bar, create_toolbar
from services.table_operations import (
    load_daily_tasks_to_table,
    load_todo_tasks_to_table,
    load_entertainment_tasks_to_table,
    toggle_daily_task_status,
    toggle_todo_task_status,
    toggle_entertainment_task_status,
    sort_todo_table_by_column,
    load_shortcuts_to_table,
    load_search_results_to_table,
)
from services.window_task_operations import TaskOperationHandler
from utils.ui_messages import show_statistics_dialog, show_about_dialog
from utils.ui_messages import show_export_success, show_export_failure
from utils.ui_messages import show_import_success, show_import_failure, confirm_data_import
from utils.logging_config import setup_logging, get_logger

import config.config

# 初始化日志系统（尽早初始化）
setup_logging(log_level=config.config.LOG_LEVEL)
logger = get_logger(__name__)


class TaskManagerMainWindow(QMainWindow):
    """任务管理器主窗口"""

    def __init__(self):
        super().__init__()
        # 延迟初始化目录（避免导入时副作用）
        config.config.ensure_directories()
        self.data_manager = DataManager()
        # 初始化任务操作处理器
        self._task_handler = TaskOperationHandler(self)
        self.current_tag_filter = ""  # 当前标签筛选
        # 状态切换防双击/防抖
        self._status_switching_row = -1   # 当前正在处理状态切换的行（-1表示无）
        self._status_switch_timestamps = {}  # task_id -> 上次切换时间戳(ms)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(config.config.WINDOW_TITLE)
        self.setGeometry(100, 100, config.config.WINDOW_WIDTH, config.config.WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.create_search_tab()
        self.create_daily_tab()
        self.create_todo_tab()
        self.create_entertainment_tab()
        self.create_shortcuts_tab()

        self.create_menu_bar()
        self.create_toolbar()

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

    def create_search_tab(self):
        """创建全局搜索标签页"""
        search_widget = create_search_tab_ui(self)
        self.tab_widget.insertTab(0, search_widget, '搜索')

    def load_data(self):
        """加载所有数据"""
        self.load_daily_tasks()
        self.load_todo_tasks()
        self.load_entertainment_tasks()
        self.load_shortcuts()
        self.update_status_bar()

    # ==================== 加载与切换 ====================

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

    def load_shortcuts(self):
        """加载快捷入口"""
        load_shortcuts_to_table(self)

    # ==================== 全局搜索 ====================

    def on_search_text_changed(self, text: str):
        """搜索框文字变化时加载搜索结果"""
        if not text.strip():
            self.search_results_table.setRowCount(0)
            self.search_status_label.setText('请输入关键词搜索')
            return
        load_search_results_to_table(self)

    def on_search_clear(self):
        """清除搜索"""
        self.search_input.clear()
        self.search_results_table.setRowCount(0)
        self.search_status_label.setText('请输入关键词搜索')

    def on_search_result_double_click(self, row: int, column: int):
        """双击搜索结果行，跳转到对应任务的Tab并选中"""
        type_item = self.search_results_table.item(row, 0)
        if type_item is None:
            return

        task_type_map = {
            '每日任务': 'daily',
            '待办事项': 'todo',
            '娱乐任务': 'entertainment',
            '快捷入口': 'shortcuts',
        }

        type_text = type_item.text()
        target_tab = task_type_map.get(type_text)
        if target_tab is None:
            return

        # 获取任务ID（存储在类型列的UserRole中）
        task_id = type_item.data(Qt.ItemDataRole.UserRole)

        # 切换到对应Tab（Tab 0是搜索，所以索引要+1）
        tab_index_map = {
            'daily': 1,
            'todo': 2,
            'entertainment': 3,
            'shortcuts': 4,
        }
        target_index = tab_index_map.get(target_tab)
        if target_index is not None:
            self.tab_widget.setCurrentIndex(target_index)
            # 选中对应行
            self._select_task_in_table(target_tab, task_id)

    def _select_task_in_table(self, task_type: str, task_id: str):
        """在指定类型的表格中选中指定ID的任务"""
        table_map = {
            'daily': (self.daily_table, self.load_daily_tasks),
            'todo': (self.todo_table, self.load_todo_tasks),
            'entertainment': (self.entertainment_table, self.load_entertainment_tasks),
            'shortcuts': (self.shortcuts_table, self.load_shortcuts),
        }

        table, reload_func = table_map.get(task_type, (None, None))
        if table is None:
            return

        # 重新加载表格确保数据最新
        reload_func()

        # 查找并选中对应行
        for row in range(table.rowCount()):
            if task_type == 'shortcuts':
                # 快捷入口的task_id存储在按钮属性中
                btn = table.cellWidget(row, 0)
                if btn and btn.property('task_id') == task_id:
                    table.selectRow(row)
                    return
            else:
                # 普通任务的task_id存储在UserRole中
                item = table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                    table.selectRow(row)
                    table.scrollToItem(item)
                    return

    # ==================== 每日任务操作（委托） ====================

    def add_daily_task(self):
        """添加每日任务"""
        self._task_handler.add_daily_task()

    def edit_daily_task(self):
        """编辑每日任务"""
        self._task_handler.edit_daily_task()

    def delete_daily_task(self):
        """删除每日任务"""
        self._task_handler.delete_daily_task()

    def reset_today_daily_tasks(self):
        """手动重置今日已完成的每日任务"""
        self._task_handler.reset_today_daily_tasks()

    def random_daily_task(self):
        """随机抽取每日任务（根据当前筛选条件）"""
        self._task_handler.random_daily_task()

    # ==================== 待办事项操作（委托） ====================

    def add_todo_task(self):
        """添加待办事项"""
        self._task_handler.add_todo_task()

    def edit_todo_task(self):
        """编辑待办事项"""
        self._task_handler.edit_todo_task()

    def delete_todo_task(self):
        """删除待办事项"""
        self._task_handler.delete_todo_task()

    def random_todo_task(self):
        """随机抽取待办事项（按权重）"""
        self._task_handler.random_todo_task()

    # ==================== 娱乐任务操作（委托） ====================

    def add_entertainment_task(self):
        """添加娱乐任务"""
        self._task_handler.add_entertainment_task()

    def edit_entertainment_task(self):
        """编辑娱乐任务"""
        self._task_handler.edit_entertainment_task()

    def delete_entertainment_task(self):
        """删除娱乐任务"""
        self._task_handler.delete_entertainment_task()

    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        self._task_handler.random_entertainment_task()

    # ==================== 批量操作（委托） ====================

    def batch_edit_daily_status(self):
        """批量修改每日任务状态"""
        self._task_handler.batch_edit_daily_status()

    def batch_edit_todo_status(self):
        """批量修改待办事项状态"""
        self._task_handler.batch_edit_todo_status()

    def batch_edit_entertainment_status(self):
        """批量修改娱乐任务状态"""
        self._task_handler.batch_edit_entertainment_status()

    def batch_edit_daily_tags(self):
        """批量编辑每日任务标签"""
        self._task_handler.batch_edit_tags('daily')

    def batch_edit_todo_tags(self):
        """批量编辑待办事项标签"""
        self._task_handler.batch_edit_tags('todo')

    def batch_edit_entertainment_tags(self):
        """批量编辑娱乐任务标签"""
        self._task_handler.batch_edit_tags('entertainment')

    # ==================== 快捷入口操作（委托） ====================

    def add_shortcut(self):
        """添加快捷入口"""
        self._task_handler.add_shortcut()

    def edit_shortcut(self):
        """编辑选中的快捷入口"""
        self._task_handler.edit_shortcut()

    def delete_shortcut(self):
        """删除选中的快捷入口（不经过垃圾桶）"""
        self._task_handler.delete_shortcut()

    def open_shortcut(self):
        """打开选中的快捷入口"""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            from utils.ui_messages import warn_no_task_selected
            warn_no_task_selected()
            return
        btn = self.shortcuts_table.cellWidget(row, 0)
        if btn is None:
            return
        shortcut_id = btn.property('task_id')
        if not shortcut_id:
            return
        # 获取快捷入口数据以确定操作类型
        shortcuts = self.data_manager.get_all_shortcuts()
        shortcut_data = next((s for s in shortcuts if s['id'] == shortcut_id), None)
        if not shortcut_data:
            return
        from services.table_operations import _open_shortcut_path
        _open_shortcut_path(shortcut_data['shortcut_path'], shortcut_data.get('action_type', 'open'))

    def on_shortcuts_cell_clicked(self, row, col):
        """快捷入口表格单击处理（列0时触发按钮点击）"""
        if col == 0:
            btn = self.shortcuts_table.cellWidget(row, 0)
            if btn:
                btn.click()

    # ==================== 数据导入导出 ====================

    def export_data(self):
        """导出数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, '导出数据', 'tasks_export.json', 'JSON Files (*.json)'
        )
        if not filepath:
            return
        success = self.data_manager.export_to_json(filepath)
        if success:
            show_export_success()
        else:
            show_export_failure()

    def import_data(self):
        """导入数据"""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, '导入数据', '', 'JSON Files (*.json)'
        )
        if not filepath:
            return
        if confirm_data_import(self) != QMessageBox.StandardButton.Yes:
            return
        success = self.data_manager.import_from_json(filepath)
        if success:
            self.load_data()
            show_import_success(self)
            self.status_bar.showMessage('数据导入成功')
        else:
            show_import_failure(self)
            self.status_bar.showMessage('数据导入失败')

    # ==================== 其他 ====================

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
        show_about_dialog(self)

    def update_status_bar(self):
        """更新状态栏"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        try:
            stats = self.data_manager.get_statistics()
            msg = (f"每日: {stats['daily']['completed']}/{stats['daily']['total']} 完成 | "
                   f"待办: {stats['todo']['completed']}/{stats['todo']['total']} 完成 "
                   f"({stats['todo']['expired']} 过期) | "
                   f"娱乐: {stats['entertainment']['completed']}/{stats['entertainment']['total']} 完成")
            logger.info(f"设置状态栏: {msg}")
            self.status_bar.showMessage(msg, 0)  # 0 表示永久显示，不自动消失
        except Exception as e:
            logger.error(f"更新状态栏失败: {e}\n{traceback.format_exc()}")
            self.status_bar.showMessage(f"获取统计数据时出错: {e}", 0)

    def update_task_row_style(self, table, row, is_completed):
        """更新任务行样式（根据完成状态）"""
        from utils.ui_messages import update_task_row_style as update_style
        update_style(table, row, is_completed)

    def closeEvent(self, event):
        """关闭事件处理"""
        self.data_manager.close_session()
        event.accept()

    def open_trash_dialog(self):
        """打开垃圾桶对话框"""
        dialog = TrashDialog(self, self.data_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def is_auto_cleanup_enabled(self) -> bool:
        """检查是否启用了自动检测删除未使用标签"""
        return self.data_manager.get_config('auto_cleanup_unused_tags', '0') == '1'

    def cleanup_unused_tags_manual(self):
        """手动清理所有类别中未被任务使用的标签"""
        result = self.data_manager.cleanup_unused_tags()
        total_cleaned = sum(result.values())
        self.daily_tag_filter.refresh_tags()
        self.todo_tag_filter.refresh_tags()
        self.entertainment_tag_filter.refresh_tags()
        self.shortcut_tag_filter.refresh_tags()
        QMessageBox.information(
            self, '清理完成',
            f'共清理了 {total_cleaned} 个未使用标签\n'
            f'每日任务: {result.get("daily", 0)} 个\n'
            f'待办事项: {result.get("todo", 0)} 个\n'
            f'娱乐任务: {result.get("entertainment", 0)} 个\n'
            f'快捷入口: {result.get("shortcut", 0)} 个'
        )
        self.status_bar.showMessage(f'标签清理完成，共删除 {total_cleaned} 个未使用标签')


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = TaskManagerMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
