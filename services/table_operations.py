"""
Task Table Operations Module
处理任务表格的各种操作，包括加载、状态切换、排序等功能
"""

import logging
from functools import partial
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import config.config as config

logger = logging.getLogger(__name__)

from services.shortcut_table_service import (
    render_shortcut_row,
    render_history_row,
    _open_shortcut_path,
)

# 优先级显示/排序（从 managers.priority 派生）
# 真正的定义在 managers/priority.py PRIORITY_LEVELS
from managers.priority import (  # noqa: E402,F401
    PRIORITY_DISPLAY_MAP,
    get_priority_label,
    get_priority_rank,
)


def _get_priority_display(priority):
    """获取优先级的显示文本"""
    return get_priority_label(priority)


def _get_status_filter(status_text):
    """将界面状态文本转换为过滤器值"""
    return config.STATUS_FILTER_MAP.get(status_text, 'all')


def load_search_results_to_table(window):
    """加载全局搜索结果到搜索结果表格"""
    keyword = getattr(window, 'search_input', None)
    if keyword is None:
        return
    keyword_text = keyword.text().strip()

    results = window.data_manager.search_all_tasks(keyword_text)

    window.search_results_table.setRowCount(len(results))

    # 类型映射
    TYPE_LABELS = {
        'daily': '每日任务',
        'todo': '待办事项',
        'entertainment': '娱乐任务',
        'shortcut': '快捷入口',
    }

    for row, item in enumerate(results):
        task_type = item.get('task_type', 'unknown')
        type_label = TYPE_LABELS.get(task_type, task_type)

        # 类型列
        type_item = QTableWidgetItem(type_label)
        type_item.setData(Qt.ItemDataRole.UserRole, item.get('id', ''))
        window.search_results_table.setItem(row, 0, type_item)

        # 状态列
        status = item.get('status', 'pending')
        status_text = config.STATUS_DISPLAY_MAP.get(status, '○')
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setData(Qt.ItemDataRole.UserRole, item.get('id', ''))
        window.search_results_table.setItem(row, 1, status_item)

        # 星期列（仅每日任务显示星期几）
        if task_type == 'daily':
            week_day = item.get('week_day', '')
            week_text = week_day if week_day else '每天'
        else:
            week_text = '-'
        week_item = QTableWidgetItem(week_text)
        week_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.search_results_table.setItem(row, 2, week_item)

        # 标题列
        title = item.get('title', '')
        title_item = QTableWidgetItem(title)
        title_item.setData(Qt.ItemDataRole.UserRole, item.get('id', ''))
        window.search_results_table.setItem(row, 3, title_item)

        # 分类列
        category = item.get('category', '') or '-'
        window.search_results_table.setItem(row, 4, QTableWidgetItem(category))

        # 标签列
        tags = item.get('tags', '') or '-'
        window.search_results_table.setItem(row, 5, QTableWidgetItem(tags))

        # 用时预估列
        duration = item.get('estimated_duration', 0) or 0
        duration_text = str(duration) if duration else '-'
        window.search_results_table.setItem(row, 6, QTableWidgetItem(duration_text))

        # 描述列
        description = item.get('description', '') or '-'
        desc_item = QTableWidgetItem(description)
        if len(description) > 50:
            desc_item.setToolTip(description)
        window.search_results_table.setItem(row, 7, desc_item)

        # 创建日期列
        created_at = item.get('created_at', '')
        if created_at:
            if hasattr(created_at, 'strftime'):
                date_str = created_at.strftime('%Y-%m-%d')
            else:
                date_str = str(created_at)[:10]
        else:
            date_str = '-'
        window.search_results_table.setItem(row, 8, QTableWidgetItem(date_str))

        # 优先级列
        priority = item.get('priority', 'normal')
        priority_display = PRIORITY_DISPLAY_MAP.get(priority, '普通')
        window.search_results_table.setItem(row, 9, QTableWidgetItem(priority_display))

        # 设置行背景色和文字颜色（基于优先级）
        bg_color = QColor(config.PRIORITY_BG_COLORS.get(priority, '#FFFFFF'))
        text_color = QColor(config.PRIORITY_TEXT_COLORS.get(priority, '#333333'))
        for col in range(10):
            cell_item = window.search_results_table.item(row, col)
            if cell_item:
                cell_item.setBackground(bg_color)
                cell_item.setForeground(text_color)

    # 更新状态栏显示结果数量
    window.search_status_label.setText(f"找到 {len(results)} 条结果")


