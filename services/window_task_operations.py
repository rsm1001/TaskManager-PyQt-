"""
任务操作服务
封装 TaskManagerMainWindow 中各任务类型的增删改查操作逻辑
"""

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from managers.data_manager import TaskType
from ui.task_edit_dialog import TaskEditDialog
from dialogs.shortcut_edit_dialog import ShortcutEditDialog
from utils.ui_messages import (
    show_task_added_confirmation,
    show_task_updated_confirmation,
    show_task_deleted_confirmation,
    warn_no_task_selected,
    confirm_task_deletion,
    confirm_batch_deletion,
    show_random_daily_task_dialog,
    show_random_todo_task_dialog,
    show_random_entertainment_task_dialog,
    inform_no_suitable_tasks,
    inform_no_pending_tasks,
)
from services.random_task_service import (
    pick_random_daily_task,
    pick_random_todo_task,
    pick_random_entertainment_task,
)


class TaskOperationHandler:
    """任务操作处理器：封装各类型任务的增删改及随机抽取逻辑"""

    def __init__(self, window):
        """
        Args:
            window: TaskManagerMainWindow 实例
        """
        self._w = window

    # ==================== 每日任务 ====================

    def add_daily_task(self):
        """添加每日任务"""
        dialog = TaskEditDialog(TaskType.DAILY, self._w, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.create_daily_task(
            title=data['title'],
            description=data['description'],
            week_day=data['weekday'],
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', '')
        )
        self._w.load_daily_tasks()
        self._validate_and_refresh_filter('daily')
        show_task_added_confirmation('daily', self._w)
        self._w.status_bar.showMessage('每日任务添加成功')

    def edit_daily_task(self):
        """编辑选中的每日任务"""
        row = self._w.daily_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        item = self._w.daily_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._w.data_manager.get_daily_task_by_id(task_id)
        if not task:
            return
        dialog = TaskEditDialog(TaskType.DAILY, self._w, task, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.update_daily_task(
            task_id=task_id,
            title=data['title'],
            description=data['description'],
            week_day=data['weekday'],
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', '')
        )
        self._w.load_daily_tasks()
        self._validate_and_refresh_filter('daily')
        show_task_updated_confirmation('daily', self._w)
        self._w.status_bar.showMessage('每日任务更新成功')

    def _auto_cleanup_if_enabled(self):
        """检查是否启用了自动清理，若是则执行并刷新标签栏"""
        if self._w.is_auto_cleanup_enabled():
            self._w.data_manager.cleanup_unused_tags()
            self._w.daily_tag_filter.refresh_tags()
            self._w.todo_tag_filter.refresh_tags()
            self._w.entertainment_tag_filter.refresh_tags()
            self._w.shortcut_tag_filter.refresh_tags()

    def _validate_and_refresh_filter(self, task_type: str):
        """
        验证并刷新标签筛选状态。
        当任务发生状态切换、更新、删除后调用，确保当前激活的标签筛选仍然有效。
        如果当前标签在刷新后的可见标签列表中不存在，说明该标签已失效，清空筛选条件并重新加载。

        Args:
            task_type: 任务类型，取值 'daily'、'todo'、'entertainment'、'shortcuts'
        """
        # 获取当前激活的标签和对应的 FilterBar
        if task_type == 'shortcuts':
            current_tag = getattr(self._w, 'current_shortcut_tag_filter', '')
            filter_bar = self._w.shortcut_tag_filter
        else:
            current_tag = self._w.current_tag_filter
            filter_bar = getattr(self._w, f'{task_type}_tag_filter')

        # 先刷新 FilterBar 使其获取最新标签列表
        filter_bar.refresh_tags()
        visible_tags = filter_bar.get_visible_tags()

        # 如果当前标签不在可见列表中，说明该标签已失效
        if current_tag and current_tag not in visible_tags:
            # 清空标签筛选条件
            if task_type == 'shortcuts':
                self._w.current_shortcut_tag_filter = ''
            else:
                self._w.current_tag_filter = ''
            # 重新加载（不带标签过滤），刷新 FilterBar 按钮状态
            self._reload_tasks(task_type)
            filter_bar.update_button_states()

    def _reload_tasks(self, task_type: str):
        """
        根据任务类型重新加载对应的表格数据。
        仅内部使用，不触发验证逻辑。
        """
        if task_type == 'daily':
            self._w.load_daily_tasks()
        elif task_type == 'todo':
            self._w.load_todo_tasks()
        elif task_type == 'entertainment':
            self._w.load_entertainment_tasks()
        elif task_type == 'shortcuts':
            self._w.load_shortcuts()

    def delete_daily_task(self):
        """删除选中的每日任务（支持批量）"""
        selected_rows = self._w.daily_table.selectionModel().selectedRows()
        if not selected_rows:
            warn_no_task_selected()
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count) != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for row_obj in selected_rows:
            row = row_obj.row()
            item = self._w.daily_table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id and self._w.data_manager.delete_daily_task(task_id):
                deleted += 1
        self._w.load_daily_tasks()
        self._auto_cleanup_if_enabled()
        self._validate_and_refresh_filter('daily')
        show_task_deleted_confirmation('daily', self._w)
        self._w.status_bar.showMessage(f'每日任务删除成功 ({deleted}/{count})')

    def reset_today_daily_tasks(self):
        """手动重置今日已完成的每日任务"""
        reply = QMessageBox.question(
            self._w, '确认', '确定要重置今日已完成的每日任务吗?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._w.data_manager.reset_daily_tasks()
        self._w.load_daily_tasks()
        self._validate_and_refresh_filter('daily')
        self._w.update_status_bar()
        self._w.status_bar.showMessage('今日任务已重置')

    def random_daily_task(self):
        """随机抽取每日任务（根据当前筛选条件）"""
        weekday = self._w.daily_weekday_combo.currentText()
        weekday_map = {'全部': 'all', '每天': 'daily'}
        weekday_filter = weekday_map.get(weekday, weekday)

        status = self._w.daily_status_combo.currentText()
        status_map = {'全部': 'all', '进行中': 'pending', '已完成': 'completed'}
        status_filter = status_map.get(status, 'all')

        task = pick_random_daily_task(self._w.data_manager, weekday_filter, status_filter)
        if task is None:
            tasks = self._w.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)
            msg = '没有符合条件的每日任务' if not tasks else None
            if msg:
                inform_no_suitable_tasks(msg)
            else:
                inform_no_pending_tasks('daily')
            return
        show_random_daily_task_dialog(task)

    # ==================== 待办事项 ====================

    def add_todo_task(self):
        """添加待办事项"""
        dialog = TaskEditDialog(TaskType.TODO, self._w, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.create_todo_task(
            title=data['title'],
            description=data['description'],
            deadline=data['deadline'] if data.get('deadline') else '',
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', '')
        )
        self._w.load_todo_tasks()
        self._validate_and_refresh_filter('todo')
        show_task_added_confirmation('todo', self._w)
        self._w.status_bar.showMessage('待办事项添加成功')

    def edit_todo_task(self):
        """编辑选中的待办事项"""
        row = self._w.todo_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        item = self._w.todo_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._w.data_manager.get_todo_task_by_id(task_id)
        if not task:
            return
        dialog = TaskEditDialog(TaskType.TODO, self._w, task, data_manager=self._w.data_manager)
        if dialog.exec() != TaskEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        self._w.data_manager.update_todo_task(
            task_id=task_id,
            title=data['title'],
            description=data['description'],
            deadline=data['deadline'] if data.get('deadline') else '',
            completed=data['completed'],
            status=data.get('status', 'pending'),
            tags=data.get('tags', '')
        )
        self._w.load_todo_tasks()
        self._validate_and_refresh_filter('todo')
        show_task_updated_confirmation('todo', self._w)
        self._w.status_bar.showMessage('待办事项更新成功')

    def delete_todo_task(self):
        """删除选中的待办事项（支持批量）"""
        selected_rows = self._w.todo_table.selectionModel().selectedRows()
        if not selected_rows:
            warn_no_task_selected()
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count) != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for row_obj in selected_rows:
            row = row_obj.row()
            item = self._w.todo_table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id and self._w.data_manager.delete_todo_task(task_id):
                deleted += 1
        self._w.load_todo_tasks()
        self._auto_cleanup_if_enabled()
        self._validate_and_refresh_filter('todo')
        show_task_deleted_confirmation('todo', self._w)
        self._w.status_bar.showMessage(f'待办事项删除成功 ({deleted}/{count})')

    def random_todo_task(self):
        """随机抽取待办事项（按权重）"""
        task = pick_random_todo_task(self._w.data_manager)
        if task is None:
            inform_no_pending_tasks('todo')
            return
        show_random_todo_task_dialog(task)

    # ==================== 娱乐任务 ====================

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
            tags=data.get('tags', '')
        )
        self._w.load_entertainment_tasks()
        self._validate_and_refresh_filter('entertainment')
        show_task_added_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage('娱乐任务添加成功')

    def edit_entertainment_task(self):
        """编辑选中的娱乐任务"""
        row = self._w.entertainment_table.currentRow()
        if row < 0:
            warn_no_task_selected()
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
            tags=data.get('tags', '')
        )
        self._w.load_entertainment_tasks()
        self._validate_and_refresh_filter('entertainment')
        show_task_updated_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage('娱乐任务更新成功')

    def delete_entertainment_task(self):
        """删除选中的娱乐任务（支持批量）"""
        selected_rows = self._w.entertainment_table.selectionModel().selectedRows()
        if not selected_rows:
            warn_no_task_selected()
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count) != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for row_obj in selected_rows:
            row = row_obj.row()
            item = self._w.entertainment_table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id and self._w.data_manager.delete_entertainment_task(task_id):
                deleted += 1
        self._w.load_entertainment_tasks()
        self._auto_cleanup_if_enabled()
        self._validate_and_refresh_filter('entertainment')
        show_task_deleted_confirmation('entertainment', self._w)
        self._w.status_bar.showMessage(f'娱乐任务删除成功 ({deleted}/{count})')

    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        task = pick_random_entertainment_task(self._w.data_manager)
        if task is None:
            inform_no_pending_tasks('entertainment')
            return
        show_random_entertainment_task_dialog(task)

    # ==================== 快捷入口 ====================

    def add_shortcut(self):
        """添加快捷入口"""
        dialog = ShortcutEditDialog(self._w, data_manager=self._w.data_manager)
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not data['title']:
            QMessageBox.warning(self._w, '警告', '请输入快捷入口名称')
            return
        if not data['shortcut_path']:
            QMessageBox.warning(self._w, '警告', '请拖拽文件或文件夹到对话框中')
            return
        self._w.data_manager.create_shortcut('todo', data['title'], data['shortcut_path'], data.get('tags', ''))
        self._w.load_shortcuts()
        self._validate_and_refresh_filter('shortcuts')
        show_task_added_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('快捷入口添加成功')

    def edit_shortcut(self):
        """编辑选中的快捷入口"""
        row = self._w.shortcuts_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        btn = self._w.shortcuts_table.cellWidget(row, 0)
        if btn is None:
            return
        shortcut_id = btn.property('task_id')
        if not shortcut_id:
            return
        shortcuts = self._w.data_manager.get_all_shortcuts()
        shortcut_data = next((s for s in shortcuts if s['id'] == shortcut_id), None)
        if not shortcut_data:
            return
        dialog = ShortcutEditDialog(
            self._w, data_manager=self._w.data_manager,
            initial_title=shortcut_data['title'],
            initial_path=shortcut_data['shortcut_path'],
            initial_tags=shortcut_data.get('tags', '')
        )
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not data['title']:
            QMessageBox.warning(self._w, '警告', '请输入快捷入口名称')
            return
        self._w.data_manager.update_shortcut(
            shortcut_id,
            title=data['title'],
            shortcut_path=data['shortcut_path'],
            tags=data.get('tags', '')
        )
        self._w.load_shortcuts()
        self._validate_and_refresh_filter('shortcuts')
        show_task_updated_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('快捷入口更新成功')

    def delete_shortcut(self):
        """删除选中的快捷入口（支持批量，不经过垃圾桶）"""
        selected_rows = self._w.shortcuts_table.selectionModel().selectedRows()
        if not selected_rows:
            warn_no_task_selected()
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count) != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for row_obj in selected_rows:
            row = row_obj.row()
            btn = self._w.shortcuts_table.cellWidget(row, 0)
            if btn is None:
                continue
            shortcut_id = btn.property('task_id')
            if shortcut_id and self._w.data_manager.delete_shortcut(shortcut_id):
                deleted += 1
        self._w.load_shortcuts()
        self._validate_and_refresh_filter('shortcuts')
        show_task_deleted_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage(f'快捷入口删除成功 ({deleted}/{count})')

    def on_shortcuts_cell_clicked(self, row, col):
        """快捷入口表格单击处理（列0时触发按钮点击）"""
        if col == 0:
            btn = self._w.shortcuts_table.cellWidget(row, 0)
            if btn:
                btn.click()
