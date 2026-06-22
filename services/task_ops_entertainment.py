"""
娱乐任务操作模块
封装娱乐任务的增删改查及随机抽取逻辑
"""

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from managers.data_manager import TaskType
from ui.task_edit_dialog import TaskEditDialog
from utils.ui_messages import (
    show_task_added_confirmation,
    show_task_updated_confirmation,
    show_task_deleted_confirmation,
    warn_no_task_selected,
    confirm_batch_deletion,
    show_random_entertainment_task_dialog,
    inform_no_pending_tasks,
)
from services.random_task_service import pick_random_entertainment_task


class EntertainmentTaskOperations:
    """娱乐任务操作处理器"""

    def __init__(self, window):
        """
        Args:
            window: TaskManagerMainWindow 实例
        """
        self._w = window

    def add_entertainment_task(self):
        """添加娱乐任务"""
        dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self._w, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.create_entertainment_task(
            title=data['title'],
            description=data['description'],
            fun_category=data['fun_category'],
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', ''),
            category=data.get('category', ''),
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]'),
            estimated_duration=data.get('estimated_duration', 0)
        )
        self._w.load_entertainment_tasks()
        self._validate_and_refresh_filter('entertainment')
        show_task_added_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage('娱乐任务添加成功')
        self._w.update_status_bar()

    def edit_entertainment_task(self):
        """编辑选中的娱乐任务"""
        row = self._w.entertainment_table.currentRow()
        if row < 0:
            warn_no_task_selected(self._w)
            return
        if self._w._status_switching_row == row:
            return
        item = self._w.entertainment_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._w.data_manager.get_entertainment_task_by_id(task_id)
        if not task:
            return
        dialog = TaskEditDialog(TaskType.ENTERTAINMENT, self._w, task, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.update_entertainment_task(
            task_id=task_id,
            title=data['title'],
            description=data['description'],
            fun_category=data['fun_category'],
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', ''),
            category=data.get('category', ''),
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]'),
            estimated_duration=data.get('estimated_duration', 0)
        )
        self._w.load_entertainment_tasks()
        self._validate_and_refresh_filter('entertainment')
        show_task_updated_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage('娱乐任务更新成功')
        self._w.update_status_bar()

    def delete_entertainment_task(self):
        """删除选中的娱乐任务（支持批量）"""
        selected_rows = self._w.entertainment_table.selectionModel().selectedRows()
        if not selected_rows:
            warn_no_task_selected(self._w)
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count, self._w) != QMessageBox.StandardButton.Yes:
            return
        task_ids = []
        for row_obj in selected_rows:
            row = row_obj.row()
            item = self._w.entertainment_table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                task_ids.append(task_id)
        deleted = self._w.data_manager.delete_entertainment_tasks_batch(task_ids)
        self._w.load_entertainment_tasks()
        self._auto_cleanup_if_enabled()
        self._validate_and_refresh_filter('entertainment')
        show_task_deleted_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage(f'娱乐任务删除成功 ({deleted}/{count})')
        self._w.update_status_bar()

    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        task = pick_random_entertainment_task(self._w.data_manager)
        if task is None:
            inform_no_pending_tasks('entertainment', self._w)
            return
        show_random_entertainment_task_dialog(task, self._w)

    # 公共方法引用（由主模块提供）
    def _auto_cleanup_if_enabled(self):
        """检查是否启用了自动清理，若是则执行并刷新标签栏"""
        if self._w.is_auto_cleanup_enabled():
            self._w.data_manager.cleanup_unused_tags()
            self._w.daily_tag_filter.refresh_tags()
            self._w.todo_tag_filter.refresh_tags()
            self._w.entertainment_tag_filter.refresh_tags()
            self._w.shortcut_tag_filter.refresh_tags()

    def _validate_and_refresh_filter(self, task_type: str):
        """验证并刷新标签筛选状态"""
        current_tag = self._w.entertainment_tag_filter_value
        filter_bar = self._w.entertainment_tag_filter
        filter_bar.refresh_tags()
        visible_tags = filter_bar.get_visible_tags()
        if current_tag and current_tag not in visible_tags:
            self._w.entertainment_tag_filter_value = ''
            self._w.load_entertainment_tasks()
            filter_bar.update_button_states()