def _render_shortcut_row(table, row, shortcut_item, on_open_callback=None):
    """渲染快捷入口表格的一行（委托给 ShortcutTableService）"""
    render_shortcut_row(table, row, shortcut_item, on_open_callback)


def _get_claude_path():
    """动态查找claude可执行文件路径（委托给 ShortcutTableService）"""
    from services.shortcut_table_service import _get_claude_path as get_path
    return get_path()


def _open_in_terminal(path):
    """在文件/文件夹所在目录启动cmd执行claude"""
    from services.shortcut_table_service import _open_in_terminal as open_terminal
    open_terminal(path)


def _open_shortcut_path(path, action_type='open'):
    """打开快捷入口路径"""
    from services.shortcut_table_service import _open_shortcut_path as open_path
    open_path(path, action_type)


def _set_task_row_data(table, row, task, columns, editable_cols=None):
    """设置普通任务表格行的数据

    Args:
        table: 表格控件
        row: 行索引
        task: 任务对象
        columns: list of (col_idx, value) 元组
        editable_cols: 允许编辑的列索引集合，None表示全部不可编辑（除status列外）
    """
    status_text = config.STATUS_DISPLAY_MAP.get(task.status, '○')
    status_item = QTableWidgetItem(status_text)
    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 状态栏不可编辑
    table.setItem(row, 0, status_item)
    for col_idx, value in columns:
        item = QTableWidgetItem(value)
        # editable_cols 为 None 时，默认所有列不可编辑（由 setEditTriggers 统一控制）
        if editable_cols is not None and col_idx in editable_cols:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, col_idx, item)
    status_item.setData(Qt.ItemDataRole.UserRole, task.id)

    # 设置行背景色和文字颜色（基于优先级）
    priority = getattr(task, 'priority', 'normal')
    bg_color = QColor(config.PRIORITY_BG_COLORS.get(priority, '#FFFFFF'))
    text_color = QColor(config.PRIORITY_TEXT_COLORS.get(priority, '#333333'))
    for col_idx, _ in columns:
        item = table.item(row, col_idx)
        if item:
            item.setBackground(bg_color)
            item.setForeground(text_color)


def load_daily_tasks_to_table(window):
    """加载每日任务到表格"""
    weekday = window.daily_weekday_combo.currentText()
    if weekday == '全部':
        weekday_filter = 'all'
    elif weekday == '每天':
        weekday_filter = 'daily'
    else:
        weekday_filter = weekday

    status_filter = _get_status_filter(window.daily_status_combo.currentText())
    tag_filter = getattr(window, 'daily_tag_filter_value', '')

    tasks = window.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter, tag=tag_filter)

    window.daily_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        duration = getattr(task, 'estimated_duration', 0) or 0
        columns = [
            (1, task.title),
            (2, task.category if task.category else '-'),
            (3, task.week_day if task.week_day else '每天'),
            (4, task.tags if task.tags else '-'),
            (5, str(duration) if duration else '-'),
            (6, task.description or '-'),
            (7, task.created_at.strftime('%Y-%m-%d')),
            (8, _get_priority_display(getattr(task, 'priority', 'normal')))
        ]
        _set_task_row_data(window.daily_table, row, task, columns)

    window.update_status_bar()


def load_todo_tasks_to_table(window):
    """加载待办事项到表格"""
    status_text = window.todo_status_combo.currentText()
    if status_text == '已过期':
        status_filter = 'expired'
    else:
        status_filter = _get_status_filter(status_text)

    tag_filter = getattr(window, 'todo_tag_filter_value', '')

    tasks = window.data_manager.get_todo_tasks(status=status_filter, tag=tag_filter)

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        duration = getattr(task, 'estimated_duration', 0) or 0
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, task.category if task.category else '-'),
            (4, f"{task.urgency_score:.2f}"),
            (5, task.tags if task.tags else '-'),
            (6, str(duration) if duration else '-'),
            (7, task.description or '-'),
            (8, task.created_at.strftime('%Y-%m-%d')),
            (9, _get_priority_display(getattr(task, 'priority', 'normal')))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)

    window.update_status_bar()


