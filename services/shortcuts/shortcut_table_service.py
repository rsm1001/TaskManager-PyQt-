"""
Shortcut Table Service - 快捷入口表格服务模块
提供快捷入口表格的渲染和操作功能
"""

import os
import logging
import sqlite3
import shutil
import subprocess
import sys
import config.config as _config
from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QPushButton, QTableWidgetItem

from services.shortcuts.terminal_service import (
    AGENT_TERMINAL_GROUP,
    SCRIPT_TERMINAL_GROUP,
    launch_terminal_tab,
)

logger = logging.getLogger(__name__)


# Keep the action buttons in separate visual hit areas.  QTableWidget places a
# cell widget flush against the neighbouring cell by default, which makes the
# shortcut, Claude, and Codex buttons especially easy to hit accidentally.
_BUTTON_CELL_HORIZONTAL_MARGIN = 6
_BUTTON_CELL_VERTICAL_MARGIN = 4


class _PaddedButtonCell(QWidget):
    """Container that keeps the existing cell-button API for callers.

    A few parts of the application read ``cellWidget(row, 0)`` and call
    ``property('task_id')`` or ``click()`` on it.  Forward those operations to
    the actual button while using the container to provide the visual gap.
    """

    def __init__(self, button):
        super().__init__()
        self.button = button
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _BUTTON_CELL_HORIZONTAL_MARGIN,
            _BUTTON_CELL_VERTICAL_MARGIN,
            _BUTTON_CELL_HORIZONTAL_MARGIN,
            _BUTTON_CELL_VERTICAL_MARGIN,
        )
        layout.addWidget(button)

    def click(self):
        self.button.click()

    def property(self, name):
        value = super().property(name)
        return value if value is not None else self.button.property(name)


def _set_button_cell(table, row, column, button):
    """Place a button in a padded cell so adjacent actions are clearly separated."""
    table.setCellWidget(row, column, _PaddedButtonCell(button))

# 优先级显示映射（从 managers.tasks.priority 派生）
# 真正的定义在 managers/priority.py PRIORITY_LEVELS
from managers.tasks.priority import PRIORITY_DISPLAY_MAP, get_priority_label  # noqa: E402,F401


def _get_priority_display(priority):
    """获取优先级的显示文本"""
    return get_priority_label(priority)


def _get_cli_path(command_name):
    """Resolve a CLI executable without relying solely on the inherited PATH."""
    path = shutil.which(command_name)
    if path:
        return path

    candidates = []
    if os.name == "nt":
        # npm installs Windows global command shims here by default. Explorer
        # shortcuts can retain an older PATH, so probe this location directly.
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "npm", f"{command_name}.cmd"))
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(os.path.join(local_appdata, "npm", f"{command_name}.cmd"))

    user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    candidates.append(os.path.join(user_bin, command_name + (".exe" if os.name == "nt" else "")))

    for candidate in candidates:
        if os.path.isfile(candidate):
            logger.info("Resolved %s from a known installation path: %s", command_name, candidate)
            return candidate

    logger.warning("Unable to resolve %s from PATH or known installation paths", command_name)
    return None


def _get_claude_path():
    """Find the Claude CLI executable path, if it is installed."""
    return _get_cli_path("claude")


def _get_codex_path():
    """Find the Codex CLI executable path, if it is installed."""
    return _get_cli_path("codex")


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
    """Build the Claude command, respecting the permission setting."""
    executable = _get_claude_path()
    if not executable:
        return None
    command = [executable]
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
    """Build the Codex command, respecting the permission setting."""
    executable = _get_codex_path()
    if not executable:
        return None
    command = [executable]
    if _is_codex_skip_permissions_enabled():
        command.append(_config.CODEX_DANGEROUS_SKIP_PERMISSIONS_FLAG)
    return command

def _launch_terminal(target_dir, command, provider="Claude"):
    """Open a Claude/Codex tab in the shared agent terminal window."""
    working_dir = _get_existing_terminal_directory(target_dir)
    tab_title = f"{provider} - {os.path.basename(os.path.normpath(working_dir)) or 'project'}"
    logger.info("Launch terminal tab provider=%s command=%s cwd=%s", provider, command, working_dir)
    try:
        return launch_terminal_tab(
            command,
            working_dir,
            AGENT_TERMINAL_GROUP,
            title=tab_title,
            popen=subprocess.Popen,
        )
    except OSError:
        logger.exception("Terminal launch failed command=%s cwd=%s", command, working_dir)
        return None


