"""
待办事项 Tab 构建器
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from components.tab_builders.base_builder import BaseTabBuilder
from components.tab_filters import on_tag_filter_clicked
from components.tag_filter_bar import TagFilterBar
from managers.data_manager import TaskType

logger = logging.getLogger(__name__)


class TodoTabBuilder(BaseTabBuilder):
    """构建"待办事项"标签页

    结构：标签筛选条 → 控制按钮行 → 筛选行 → 表格（支持表头排序）
    """

    HEADERS = ['状态', '标题', '截止日期', '分类', '紧急程度', '标签',
               '用时(分钟)', '描述', '创建日期', '优先级', '时段']

    def build(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标签分类栏
        win.todo_tag_filter = TagFilterBar(parent=win, data_manager=win.data_manager)
        win.todo_tag_filter.set_task_type(TaskType.TODO)
        win.todo_tag_filter.tagClicked.connect(
            lambda tag: on_tag_filter_clicked(win, tag, 'todo')
        )
        layout.addWidget(win.todo_tag_filter)

        # 控制按钮 + 筛选（保持与原始 ui_components.py 一致的单行布局）
        self._make_control_row(layout)

        # 任务表格
        table = self.make_table(
            'todo_table',
            self.HEADERS,
            column_count=11,
            edit_handler=win.edit_todo_task,
            click_handler=win.toggle_todo_task_status,
            task_type='todo',
        )
        # 待办表支持表头点击排序
        table.horizontalHeader().sectionClicked.connect(win.sort_todo_table_by_column)
        win.todo_sort_column = -1
        win.todo_sort_order = Qt.SortOrder.AscendingOrder
        layout.addWidget(table)

        logger.info("[Tab 构建] 待办事项 Tab 装配完成")
        return widget

    def _make_control_row(self, parent_layout):
        """构建单行布局：左侧 6 个按钮 + 弹性间距 + 状态/时段筛选

        与原始 ui_components.py 中 create_todo_tab_ui 的控制行布局一致
        （todo 没有"星期"筛选，仅状态 + 时段）。

        Args:
            parent_layout: 外层垂直布局，控件行将被加入其中
        """
        row = QHBoxLayout()
        win = self.parent_window
        # 左侧操作按钮（顺序与原代码一致）
        self.add_control_button(row, 'add_todo_btn', '添加任务', win.add_todo_task)
        self.add_control_button(row, 'edit_todo_btn', '编辑任务', win.edit_todo_task)
        self.add_control_button(row, 'delete_todo_btn', '删除任务', win.delete_todo_task)
        self.add_control_button(row, 'random_todo_btn', '随机抽取', win.random_todo_task)
        self.add_control_button(row, 'batch_status_todo_btn', '批量改状态', win.batch_edit_todo_status)
        self.add_control_button(row, 'batch_tags_todo_btn', '批量编辑标签', win.batch_edit_todo_tags)
        # 弹性间距
        row.addStretch()
        # 右侧筛选下拉框
        self.build_status_filter(
            row, 'todo_status_combo',
            ['全部', '进行中', '已完成', '已过期', '暂弃'],
            default_text='进行中',
            reload_slot=win.load_todo_tasks,
        )
        self.build_time_period_filter(
            row, 'todo_time_period_combo', task_type='todo',
            reload_slot=win.load_todo_tasks,
        )
        parent_layout.addLayout(row)