def load_entertainment_tasks_to_table(window):
    """加载娱乐任务到表格"""
    status_filter = _get_status_filter(window.entertainment_status_combo.currentText())
    tag_filter = getattr(window, 'entertainment_tag_filter_value', '')

    tasks = window.data_manager.get_entertainment_tasks(status=status_filter, tag=tag_filter)

    window.entertainment_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        duration = getattr(task, 'estimated_duration', 0) or 0
        columns = [
            (1, task.title),
            (2, task.fun_category),
            (3, task.category if task.category else '-'),
            (4, task.tags if task.tags else '-'),
            (5, str(duration) if duration else '-'),
            (6, task.description or '-'),
            (7, task.created_at.strftime('%Y-%m-%d')),
            (8, _get_priority_display(getattr(task, 'priority', 'normal')))
        ]
        _set_task_row_data(window.entertainment_table, row, task, columns, editable_cols={1, 2, 3, 4})

    window.update_status_bar()


def load_shortcuts_to_table(window):
    """加载所有快捷入口到快捷入口表格"""
    tag_filter = getattr(window, 'current_shortcut_tag_filter', '')
    shortcuts = window.data_manager.get_all_shortcuts(tag=tag_filter if tag_filter else None)
    window.shortcuts_table.setRowCount(len(shortcuts))

    def add_history_callback(shortcut_item):
        """点击快捷入口时添加历史记录"""
        window.data_manager.add_or_update_history(
            shortcut_item['id'],
            shortcut_item['title'],
            shortcut_item['shortcut_path'],
            shortcut_item.get('action_type', 'open')
        )
        if hasattr(window, 'load_shortcuts_history'):
            window.load_shortcuts_history()
        if hasattr(window, '_update_history_limit_label'):
            window._update_history_limit_label()

    for row, item in enumerate(shortcuts):
        _render_shortcut_row(window.shortcuts_table, row, item, on_open_callback=add_history_callback)


def load_shortcut_history_to_table(window):
    """加载历史记录到历史记录表格"""
    history_list = window.data_manager.get_all_history()
    window.shortcut_history_table.setRowCount(len(history_list))
    for row, item in enumerate(history_list):
        render_history_row(
            window.shortcut_history_table, row, item,
            on_open_callback=partial(_on_history_open, window),
            on_pin_callback=partial(_on_history_pin, window),
            on_delete_callback=partial(_on_history_delete, window),
            on_terminal_callback=partial(_on_history_terminal, window)
        )


def _on_history_open(window, history_item):
    """打开历史记录对应的快捷入口"""
    from services.shortcut_table_service import _open_shortcut_path
    _open_shortcut_path(history_item.get('shortcut_path', ''), history_item.get('action_type', 'open'))


def _on_history_terminal(window, history_item):
    """在终端中打开历史记录对应的路径"""
    from services.shortcut_table_service import _open_in_terminal
    _open_in_terminal(history_item.get('shortcut_path', ''))


def _on_history_pin(window, history_id):
    """切换历史记录的置顶状态"""
    window.data_manager.toggle_history_pin(history_id)
    load_shortcut_history_to_table(window)


def _on_history_delete(window, history_id):
    """删除历史记录"""
    if not window.data_manager.delete_history(history_id):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(window, '提示', '置顶记录不可删除')
        return
    load_shortcut_history_to_table(window)


def toggle_daily_task_status(window, row, column):
    """切换每日任务状态"""
    if column == 0:
        item = window.daily_table.item(row, 0)
        if item is None:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            import time
            # 防抖：2秒内同一任务只触发一次
            last_time = window._status_switch_timestamps.get(task_id, 0)
            if time.time() * 1000 - last_time < 2000:
                return
            window._status_switch_timestamps[task_id] = time.time() * 1000
            # 标记当前行，防止双击事件触发编辑
            window._status_switching_row = row
            logger.info(f"[状态切换] 每日任务 | task_id={task_id} | row={row}")
            window.data_manager.toggle_daily_task_completion(task_id)
            QTimer.singleShot(0, lambda: setattr(window, '_status_switching_row', -1))
            load_daily_tasks_to_table(window)
            window.daily_table.clearSelection()


