"""
Task Table Operations Module
处理任务表格的各种操作，包括加载、状态切换、排序等功能
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


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
    
    status = window.daily_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    elif status == '已完成':
        status_filter = 'completed'
    elif status == '暂弃':
        status_filter = 'abandoned'
    else:
        status_filter = 'all'

    tasks = window.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)

    window.daily_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_map = {'pending': '○', 'completed': '✓', 'abandoned': '✗'}
        status_text = status_map.get(task.status, '○')
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.daily_table.setItem(row, 0, status_item)
        
        # 标题
        window.daily_table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 星期
        weekday = task.week_day if task.week_day else '每天'
        window.daily_table.setItem(row, 2, QTableWidgetItem(weekday))
        
        # 描述
        window.daily_table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        window.daily_table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)

    window.update_status_bar()


def load_todo_tasks_to_table(window):
    """加载待办事项到表格"""
    # 获取筛选条件
    status = window.todo_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    elif status == '已完成':
        status_filter = 'completed'
    elif status == '暂弃':
        status_filter = 'abandoned'
    else:  # '已过期'
        status_filter = 'all'  # 已过期需要特殊处理

    tasks = window.data_manager.get_todo_tasks(status=status_filter)

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_map = {'pending': '○', 'completed': '✓', 'abandoned': '✗'}
        status_text = status_map.get(task.status, '○')
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.todo_table.setItem(row, 0, status_item)
        
        # 标题
        window.todo_table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 截止日期
        deadline = task.deadline if task.deadline else '无'
        window.todo_table.setItem(row, 2, QTableWidgetItem(deadline))
        
        # 紧急程度
        window.todo_table.setItem(row, 3, QTableWidgetItem(str(task.urgency_score)))
        
        # 描述
        window.todo_table.setItem(row, 4, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        window.todo_table.setItem(row, 5, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)

    window.update_status_bar()


def load_entertainment_tasks_to_table(window):
    """加载娱乐任务到表格"""
    # 获取筛选条件
    status = window.entertainment_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    elif status == '已完成':
        status_filter = 'completed'
    elif status == '暂弃':
        status_filter = 'abandoned'
    else:
        status_filter = 'all'

    tasks = window.data_manager.get_entertainment_tasks(status=status_filter)

    window.entertainment_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_map = {'pending': '○', 'completed': '✓', 'abandoned': '✗'}
        status_text = status_map.get(task.status, '○')
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.entertainment_table.setItem(row, 0, status_item)
        
        # 标题
        window.entertainment_table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 类别
        window.entertainment_table.setItem(row, 2, QTableWidgetItem(task.fun_category))
        
        # 描述
        window.entertainment_table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        window.entertainment_table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)

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
    status = window.todo_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    elif status == '暂弃':
        status_filter = 'abandoned'
    else:  # '已完成' 或 '已过期'
        status_filter = 'completed'

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
        # 状态
        status_map = {'pending': '○', 'completed': '✓', 'abandoned': '✗'}
        status_text = status_map.get(task.status, '○')
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        window.todo_table.setItem(row, 0, status_item)
        
        # 标题
        window.todo_table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 截止日期
        deadline = task.deadline if task.deadline else '无'
        window.todo_table.setItem(row, 2, QTableWidgetItem(deadline))
        
        # 紧急程度
        window.todo_table.setItem(row, 3, QTableWidgetItem(str(task.urgency_score)))
        
        # 描述
        window.todo_table.setItem(row, 4, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        window.todo_table.setItem(row, 5, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)