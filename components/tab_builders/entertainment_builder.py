"""
娱乐任务 Tab 构建器
"""

import logging

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from components.tab_builders.base_builder import BaseTabBuilder
from components.tab_filters import on_tag_filter_clicked
from components.tag_filter_bar import TagFilterBar
from managers.data_manager import TaskType

logger = logging.getLogger(__name__)


class EntertainmentTabBuilder(BaseTabBuilder):
    """构建"娱乐任务"标签页

    结构：标签筛选条 → 控制按钮行 → 筛选行 → 表格
    """

    HEADERS = ['状态', '标题', '类别', '分类', '标签', '用时(分钟)',
               '描述', '创建日期', '优先级', '时段']

    def build(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标签分类栏
        win.entertainment_tag_filter = TagFilterBar(parent=win, data_manager=win.data_manager)
        win.entertainment_tag_filter.set_task_type(TaskType.ENTERTAINMENT)
        win.entertainment_tag_filter.tagClicked.connect(
            lambda tag: on_tag_filter_clicked(win, tag, 'entertainment')
        )
        layout.addWidget(win.entertainment_tag_filter)

        # 控制按钮 + 筛选（保持与原始 ui_components.py 一致的单行布局）
        self._make_control_row(layout)

        # 任务表格
        table = self.make_table(
            'entertainment_table',
            self.HEADERS,
            column_count=10,
            edit_handler=win.edit_entertainment_task,
            click_handler=win.toggle_entertainment_task_status,
            task_type='entertainment',
        )
        layout.addWidget(table)

        logger.info("[Tab 构建] 娱乐任务 Tab 装配完成")
        return widget

    def _make_control_row(self, parent_layout):
        """构建单行布局：左侧 6 个按钮 + 弹性间距 + 状态/时段筛选

        与原始 ui_components.py 中 create_entertainment_tab_ui 的控制行布局一致
        （entertainment 没有"星期"筛选）。

        Args:
            parent_layout: 外层垂直布局，控件行将被加入其中
        """
        row = QHBoxLayout()
        win = self.parent_window
        # 左侧操作按钮（顺序与原代码一致）
        self.add_control_button(row, 'add_entertainment_btn', '添加任务', win.add_entertainment_task)
        self.add_control_button(row, 'edit_entertainment_btn', '编辑任务', win.edit_entertainment_task)
        self.add_control_button(row, 'delete_entertainment_btn', '删除任务', win.delete_entertainment_task)
        self.add_control_button(row, 'random_entertainment_btn', '随机抽取', win.random_entertainment_task)
        self.add_control_button(row, 'batch_status_entertainment_btn', '批量改状态', win.batch_edit_entertainment_status)
        self.add_control_button(row, 'batch_tags_entertainment_btn', '批量编辑标签', win.batch_edit_entertainment_tags)
        # 弹性间距
        row.addStretch()
        # 右侧筛选下拉框
        self.build_status_filter(
            row, 'entertainment_status_combo',
            ['全部', '进行中', '已完成', '暂弃'],
            default_text='进行中',
            reload_slot=win.load_entertainment_tasks,
        )
        self.build_time_period_filter(
            row, 'entertainment_time_period_combo', task_type='entertainment',
            reload_slot=win.load_entertainment_tasks,
        )
        parent_layout.addLayout(row)
