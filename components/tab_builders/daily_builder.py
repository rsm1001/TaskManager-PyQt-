"""
每日任务 Tab 构建器
"""

import logging

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from components.tab_builders.base_builder import BaseTabBuilder
from components.tag_filter_bar import TagFilterBar
from components.tab_filters import on_tag_filter_clicked
from managers.data_manager import TaskType

logger = logging.getLogger(__name__)


class DailyTabBuilder(BaseTabBuilder):
    """构建"每日必做"标签页

    结构：标签筛选条 → 控制按钮行（添加 / 编辑 / 删除 / 重置今日 / 随机抽取 / 批量）→ 表格
    """

    HEADERS = ['状态', '标题', '分类', '星期', '标签', '用时(分钟)',
               '描述', '创建日期', '优先级', '时段']

    def build(self) -> QWidget:
        win = self.parent_window
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标签分类栏
        win.daily_tag_filter = TagFilterBar(parent=win, data_manager=win.data_manager)
        win.daily_tag_filter.set_task_type(TaskType.DAILY)
        win.daily_tag_filter.tagClicked.connect(
            lambda tag: on_tag_filter_clicked(win, tag, 'daily')
        )
        layout.addWidget(win.daily_tag_filter)

        # 控制按钮 + 筛选（保持与原始 ui_components.py 一致的单行布局）
        self._make_control_row(layout)

        # 任务表格
        table = self.make_table(
            'daily_table',
            self.HEADERS,
            column_count=10,
            edit_handler=win.edit_daily_task,
            click_handler=win.toggle_daily_task_status,
            task_type='daily',
        )
        layout.addWidget(table)

        logger.info("[Tab 构建] 每日必做 Tab 装配完成")
        return widget

    def _make_control_row(self, parent_layout):
        """构建单行布局：左侧 7 个按钮 + 弹性间距 + 星期/状态/时段筛选

        与原始 ui_components.py 中 create_daily_tab_ui 的控制行布局一致。

        Args:
            parent_layout: 外层垂直布局，控件行将被加入其中
        """
        from PyQt6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        win = self.parent_window
        # 左侧操作按钮（顺序与原代码一致）
        self.add_control_button(row, 'add_daily_btn', '添加任务', win.add_daily_task)
        self.add_control_button(row, 'edit_daily_btn', '编辑任务', win.edit_daily_task)
        self.add_control_button(row, 'delete_daily_btn', '删除任务', win.delete_daily_task)
        self.add_control_button(row, 'reset_today_btn', '重置今日', win.reset_today_daily_tasks)
        self.add_control_button(row, 'random_daily_btn', '随机抽取', win.random_daily_task)
        self.add_control_button(row, 'batch_status_daily_btn', '批量改状态', win.batch_edit_daily_status)
        self.add_control_button(row, 'batch_tags_daily_btn', '批量编辑标签', win.batch_edit_daily_tags)
        # 弹性间距把筛选推到右侧
        row.addStretch()
        # 右侧筛选下拉框（顺序：星期 → 状态 → 时段）
        self.build_weekday_filter(row, 'daily_weekday_combo', win.load_daily_tasks)
        self.build_status_filter(
            row, 'daily_status_combo',
            ['全部', '进行中', '已完成', '暂弃'], default_text='进行中',
            reload_slot=win.load_daily_tasks,
        )
        self.build_time_period_filter(
            row, 'daily_time_period_combo', task_type='daily',
            reload_slot=win.load_daily_tasks,
        )
        parent_layout.addLayout(row)
