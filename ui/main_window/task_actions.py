"""主窗口的任务、快捷入口与权限设置行为。"""

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QCursor

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

    def add_child_shortcut(self, parent_id=None):
        self._task_handler.add_child_shortcut(parent_id)

    def edit_shortcut(self):
        self._task_handler.edit_shortcut()

    def delete_shortcut(self):
        self._task_handler.delete_shortcut()

    def open_shortcut(self):
        item = self.shortcuts_table.currentItem()
        if item is None:
            warn_no_task_selected()
            return
        shortcut_id = item.data(0, self._shortcut_user_role())
        if not shortcut_id:
            return
        shortcut_data = item.data(0, Qt.ItemDataRole.UserRole + 1) or {}
        is_workspace = (
            shortcut_data.get('category') == 'workspace'
            or self._workspace_service().get_workspace(shortcut_id)
        )
        if is_workspace:
            self.launch_agent_workspace(shortcut_id)
        else:
            self._shortcut_service().open_shortcut(shortcut_id)
        self.load_shortcuts_history()
        self._update_history_limit_label()

    @staticmethod
    def _shortcut_user_role():
        from PyQt6.QtCore import Qt
        return Qt.ItemDataRole.UserRole

    def on_shortcuts_cell_clicked(self, row, column):
        return None

    def show_shortcut_context_menu(self, position):
        from PyQt6.QtWidgets import QMenu
        item = self.shortcuts_table.itemAt(position)
        if item is None:
            return
        self.shortcuts_table.setCurrentItem(item)
        data = item.data(0, Qt.ItemDataRole.UserRole + 1) or {}
        shortcut_id = data.get('id') or item.data(0, Qt.ItemDataRole.UserRole)
        workspace = self._workspace_service().get_workspace(shortcut_id) if shortcut_id else None
        menu = QMenu(self)
        add_child_action = None
        configure_repo_action = None
        new_workspace_action = None
        active_limit_action = None
        pool_size_action = None
        launch_workspace_action = None
        force_stop_workspace_action = None
        force_delete_workspace_action = None
        status_workspace_action = None
        recycle_workspace_action = None
        merge_workspace_action = None
        open_workspace_directory_action = None
        merge_provider_action = None
        merge_instruction_action = None
        reset_merge_instruction_action = None
        vscode_add_action = menu.addAction('加入 VS Code 工作区')
        vscode_remove_action = menu.addAction('移出 VS Code 工作区')
        cleanup_branches_action = menu.addAction('\u6e05\u9664\u975e\u4e3b\u5206\u652f\uff08master/main\uff09')
        menu.addSeparator()
        if workspace:
            launch_workspace_action = menu.addAction('启动本地项目')
            open_workspace_directory_action = menu.addAction('打开工作目录')
            if workspace.get('runtime_state') == 'running':
                force_stop_workspace_action = menu.addAction('强制关闭本地项目')
            force_delete_workspace_action = menu.addAction('\u5f3a\u5236\u5220\u9664\u667a\u80fd\u4f53\u5de5\u4f5c\u533a')
            status_workspace_action = menu.addAction('查看 Git 工作区状态')
            if workspace.get('state') == 'active':
                provider_name = 'Codex' if self._workspace_service().get_merge_provider() == 'codex' else 'Claude Code'
                merge_workspace_action = menu.addAction('交给 {} 合并分支'.format(provider_name))
                recycle_workspace_action = menu.addAction('确认已合并并归还工作区')
            menu.addSeparator()
        elif not data.get('parent_id'):
            add_child_action = menu.addAction('新增普通子快捷入口')
            new_workspace_action = menu.addAction('快速新建智能体子类')
            configure_repo_action = menu.addAction('配置仓库与启动脚本')
            active_limit_action = menu.addAction('设置同时开发子类上限')
            pool_size_action = menu.addAction('设置空闲工作区保留数量')
            merge_provider_action = menu.addAction('设置合并智能体（Codex / Claude Code）')
            merge_instruction_action = menu.addAction('编辑合并指令')
            reset_merge_instruction_action = menu.addAction('恢复默认合并指令')
            menu.addSeparator()
        else:
            add_child_action = menu.addAction('新增普通子快捷入口')
            menu.addSeparator()
        edit_action = menu.addAction('Edit')
        delete_action = menu.addAction('Delete')
        chosen = menu.exec(self.shortcuts_table.viewport().mapToGlobal(position))
        if chosen is vscode_add_action:
            self.add_shortcut_to_vscode_workspace(shortcut_id)
        elif chosen is vscode_remove_action:
            self.remove_shortcut_from_vscode_workspace(shortcut_id)
        elif chosen is cleanup_branches_action:
            repository_shortcut_id = data.get('parent_id') or shortcut_id
            self.cleanup_non_main_branches(repository_shortcut_id)
        elif chosen is configure_repo_action:
            self.configure_shortcut_repository(shortcut_id)
        elif chosen is pool_size_action:
            self.set_agent_workspace_pool_size()
        elif chosen is active_limit_action:
            self.set_agent_workspace_active_limit()
        elif chosen is new_workspace_action:
            self.create_agent_workspace(shortcut_id)
        elif chosen is launch_workspace_action:
            self.launch_agent_workspace(shortcut_id)
        elif chosen is open_workspace_directory_action:
            self.open_agent_workspace_directory(shortcut_id)
        elif chosen is force_stop_workspace_action:
            self.force_stop_agent_workspace_project(shortcut_id)
        elif chosen is force_delete_workspace_action:
            self.force_delete_agent_workspace(shortcut_id)
        elif chosen is status_workspace_action:
            self.show_agent_workspace_status(shortcut_id)
        elif chosen is merge_workspace_action:
            self.launch_agent_workspace_merge(shortcut_id)
        elif chosen is recycle_workspace_action:
            self.recycle_agent_workspace(shortcut_id)
        elif chosen is merge_provider_action:
            self.set_agent_workspace_merge_provider()
        elif chosen is merge_instruction_action:
            self.edit_agent_workspace_merge_instruction()
        elif chosen is reset_merge_instruction_action:
            self.reset_agent_workspace_merge_instruction()
        elif chosen is add_child_action:
            self.add_child_shortcut()
        elif chosen is edit_action:
            self.edit_shortcut()
        elif chosen is delete_action:
            self.delete_shortcut()

    def cleanup_non_main_branches(self, parent_shortcut_id):
        """Select branches to delete, while showing and managing worktree use."""
        if not parent_shortcut_id:
            QMessageBox.warning(
                self, '\u6e05\u7406\u5206\u652f\u5931\u8d25',
                '\u65e0\u6cd5\u786e\u5b9a\u5bf9\u5e94\u7684\u4ed3\u5e93\u5feb\u6377\u5165\u53e3\u3002',
            )
            return
        service = self._workspace_service()
        try:
            details = service.get_non_main_branches(parent_shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '\u6e05\u7406\u5206\u652f\u5931\u8d25', str(error))
            return

        branches = details.get('branches', [])
        if not branches:
            QMessageBox.information(
                self, '\u65e0\u9700\u6e05\u7406',
                '\u5f53\u524d\u4ed3\u5e93\u6ca1\u6709\u53ef\u6e05\u7406\u7684\u672c\u5730\u5206\u652f\u3002\n'
                '\u4fdd\u7559\u5206\u652f\uff1a{}\u3002'.format(
                    '\u3001'.join(details.get('protected_branches', ['main', 'master']))
                ),
            )
            return

        # Checked means "delete this branch". Keep the default checked so the
        # action remains a one-click cleanup, while allowing individual
        # branches to be unchecked to preserve them.
        dialog = QDialog(self)
        dialog.setWindowTitle('\u9009\u62e9\u8981\u5220\u9664\u7684\u5206\u652f')
        dialog.setMinimumSize(820, 500)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            '\u8bf7\u52fe\u9009\u8981\u5220\u9664\u7684\u5206\u652f\uff08\u9ed8\u8ba4\u5168\u90e8\u52fe\u9009\uff09\uff1a'
        ))
        legend = QLabel(
            '<span style="color:#d32f2f;font-weight:600">'
            '\u7ea2\u8272\uff1a\u5206\u652f\u6709\u6b63\u5728\u8fd0\u884c\u7684\u5de5\u4f5c\u533a\u9879\u76ee</span>'
            '\uff08\u53ef\u5728\u6b64\u5f3a\u5236\u505c\u6b62\uff09'
        )
        layout.addWidget(legend)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setToolTip('\u5c06\u9f20\u6807\u60ac\u6d6e\u5728\u5206\u652f\u4e0a\u53ef\u67e5\u770b\u5b8c\u6574\u5206\u652f\u540d\u79f0')
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setSpacing(4)
        checkboxes = {}
        branch_usage = details.get('branch_usage', {})

        def force_stop_workspace(shortcut_id, button, branch):
            answer = QMessageBox.question(
                dialog,
                '\u5f3a\u5236\u505c\u6b62\u5de5\u4f5c\u533a',
                '\u8fd9\u4f1a\u7ed3\u675f\u8be5\u5206\u652f\u5bf9\u5e94\u7684\u5de5\u4f5c\u533a\u542f\u52a8\u811a\u672c\u53ca\u5176\u5b50\u8fdb\u7a0b\uff0c\u672a\u4fdd\u5b58\u6570\u636e\u53ef\u80fd\u4e22\u5931\u3002\n\n\u5206\u652f\uff1a{}\n\n\u786e\u5b9a\u7ee7\u7eed\u5417\uff1f'.format(branch),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                result = service.force_stop_workspace_project(shortcut_id)
            except Exception as error:
                QMessageBox.warning(dialog, '\u5f3a\u5236\u505c\u6b62\u5931\u8d25', str(error))
                return
            button.setEnabled(False)
            button.setText('\u5df2\u505c\u6b62')
            button.setToolTip('\u5df2\u505c\u6b62\uff1a{}'.format(branch))
            for usage in branch_usage.get(branch, []):
                if usage.get('shortcut_id') == shortcut_id:
                    usage['runtime_state'] = 'stopped'
            if not any(
                usage.get('runtime_state') == 'running'
                for usage in branch_usage.get(branch, [])
            ):
                checkboxes[branch].setStyleSheet('')
            self.status_bar.showMessage(
                '\u5df2\u5f3a\u5236\u505c\u6b62\u5206\u652f {} \u5bf9\u5e94\u7684\u5de5\u4f5c\u533a\uff08\u7ed3\u675f {} \u4e2a\u8fdb\u7a0b\uff09'.format(
                    branch, result.get('terminated_processes', 0)
                ),
                5000,
            )

        for branch in branches:
            row = QWidget(list_widget)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox(branch, row)
            checkbox.setChecked(True)
            checkbox.setToolTip(branch)
            checkbox.setStatusTip(branch)
            row.setToolTip(branch)
            usage_entries = branch_usage.get(branch, [])
            active_usage_entries = [
                usage for usage in usage_entries
                if usage.get('runtime_state') == 'running'
            ]
            if active_usage_entries:
                checkbox.setStyleSheet('QCheckBox { color: #d32f2f; font-weight: 600; }')
            if usage_entries:
                usage_text = '\n'.join(
                    '{}{}{}'.format(
                        usage.get('worktree_path', ''),
                        '\uFF08\u8FD0\u884C\u4E2D\uFF09' if usage.get('runtime_state') == 'running' else '',
                        ' [\u5DE5\u4F5C\u533A]' if usage.get('is_agent_workspace') else ' [\u5F53\u524D\u68C0\u51FA]',
                    )
                    for usage in usage_entries
                )
                checkbox.setToolTip('{}\n\n\u4F7F\u7528\u4F4D\u7F6E\uff1a\n{}'.format(branch, usage_text))
                row.setToolTip('{}\n\n\u4F7F\u7528\u4F4D\u7F6E\uff1a\n{}'.format(branch, usage_text))
            row_layout.addWidget(checkbox, 1)
            checkboxes[branch] = checkbox

            for usage in usage_entries:
                shortcut_id = usage.get('shortcut_id')
                if not shortcut_id or not usage.get('is_agent_workspace'):
                    continue
                stop_button = QPushButton('\u5f3a\u5236\u505c\u6b62\u5de5\u4f5c\u533a', row)
                stop_button.setEnabled(True)
                stop_button.setToolTip('\u5f3a\u5236\u505c\u6b62\uff1a{}'.format(branch))
                stop_button.clicked.connect(
                    lambda _checked=False, sid=shortcut_id, button=stop_button, name=branch:
                    force_stop_workspace(sid, button, name)
                )
                row_layout.addWidget(stop_button)
            list_layout.addWidget(row)
        list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll)

        protected_text = '\u3001'.join(details.get('protected_branches', ['main', 'master']))
        layout.addWidget(QLabel('\u59cb\u7ec8\u4fdd\u7559\uff1a{}'.format(protected_text)))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        branches_to_delete = [
            branch for branch in branches if checkboxes[branch].isChecked()
        ]
        if not branches_to_delete:
            QMessageBox.information(
                self, '\u672a\u9009\u62e9\u5220\u9664',
                '\u6ca1\u6709\u52fe\u9009\u4efb\u4f55\u5206\u652f\uff0c\u672a\u6267\u884c\u5220\u9664\u3002',
            )
            return

        branch_text = '\n'.join('  \u2022 {}'.format(branch) for branch in branches_to_delete)
        second = QMessageBox.question(
            self,
            '\u518d\u6b21\u786e\u8ba4\uff1a\u4e0d\u53ef\u64a4\u9500',
            '\u4ee5\u4e0b\u672c\u5730\u5206\u652f\u5c06\u88ab\u5220\u9664\uff08\u4e0d\u4f1a\u5220\u9664\u8fdc\u7a0b\u5206\u652f\uff09\uff1a\n\n{}'
            '\n\n\u5206\u652f\u5220\u9664\u540e\u4e0d\u80fd\u901a\u8fc7\u672c\u5e94\u7528\u6062\u590d\uff0c\u786e\u5b9a\u7ee7\u7eed\u5417\uff1f'.format(
                branch_text,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if second != QMessageBox.StandardButton.Yes:
            return

        try:
            result = service.cleanup_non_main_branches(
                parent_shortcut_id, branches=branches_to_delete,
            )
        except Exception as error:
            QMessageBox.warning(self, '\u6e05\u7406\u5206\u652f\u5931\u8d25', str(error))
            return

        deleted = result.get('deleted', [])
        skipped = result.get('skipped', [])
        message = '\u5df2\u6e05\u7406 {} \u4e2a\u672c\u5730\u5206\u652f\u3002'.format(len(deleted))
        if skipped:
            skipped_text = '\n'.join(
                '  \u2022 {}\uff1a{}'.format(
                    entry.get('branch', ''), entry.get('reason', '\u672a\u5220\u9664')
                )
                for entry in skipped
            )
            QMessageBox.warning(
                self,
                '\u5206\u652f\u6e05\u7406\u5b8c\u6210\uff0c\u4f46\u6709\u5206\u652f\u8df3\u8fc7',
                '{}\n\n\u4ee5\u4e0b\u5206\u652f\u672a\u5220\u9664\uff1a\n{}'.format(
                    message, skipped_text
                ),
            )
        else:
            QMessageBox.information(self, '\u5206\u652f\u6e05\u7406\u5b8c\u6210', message)
        self.status_bar.showMessage(message, 5000)

    def _shortcut_service(self):
        return self.data_manager._service_factory.get_shortcut_operation_service()

    def _workspace_service(self):
        return self.data_manager._service_factory.get_git_worktree_service()

    def _vscode_workspace_service(self):
        return self.data_manager._service_factory.get_vscode_workspace_service()

    def _change_shortcut_vscode_workspace(self, shortcut_id, operation):
        shortcut = self.data_manager.shortcut_manager.get_by_id(shortcut_id) or {}
        path = shortcut.get('shortcut_path', '')
        if not path:
            QMessageBox.warning(self, 'VS Code 工作区操作失败', '该快捷入口没有可加入工作区的路径。')
            return
        try:
            service = self._vscode_workspace_service()
            if operation == 'add':
                result = service.add_folder_to_workspace(path)
                message = '已主动加入 VS Code 工作区：{}'.format(result['folder'])
            else:
                result = service.remove_folder_from_workspace(path)
                message = '已主动移出 VS Code 工作区：{}'.format(result['folder'])
        except Exception as error:
            QMessageBox.warning(self, 'VS Code 工作区操作失败', str(error))
            return
        self.status_bar.showMessage(message, 4000)

    def _current_shortcut_id(self):
        item = self.shortcuts_table.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole + 1) or {}
        return data.get('id') or item.data(0, Qt.ItemDataRole.UserRole)

    def add_shortcut_to_vscode_workspace(self, shortcut_id):
        self._change_shortcut_vscode_workspace(shortcut_id, 'add')

    def remove_shortcut_from_vscode_workspace(self, shortcut_id):
        self._change_shortcut_vscode_workspace(shortcut_id, 'remove')

    def add_current_shortcut_to_vscode_workspace(self):
        shortcut_id = self._current_shortcut_id()
        if not shortcut_id:
            warn_no_task_selected()
            return
        self.add_shortcut_to_vscode_workspace(shortcut_id)

    def remove_current_shortcut_from_vscode_workspace(self):
        shortcut_id = self._current_shortcut_id()
        if not shortcut_id:
            warn_no_task_selected()
            return
        self.remove_shortcut_from_vscode_workspace(shortcut_id)

    def configure_shortcut_repository(self, parent_shortcut_id):
        """Configure a root shortcut as an agent-workspace repository."""
        service = self._workspace_service()
        profile = service.get_repository_profile(parent_shortcut_id) or {}
        parent = self.data_manager.shortcut_manager.get_by_id(parent_shortcut_id) or {}
        root = parent.get('shortcut_path', '')
        default_script = os.path.basename(root) if os.path.isfile(root) else ''
        if not default_script:
            default_script = profile.get('launch_script', '')
        if not default_script:
            if root:
                for candidate in ('launch.bat', 'launch.py', 'launch.sh'):
                    if os.path.isfile(os.path.join(root, candidate)):
                        default_script = candidate
                        break
        script, accepted = QInputDialog.getText(
            self, '配置智能体仓库',
            '项目启动脚本（相对仓库根目录，例如 launch.bat）：', text=default_script,
        )
        if not accepted:
            return False
        base_ref, accepted = QInputDialog.getText(
            self, '配置智能体仓库',
            '基线分支（留空自动使用远程默认分支）：',
            text=profile.get('base_ref', ''),
        )
        if not accepted:
            return False
        try:
            service.configure_repository(parent_shortcut_id, script, base_ref)
        except Exception as error:
            QMessageBox.warning(self, '仓库配置失败', str(error))
            return False
        self.status_bar.showMessage('智能体仓库配置已保存', 3000)
        return True

    def create_agent_workspace(self, parent_shortcut_id):
        """Create a ready-to-run child worktree without asking for any input."""
        service = self._workspace_service()
        try:
            workspace = service.create_or_reuse_workspace(parent_shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '创建工作区失败', str(error))
            return
        try:
            self._vscode_workspace_service().add_folder_to_workspace_if_enabled(
                workspace.get('worktree_path', ''),
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                '加入 VS Code 工作区失败',
                '工作区已创建，但未能加入当前 VS Code 工作区：\n{}'.format(error),
            )
        self.load_shortcuts()
        action = '已复用空闲工作区' if workspace.get('workspace_reused') else '已创建新工作区'
        self.status_bar.showMessage(action, 5000)

    def set_agent_workspace_pool_size(self):
        service = self._workspace_service()
        size, accepted = QInputDialog.getInt(
            self, '空闲工作区保留数量',
            '已合并工作区最多保留多少个可复用本地目录：',
            value=service.get_warm_pool_size(), min=0, max=20,
        )
        if accepted:
            service.set_warm_pool_size(size)
            self.status_bar.showMessage('空闲工作区保留数量已设为 {}'.format(size), 3000)

    def set_agent_workspace_active_limit(self):
        service = self._workspace_service()
        size, accepted = QInputDialog.getInt(
            self, '同时开发子类上限',
            '同时处于开发状态的智能体子类最多数量（0 表示不限制）：',
            value=service.get_active_workspace_limit(), min=0, max=100,
        )
        if accepted:
            service.set_active_workspace_limit(size)
            label = '不限制' if size == 0 else str(size)
            self.status_bar.showMessage('同时开发子类上限已设为 {}'.format(label), 3000)

    def launch_agent_workspace(self, shortcut_id):
        try:
            self._workspace_service().launch_workspace_project(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '启动项目失败', str(error))

    def open_agent_workspace_directory(self, shortcut_id):
        """Keep folder browsing available without confusing it with project launch."""
        workspace = self._workspace_service().get_workspace(shortcut_id)
        path = workspace.get('worktree_path', '') if workspace else ''
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, '工作目录不可用', '该智能体工作区目录不存在。')
            return
        try:
            os.startfile(path)
        except OSError as error:
            QMessageBox.warning(self, '打开工作目录失败', str(error))

    def launch_agent_workspace_merge(self, shortcut_id):
        """Ask the configured local CLI to merge; never merge directly in the UI."""
        try:
            result = self._workspace_service().launch_merge_agent(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '启动合并智能体失败', str(error))
            return
        provider = 'Codex' if result['provider'] == 'codex' else 'Claude Code'
        self.status_bar.showMessage(
            '{} 已在父仓库中启动合并。完成后请使用“确认已合并并归还工作区”。'.format(provider),
            6000,
        )

    def set_agent_workspace_merge_provider(self):
        service = self._workspace_service()
        current = service.get_merge_provider()
        options = ['Codex', 'Claude Code']
        selected, accepted = QInputDialog.getItem(
            self, '设置合并智能体', '将本地哪个智能体用于合并分支：',
            options, 0 if current == 'codex' else 1, False,
        )
        if not accepted:
            return
        try:
            service.set_merge_provider('codex' if selected == 'Codex' else 'claude')
        except Exception as error:
            QMessageBox.warning(self, '保存合并智能体失败', str(error))
            return
        self.status_bar.showMessage('合并智能体已设为 {}'.format(selected), 3000)

    def edit_agent_workspace_merge_instruction(self):
        service = self._workspace_service()
        instruction, accepted = QInputDialog.getMultiLineText(
            self, '编辑合并指令',
            '可用占位符：{branch}、{base_branch}、{repository_root}、{worktree_path}',
            service.get_merge_instruction(),
        )
        if not accepted:
            return
        try:
            service.set_merge_instruction(instruction)
        except Exception as error:
            QMessageBox.warning(self, '保存合并指令失败', str(error))
            return
        self.status_bar.showMessage('合并指令已保存', 3000)

    def reset_agent_workspace_merge_instruction(self):
        answer = QMessageBox.question(
            self, '恢复默认合并指令', '确定恢复默认合并指令吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._workspace_service().reset_merge_instruction()
        self.status_bar.showMessage('已恢复默认合并指令', 3000)

    def mark_agent_workspace_project_stopped(self, shortcut_id):
        try:
            self._workspace_service().mark_workspace_project_stopped(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '无法更新运行状态', str(error))
            return
        self.status_bar.showMessage('已标记本地项目停止，可安全归还或删除工作区', 4000)

    def force_stop_agent_workspace_project(self, shortcut_id):
        answer = QMessageBox.question(
            self, '强制关闭本地项目',
            '这会结束该工作区启动脚本及其子进程，未保存的数据可能丢失。继续吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self._workspace_service().force_stop_workspace_project(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '无法强制关闭本地项目', str(error))
            return
        count = result.get('terminated_processes', 0)
        self.status_bar.showMessage('已强制关闭本地项目（结束 {} 个进程）'.format(count), 4000)

    def force_delete_agent_workspace(self, shortcut_id):
        answer = QMessageBox.question(
            self,
            '\u5f3a\u5236\u5220\u9664\u667a\u80fd\u4f53\u5de5\u4f5c\u533a',
            '\u8fd9\u5c06\u6c38\u4e45\u5220\u9664\u5de5\u4f5c\u533a\u76ee\u5f55\u548c\u529f\u80fd\u5206\u652f\uff0c\u5305\u62ec '
            '\u672a\u5408\u5e76\u7684\u63d0\u4ea4\u548c\u672a\u63d0\u4ea4\u6587\u4ef6\u90fd\u4f1a\u4e22\u5931\uff0c\u4e14\u4e0d\u53ef\u64a4\u9500\u3002\u7ee7\u7eed\u5417\uff1f',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self._workspace_service().force_remove_workspace(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '\u5f3a\u5236\u5220\u9664\u5931\u8d25', str(error))
            return
        if result.get('removed'):
            # 强制删除不会经过普通快捷入口删除流程，因此这里也要清理引用。
            # 否则工作区和功能分支虽然已删除，行程仍可能指向已移除的子类。
            self.data_manager.delete_itinerary_by_task_ref(shortcut_id, 'shortcut')
            self.data_manager.clear_itinerary_shortcut_bindings(shortcut_id)
            self.load_shortcuts()
            self.refresh_itinerary_after_task_deletion()
            self.status_bar.showMessage('\u667a\u80fd\u4f53\u5de5\u4f5c\u533a\u5df2\u5f3a\u5236\u5220\u9664', 4000)

    def show_agent_workspace_status(self, shortcut_id):
        try:
            status = self._workspace_service().workspace_status(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '无法读取工作区状态', str(error))
            return
        message = (
            '功能：{feature}\n分支：{branch}\n状态：{state}\n未提交改动：{dirty}\n路径：{path}'
        ).format(
            feature=status.get('feature_name') or '空闲工作区',
            branch=status.get('branch_name') or '(detached)',
            state=status.get('state', ''),
            dirty='是' if status.get('dirty') else '否',
            path=status.get('worktree_path', ''),
        )
        message += '\n本地项目：{}'.format(
            '运行中' if status.get('runtime_state') == 'running' else '已停止'
        )
        QMessageBox.information(self, 'Git 工作区状态', message)

    def recycle_agent_workspace(self, shortcut_id):
        answer = QMessageBox.question(
            self, '归还智能体工作区',
            '将验证分支已合并且工作区干净，然后归还到空闲池。继续吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self._workspace_service().recycle_merged_workspace(shortcut_id)
        except Exception as error:
            QMessageBox.warning(self, '无法归还工作区', str(error))
            return
        self.load_shortcuts()
        removed = result.get('removed_idle_workspaces', 0)
        self.status_bar.showMessage('工作区已归还；已清理 {} 个超额空闲工作区'.format(removed), 5000)

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

    def _load_add_to_vscode_workspace_state(self):
        checkbox = getattr(self, 'add_to_vscode_workspace_checkbox', None)
        if checkbox is None:
            return
        try:
            enabled = self._vscode_workspace_service().is_enabled()
        except Exception:
            logger.warning('加载 VS Code 工作区设置失败')
            enabled = config.config.VSCODE_ADD_TO_WORKSPACE_DEFAULT
        checkbox.blockSignals(True)
        checkbox.setChecked(enabled)
        checkbox.blockSignals(False)

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

    def on_add_to_vscode_workspace_toggled(self, state):
        enabled = bool(state)
        checkbox = getattr(self, 'add_to_vscode_workspace_checkbox', None)
        try:
            self._vscode_workspace_service().set_enabled(enabled)
            self.status_bar.showMessage(
                '已{}新建快捷入口时加入 VS Code 工作区'.format('开启' if enabled else '关闭'),
                3000,
            )
        except Exception as error:
            logger.exception('保存 VS Code 工作区设置失败')
            QMessageBox.warning(self, '保存失败', '无法保存 VS Code 工作区设置: {}'.format(error))
            if checkbox is not None:
                checkbox.blockSignals(True)
                checkbox.setChecked(not enabled)
                checkbox.blockSignals(False)

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
