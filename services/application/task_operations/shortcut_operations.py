"""
快捷入口操作模块
封装快捷入口的增删改查逻辑
"""

from PyQt6.QtWidgets import QMessageBox, QPushButton
from PyQt6.QtGui import QCursor
from managers.application.data_manager import TaskType
from dialogs.shortcut_edit_dialog import ShortcutEditDialog
from utils.ui_messages import (
    show_task_added_confirmation,
    show_task_updated_confirmation,
    show_task_deleted_confirmation,
    warn_no_task_selected,
    confirm_batch_deletion,
)
import os


class ShortcutOperations:
    """快捷入口操作处理器"""

    def __init__(self, window):
        """
        Args:
            window: TaskManagerMainWindow 实例
        """
        self._w = window

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
        if data['action_type'] == 'open' and not os.path.exists(data['shortcut_path']):
            QMessageBox.warning(self._w, '警告', '文件或文件夹不存在，请检查路径是否正确')
            return
        self._w.data_manager.create_shortcut('todo', data['title'], data['shortcut_path'], data.get('tags', ''), data.get('action_type', 'open'))
        self._w.load_shortcuts()
        self._validate_and_refresh_filter('shortcuts')
        show_task_added_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('快捷入口添加成功')
        self._w.update_status_bar()

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
            initial_tags=shortcut_data.get('tags', ''),
            initial_action_type=shortcut_data.get('action_type', 'open')
        )
        if dialog.exec() != ShortcutEditDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        if not data['title']:
            QMessageBox.warning(self._w, '警告', '请输入快捷入口名称')
            return
        if data['action_type'] == 'open' and not os.path.exists(data['shortcut_path']):
            QMessageBox.warning(self._w, '警告', '文件或文件夹不存在，请检查路径是否正确')
            return
        self._w.data_manager.update_shortcut(
            shortcut_id,
            title=data['title'],
            shortcut_path=data['shortcut_path'],
            tags=data.get('tags', ''),
            action_type=data.get('action_type', 'open')
        )
        self._w.load_shortcuts()
        self._validate_and_refresh_filter('shortcuts')
        show_task_updated_confirmation('shortcut', self._w)
        self._w.status_bar.showMessage('快捷入口更新成功')
        self._w.update_status_bar()

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
        self._w.update_status_bar()

    def on_shortcuts_cell_clicked(self, row, col):
        """Only trigger the shortcut when the name button itself was clicked."""
        if col != 0:
            return
        cell = self._w.shortcuts_table.cellWidget(row, 0)
        if not cell:
            return
        button = cell if isinstance(cell, QPushButton) else cell.findChild(QPushButton)
        if button and button.rect().contains(button.mapFromGlobal(QCursor.pos())):
            button.click()

    def _validate_and_refresh_filter(self, task_type: str):
        """验证并刷新标签筛选状态"""
        current_tag = getattr(self._w, 'current_shortcut_tag_filter', '')
        filter_bar = self._w.shortcut_tag_filter
        filter_bar.refresh_tags()
        visible_tags = filter_bar.get_visible_tags()
        if current_tag and current_tag not in visible_tags:
            self._w.current_shortcut_tag_filter = ''
            self._w.load_shortcuts()
            filter_bar.update_button_states()
