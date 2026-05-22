"""
Task Table Operations Module
处理任务表格的各种操作，包括加载、状态切换、排序等功能
"""

from PyQt6.QtWidgets import QTableWidgetItem, QPushButton
from PyQt6.QtCore import Qt, QUrl, QProcess
from PyQt6.QtGui import QDesktopServices
import config.config as config
import os


def _get_status_filter(status_text):
    """将界面状态文本转换为过滤器值"""
    return config.STATUS_FILTER_MAP.get(status_text, 'all')


def _render_shortcut_row(table, row, shortcut_item):
    """渲染快捷入口表格的一行

    Args:
        table: 表格控件
        row: 行索引
        shortcut_item: dict，包含 keys: task_id, task_type, title, shortcut_path, tags, created_at
    """
    title = shortcut_item['title']
    shortcut_path = shortcut_item['shortcut_path']
    task_type = shortcut_item['task_type']
    tags = shortcut_item.get('tags', '') or ''

    # 名称列：创建按钮
    btn = QPushButton(title)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            background-color: #e3f2fd;
            border: 1px solid #2196F3;
            border-radius: 4px;
            padding: 4px 12px;
            color: #1976D2;
            font-size: 13px;
            text-align: left;
        }
        QPushButton:hover {
            background-color: #bbdefb;
        }
        QPushButton:pressed {
            background-color: #90caf9;
        }
    """)
    # 点击按钮直接打开
    btn.clicked.connect(lambda _=False, p=shortcut_path: _open_shortcut_path(p))
    table.setCellWidget(row, 0, btn)

    # 类型列：显示文件或文件夹
    if os.path.isfile(shortcut_path):
        type_display = '文件'
    elif os.path.isdir(shortcut_path):
        type_display = '文件夹'
    else:
        type_display = '未知'
    table.setItem(row, 1, QTableWidgetItem(type_display))

    # 标签列
    tags_display = tags if tags else '-'
    table.setItem(row, 2, QTableWidgetItem(tags_display))

    # 路径列
    path_text = shortcut_path if shortcut_path else '-'
    path_item = QTableWidgetItem(path_text)
    path_item.setToolTip(path_text)
    table.setItem(row, 3, path_item)

    # 创建日期列
    table.setItem(row, 4, QTableWidgetItem(shortcut_item.get('created_at', '-')))

    # 将 id 存在按钮属性中，方便查找
    btn.setProperty("task_id", shortcut_item['id'])
    btn.setProperty("task_type", task_type)


def _open_shortcut_path(path):
    """打开快捷入口路径（文件直接打开，文件夹打开目录）"""
    if not path:
        return
    if os.path.isfile(path) and path.lower().endswith(('.bat', '.cmd')):
        # bat/cmd 文件：用 QProcess 执行，设置正确的工作目录
        working_dir = os.path.dirname(os.path.abspath(path))
        QProcess.startDetached('cmd.exe', ['/c', 'start', '', path], working_dir)
    elif os.path.isfile(path):
        # 文件：直接打开
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    elif os.path.isdir(path):
        # 文件夹：打开目录
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    else:
        # 路径不存在，也尝试打开
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


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
    tag_filter = getattr(window, 'current_tag_filter', '')

    tasks = window.data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter, tag=tag_filter)

    window.daily_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        columns = [
            (1, task.title),
            (2, task.category if task.category else '-'),
            (3, task.week_day if task.week_day else '每天'),
            (4, task.tags if task.tags else '-'),
            (5, task.description or '-'),
            (6, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.daily_table, row, task, columns)

    window.update_status_bar()


def load_todo_tasks_to_table(window):
    """加载待办事项到表格"""
    status_text = window.todo_status_combo.currentText()
    if status_text == '已过期':
        status_filter = 'all'
    else:
        status_filter = _get_status_filter(status_text)

    tag_filter = getattr(window, 'current_tag_filter', '')

    tasks = window.data_manager.get_todo_tasks(status=status_filter, tag=tag_filter)

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, task.category if task.category else '-'),
            (4, f"{task.urgency_score:.2f}"),
            (5, task.tags if task.tags else '-'),
            (6, task.description or '-'),
            (7, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)

    window.update_status_bar()


def load_entertainment_tasks_to_table(window):
    """加载娱乐任务到表格"""
    status_filter = _get_status_filter(window.entertainment_status_combo.currentText())
    tag_filter = getattr(window, 'current_tag_filter', '')

    tasks = window.data_manager.get_entertainment_tasks(status=status_filter, tag=tag_filter)

    window.entertainment_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        columns = [
            (1, task.title),
            (2, task.fun_category),
            (3, task.category if task.category else '-'),
            (4, task.tags if task.tags else '-'),
            (5, task.description or '-'),
            (6, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.entertainment_table, row, task, columns, editable_cols={1, 2, 3, 4})

    window.update_status_bar()


def load_shortcuts_to_table(window):
    """加载所有快捷入口到快捷入口表格"""
    tag_filter = getattr(window, 'current_shortcut_tag_filter', '')
    shortcuts = window.data_manager.get_all_shortcuts(tag=tag_filter if tag_filter else None)
    window.shortcuts_table.setRowCount(len(shortcuts))
    for row, item in enumerate(shortcuts):
        _render_shortcut_row(window.shortcuts_table, row, item)


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
            window.data_manager.toggle_daily_task_completion(task_id)
            from PyQt6.QtCore import QTimer
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
            window.data_manager.toggle_todo_task_completion(task_id)
            from PyQt6.QtCore import QTimer
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
            window.data_manager.toggle_entertainment_task_completion(task_id)
            from PyQt6.QtCore import QTimer
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
        status_filter = 'all'
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

    window.todo_table.setRowCount(len(tasks))
    for row, task in enumerate(tasks):
        columns = [
            (1, task.title),
            (2, task.deadline if task.deadline else '无'),
            (3, task.category if task.category else '-'),
            (4, f"{task.urgency_score:.2f}"),
            (5, task.tags if task.tags else '-'),
            (6, task.description or '-'),
            (7, task.created_at.strftime('%Y-%m-%d'))
        ]
        _set_task_row_data(window.todo_table, row, task, columns)
