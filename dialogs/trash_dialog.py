"""
垃圾桶对话框 - 查看和恢复已删除任务
从 main.py 解耦独立
"""

import json
from datetime import datetime

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt


class TrashDialog(QDialog):
    """垃圾桶对话框 - 查看和恢复已删除任务"""

    TYPE_LABELS = {
        'daily': '每日任务',
        'todo': '待办事项',
        'entertainment': '娱乐任务',
        'shortcut': '快捷入口',
    }

    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle('垃圾桶')
        self.setModal(True)
        self.resize(700, 500)
        self._init_ui()
        self._load_trashed()

    def _init_ui(self):
        """初始化对话框UI"""
        layout = QVBoxLayout(self)

        # 顶部筛选区
        top_layout = QHBoxLayout()

        # 类型筛选
        top_layout.addWidget(QLabel('类型:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['全部', '每日任务', '待办事项', '娱乐任务', '快捷入口'])
        self.type_combo.currentTextChanged.connect(self._load_trashed)
        top_layout.addWidget(self.type_combo)

        top_layout.addSpacing(20)

        # 搜索框
        top_layout.addWidget(QLabel('搜索:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索标题/描述...')
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_input)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 任务列表
        self.trash_table = QTableWidget()
        self.trash_table.setColumnCount(6)
        self.trash_table.setHorizontalHeaderLabels(['类型', '标题', '描述', '标签', '删除时间', '操作'])
        self.trash_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.trash_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.trash_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.trash_table)

        # 底部按钮
        btn_layout = QHBoxLayout()

        restore_btn = QPushButton('恢复选中')
        restore_btn.clicked.connect(self._restore_selected)
        btn_layout.addWidget(restore_btn)

        delete_btn = QPushButton('彻底删除')
        delete_btn.clicked.connect(self._purge_selected)
        btn_layout.addWidget(delete_btn)

        batch_delete_btn = QPushButton('批量删除')
        batch_delete_btn.clicked.connect(self._purge_selected_batch)
        btn_layout.addWidget(batch_delete_btn)

        btn_layout.addStretch()

        clear_btn = QPushButton('清空垃圾桶')
        clear_btn.clicked.connect(self._purge_all)
        btn_layout.addWidget(clear_btn)

        cancel_btn = QPushButton('关闭')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _get_filter_type(self):
        """获取当前筛选类型"""
        text = self.type_combo.currentText()
        if text == '全部':
            return None
        elif text == '每日任务':
            return 'daily'
        elif text == '待办事项':
            return 'todo'
        elif text == '娱乐任务':
            return 'entertainment'
        elif text == '快捷入口':
            return 'shortcut'
        return None

    def _load_trashed(self):
        """加载垃圾桶中的任务"""
        filter_type = self._get_filter_type()
        rows = self.data_manager.get_trashed_tasks(task_type=filter_type)

        self.trash_table.setRowCount(len(rows))
        # 记录每行的 shortcut_path（用于搜索时判断快捷入口类型）
        self._row_shortcut_paths = {}

        for row, (trash_id, task_type, task_id, data_json, deleted_at) in enumerate(rows):
            data = json.loads(data_json)

            # 类型：快捷入口优先判断（shortcut_path 非空则显示"快捷入口"）
            shortcut_path = data.get('shortcut_path', '') or ''
            self._row_shortcut_paths[row] = shortcut_path
            if shortcut_path:
                type_text = '快捷入口'
                type_key = 'shortcut'
            else:
                type_text = self.TYPE_LABELS.get(task_type, task_type)
                type_key = task_type

            # 先统一设为可见，类型筛选逻辑在末尾统一设置隐藏
            self.trash_table.setRowHidden(row, False)

            # 类型筛选
            if filter_type == 'shortcut':
                # 只隐藏非 shortcut 行（type_key != 'shortcut' 的都是其他任务类型）
                if type_key != 'shortcut':
                    self.trash_table.setRowHidden(row, True)
            elif filter_type and type_key != filter_type:
                self.trash_table.setRowHidden(row, True)

            type_item = QTableWidgetItem(type_text)
            type_item.setData(Qt.ItemDataRole.UserRole, trash_id)
            self.trash_table.setItem(row, 0, type_item)

            # 标题
            self.trash_table.setItem(row, 1, QTableWidgetItem(data.get('title', '')))

            # 描述
            desc = data.get('description', '')
            if len(desc) > 30:
                desc = desc[:30] + '...'
            self.trash_table.setItem(row, 2, QTableWidgetItem(desc or '-'))

            # 标签
            tags = data.get('tags', '')
            self.trash_table.setItem(row, 3, QTableWidgetItem(tags or '-'))

            # 删除时间
            try:
                dt = datetime.fromisoformat(deleted_at)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                time_str = deleted_at
            self.trash_table.setItem(row, 4, QTableWidgetItem(time_str))

            # 操作提示
            op_item = QTableWidgetItem('双击恢复')
            op_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.trash_table.setItem(row, 5, op_item)

        # 双击恢复（先断开旧连接防止重复绑定）
        try:
            self.trash_table.cellDoubleClicked.disconnect(self._on_double_click)
        except TypeError:
            pass
        self.trash_table.cellDoubleClicked.connect(self._on_double_click)

    def _on_search_changed(self, text):
        """搜索框内容变化，实时过滤表格"""
        keyword = text.strip().lower()
        filter_type = self._get_filter_type()

        for row in range(self.trash_table.rowCount()):
            type_text = self.trash_table.item(row, 0).text() if self.trash_table.item(row, 0) else ''
            shortcut_path = getattr(self, '_row_shortcut_paths', {}).get(row, '')

            # 先以类型筛选结果为基础
            if filter_type == 'shortcut':
                # 非 shortcut 行全部隐藏（不需要 shortcut_path 判断）
                if type_text != '快捷入口':
                    self.trash_table.setRowHidden(row, True)
                    continue
            elif filter_type and type_text != self.TYPE_LABELS.get(filter_type, ''):
                self.trash_table.setRowHidden(row, True)
                continue

            # 类型命中后，再按关键词过滤
            if not keyword:
                continue

            match = False
            for col in [1, 2]:  # 标题、描述列
                item = self.trash_table.item(row, col)
                if item and keyword in item.text().lower():
                    match = True
                    break
            self.trash_table.setRowHidden(row, not match)

    def _on_double_click(self, row, column):
        """双击恢复任务"""
        item = self.trash_table.item(row, 0)
        if item:
            trash_id = item.data(Qt.ItemDataRole.UserRole)
            self._do_restore(trash_id)

    def _restore_selected(self):
        """恢复选中的任务"""
        row = self.trash_table.currentRow()
        if row < 0:
            QMessageBox.information(self, '提示', '请先选中要恢复的任务')
            return
        item = self.trash_table.item(row, 0)
        if item:
            trash_id = item.data(Qt.ItemDataRole.UserRole)
            self._do_restore(trash_id)

    def _do_restore(self, trash_id):
        """执行恢复操作"""
        success = self.data_manager.restore_trashed_task(trash_id)
        if success:
            QMessageBox.information(self, '成功', '任务已恢复')
            self._load_trashed()
            self.accept()  # 通知主窗口刷新
        else:
            QMessageBox.warning(self, '失败', '恢复失败，任务可能已不存在')

    def _purge_selected(self):
        """彻底删除选中的任务"""
        row = self.trash_table.currentRow()
        if row < 0:
            QMessageBox.information(self, '提示', '请先选中要删除的任务')
            return

        reply = QMessageBox.question(
            self, '确认',
            '彻底删除后无法恢复，确定要删除吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            item = self.trash_table.item(row, 0)
            if item:
                trash_id = item.data(Qt.ItemDataRole.UserRole)
                self.data_manager.purge_trashed_task(trash_id)
                self._load_trashed()

    def _purge_selected_batch(self):
        """批量彻底删除选中的任务"""
        selected_rows = self.trash_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, '提示', '请先选中要删除的任务')
            return

        trash_ids = []
        for index in selected_rows:
            item = self.trash_table.item(index.row(), 0)
            if item:
                trash_ids.append(item.data(Qt.ItemDataRole.UserRole))

        if not trash_ids:
            return

        count = len(trash_ids)
        reply = QMessageBox.question(
            self, '确认',
            f'彻底删除 {count} 项任务后无法恢复，确定要删除吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.purge_trashed_tasks(trash_ids)
            self._load_trashed()

    def _purge_all(self):
        """清空垃圾桶"""
        reply = QMessageBox.question(
            self, '确认',
            '清空垃圾桶后所有任务都无法恢复，确定要清空吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            filter_type = self._get_filter_type()
            self.data_manager.purge_all_trashed(task_type=filter_type)
            self._load_trashed()