def toggle_todo_task_status(window, row, column):
    """切换待办事项状态"""
    if column == 0:
        item = window.todo_table.item(row, 0)
        if item is None:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            import time
            # 防抖：2秒内同一任务只触发一次
            last_time = window._status_switch_timestamps.get(task_id, 0)
            if time.time() * 1000 - last_time < 2000:
                return
            window._status_switch_timestamps[task_id] = time.time() * 1000
            # 标记当前行，防止双击事件触发编辑
            window._status_switching_row = row
            logger.info(f"[状态切换] 待办事项 | task_id={task_id} | row={row}")
            window.data_manager.toggle_todo_task_completion(task_id)
            QTimer.singleShot(0, lambda: setattr(window, '_status_switching_row', -1))
            load_todo_tasks_to_table(window)
            window.todo_table.clearSelection()


def toggle_entertainment_task_status(window, row, column):
    """切换娱乐任务状态"""
    if column == 0:
        item = window.entertainment_table.item(row, 0)
        if item is None:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            import time
            # 防抖：2秒内同一任务只触发一次
            last_time = window._status_switch_timestamps.get(task_id, 0)
            if time.time() * 1000 - last_time < 2000:
                return
            window._status_switch_timestamps[task_id] = time.time() * 1000
            # 标记当前行，防止双击事件触发编辑
            window._status_switching_row = row
            logger.info(f"[状态切换] 娱乐任务 | task_id={task_id} | row={row}")
            window.data_manager.toggle_entertainment_task_completion(task_id)
            QTimer.singleShot(0, lambda: setattr(window, '_status_switching_row', -1))
            load_entertainment_tasks_to_table(window)
            window.entertainment_table.clearSelection()


def sort_todo_table_by_column(window, column):
    """根据列进行排序（支持正序和倒序）"""
    if window.todo_sort_column == column:
        if window.todo_sort_order == Qt.SortOrder.AscendingOrder:
            window.todo_sort_order = Qt.SortOrder.DescendingOrder
        elif window.todo_sort_order == Qt.SortOrder.DescendingOrder:
            window.todo_sort_column = -1
            window.todo_sort_order = Qt.SortOrder.AscendingOrder
            load_todo_tasks_to_table(window)
            return
    else:
        window.todo_sort_column = column
        window.todo_sort_order = Qt.SortOrder.AscendingOrder

    status_text = window.todo_status_combo.currentText()
    if status_text == '已过期':
        status_filter = 'expired'
    else:
        status_filter = _get_status_filter(status_text)

    tasks = window.data_manager.get_todo_tasks(status=status_filter)

    if column == 0:
        tasks.sort(key=lambda x: x.status, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 1:
        tasks.sort(key=lambda x: x.title.lower(), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 2:
        tasks.sort(key=lambda x: (x.deadline or ''), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 3:
        tasks.sort(key=lambda x: (x.category or ''), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 4:
        tasks.sort(key=lambda x: x.urgency_score, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 5:
        tasks.sort(key=lambda x: (x.tags or '').lower(), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 6:
        tasks.sort(key=lambda x: (x.description or '').lower(), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 7:
        tasks.sort(key=lambda x: x.created_at, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 8:
        # 用 rank 字典排序，5 档下不能字符串字典序（"high" < "idle" 字典序错乱）
        tasks.sort(
            key=lambda x: get_priority_rank(getattr(x, 'priority', 'normal')),
            reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder)
        )

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        duration = getattr(task, 'estimated_duration', 0) or 0
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, task.category if task.category else '-'),
            (4, f"{task.urgency_score:.2f}"),
            (5, task.tags if task.tags else '-'),
            (6, str(duration) if duration else '-'),
            (7, task.description or '-'),
            (8, task.created_at.strftime('%Y-%m-%d')),
            (9, _get_priority_display(getattr(task, 'priority', 'normal')))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)
