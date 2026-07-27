"""
Shortcut Table Service - 快捷入口表格服务模块
提供快捷入口表格的渲染和操作功能
"""

import os
import logging
import sqlite3
import subprocess
import sys
import config.config as _config
from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QPushButton, QTableWidgetItem

logger = logging.getLogger(__name__)

# 优先级显示映射（从 managers.tasks.priority 派生）
# 真正的定义在 managers/priority.py PRIORITY_LEVELS
from managers.tasks.priority import PRIORITY_DISPLAY_MAP, get_priority_label  # noqa: E402,F401


def _get_priority_display(priority):
    """获取优先级的显示文本"""
    return get_priority_label(priority)


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


def _get_codex_path():
    """动态查找codex可执行文件路径"""
    import shutil
    path = shutil.which('codex')
    if path:
        return path
    # 尝试常见的用户安装路径
    user_bin = os.path.join(os.path.expanduser('~'), '.local', 'bin', 'codex.exe')
    if os.path.exists(user_bin):
        return user_bin
    return 'codex'  # fallback


def _is_dangerously_skip_permissions_enabled():
    """读取持久化的"放权启动"开关，失败时回落到默认值。

    该函数被启动 claude 的命令调用，调用频次低（用户点击时），因此
    直接打开一次 sqlite 只读连接查询即可，不引入额外缓存复杂度。
    """
    try:
        conn = sqlite3.connect(_config.DATABASE_PATH)
        try:
            cursor = conn.execute(
                "SELECT value FROM configs WHERE key = ?",
                (_config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_KEY,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        if not row or row[0] is None:
            return _config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_DEFAULT
        return str(row[0]).strip().lower() in ('1', 'true', 'yes', 'on')
    except Exception as e:
        logger.warning(f"读取 Claude 放权设置失败，回落默认: {e}")
        return _config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_DEFAULT


def _build_claude_command():
    """根据放权开关构造 Claude 命令参数。"""
    command = [_get_claude_path()]
    if _is_dangerously_skip_permissions_enabled():
        command.append(_config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_FLAG)
    return command


def _is_codex_skip_permissions_enabled():
    """读取持久化的"Codex 放权启动"开关，失败时回落到默认值。"""
    try:
        conn = sqlite3.connect(_config.DATABASE_PATH)
        try:
            cursor = conn.execute(
                "SELECT value FROM configs WHERE key = ?",
                (_config.CODEX_DANGEROUS_SKIP_PERMISSIONS_KEY,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        if not row or row[0] is None:
            return _config.CODEX_DANGEROUS_SKIP_PERMISSIONS_DEFAULT
        return str(row[0]).strip().lower() in ('1', 'true', 'yes', 'on')
    except Exception as e:
        logger.warning(f"读取 Codex 放权设置失败，回落默认: {e}")
        return _config.CODEX_DANGEROUS_SKIP_PERMISSIONS_DEFAULT


def _build_codex_command():
    """根据放权开关构造 Codex 命令参数。"""
    command = [_get_codex_path()]
    if _is_codex_skip_permissions_enabled():
        command.append(_config.CODEX_DANGEROUS_SKIP_PERMISSIONS_FLAG)
    return command


def _launch_terminal(target_dir, command):
    """在目标目录的新终端中执行命令，目录不参与 CMD 文本解析。"""
    working_dir = _get_existing_terminal_directory(target_dir)
    logger.info("启动终端 command=%s working_directory=%s", command, working_dir)
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["cmd.exe", "/k", *command],
                cwd=working_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return
        subprocess.Popen(command, cwd=working_dir)
    except OSError:
        logger.exception("启动终端失败 command=%s working_directory=%s", command, working_dir)


def _get_existing_terminal_directory(target_dir):
    """Return the nearest existing directory for a terminal working directory."""
    candidate = os.path.abspath(target_dir) if target_dir else os.getcwd()
    while not os.path.isdir(candidate):
        parent = os.path.dirname(candidate)
        if parent == candidate:
            logger.warning("No valid terminal directory found for %s; using the current directory", target_dir)
            return os.getcwd()
        candidate = parent
    if os.path.abspath(target_dir) != candidate:
        logger.warning("Terminal directory does not exist; using parent directory: %s", candidate)
    return candidate


def _get_terminal_directory(path):
    """Return the directory in which a terminal should open for a shortcut path."""
    absolute_path = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(absolute_path):
        return absolute_path
    if os.path.isfile(absolute_path) or os.path.splitext(os.path.basename(absolute_path))[1]:
        return os.path.dirname(absolute_path)
    return absolute_path


def _get_script_environment():
    '''Provide launched scripts with the Python used by this application.'''
    environment = os.environ.copy()
    python_directories = []
    for executable in (sys.executable, getattr(sys, '_base_executable', '')):
        if executable:
            directory = os.path.dirname(os.path.abspath(executable))
            if os.path.isdir(directory) and directory not in python_directories:
                python_directories.append(directory)

    if python_directories:
        path_key = next((key for key in environment if key.upper() == 'PATH'), 'PATH')
        existing_path = environment.get(path_key, '')
        environment[path_key] = os.pathsep.join([*python_directories, existing_path])
    return environment


def _open_codex_in_terminal(path):
    """在文件/文件夹所在目录启动cmd执行codex"""
    if not path:
        return
    target_dir = _get_terminal_directory(path)
    _launch_terminal(target_dir, _build_codex_command())


def _open_in_terminal(path):
    """在文件/文件夹所在目录启动cmd执行claude"""
    if not path:
        return
    target_dir = _get_terminal_directory(path)
    _launch_terminal(target_dir, _build_claude_command())


def _run_script(path):
    """Run a script from its own directory and keep command output visible."""
    script_path = os.path.abspath(os.path.expanduser(path))
    working_dir = os.path.dirname(script_path)
    extension = os.path.splitext(script_path)[1].lower()

    if os.name == "nt" and extension in (".bat", ".cmd"):
        subprocess.Popen(
            ["cmd.exe", "/k", "call", script_path],
            cwd=working_dir,
            env=_get_script_environment(),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    elif os.name == "nt" and extension == ".ps1":
        subprocess.Popen(
            ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", script_path],
            cwd=working_dir,
            env=_get_script_environment(),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    elif os.name == "nt":
        os.startfile(script_path)
    else:
        subprocess.Popen([script_path], cwd=working_dir)


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
        _run_script(path)
    elif os.path.isfile(path) and path.lower().endswith(('.bat', '.cmd')):
        _run_script(path)
    elif os.path.isfile(path):
        # 文件：直接打开
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    elif os.path.isdir(path):
        # 文件夹：打开目录
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    else:
        # 路径不存在，也尝试打开
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def render_shortcut_row(table, row, shortcut_item, on_open_callback=None):
    """渲染快捷入口表格的一行

    Args:
        table: 表格控件
        row: 行索引
        shortcut_item: dict，包含 keys: task_id, task_type, title, shortcut_path, action_type, tags, created_at
        on_open_callback: 可选的打开回调，接收 (shortcut_item) 参数，用于在打开时添加历史记录
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
    def on_click(checked, si=shortcut_item, cb=on_open_callback):
        _open_shortcut_path(si['shortcut_path'], si.get('action_type', 'open'))
        if cb:
            cb(si)
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

    # Codex Terminal按钮列（列2）
    codex_btn = QPushButton('>_ ')
    codex_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    codex_btn.setToolTip(f'在 "{shortcut_path}" 所在目录启动Codex')
    codex_btn.setStyleSheet("""
        QPushButton {
            background-color: #e8f5e9;
            border: 1px solid #2e7d32;
            border-radius: 4px;
            padding: 4px 8px;
            color: #1b5e20;
            font-size: 13px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #c8e6c9;
        }
        QPushButton:pressed {
            background-color: #a5d6a7;
        }
    """)
    def on_codex_clicked(checked, p=shortcut_path):
        _open_codex_in_terminal(p)
    codex_btn.clicked.connect(on_codex_clicked)
    table.setCellWidget(row, 2, codex_btn)

    # 类型列（列2 → 列3）
    if os.path.isfile(shortcut_path):
        type_display = '文件'
    elif os.path.isdir(shortcut_path):
        type_display = '文件夹'
    else:
        type_display = '未知'
    table.setItem(row, 3, QTableWidgetItem(type_display))

    # 标签列（列3 → 列4）
    tags_display = tags if tags else '-'
    table.setItem(row, 4, QTableWidgetItem(tags_display))

    # 路径列（列4 → 列5）
    path_text = shortcut_path if shortcut_path else '-'
    path_item = QTableWidgetItem(path_text)
    path_item.setToolTip(path_text)
    table.setItem(row, 5, path_item)

    # 创建日期列（列5 → 列6）
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
    table.setItem(row, 6, QTableWidgetItem(date_display))

    # 将 id 存在按钮属性中，方便查找
    btn.setProperty("task_id", shortcut_item['id'])
    btn.setProperty("task_type", task_type)
    logger.debug(f"渲染快捷入口行: {title}")


def render_history_row(table, row, history_item, on_open_callback, on_pin_callback, on_delete_callback, on_terminal_callback, on_codex_callback=None):
    """渲染历史记录表格的一行

    Args:
        table: 表格控件
        row: 行索引
        history_item: dict，包含 keys: id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned
        on_open_callback: 打开历史记录的回调函数，接收 (history_item)
        on_pin_callback: 切换置顶的回调函数，接收 (history_id)
        on_delete_callback: 删除历史记录的回调函数，接收 (history_id)
        on_terminal_callback: 终端打开的回调函数，接收 (history_item) —— Claude
        on_codex_callback: 终端打开的回调函数，接收 (history_item) —— Codex（可选）
    """
    from PyQt6.QtWidgets import QPushButton, QTableWidgetItem, QWidget, QHBoxLayout
    from PyQt6.QtCore import Qt

    title = history_item.get('shortcut_title', '') or history_item.get('title', '')
    path = history_item.get('shortcut_path', '') or history_item.get('path', '')
    is_pinned = history_item.get('is_pinned', 0) == 1

    # 名称列：创建按钮
    btn = QPushButton(title if title else '(已删除)')
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
    def on_click(checked, h=history_item):
        on_open_callback(h)
    btn.clicked.connect(on_click)
    table.setCellWidget(row, 0, btn)

    # Terminal按钮列
    terminal_btn = QPushButton('>_')
    terminal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    terminal_btn.setToolTip(f'在 "{path}" 所在目录启动Claude')
    terminal_btn.setStyleSheet("""
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
    def on_terminal_clicked(checked, h=history_item):
        on_terminal_callback(h)
    terminal_btn.clicked.connect(on_terminal_clicked)
    table.setCellWidget(row, 1, terminal_btn)

    # Codex Terminal按钮列
    if on_codex_callback:
        codex_btn = QPushButton('>_ ')
        codex_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        codex_btn.setToolTip(f'在 "{path}" 所在目录启动Codex')
        codex_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                border: 1px solid #2e7d32;
                border-radius: 4px;
                padding: 4px 8px;
                color: #1b5e20;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
            QPushButton:pressed {
                background-color: #a5d6a7;
            }
        """)
        def on_codex_clicked(checked, h=history_item):
            on_codex_callback(h)
        codex_btn.clicked.connect(on_codex_clicked)
        table.setCellWidget(row, 2, codex_btn)

    # 置顶标记列（列2 → 列3）
    from PyQt6.QtGui import QColor
    pin_display = '★' if is_pinned else '☆'
    pin_item = QTableWidgetItem(pin_display)
    pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    if is_pinned:
        pin_item.setForeground(QColor('#e65100'))  # 橙色
    else:
        pin_item.setForeground(QColor('#9e9e9e'))  # 灰色
    table.setItem(row, 3, pin_item)

    # 路径列（列3 → 列4）
    path_text = path if path else '-'
    path_item = QTableWidgetItem(path_text)
    path_item.setToolTip(path_text)
    table.setItem(row, 4, path_item)

    # 最后打开时间列（列4 → 列5）
    from datetime import datetime
    raw_date = history_item.get('opened_at', '-')
    if raw_date and raw_date != '-':
        try:
            dt = datetime.fromisoformat(raw_date)
            date_display = dt.strftime('%Y-%m-%d %H:%M')
        except:
            date_display = raw_date
    else:
        date_display = '-'
    table.setItem(row, 5, QTableWidgetItem(date_display))

    # 操作列（列5 → 列6）：置顶/取消置顶按钮
    pin_btn = QPushButton('★' if not is_pinned else '☆')
    pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    pin_btn.setToolTip('置顶' if not is_pinned else '取消置顶')
    pin_btn.setStyleSheet("""
        QPushButton {
            background-color: #fff3e0;
            border: 1px solid #ff9800;
            border-radius: 4px;
            padding: 2px 6px;
            color: #e65100;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #ffe0b2;
        }
    """)
    def on_pin_clicked(checked, hid=history_item['id']):
        on_pin_callback(hid)
    pin_btn.clicked.connect(on_pin_clicked)

    # 删除按钮
    delete_btn = QPushButton('×')
    delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    delete_btn.setToolTip('删除' if not is_pinned else '置顶记录不可删除')
    delete_btn.setEnabled(not is_pinned)  # 置顶记录不可删除
    delete_btn.setStyleSheet("""
        QPushButton {
            background-color: #ffebee;
            border: 1px solid #f44336;
            border-radius: 4px;
            padding: 2px 6px;
            color: #c62828;
            font-size: 12px;
        }
        QPushButton:hover:enabled {
            background-color: #ffcdd2;
        }
        QPushButton:disabled {
            background-color: #e0e0e0;
            border-color: #9e9e9e;
            color: #9e9e9e;
        }
    """)
    def on_delete_clicked(checked, hid=history_item['id']):
        on_delete_callback(hid)
    delete_btn.clicked.connect(on_delete_clicked)

    # 操作列布局
    op_widget = QWidget()
    op_layout = QHBoxLayout(op_widget)
    op_layout.setContentsMargins(0, 0, 0, 0)
    op_layout.addWidget(pin_btn)
    op_layout.addWidget(delete_btn)
    op_layout.addStretch()
    table.setCellWidget(row, 6, op_widget)

    # 将 id 存在按钮属性中，方便查找
    btn.setProperty("history_id", history_item['id'])
    logger.debug(f"渲染历史记录行: {title}")
