"""
Tab Builders 子包
将原本集中在 components/ui_components.py 中的 Tab UI 创建逻辑拆分到各独立文件，
通过工厂模式统一入口（create_tab_ui），新增 Tab 类型无需改动调用方。

对外暴露的统一接口（便于 components.main_window.ui_components 继续作为门面）:
- create_daily_tab_ui(parent_window)
- create_todo_tab_ui(parent_window)
- create_entertainment_tab_ui(parent_window)
- create_shortcuts_tab_ui(parent_window)
- create_search_tab_ui(parent_window)
"""

from components.tab_builders.daily_builder import DailyTabBuilder
from components.tab_builders.entertainment_builder import EntertainmentTabBuilder
from components.tab_builders.factory import (
    DEFAULT_TABS_ORDER,
    TAB_BUILDER_REGISTRY,
    create_tab_ui,
    register_tab_builder,
    supported_tab_types,
)
from components.tab_builders.search_builder import SearchTabBuilder
from components.tab_builders.shortcuts_builder import ShortcutsTabBuilder
from components.tab_builders.todo_builder import TodoTabBuilder


def create_daily_tab_ui(parent_window):
    """便捷封装：对齐旧 ui_components.create_daily_tab_ui 签名"""
    return DailyTabBuilder(parent_window).build()


def create_todo_tab_ui(parent_window):
    """便捷封装：对齐旧 ui_components.create_todo_tab_ui 签名"""
    return TodoTabBuilder(parent_window).build()


def create_entertainment_tab_ui(parent_window):
    """便捷封装：对齐旧 ui_components.create_entertainment_tab_ui 签名"""
    return EntertainmentTabBuilder(parent_window).build()


def create_shortcuts_tab_ui(parent_window):
    """便捷封装：对齐旧 ui_components.create_shortcuts_tab_ui 签名"""
    return ShortcutsTabBuilder(parent_window).build()


def create_search_tab_ui(parent_window):
    """便捷封装：对齐旧 ui_components.create_search_tab_ui 签名"""
    return SearchTabBuilder(parent_window).build()


__all__ = [
    # 工厂
    'create_tab_ui',
    'register_tab_builder',
    'supported_tab_types',
    'TAB_BUILDER_REGISTRY',
    'DEFAULT_TABS_ORDER',
    # 兼容旧签名
    'create_daily_tab_ui',
    'create_todo_tab_ui',
    'create_entertainment_tab_ui',
    'create_shortcuts_tab_ui',
    'create_search_tab_ui',
    # Builder 类（高级场景使用）
    'DailyTabBuilder',
    'TodoTabBuilder',
    'EntertainmentTabBuilder',
    'ShortcutsTabBuilder',
    'SearchTabBuilder',
]
