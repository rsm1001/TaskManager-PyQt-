"""
Shortcut Table Service - 快捷入口表格服务模块
提供快捷入口表格的渲染和操作功能
"""

import os
import logging
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QProcess, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QPushButton, QTableWidgetItem

logger = logging.getLogger(__name__)

# 优先级显示映射
PRIORITY_DISPLAY_MAP = {
    'high': '重要',
    'normal': '普通',
    'low': '低'
}


def _get_priority_display(priority):
    """获取优先级的显示文本"""
    return PRIORITY_DISPLAY_MAP.get(priority, '普通')


def _get_claude_path():
    """动态查找claude可执行文件路径"""
    import shutil
    path = shutil.which('claude')
    if path:
        return path
    # 尝试常见的用户安装路径
    user_bin = os.path.join(os.path.expanduser('~'), '.local', 'bin', 'claude.exe')
    if os.path.exists(user_bin):
        return user_bin
    return 'claude'  # fallback


def _open_in_terminal(path):
    """在文件/文件夹所在目录启动cmd执行claude"""
    if not path:
        return
    target_dir = os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) else os.path.abspath(path)
    claude_path = _get_claude_path()
    logger.info(f"在终端中打开路径: {target_dir}")
    os.system(f'start cmd /k "cd /d {target_dir} && {claude_path}"')


def _open_shortcut_path(path, action_type='open'):
    """打开快捷入口路径（文件直接打开，文件夹打开目录，执行脚本）

    Args:
        path: 快捷路径
        action_type: 操作类型 ('open' 或 'script')
    """
    if not path:
        logger.warning("快捷路径为空")
        return

    logger.info(f"打开快捷路径: {path}, 操作类型: {action_type}")

    if action_type == 'script':
        # 执行脚本：在文件所在目录启动cmd执行claude
        script_dir = os.path.dirname(os.path.abspath(path)) if path else ''
        QProcess.startDetached('cmd.exe', ['/c', 'start', 'cmd', '/k', f'cd /d "{script_dir}" && claude'], script_dir)
    elif os.path.isfile(path) and path.lower().endswith(('.bat', '.cmd')):
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


def render_shortcut_row(table, row, shortcut_item):
    """渲染快捷入口表格的一行

    Args:
        table: 表格控件
        row: 行索引
        shortcut_item: dict，包含 keys: task_id, task_type, title, shortcut_path, action_type, tags, created_at
    """
    title = shortcut_item['title']
    shortcut_path = shortcut_item['shortcut_path']
    task_type = shortcut_item['task_type']
    action_type = shortcut_item.get('action_type', 'open')
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
    # 点击按钮执行对应操作
    def on_click(checked, p=shortcut_path, at=action_type):
        _open_shortcut_path(p, at)
    btn.clicked.connect(on_click)
    table.setCellWidget(row, 0, btn)

    # Terminal按钮列：在文件所在目录启动Claude
    claude_btn = QPushButton('>_')
    claude_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    claude_btn.setToolTip(f'在 "{shortcut_path}" 所在目录启动Claude')
    claude_btn.setStyleSheet("""
        QPushButton {
            background-color: #f3e5f5;
            border: 1px solid #9c27b0;
            border-radius: 4px;
            padding: 4px 8px;
            color: #7b1fa2;
            font-size: 13px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e1bee7;
        }
        QPushButton:pressed {
            background-color: #ce93d8;
        }
    """)
    def on_claude_clicked(checked, p=shortcut_path):
        _open_in_terminal(p)
    claude_btn.clicked.connect(on_claude_clicked)
    table.setCellWidget(row, 1, claude_btn)

    # 类型列：显示文件/文件夹
    if os.path.isfile(shortcut_path):
        type_display = '文件'
    elif os.path.isdir(shortcut_path):
        type_display = '文件夹'
    else:
        type_display = '未知'
    table.setItem(row, 2, QTableWidgetItem(type_display))

    # 标签列
    tags_display = tags if tags else '-'
    table.setItem(row, 3, QTableWidgetItem(tags_display))

    # 路径列
    path_text = shortcut_path if shortcut_path else '-'
    path_item = QTableWidgetItem(path_text)
    path_item.setToolTip(path_text)
    table.setItem(row, 4, path_item)

    # 创建日期列
    from datetime import datetime
    raw_date = shortcut_item.get('created_at', '-')
    if raw_date and raw_date != '-':
        try:
            dt = datetime.fromisoformat(raw_date)
            date_display = dt.strftime('%Y-%m-%d %H:%M')
        except:
            date_display = raw_date
    else:
        date_display = '-'
    table.setItem(row, 5, QTableWidgetItem(date_display))

    # 将 id 存在按钮属性中，方便查找
    btn.setProperty("task_id", shortcut_item['id'])
    btn.setProperty("task_type", task_type)
    logger.debug(f"渲染快捷入口行: {title}")
