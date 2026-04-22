"""
Task Table Operations Module
处理任务表格的各种操作，包括加载、状态切换、排序等功能
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt
import config.config as config


def _get_status_filter(status_text):
    """将界面状态文本转换为过滤器值
    
    Args:
        status_text: 界面显示的状态文本
        
    Returns:
        对应的状态过滤值
    """
    return config.STATUS_FILTER_MAP.get(status_text, 'all')


def _set_task_row_data(table, row, task, columns):
    """设置任务表格行的数据
    
    Args:
        table: 表格控件
        row: 行索引
        task: 任务对象
        columns: 列数据列表，每个元素为 (列索引, 值)
    """
    # 状态列（始终在第一列）
    status_text = config.STATUS_DISPLAY_MAP.get(task.status, '○')
    status_item = QTableWidgetItem(status_text)
    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    table.setItem(row, 0, status_item)
    
    # 设置其他列
    for col_idx, value in columns:
        table.setItem(row, col_idx, QTableWidgetItem(value))
    
    # 存储任务ID用于后续操作
    status_item.setData(Qt.ItemDataRole.UserRole, task.id)


def load_daily_tasks_to_table(window):
    """加载每日任务到表格"""
    # 获取筛选条件
    weekday = window.daily_weekday_combo.currentText()
    if weekday == '全部':
        weekday_filter = 'all'
    elif weekday == '每天':
        weekday_filter = 'daily'  # 对应数据库中week_day为空的情况
    else:
        weekday_filter = weekday
    
    status_filter = _get_status_filter(window.daily_status_combo.currentText())

    tasks = window.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)

    window.daily_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 准备列数据：(列索引, 值)
        columns = [
            (1, task.title),
            (2, task.week_day if task.week_day else '每天'),
            (3, task.description or '-'),
            (4, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.daily_table, row, task, columns)

    window.update_status_bar()


def load_todo_tasks_to_table(window):
    """加载待办事项到表格"""
    # 获取筛选条件
    status_text = window.todo_status_combo.currentText()
    if status_text == '已过期':
        status_filter = 'all'  # 已过期需要特殊处理
    else:
        status_filter = _get_status_filter(status_text)

    tasks = window.data_manager.get_todo_tasks(status=status_filter)

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 准备列数据
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, str(task.urgency_score)),
            (4, task.description or '-'),
            (5, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)

    window.update_status_bar()


def load_entertainment_tasks_to_table(window):
    """加载娱乐任务到表格"""
    # 获取筛选条件
    status_filter = _get_status_filter(window.entertainment_status_combo.currentText())

    tasks = window.data_manager.get_entertainment_tasks(status=status_filter)

    window.entertainment_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 准备列数据
        columns = [
            (1, task.title),
            (2, task.fun_category),
            (3, task.description or '-'),
            (4, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.entertainment_table, row, task, columns)

    window.update_status_bar()


def toggle_daily_task_status(window, row, column):
    """切换每日任务状态"""
    if column == 0:  # 状态列
        item = window.daily_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            window.data_manager.toggle_daily_task_completion(task_id)
            
            # 重新加载任务以确保数据一致性
            load_daily_tasks_to_table(window)
            
            # 清除选中状态
            window.daily_table.clearSelection()


def toggle_todo_task_status(window, row, column):
    """切换待办事项状态"""
    if column == 0:  # 状态列
        item = window.todo_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            window.data_manager.toggle_todo_task_completion(task_id)
            
            # 重新加载任务以确保数据一致性
            load_todo_tasks_to_table(window)
            
            # 清除选中状态
            window.todo_table.clearSelection()


def toggle_entertainment_task_status(window, row, column):
    """切换娱乐任务状态"""
    if column == 0:  # 状态列
        item = window.entertainment_table.item(row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            window.data_manager.toggle_entertainment_task_completion(task_id)
            
            # 重新加载任务以确保数据一致性
            load_entertainment_tasks_to_table(window)
            
            # 清除选中状态
            window.entertainment_table.clearSelection()


def sort_todo_table_by_column(window, column):
    """根据列进行排序（支持正序和倒序）"""
    # 如果点击的是同一列，则切换排序顺序（升序->降序->原始顺序）
    if window.todo_sort_column == column:
        if window.todo_sort_order == Qt.SortOrder.AscendingOrder:
            window.todo_sort_order = Qt.SortOrder.DescendingOrder
        elif window.todo_sort_order == Qt.SortOrder.DescendingOrder:
            # 第三次点击恢复原始顺序（不排序）
            window.todo_sort_column = -1
            window.todo_sort_order = Qt.SortOrder.AscendingOrder
            load_todo_tasks_to_table(window)  # 重新加载原始数据
            return
    else:
        # 如果点击的是不同列，开始新列的升序排序
        window.todo_sort_column = column
        window.todo_sort_order = Qt.SortOrder.AscendingOrder

    # 获取当前筛选状态
    status_text = window.todo_status_combo.currentText()
    if status_text == '已过期':
        status_filter = 'all'  # 已过期需要特殊处理
    else:
        status_filter = _get_status_filter(status_text)

    tasks = window.data_manager.get_todo_tasks(status=status_filter)
    
    # 根据列进行排序
    if column == 0:  # 状态列
        tasks.sort(key=lambda x: x.status, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 1:  # 标题列
        tasks.sort(key=lambda x: x.title.lower(), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 2:  # 截止日期列
        # 处理可能的空截止日期
        tasks.sort(key=lambda x: (x.deadline or ''), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 3:  # 紧急程度列
        tasks.sort(key=lambda x: x.urgency_score, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 4:  # 描述列
        tasks.sort(key=lambda x: (x.description or '').lower(), reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))
    elif column == 5:  # 创建日期列
        tasks.sort(key=lambda x: x.created_at, reverse=(window.todo_sort_order == Qt.SortOrder.DescendingOrder))

    # 更新表格显示
    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 准备列数据
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, str(task.urgency_score)),
            (4, task.description or '-'),
            (5, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)