"""
Task Manager Messages and Utilities Module
将原来的主界面中的消息文本、对话框逻辑和工具函数分离出来以实现解耦
"""

from PyQt6.QtWidgets import QMessageBox, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
import config.config as config


class ToastMessage(QLabel):
    """自动消失的提示消息（Toast样式）"""

    _instance = None  # 类变量：追踪唯一活跃实例

    def __init__(self, text, parent=None, duration=None):
        super().__init__(text, parent)
        self.duration = duration if duration is not None else config.TOAST_DURATION_MS
        # 必须同时设置 Window 标志，否则 FramelessWindowHint 无法使 widget
        # 成为真正的顶层窗口，导致 move() 使用父窗口相对坐标而非桌面绝对坐标
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Window
        )
        self.setStyleSheet(config.TOAST_STYLE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMargin(10)
        self.setMinimumSize(200, 40)
        self._fade_timer = None

    def show_at_center(self):
        """在父窗口中央显示"""
        # 同步清理可能残留的旧实例
        if ToastMessage._instance is not None and ToastMessage._instance != self:
            try:
                old = ToastMessage._instance
                # 停止旧实例的淡出计时器
                if old._fade_timer:
                    old._fade_timer.stop()
                    old._fade_timer = None
                # 隐藏并销毁旧窗口（同步方式）
                old.hide()
                old.deleteLater()
            except Exception:
                pass
            ToastMessage._instance = None

        ToastMessage._instance = self
        self.adjustSize()
        if self.width() < 200:
            self.resize(200, self.height())
        if self.height() < 40:
            self.resize(self.width(), 40)

        # 先 show() 将窗口注册为独立顶层窗口，
        # 再用父窗口中心点（通过 mapToGlobal 转为绝对屏幕坐标）居中定位，
        # 避免 move→show 顺序下不同平台对 parent 关联窗口坐标系行为的差异
        self.show()

        if self.parent():
            parent_win = self.parent().window()
            parent_center = parent_win.frameGeometry().center()
            x = parent_center.x() - self.width() // 2
            y = parent_center.y() - self.height() // 2
            self.move(x, y)
        QTimer.singleShot(self.duration, self._do_fade_out)

    def _do_fade_out(self):
        if ToastMessage._instance != self:
            return
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_step)
        self._fade_timer.start(50)
        self.current_opacity = 1.0

    def _fade_step(self):
        if ToastMessage._instance != self:
            self._fade_timer.stop()
            return
        self.current_opacity -= config.TOAST_FADE_STEP
        if self.current_opacity <= 0:
            self._fade_timer.stop()
            ToastMessage._instance = None
            self.close()
            self.deleteLater()
        else:
            self.setWindowOpacity(self.current_opacity)


def show_toast(parent, text, duration=None):
    """显示自动消失的提示消息

    Args:
        parent: 父窗口
        text: 显示文本
        duration: 显示时长（毫秒），默认从配置读取
    """
    # 防御性检查：parent 为 None 或 text 为空时不创建无效窗口
    if not parent or not text:
        return
    # 防止重复创建：如果已有 toast 在显示，忽略本次请求
    if ToastMessage._instance is not None:
        return
    toast = ToastMessage(text, parent, duration)
    toast.show_at_center()


# 消息文本从配置文件导入
MESSAGES = config.MESSAGES


def show_statistics_dialog(stats, parent=None):
    """显示统计信息对话框"""
    msg = f"""统计信息：

每日任务：{stats['daily']['total']} 个 ({stats['daily']['completed']} 已成, {stats['daily']['paused']} 暂弃不统计)
待办事项：{stats['todo']['total']} 个 ({stats['todo']['completed']} 已成, {stats['todo']['expired']} 过期, {stats['todo']['paused']} 暂弃不统计)
娱乐任务：{stats['entertainment']['total']} 个 ({stats['entertainment']['completed']} 已成, {stats['entertainment']['paused']} 暂弃不统计)

总计：{stats['daily']['total'] + stats['todo']['total'] + stats['entertainment']['total']} 个任务（暂弃不统计）
已完成：{stats['daily']['completed'] + stats['todo']['completed'] + stats['entertainment']['completed']} 个
已暂弃：{stats['daily']['paused'] + stats['todo']['paused'] + stats['entertainment']['paused']} 个"""

    QMessageBox.information(parent, '统计信息', msg)


