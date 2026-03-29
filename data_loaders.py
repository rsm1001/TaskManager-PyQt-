"""
Task Manager Data Loading Module
处理各类任务数据加载和表格填充功能
"""

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


def load_daily_tasks_to_table(data_manager, table, daily_weekday_combo, daily_status_combo, update_status_bar_func):
    """加载每日任务到表格"""
    # 获取筛选条件
    weekday = daily_weekday_combo.currentText()
    if weekday == '全部':
        weekday_filter = 'all'
    elif weekday == '每天':
        weekday_filter = 'daily'  # 对应数据库中week_day为空的情况
    else:
        weekday_filter = weekday
    
    status = daily_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    else:  # '已完成'
        status_filter = 'completed'

    tasks = data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)

    table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_item = QTableWidgetItem('✓' if task.completed else '○')
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 0, status_item)
        
        # 标题
        table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 星期
        weekday = task.week_day if task.week_day else '每天'
        table.setItem(row, 2, QTableWidgetItem(weekday))
        
        # 描述
        table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)
    
    update_status_bar_func()


def load_todo_tasks_to_table(data_manager, table, todo_status_combo, update_status_bar_func):
    """加载待办事项到表格"""
    # 获取筛选条件
    status = todo_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    else:  # '已完成'
        status_filter = 'completed'

    tasks = data_manager.get_todo_tasks(status=status_filter)

    table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_item = QTableWidgetItem('✓' if task.completed else '○')
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 0, status_item)
        
        # 标题
        table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 截止日期
        deadline = task.deadline if task.deadline else '无'
        table.setItem(row, 2, QTableWidgetItem(deadline))
        
        # 紧急程度
        table.setItem(row, 3, QTableWidgetItem(str(task.urgency_score)))
        
        # 描述
        table.setItem(row, 4, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        table.setItem(row, 5, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)
    
    update_status_bar_func()


def load_entertainment_tasks_to_table(data_manager, table, entertainment_status_combo, update_status_bar_func):
    """加载娱乐任务到表格"""
    # 获取筛选条件
    status = entertainment_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    else:  # '已完成'
        status_filter = 'completed'

    tasks = data_manager.get_entertainment_tasks(status=status_filter)

    table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_item = QTableWidgetItem('✓' if task.completed else '○')
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 0, status_item)
        
        # 标题
        table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 类别
        table.setItem(row, 2, QTableWidgetItem(task.fun_category))
        
        # 描述
        table.setItem(row, 3, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        table.setItem(row, 4, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)
    
    update_status_bar_func()


def toggle_daily_task_status(table, data_manager, load_daily_func):
    """切换每日任务状态"""
    current_row = table.currentRow()
    column = 0  # 状态列
    if column == 0:  # 状态列
        item = table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            task = data_manager.get_daily_task_by_id(task_id)
            if task:
                new_status = not task.completed
                data_manager.update_daily_task(task_id=task_id, completed=new_status)
                
                # 重新加载任务以确保数据一致性
                load_daily_func()
                
                # 清除选中状态
                table.clearSelection()


def toggle_todo_task_status(table, data_manager, load_todo_func):
    """切换待办事项状态"""
    current_row = table.currentRow()
    column = 0  # 状态列
    if column == 0:  # 状态列
        item = table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            task = data_manager.get_todo_task_by_id(task_id)
            if task:
                new_status = not task.completed
                data_manager.update_todo_task(task_id=task_id, completed=new_status)
                
                # 重新加载任务以确保数据一致性
                load_todo_func()
                
                # 清除选中状态
                table.clearSelection()


def toggle_entertainment_task_status(table, data_manager, load_entertainment_func):
    """切换娱乐任务状态"""
    current_row = table.currentRow()
    column = 0  # 状态列
    if column == 0:  # 状态列
        item = table.item(current_row, 0)
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id:
            # 切换状态
            task = data_manager.get_entertainment_task_by_id(task_id)
            if task:
                new_status = not task.completed
                data_manager.update_entertainment_task(task_id=task_id, completed=new_status)
                
                # 重新加载任务以确保数据一致性
                load_entertainment_func()
                
                # 清除选中状态
                table.clearSelection()


def sort_todo_table_by_column(table, data_manager, todo_status_combo, todo_sort_column, todo_sort_order, load_todo_tasks_func):
    """根据列进行排序（支持正序和倒序）"""
    from PyQt6.QtCore import Qt
    
    # 如果点击的是同一列，则切换排序顺序（升序->降序->原始顺序）
    if todo_sort_column[0] == table.currentColumn():
        if todo_sort_order[0] == Qt.SortOrder.AscendingOrder:
            todo_sort_order[0] = Qt.SortOrder.DescendingOrder
        elif todo_sort_order[0] == Qt.SortOrder.DescendingOrder:
            # 第三次点击恢复原始顺序（不排序）
            todo_sort_column[0] = -1
            todo_sort_order[0] = Qt.SortOrder.AscendingOrder
            load_todo_tasks_func()  # 重新加载原始数据
            return
    else:
        # 如果点击的是不同列，开始新列的升序排序
        todo_sort_column[0] = table.currentColumn()
        todo_sort_order[0] = Qt.SortOrder.AscendingOrder

    # 获取当前筛选状态
    status = todo_status_combo.currentText()
    if status == '全部':
        status_filter = 'all'
    elif status == '进行中':
        status_filter = 'pending'
    else:  # '已完成' 或 '已过期'
        status_filter = 'completed'

    tasks = data_manager.get_todo_tasks(status=status_filter)
    
    # 根据列进行排序
    column = todo_sort_column[0]
    if column == 0:  # 状态列
        tasks.sort(key=lambda x: x.completed, reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))
    elif column == 1:  # 标题列
        tasks.sort(key=lambda x: x.title.lower(), reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))
    elif column == 2:  # 截止日期列
        # 处理可能的空截止日期
        tasks.sort(key=lambda x: (x.deadline or ''), reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))
    elif column == 3:  # 紧急程度列
        tasks.sort(key=lambda x: x.urgency_score, reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))
    elif column == 4:  # 描述列
        tasks.sort(key=lambda x: (x.description or '').lower(), reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))
    elif column == 5:  # 创建日期列
        tasks.sort(key=lambda x: x.created_at, reverse=(todo_sort_order[0] == Qt.SortOrder.DescendingOrder))

    # 更新表格显示
    table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        # 状态
        status_item = QTableWidgetItem('✓' if task.completed else '○')
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 0, status_item)
        
        # 标题
        table.setItem(row, 1, QTableWidgetItem(task.title))
        
        # 截止日期
        deadline = task.deadline if task.deadline else '无'
        table.setItem(row, 2, QTableWidgetItem(deadline))
        
        # 紧急程度
        table.setItem(row, 3, QTableWidgetItem(str(task.urgency_score)))
        
        # 描述
        table.setItem(row, 4, QTableWidgetItem(task.description or '-'))
        
        # 创建日期
        table.setItem(row, 5, QTableWidgetItem(task.created_at.strftime('%Y-%m-%d')))
        
        # 存储任务ID用于后续操作
        status_item.setData(Qt.ItemDataRole.UserRole, task.id)