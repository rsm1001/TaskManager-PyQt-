"""
UI Components 门面模块
提供向后兼容的接口，实际实现已迁移到:
- components.tab_filters                过滤器与时段辅助函数
- components.tab_builders               各 Tab 页面的工厂与构建器

Why: 原文件 513 行混入了 5 个 Tab 的 UI 构建 + 多种过滤辅助逻辑；
     重构后本文件仅保留对外入口，新增 Tab 类型只需在工厂注册表中追加一行。
"""

import logging

# ---------- Tab UI 入口（向后兼容 main.py 中的 import 形式）----------
from components.tab_builders import (
    create_daily_tab_ui,
    create_entertainment_tab_ui,
    create_search_tab_ui,
    create_shortcuts_tab_ui,
    create_todo_tab_ui,
)

# ---------- 过滤器 / 时段辅助入口 ----------
from components.tab_filters import (
    _init_time_period_combo,  # noqa: F401  （保留以防反射式访问）
    on_shortcut_tag_filter_clicked,
    on_tag_filter_clicked,
    refresh_all_time_period_combos,
    wrap_edit_handler,
)

__all__ = [
    # Tab UI 入口
    'create_daily_tab_ui',
    'create_todo_tab_ui',
    'create_entertainment_tab_ui',
    'create_shortcuts_tab_ui',
    'create_search_tab_ui',
    # 过滤器 / 时段辅助
    'on_tag_filter_clicked',
    'on_shortcut_tag_filter_clicked',
    'refresh_all_time_period_combos',
    'wrap_edit_handler',
]

logger = logging.getLogger(__name__)
