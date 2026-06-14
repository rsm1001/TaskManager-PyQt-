"""
任务操作服务
封装 TaskManagerMainWindow 中各任务类型的增删改查操作逻辑
按功能垂直划分：每日任务、待办事项、娱乐任务、快捷入口、批量操作
"""

import logging
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from managers.data_manager import TaskType
from ui.task_edit_dialog import TaskEditDialog

logger = logging.getLogger(__name__)
from utils.ui_messages import (
    show_task_added_confirmation,
    show_task_updated_confirmation,
    show_task_deleted_confirmation,
    warn_no_task_selected,
    confirm_batch_deletion,
    show_random_daily_task_dialog,
    inform_no_suitable_tasks,
    inform_no_pending_tasks,
)
from services.random_task_service import (
    pick_random_daily_task,
)
from services.task_ops_todo import TodoTaskOperations
from services.task_ops_entertainment import EntertainmentTaskOperations
from services.task_ops_shortcuts import ShortcutOperations
from dialogs.batch_tag_edit_dialog import BatchTagEditDialog


class TaskOperationHandler:
    """任务操作处理器：封装各类型任务的增删改及随机抽取逻辑"""

    def __init__(self, window):
        """
        Args:
            window: TaskManagerMainWindow 实例
        """
        self._w = window
        # 初始化子操作模块
        self._todo_ops = TodoTaskOperations(window)
        self._entertainment_ops = EntertainmentTaskOperations(window)
        self._shortcut_ops = ShortcutOperations(window)

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
            tags=data.get('tags', ''),
            category=data.get('category', ''),
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]')
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
        if self._w._status_switching_row == row:
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
            tags=data.get('tags', ''),
            category=data.get('category', ''),
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]')
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
        if task_type == 'shortcuts':
            current_tag = getattr(self._w, 'current_shortcut_tag_filter', '')
            filter_bar = self._w.shortcut_tag_filter
        else:
            current_tag = getattr(self._w, f'{task_type}_tag_filter_value', '')
            filter_bar = getattr(self._w, f'{task_type}_tag_filter')

        filter_bar.refresh_tags()
        visible_tags = filter_bar.get_visible_tags()

        if current_tag and current_tag not in visible_tags:
            logger.info(f"[标签筛选] 标签 '{current_tag}' 不在可见列表，已清空 | task_type={task_type}")
            if task_type == 'shortcuts':
                self._w.current_shortcut_tag_filter = ''
            else:
                setattr(self._w, f'{task_type}_tag_filter_value', '')
            self._reload_tasks(task_type)
            filter_bar.update_button_states()

    def _reload_tasks(self, task_type: str):
        """根据任务类型重新加载对应的表格数据"""
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
            warn_no_task_selected(self._w)
            return
        count = len(selected_rows)
        if confirm_batch_deletion(count, self._w) != QMessageBox.StandardButton.Yes:
            return
        task_ids = []
        for row_obj in selected_rows:
            row = row_obj.row()
            item = self._w.daily_table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                task_ids.append(task_id)
        deleted = self._w.data_manager.delete_daily_tasks_batch(task_ids)
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
        show_task_updated_confirmation('daily', self._w)
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
                inform_no_suitable_tasks(msg, self._w)
            else:
                inform_no_pending_tasks('daily', self._w)
            return
        show_random_daily_task_dialog(task, self._w)

    # ==================== 待办事项（委托） ====================

    def add_todo_task(self):
        """添加待办事项"""
        self._todo_ops.add_todo_task()

    def edit_todo_task(self):
        """编辑选中的待办事项"""
        self._todo_ops.edit_todo_task()

    def delete_todo_task(self):
        """删除选中的待办事项（支持批量）"""
        self._todo_ops.delete_todo_task()

    def random_todo_task(self):
        """随机抽取待办事项（按权重）"""
        self._todo_ops.random_todo_task()

    # ==================== 娱乐任务（委托） ====================

    def add_entertainment_task(self):
        """添加娱乐任务"""
        self._entertainment_ops.add_entertainment_task()

    def edit_entertainment_task(self):
        """编辑选中的娱乐任务"""
        self._entertainment_ops.edit_entertainment_task()

    def delete_entertainment_task(self):
        """删除选中的娱乐任务（支持批量）"""
        self._entertainment_ops.delete_entertainment_task()

    def random_entertainment_task(self):
        """随机抽取娱乐任务"""
        self._entertainment_ops.random_entertainment_task()

    # ==================== 快捷入口（委托） ====================

    def add_shortcut(self):
        """添加快捷入口"""
        self._shortcut_ops.add_shortcut()

    def edit_shortcut(self):
        """编辑选中的快捷入口"""
        self._shortcut_ops.edit_shortcut()

    def delete_shortcut(self):
        """删除选中的快捷入口（支持批量，不经过垃圾桶）"""
        self._shortcut_ops.delete_shortcut()

    def on_shortcuts_cell_clicked(self, row, col):
        """快捷入口表格单击处理（列0时触发按钮点击）"""
        self._shortcut_ops.on_shortcuts_cell_clicked(row, col)

    # ==================== 批量改状态 ====================

    def _batch_change_status(self, table, task_type: str, task_ids: list, new_status: str):
        """通用批量修改状态逻辑"""
        updated = 0
        for task_id in task_ids:
            if task_type == 'daily':
                self._w.data_manager.update_daily_task(task_id, status=new_status)
                updated += 1
            elif task_type == 'todo':
                self._w.data_manager.update_todo_task(task_id, status=new_status)
                updated += 1
            elif task_type == 'entertainment':
                self._w.data_manager.update_entertainment_task(task_id, status=new_status)
                updated += 1
        self._reload_tasks(task_type)
        self._validate_and_refresh_filter(task_type)
        show_task_updated_confirmation(task_type, self._w)
        self._w.status_bar.showMessage(f'{task_type} 状态批量更新成功 ({updated}/{len(task_ids)})')

    def _show_batch_status_dialog(self, task_type: str, task_ids: list, table):
        """显示批量选择状态的对话框并执行"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
        dialog = QDialog(self._w)
        dialog.setWindowTitle(f'批量修改{task_type}状态')
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f'将 {len(task_ids)} 个任务修改为:'))

        status_combo = QComboBox()
        status_combo.addItems(['进行中', '已完成', '暂弃'])
        layout.addWidget(status_combo)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(lambda: self._do_batch_status_change(dialog, table, task_type, task_ids, status_combo))
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def _do_batch_status_change(self, dialog, table, task_type, task_ids, status_combo):
        """执行批量状态修改"""
        status_map = {'进行中': 'pending', '已完成': 'completed', '暂弃': 'abandoned'}
        new_status = status_map.get(status_combo.currentText(), 'pending')
        dialog.accept()
        self._batch_change_status(table, task_type, task_ids, new_status)

    def _get_selected_task_ids(self, table) -> list:
        """获取表格选中行的任务ID列表"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return []
        task_ids = []
        for row_obj in selected_rows:
            row = row_obj.row()
            item = table.item(row, 0)
            if item is None:
                continue
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id:
                task_ids.append(task_id)
        return task_ids

    def batch_edit_daily_status(self):
        """批量修改每日任务状态"""
        task_ids = self._get_selected_task_ids(self._w.daily_table)
        if not task_ids:
            warn_no_task_selected(self._w)
            return
        self._show_batch_status_dialog('daily', task_ids, self._w.daily_table)

    def batch_edit_todo_status(self):
        """批量修改待办事项状态"""
        task_ids = self._get_selected_task_ids(self._w.todo_table)
        if not task_ids:
            warn_no_task_selected(self._w)
            return
        self._show_batch_status_dialog('todo', task_ids, self._w.todo_table)

    def batch_edit_entertainment_status(self):
        """批量修改娱乐任务状态"""
        task_ids = self._get_selected_task_ids(self._w.entertainment_table)
        if not task_ids:
            warn_no_task_selected(self._w)
            return
        self._show_batch_status_dialog('entertainment', task_ids, self._w.entertainment_table)

    # ==================== 批量编辑标签 ====================

    def batch_edit_tags(self, task_type: str):
        """批量编辑标签（通用入口）"""
        table = getattr(self._w, f'{task_type}_table', None)
        if table is None:
            return
        task_ids = self._get_selected_task_ids(table)
        if not task_ids:
            warn_no_task_selected(self._w)
            return
        current_tags = set()
        for task_id in task_ids:
            if task_type == 'daily':
                task = self._w.data_manager.get_daily_task_by_id(task_id)
            elif task_type == 'todo':
                task = self._w.data_manager.get_todo_task_by_id(task_id)
            elif task_type == 'entertainment':
                task = self._w.data_manager.get_entertainment_task_by_id(task_id)
            else:
                return
            if task and task.tags:
                for tag in task.tags.split(','):
                    tag = tag.strip()
                    if tag:
                        current_tags.add(tag)
        self._show_batch_tag_dialog(task_type, task_ids, current_tags)

    def _show_batch_tag_dialog(self, task_type: str, task_ids: list, current_tags: set):
        """显示批量编辑标签对话框"""
        dialog = BatchTagEditDialog(
            self._w,
            self._w.data_manager,
            task_type,
            current_tags
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        add_tags, remove_tags = dialog.get_result()
        self._do_batch_edit_tags(task_type, task_ids, add_tags, remove_tags)

    def _do_batch_edit_tags(self, task_type: str, task_ids: list, add_tags: set, remove_tags: set):
        """执行批量标签编辑"""
        updated = 0
        for task_id in task_ids:
            if task_type == 'daily':
                task = self._w.data_manager.get_daily_task_by_id(task_id)
                if not task:
                    continue
                tag_set = set(t.strip() for t in (task.tags or '').split(',') if t.strip())
                tag_set.update(add_tags)
                tag_set.difference_update(remove_tags)
                new_tags = ','.join(sorted(tag_set))
                self._w.data_manager.update_daily_task(task_id, tags=new_tags)
                updated += 1
            elif task_type == 'todo':
                task = self._w.data_manager.get_todo_task_by_id(task_id)
                if not task:
                    continue
                tag_set = set(t.strip() for t in (task.tags or '').split(',') if t.strip())
                tag_set.update(add_tags)
                tag_set.difference_update(remove_tags)
                new_tags = ','.join(sorted(tag_set))
                self._w.data_manager.update_todo_task(task_id, tags=new_tags)
                updated += 1
            elif task_type == 'entertainment':
                task = self._w.data_manager.get_entertainment_task_by_id(task_id)
                if not task:
                    continue
                tag_set = set(t.strip() for t in (task.tags or '').split(',') if t.strip())
                tag_set.update(add_tags)
                tag_set.difference_update(remove_tags)
                new_tags = ','.join(sorted(tag_set))
                self._w.data_manager.update_entertainment_task(task_id, tags=new_tags)
                updated += 1
        self._reload_tasks(task_type)
        self._auto_cleanup_if_enabled()
        self._validate_and_refresh_filter(task_type)
        show_task_updated_confirmation(task_type, self._w)
        self._w.status_bar.showMessage(f'{task_type} 标签批量更新成功 ({updated}/{len(task_ids)})')
