"""
Tab Builder 工厂模块
通过注册表模式提供统一的 Tab 构建入口：
- 主窗口或其它调用方只需要传入"Tab 类型字符串"即可获得对应 Tab 页面
- 新增 Tab 类型时只需在此注册新的 Builder，无需修改调用方
- 工厂本身与具体 Builder 解耦，调用方对 Builder 实现无感知
"""

import logging
from typing import Dict, Type

from components.tab_builders.daily_builder import DailyTabBuilder
from components.tab_builders.entertainment_builder import EntertainmentTabBuilder
from components.tab_builders.search_builder import SearchTabBuilder
from components.tab_builders.shortcuts_builder import ShortcutsTabBuilder
from components.tab_builders.todo_builder import TodoTabBuilder

logger = logging.getLogger(__name__)


# Builder 类的最小接口（duck-typed）：构造时接收 parent_window，调用 build() 返回 QWidget
class _TabBuilderProtocol:
    def __init__(self, parent_window): ...
    def build(self): ...


# Tab 类型 → Builder 类的注册表
# 这是工厂的核心：新增 Tab 只需要在此追加一行
TAB_BUILDER_REGISTRY: Dict[str, Type] = {
    'daily': DailyTabBuilder,
    'todo': TodoTabBuilder,
    'entertainment': EntertainmentTabBuilder,
    'shortcuts': ShortcutsTabBuilder,
    'search': SearchTabBuilder,
}

DEFAULT_TABS_ORDER = ('daily', 'todo', 'entertainment', 'shortcuts', 'search')


def register_tab_builder(tab_type: str, builder_cls: Type) -> None:
    """注册新的 Tab Builder（供插件 / 扩展使用）

    Args:
        tab_type: Tab 类型字符串
        builder_cls: Builder 类，需实现构造(parent_window) + build() 接口
    """
    if not isinstance(tab_type, str) or not tab_type:
        raise ValueError("tab_type 必须是非空字符串")
    TAB_BUILDER_REGISTRY[tab_type] = builder_cls
    logger.info("[Tab 工厂] 注册新 Tab Builder | tab_type=%s", tab_type)


def create_tab_ui(tab_type: str, parent_window) -> "_TabBuilderProtocol.build | None":
    """工厂方法：根据 tab_type 创建对应的 Tab 页面根容器

    Args:
        tab_type: Tab 类型字符串（必须在注册表中存在）
        parent_window: 主窗口对象，会传给 Builder 构造器

    Returns:
        Builder.build() 返回的 QWidget 根容器；tab_type 未注册时返回 None
    """
    builder_cls = TAB_BUILDER_REGISTRY.get(tab_type)
    if builder_cls is None:
        logger.warning("[Tab 工厂] 未注册的 Tab 类型: %s", tab_type)
        return None
    builder = builder_cls(parent_window)
    return builder.build()


def supported_tab_types() -> list:
    """获取当前已注册的全部 Tab 类型"""
    return list(TAB_BUILDER_REGISTRY.keys())