def show_type_check_dialog(parent=None):
    """运行 mypy 类型检查并显示结果对话框"""
    import subprocess
    import sys

    files = [
        "models/model.py",
        "managers/infrastructure/data_access.py",
        "managers/tasks/task_orchestrator.py",
        "managers/application/data_manager.py",
        "managers/tasks/priority.py",
        "managers/tasks/task_type.py",
        "services/domain/statistics_service.py",
        "services/factories/service_factory.py",
    ]
    cmd = [
        sys.executable, "-m", "mypy",
        *files,
        "--config-file", "pyproject.toml",
        "--follow-imports=skip",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        QMessageBox.warning(parent, "类型检查", "mypy 运行超时（> 2 分钟）")
        return
    except FileNotFoundError:
        QMessageBox.warning(parent, "类型检查", "未找到 mypy，请先安装：pip install mypy")
        return

    output = result.stdout + result.stderr
    if not output.strip():
        output = "（无输出）"

    QMessageBox.information(
        parent,
        "类型检查结果",
        f"退出码: {result.returncode}\n\n{output[:3000]}",
    )


def show_about_dialog(parent=None):
    """显示关于信息对话框"""
    QMessageBox.about(parent, '关于', '''任务管理系统 v1.0

功能：
- 每日必做任务管理（支持按星期分类）
- 待办事项管理（带截止日期和紧急程度）
- 娱乐任务管理
- SQLite数据库存储
- 数据导入导出（JSON格式）
- 每日自动重置
- 带权重的随机选择
- 现代化图形界面

作者：AI Assistant
日期：2026年''')


def show_random_daily_task_dialog(task, parent=None):
    """显示随机抽取的每日任务对话框"""
    weekday_display = task.week_day if task.week_day else '每天'
    QMessageBox.information(parent, '随机抽取', f'建议处理任务：\n\n标题：{task.title}\n星期：{weekday_display}')


def show_random_todo_task_dialog(task, parent=None):
    """显示随机抽取的待办任务对话框"""
    QMessageBox.information(parent, '随机抽取', 
                           f'建议处理任务：\n\n标题：{task.title}\n截止日期：{task.deadline or "无"}\n紧急度：{task.urgency_score:.2f}')


def show_random_entertainment_task_dialog(task, parent=None):
    """显示随机抽取的娱乐任务对话框"""
    QMessageBox.information(parent, '随机抽取', f'建议娱乐：\n\n{task.title}')


def show_task_added_confirmation(task_type, parent=None):
    """显示任务添加成功提示（自动消失）
    
    Args:
        task_type: 任务类型（daily/todo/entertainment）
        parent: 父窗口，用于定位提示位置
    """
    message = config.MESSAGES['task_added'].get(task_type, '任务添加成功')
    if parent:
        show_toast(parent, message)
    return message


def show_task_updated_confirmation(task_type, parent=None):
    """显示任务更新成功提示（自动消失）
    
    Args:
        task_type: 任务类型（daily/todo/entertainment）
        parent: 父窗口，用于定位提示位置
    """
    message = config.MESSAGES['task_updated'].get(task_type, '任务更新成功')
    if parent:
        show_toast(parent, message)
    return message


def show_task_deleted_confirmation(task_type, parent=None):
    """显示任务删除成功提示（自动消失）
    
    Args:
        task_type: 任务类型（daily/todo/entertainment）
        parent: 父窗口，用于定位提示位置
    """
    message = config.MESSAGES['task_deleted'].get(task_type, '任务删除成功')
    if parent:
        show_toast(parent, message)
    return message


def confirm_task_deletion(parent=None):
    """确认任务删除对话框"""
    return QMessageBox.question(
        parent, 
        '确认', 
        '确定要删除这个任务吗？', 
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )


def confirm_batch_deletion(count: int, parent=None):
    """确认批量删除对话框"""
    return QMessageBox.question(
        parent,
        '确认',
        f'确定要删除这 {count} 个任务吗？',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )


def confirm_data_import(parent=None):
    """确认数据导入对话框"""
    return QMessageBox.question(
        parent, 
        '确认', 
        '导入数据将会覆盖现有数据，确定继续？', 
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )


def show_import_success(parent=None):
    """显示导入成功消息"""
    return QMessageBox.information(parent, '成功', '数据导入成功')


def show_import_failure(parent=None):
    """显示导入失败消息"""
    return QMessageBox.critical(parent, '错误', '数据导入失败，请检查JSON文件格式是否正确')


def show_export_success(parent=None):
    """显示导出成功消息"""
    return QMessageBox.information(parent, '成功', '数据导出成功')


def show_export_failure(parent=None):
    """显示导出失败消息"""
    return QMessageBox.critical(parent, '错误', '数据导出失败')


def warn_no_task_selected(parent=None):
    """警告：未选择任务"""
    return QMessageBox.warning(parent, '警告', '请先选择一个任务')


def inform_no_suitable_tasks(message, parent=None):
    """提示：没有合适的任务"""
    return QMessageBox.information(parent, '提示', message)


def inform_no_pending_tasks(task_type='task', parent=None):
    """提示：没有未完成的任务"""
    message = config.MESSAGES['no_pending'].get(task_type, config.MESSAGES['no_pending']['task'])
    return QMessageBox.information(parent, '提示', message)


def update_task_row_style(table, row, is_completed):
    """更新任务行样式（根据完成状态）"""
    from PyQt6.QtGui import QColor
    color = QColor(200, 200, 200) if is_completed else QColor(255, 255, 255)
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            item.setBackground(color)
