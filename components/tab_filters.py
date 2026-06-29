"""
Tab 过滤器工具模块
封装 Tab 页面中可复用的过滤逻辑：
- 标签筛选点击处理（普通任务 / 快捷入口）
- 时段筛选下拉框初始化与刷新
- 双击编辑事件包装器（拦截第 0 列）
"""

import logging

from PyQt6.QtWidgets import QComboBox

logger = logging.getLogger(__name__)


def on_tag_filter_clicked(parent_window, tag: str, task_type: str):
    """普通任务标签筛选点击处理（每日 / 待办 / 娱乐）

    - 将目标 tag 写入主窗口对应 task_type 的筛选变量
    - 根据 task_type 触发对应任务列表的重新加载

    Args:
        parent_window: 主窗口对象
        tag: 选中的标签名
        task_type: 任务大类（daily/todo/entertainment）
    """
    attr_name = f'{task_type}_tag_filter_value'
    setattr(parent_window, attr_name, tag)
    logger.info(
        "[标签筛选] 设置筛选 | task_type=%s | tag='%s'",
        task_type, tag,
    )

    loader_attr = f'load_{task_type}_tasks'
    loader = getattr(parent_window, loader_attr, None)
    if callable(loader):
        loader()


def on_shortcut_tag_filter_clicked(parent_window, tag: str):
    """快捷入口标签筛选点击处理

    Args:
        parent_window: 主窗口对象
        tag: 选中的标签名
    """
    parent_window.current_shortcut_tag_filter = tag
    logger.info("[标签筛选] 设置筛选 | task_type=shortcut | tag='%s'", tag)
    if hasattr(parent_window, 'load_shortcuts'):
        parent_window.load_shortcuts()


def _init_time_period_combo(parent_window, task_type: str) -> None:
    """初始化表格上方的"时段筛选"下拉框

    - 第一个固定为"全部时段"（哨兵 __ALL__ → 不过滤）
    - 然后是已存在的时段（按名字升序，绑定真实 id）
    - 最后是"未设时段"（哨兵 __NONE__ → time_period_id 为空）

    使用字符串哨兵而非 None，能避免与任意合法 id 冲突，也让过滤逻辑更稳。

    Args:
        parent_window: 主窗口对象
        task_type: 任务大类（daily/todo/entertainment）
    """
    from services.table_operations import _SENTINEL_ALL, _SENTINEL_NONE

    combo = getattr(parent_window, f'{task_type}_time_period_combo', None)
    if combo is None or not isinstance(combo, QComboBox):
        return

    combo.blockSignals(True)
    try:
        combo.clear()
        combo.addItem('全部时段', _SENTINEL_ALL)
        periods = []
        try:
            if getattr(parent_window, 'data_manager', None):
                periods = parent_window.data_manager.get_all_time_periods()
        except Exception as exc:  # noqa: BLE001 - 上抛到调用方再处理
            logger.warning(
                "[时段筛选] 拉取时段列表失败 | task_type=%s | error=%s",
                task_type, exc,
            )
            periods = []
        for p in periods:
            combo.addItem(p.name, p.id)
        combo.addItem('未设时段', _SENTINEL_NONE)
        combo.setCurrentIndex(0)
    finally:
        combo.blockSignals(False)


def refresh_all_time_period_combos(parent_window) -> None:
    """时段集合变更后（如增删 / 重命名），刷新所有筛选下拉框并触发重新加载

    Args:
        parent_window: 主窗口对象
    """
    for task_type in ('daily', 'todo', 'entertainment'):
        _init_time_period_combo(parent_window, task_type)

    # 重载表格让"时段"列显示同步更新
    for loader_name in (
        'load_daily_tasks',
        'load_todo_tasks',
        'load_entertainment_tasks',
    ):
        loader = getattr(parent_window, loader_name, None)
        if callable(loader):
            loader()


def wrap_edit_handler(handler):
    """包装编辑事件处理器，拦截对状态栏（列 0）的双击

    表格第 0 列是状态列，点击即切换任务状态，因此双击应忽略，避免与单击冲突。

    Args:
        handler: 真正的双击编辑处理函数

    Returns:
        wrapper(row, col): 仅当 col != 0 时调用 handler
    """
    def wrapper(row, col):
        if col != 0:
            handler()
    return wrapper
