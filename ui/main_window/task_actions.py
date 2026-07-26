"""主窗口的任务、快捷入口与权限设置行为。"""

import logging

from PyQt6.QtWidgets import QInputDialog, QMessageBox

import config.config
from utils.ui_messages import warn_no_task_selected

logger = logging.getLogger(__name__)


class MainWindowTaskActionsMixin:
    """保留菜单信号所需的稳定方法名，并委托任务处理器执行。"""

    def add_daily_task(self):
        self._task_handler.add_daily_task()

    def edit_daily_task(self):
        self._task_handler.edit_daily_task()

    def delete_daily_task(self):
        self._task_handler.delete_daily_task()

    def reset_today_daily_tasks(self):
        self._task_handler.reset_today_daily_tasks()

    def random_daily_task(self):
        self._task_handler.random_daily_task()

    def add_todo_task(self):
        self._task_handler.add_todo_task()

    def edit_todo_task(self):
        self._task_handler.edit_todo_task()

    def delete_todo_task(self):
        self._task_handler.delete_todo_task()

    def random_todo_task(self):
        self._task_handler.random_todo_task()

    def add_entertainment_task(self):
        self._task_handler.add_entertainment_task()

    def edit_entertainment_task(self):
        self._task_handler.edit_entertainment_task()

    def delete_entertainment_task(self):
        self._task_handler.delete_entertainment_task()

    def random_entertainment_task(self):
        self._task_handler.random_entertainment_task()

    def batch_edit_daily_status(self):
        self._task_handler.batch_edit_daily_status()

    def batch_edit_todo_status(self):
        self._task_handler.batch_edit_todo_status()

    def batch_edit_entertainment_status(self):
        self._task_handler.batch_edit_entertainment_status()

    def batch_edit_daily_tags(self):
        self._task_handler.batch_edit_tags('daily')

    def batch_edit_todo_tags(self):
        self._task_handler.batch_edit_tags('todo')

    def batch_edit_entertainment_tags(self):
        self._task_handler.batch_edit_tags('entertainment')

    def add_shortcut(self):
        self._task_handler.add_shortcut()

    def edit_shortcut(self):
        self._task_handler.edit_shortcut()

    def delete_shortcut(self):
        self._task_handler.delete_shortcut()

    def open_shortcut(self):
        row = self.shortcuts_table.currentRow()
        if row < 0:
            warn_no_task_selected()
            return
        button = self.shortcuts_table.cellWidget(row, 0)
        shortcut_id = button.property('task_id') if button else None
        if not shortcut_id:
            return
        self._shortcut_service().open_shortcut(shortcut_id)
        self.load_shortcuts_history()
        self._update_history_limit_label()

    def on_shortcuts_cell_clicked(self, row, column):
        if column == 0:
            button = self.shortcuts_table.cellWidget(row, 0)
            if button:
                button.click()

    def _shortcut_service(self):
        return self.data_manager._service_factory.get_shortcut_operation_service()

    def set_history_limit(self):
        current_limit = self._shortcut_service().get_history_limit()
        new_limit, accepted = QInputDialog.getInt(self, '设置缓存数量', '请输入历史记录缓存数量（1-1000）：', value=current_limit, min=1, max=1000)
        if not accepted:
            return
        self._shortcut_service().set_history_limit(new_limit)
        self._update_history_limit_label()
        self.load_shortcuts_history()
        QMessageBox.information(self, '设置完成', f'历史记录缓存数量已设置为 {new_limit} 条')

    def clear_history(self):
        count = self._shortcut_service().clear_history()
        self.load_shortcuts_history()
        QMessageBox.information(self, '清空完成', f'已清空 {count} 条非置顶历史记录')

    def _update_history_limit_label(self):
        if hasattr(self, 'history_limit_label'):
            self.history_limit_label.setText(f'当前缓存: {self._shortcut_service().get_history_limit()} 条')

    def _load_claude_skip_permission_state(self):
        self._load_permission_state('claude_skip_perm_checkbox', 'get_dangerously_skip_permissions', config.config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_DEFAULT, 'Claude')

    def _load_codex_skip_permission_state(self):
        self._load_permission_state('codex_skip_perm_checkbox', 'get_codex_dangerously_skip_permissions', config.config.CODEX_DANGEROUS_SKIP_PERMISSIONS_DEFAULT, 'Codex')

    def _load_permission_state(self, checkbox_name, getter_name, default, provider):
        checkbox = getattr(self, checkbox_name, None)
        if checkbox is None:
            return
        try:
            enabled = getattr(self._shortcut_service(), getter_name)()
        except Exception:
            logger.warning('加载授权状态失败', extra={'trace_id': provider})
            enabled = default
        checkbox.blockSignals(True)
        checkbox.setChecked(enabled)
        checkbox.blockSignals(False)

    def on_claude_skip_permission_toggled(self, state):
        self._save_permission_state('claude_skip_perm_checkbox', 'set_dangerously_skip_permissions', state, 'Claude')

    def on_codex_skip_permission_toggled(self, state):
        self._save_permission_state('codex_skip_perm_checkbox', 'set_codex_dangerously_skip_permissions', state, 'Codex')

    def _save_permission_state(self, checkbox_name, setter_name, state, provider):
        enabled = bool(state)
        try:
            getattr(self._shortcut_service(), setter_name)(enabled)
            action = '开启' if enabled else '关闭'
            self.status_bar.showMessage(f'已{action} {provider} 授权启动', 3000)
            logger.info('授权设置已更新', extra={'trace_id': provider, 'enabled': enabled})
        except Exception as error:
            logger.exception('保存授权设置失败', extra={'trace_id': provider})
            QMessageBox.warning(self, '保存失败', f'无法保存授权设置: {error}')
            checkbox = getattr(self, checkbox_name)
            checkbox.blockSignals(True)
            checkbox.setChecked(not enabled)
            checkbox.blockSignals(False)
