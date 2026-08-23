"""Shortcut entry CRUD and tree actions."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from dialogs.shortcut_edit_dialog import ShortcutEditDialog
from utils.ui_messages import (
    confirm_batch_deletion,
    show_task_added_confirmation,
    show_task_deleted_confirmation,
    show_task_updated_confirmation,
    warn_no_task_selected,
)


class ShortcutOperations:
    """Application-level shortcut operations."""

    def __init__(self, window):
        self._w = window

    def _current_item(self):
        return self._w.shortcuts_table.currentItem()

    def _item_data(self, item):
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if isinstance(data, dict):
            return data
        shortcut_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not shortcut_id:
            return None
        return next(
            (entry for entry in self._w.data_manager.get_all_shortcuts()
             if entry.get('id') == shortcut_id),
            None,
        )

    def _valid_parent_exclusions(self, shortcut_id):
        all_items = self._w.data_manager.get_all_shortcuts()
        excluded = {shortcut_id}
        child_ids = {
            entry['id'] for entry in all_items
            if entry.get('parent_id') == shortcut_id
        }
        excluded.update(child_ids)
        # A root that already owns children cannot be moved below another root
        # in the two-level model, so hide all root targets in that case.
        if child_ids:
            excluded.update(
                entry['id'] for entry in all_items if not entry.get('parent_id')
            )
        return excluded

    def _validate_data(self, data):
        if not data.get('title'):
            QMessageBox.warning(self._w, 'Warning', 'Please enter a shortcut name')
            return False
        if not data.get('shortcut_path'):
            QMessageBox.warning(self._w, 'Warning', 'Please provide a shortcut path')
            return False
        if data.get('action_type') == 'open' and not os.path.exists(data['shortcut_path']):
            QMessageBox.warning(self._w, 'Warning', 'The selected path does not exist')
            return False
        return True

    def _add_folder_to_vscode_workspace_if_enabled(self, shortcut_path):
        """Best-effort post-create integration with the active VS Code window."""
        service = self._w.data_manager._service_factory.get_vscode_workspace_service()
        try:
            service.add_folder_to_workspace_if_enabled(shortcut_path)
        except Exception as error:
            # The shortcut is already persisted; an external CLI failure must
            # not roll back the user's shortcut.
            QMessageBox.warning(
                self._w,
                '加入 VS Code 工作区失败',
                '快捷入口已创建，但未能加入当前 VS Code 工作区：\n{}'.format(error),
            )

    def add_shortcut(self):
        dialog = ShortcutEditDialog(self._w, data_manager=self._w.data_manager)
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not self._validate_data(data):
            return
        created = self._w.data_manager.create_shortcut(
            'todo', data['title'], data['shortcut_path'], data.get('tags', ''),
            data.get('action_type', 'open'), parent_id=data.get('parent_id'),
        )
        if not created:
            QMessageBox.warning(self._w, 'Save failed', 'The selected parent shortcut is invalid')
            return
        self._add_folder_to_vscode_workspace_if_enabled(data['shortcut_path'])
        self._w.load_shortcuts()
        self._validate_and_refresh_filter()
        show_task_added_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('Shortcut added successfully')
        self._w.update_status_bar()

    def add_child_shortcut(self, parent_id=None):
        """Add a child under the selected root shortcut."""
        if parent_id is None:
            selected = self._item_data(self._current_item())
            if not selected:
                warn_no_task_selected()
                return
            parent_id = selected.get('parent_id') or selected.get('id')
        parent = next(
            (entry for entry in self._w.data_manager.get_all_shortcuts()
             if entry.get('id') == parent_id and not entry.get('parent_id')),
            None,
        )
        if not parent:
            QMessageBox.warning(self._w, 'Notice', 'Children can only be added under a root shortcut')
            return
        dialog = ShortcutEditDialog(
            self._w,
            data_manager=self._w.data_manager,
            initial_parent_id=parent_id,
        )
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not self._validate_data(data):
            return
        selected_parent_id = data.get('parent_id')
        selected_parent = next(
            (entry for entry in self._w.data_manager.get_all_shortcuts()
             if entry.get('id') == selected_parent_id and not entry.get('parent_id')),
            None,
        )
        created = self._w.data_manager.create_shortcut(
            'todo', data['title'], data['shortcut_path'], data.get('tags', ''),
            data.get('action_type', 'open'), parent_id=selected_parent_id,
        )
        if not created:
            QMessageBox.warning(self._w, 'Save failed', 'The child shortcut could not be created')
            return
        self._add_folder_to_vscode_workspace_if_enabled(data['shortcut_path'])
        self._w.load_shortcuts()
        self._validate_and_refresh_filter()
        show_task_added_confirmation('shortcut', self._w)
        parent_title = selected_parent.get('title', '') if selected_parent else 'root'
        self._w.status_bar.showMessage(
            f"Child shortcut added under {parent_title}"
        )
        self._w.update_status_bar()

    def edit_shortcut(self):
        data = self._item_data(self._current_item())
        if not data:
            warn_no_task_selected()
            return
        workspace_service = self._w.data_manager._service_factory.get_git_worktree_service()
        if workspace_service.get_workspace(data['id']):
            QMessageBox.information(
                self._w, '智能体工作区',
                '智能体工作区的路径和父级由 Git 生命周期管理，不能作为普通快捷入口编辑。',
            )
            return
        if workspace_service.get_repository_profile(data['id']):
            QMessageBox.information(
                self._w, '仓库入口',
                '仓库路径和基线设置请通过右键菜单中的“配置仓库与启动脚本”修改。',
            )
            return
        dialog = ShortcutEditDialog(
            self._w,
            data_manager=self._w.data_manager,
            initial_title=data['title'],
            initial_path=data['shortcut_path'],
            initial_tags=data.get('tags', ''),
            initial_action_type=data.get('action_type', 'open'),
            initial_parent_id=data.get('parent_id'),
            excluded_parent_ids=self._valid_parent_exclusions(data['id']),
        )
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        updated = dialog.get_data()
        if not self._validate_data(updated):
            return
        saved = self._w.data_manager.update_shortcut(
            data['id'],
            title=updated['title'],
            shortcut_path=updated['shortcut_path'],
            tags=updated.get('tags', ''),
            action_type=updated.get('action_type', 'open'),
            parent_id=updated.get('parent_id'),
        )
        if not saved:
            QMessageBox.warning(self._w, 'Save failed', 'The shortcut hierarchy is invalid')
            return
        self._w.load_shortcuts()
        self._w.refresh_itinerary_after_task_update()
        self._validate_and_refresh_filter()
        show_task_updated_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('Shortcut updated successfully')
        self._w.update_status_bar()

    def delete_shortcut(self):
        """Delete selected roots/children; a root includes its children."""
        selected_items = list(self._w.shortcuts_table.selected_shortcut_items())
        if not selected_items:
            warn_no_task_selected()
            return
        selected_data = [self._item_data(item) for item in selected_items]
        selected_data = [entry for entry in selected_data if entry]
        selected_ids = {entry['id'] for entry in selected_data}
        delete_data = [
            entry for entry in selected_data
            if not (entry.get('parent_id') and entry.get('parent_id') in selected_ids)
        ]
        if not delete_data:
            return
        if confirm_batch_deletion(len(delete_data)) != QMessageBox.StandardButton.Yes:
            return
        workspace_service = self._w.data_manager._service_factory.get_git_worktree_service()
        bundles = {}
        workspace_ids = []
        for entry in delete_data:
            if workspace_service.get_workspace(entry['id']):
                workspace_ids.append(entry['id'])
                continue
            bundle = [entry]
            bundle.extend(self._w.data_manager.get_shortcut_children(entry['id']))
            bundles[entry['id']] = bundle
            workspace_ids.extend(
                child['id'] for child in bundle[1:]
                if workspace_service.get_workspace(child['id'])
            )
        # Complete all safety checks before removing the first child worktree.
        # Git worktree removal is filesystem-destructive and cannot be rolled
        # back cheaply, so a parent deletion is all-or-nothing at this stage.
        try:
            for workspace_id in dict.fromkeys(workspace_ids):
                workspace_service.validate_workspace_removal(workspace_id)
        except Exception as error:
            QMessageBox.warning(self._w, '无法删除智能体工作区', str(error))
            return

        deleted = 0
        for entry in delete_data:
            workspace = workspace_service.get_workspace(entry['id'])
            if workspace:
                try:
                    workspace_service.remove_workspace(entry['id'])
                except Exception as error:
                    QMessageBox.warning(self._w, '无法删除智能体工作区', str(error))
                    continue
                self._w.data_manager.delete_itinerary_by_task_ref(entry['id'], 'shortcut')
                self._w.data_manager.clear_itinerary_shortcut_bindings(entry['id'])
                deleted += 1
                continue
            bundle = bundles[entry['id']]
            try:
                for child in bundle[1:]:
                    if workspace_service.get_workspace(child['id']):
                        workspace_service.remove_workspace(child['id'])
            except Exception as error:
                QMessageBox.warning(self._w, '无法删除智能体工作区', str(error))
                continue
            if self._w.data_manager.delete_shortcut(entry['id']):
                for child in bundle:
                    self._w.data_manager.delete_itinerary_by_task_ref(child['id'], 'shortcut')
                    self._w.data_manager.clear_itinerary_shortcut_bindings(child['id'])
                deleted += 1
        self._w.load_shortcuts()
        self._w.refresh_itinerary_after_task_deletion()
        self._validate_and_refresh_filter()
        show_task_deleted_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage(
            f'Shortcuts deleted successfully ({deleted}/{len(delete_data)})'
        )
        self._w.update_status_bar()

    def on_shortcuts_cell_clicked(self, row, col):
        """Compatibility slot retained for older external callers."""
        return None

    def _validate_and_refresh_filter(self):
        current_tag = getattr(self._w, 'current_shortcut_tag_filter', '')
        filter_bar = self._w.shortcut_tag_filter
        filter_bar.refresh_tags()
        visible_tags = filter_bar.get_visible_tags()
        if current_tag and current_tag not in visible_tags:
            self._w.current_shortcut_tag_filter = ''
            self._w.load_shortcuts()
            filter_bar.update_button_states()