def _get_existing_terminal_directory(target_dir):
    """Return the nearest existing directory for a terminal working directory."""
    requested = os.path.abspath(target_dir) if target_dir else os.getcwd()
    candidate = requested
    while not os.path.isdir(candidate):
        parent = os.path.dirname(candidate)
        if parent == candidate:
            logger.warning("No valid terminal directory found for %s; using the current directory", target_dir)
            return os.getcwd()
        candidate = parent
    if requested != candidate:
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


def _show_cli_not_found(display_name, command_name):
    """Show a clear in-app error instead of opening CMD with a bare command."""
    npm_directory = r"%APPDATA%\npm"
    message = (
        f"未检测到 {display_name} 命令行工具。\n\n"
        f"请确认已安装 `{command_name}`，并将 npm 全局目录加入用户 PATH：\n"
        f"{npm_directory}\n\n"
        "完成后请完全退出并重新启动任务管理器，再重试。"
    )
    logger.error("%s CLI was not found; terminal launch cancelled", display_name)
    QMessageBox.warning(None, f"{display_name} 未找到", message)

def _open_codex_in_terminal(path):
    """Open a Codex tab in the shared agent terminal window."""
    if not path:
        return
    command = _build_codex_command()
    if not command:
        _show_cli_not_found("Codex", "codex")
        return
    target_dir = _get_terminal_directory(path)
    _launch_terminal(target_dir, command, provider="Codex")


def _open_in_terminal(path):
    """Open a Claude tab in the shared agent terminal window."""
    if not path:
        return
    command = _build_claude_command()
    if not command:
        _show_cli_not_found("Claude", "claude")
        return
    target_dir = _get_terminal_directory(path)
    _launch_terminal(target_dir, command, provider="Claude")


def _run_script(path):
    """Run a script in the separate script terminal window."""
    script_path = os.path.abspath(os.path.expanduser(path))
    working_dir = os.path.dirname(script_path) or os.getcwd()
    extension = os.path.splitext(script_path)[1].lower()
    environment = _get_script_environment()

    if os.name == "nt" and extension in (".bat", ".cmd"):
        command = ["cmd.exe", "/d", "/c", "call", script_path]
    elif os.name == "nt" and extension == ".ps1":
        command = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", script_path]
    elif os.name == "nt" and extension == ".py":
        # Use the interpreter running this application, not a file association.
        command = [sys.executable, script_path]
    elif os.name == "nt" and extension == ".exe":
        command = [script_path]
    elif os.name != "nt":
        command = [script_path]
    else:
        # File associations such as .lnk do not expose a safe command line.
        # Keep the existing system-open behavior for those entries.
        try:
            os.startfile(script_path)
        except OSError:
            logger.exception("Script open failed path=%s", script_path)
            return False
        return True

    title = f"Script - {os.path.basename(script_path) or 'unnamed'}"
    try:
        launch_terminal_tab(
            command,
            working_dir,
            SCRIPT_TERMINAL_GROUP,
            title=title,
            env=environment,
            popen=subprocess.Popen,
            wrap_in_cmd=False,
        )
        return True
    except OSError:
        logger.exception("Script terminal launch failed path=%s", script_path)
        return False


def _open_shortcut_path(path, action_type='open'):
    """Open a shortcut path and return whether the launch request was accepted."""
    if not path:
        logger.warning("Shortcut path is empty")
        return False

    logger.info("Open shortcut path: %s, action type: %s", path, action_type)

    if action_type == 'script':
        return bool(_run_script(path))
    if os.path.isfile(path) and path.lower().endswith(('.bat', '.cmd')):
        return bool(_run_script(path))

    url = QUrl.fromLocalFile(path)
    opened = QDesktopServices.openUrl(url)
    if not opened:
        logger.warning("The operating system rejected shortcut path: %s", path)
    return bool(opened)


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
        if not _open_shortcut_path(si['shortcut_path'], si.get('action_type', 'open')):
            QMessageBox.warning(table, 'Launch failed', 'The operating system could not open this shortcut.')
            return
        if cb:
            cb(si)
    btn.clicked.connect(on_click)
    _set_button_cell(table, row, 0, btn)

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
    _set_button_cell(table, row, 1, claude_btn)

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
    _set_button_cell(table, row, 2, codex_btn)

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
    btn.setProperty("shortcut_path", shortcut_path)
    btn.setProperty("action_type", action_type)
    btn.setToolTip("\u70b9\u51fb\u542f\u52a8\uff1b\u4ece\u7c7b\u578b\u3001\u6807\u7b7e\u6216\u8def\u5f84\u5217\u62d6\u5165\u884c\u7a0b\u89c4\u5212\u4ee5\u7ed1\u5b9a")
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
    _set_button_cell(table, row, 0, btn)

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
    _set_button_cell(table, row, 1, terminal_btn)

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
        _set_button_cell(table, row, 2, codex_btn)

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
