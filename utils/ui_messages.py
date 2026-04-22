"""
Task Manager Messages and Utilities Module
将原来的主界面中的消息文本、对话框逻辑和工具函数分离出来以实现解耦
"""

from PyQt6.QtWidgets import QMessageBox, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
import config.config as config


class ToastMessage(QLabel):
    """自动消失的提示消息（Toast样式）"""
    
    def __init__(self, text, parent=None, duration=None):
        """
        Args:
            text: 显示文本
            parent: 父窗口
            duration: 显示时长（毫秒），默认从配置读取
        """
        super().__init__(text, parent)
        self.duration = duration if duration is not None else config.TOAST_DURATION_MS
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI样式"""
        self.setStyleSheet(config.TOAST_STYLE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.adjustSize()
        
        # 设置透明度效果用于淡出动画
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)
        
    def show_at_center(self):
        """在父窗口中央显示"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + parent_rect.height() // 2 - 50
            self.move(x, y)
        self.show()
        self.raise_()
        
        # 启动定时器，延迟后淡出
        QTimer.singleShot(self.duration, self.start_fade_out)
        
    def start_fade_out(self):
        """开始淡出动画"""
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_step)
        self.fade_timer.start(50)
        self.current_opacity = 1.0
        
    def fade_step(self):
        """淡出步骤"""
        self.current_opacity -= config.TOAST_FADE_STEP
        if self.current_opacity <= 0:
            self.fade_timer.stop()
            self.close()
            self.deleteLater()
        else:
            self.opacity_effect.setOpacity(self.current_opacity)


def show_toast(parent, text, duration=None):
    """显示自动消失的提示消息
    
    Args:
        parent: 父窗口
        text: 显示文本
        duration: 显示时长（毫秒），默认从配置读取
    """
    toast = ToastMessage(text, parent, duration)
    toast.show_at_center()


# 消息文本从配置文件导入
MESSAGES = config.MESSAGES


def show_statistics_dialog(stats):
    """显示统计信息对话框"""
    msg = f"""统计信息：
    
每日任务：{stats['daily']['total']} 个 ({stats['daily']['completed']} 已成)
待办事项：{stats['todo']['total']} 个 ({stats['todo']['completed']} 已成, {stats['todo']['expired']} 已过期)
娱乐任务：{stats['entertainment']['total']} 个 ({stats['entertainment']['completed']} 已成)

总计：{stats['daily']['total'] + stats['todo']['total'] + stats['entertainment']['total']} 个任务
已完成：{stats['daily']['completed'] + stats['todo']['completed'] + stats['entertainment']['completed']} 个"""

    QMessageBox.information(None, '统计信息', msg)


def show_about_dialog():
    """显示关于信息对话框"""
    QMessageBox.about(None, '关于', '''任务管理系统 v1.0

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


def show_random_daily_task_dialog(task):
    """显示随机抽取的每日任务对话框"""
    weekday_display = task.week_day if task.week_day else '每天'
    QMessageBox.information(None, '随机抽取', f'建议处理任务：\n\n标题：{task.title}\n星期：{weekday_display}')


def show_random_todo_task_dialog(task):
    """显示随机抽取的待办任务对话框"""
    QMessageBox.information(None, '随机抽取', 
                           f'建议处理任务：\n\n标题：{task.title}\n截止日期：{task.deadline or "无"}\n紧急度：{task.urgency_score}')


def show_random_entertainment_task_dialog(task):
    """显示随机抽取的娱乐任务对话框"""
    QMessageBox.information(None, '随机抽取', f'建议娱乐：\n\n{task.title}')


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


def confirm_task_deletion():
    """确认任务删除对话框"""
    return QMessageBox.question(
        None, 
        '确认', 
        '确定要删除这个任务吗？', 
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )


def confirm_data_import():
    """确认数据导入对话框"""
    return QMessageBox.question(
        None, 
        '确认', 
        '导入数据将会覆盖现有数据，确定继续？', 
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )


def show_import_success():
    """显示导入成功消息"""
    return QMessageBox.information(None, '成功', '数据导入成功')


def show_import_failure():
    """显示导入失败消息"""
    return QMessageBox.critical(None, '错误', '数据导入失败，请检查JSON文件格式是否正确')


def show_export_success():
    """显示导出成功消息"""
    return QMessageBox.information(None, '成功', '数据导出成功')


def show_export_failure():
    """显示导出失败消息"""
    return QMessageBox.critical(None, '错误', '数据导出失败')


def warn_no_task_selected():
    """警告：未选择任务"""
    return QMessageBox.warning(None, '警告', '请先选择一个任务')


def inform_no_suitable_tasks(message):
    """提示：没有合适的任务"""
    return QMessageBox.information(None, '提示', message)


def inform_no_pending_tasks(task_type='task'):
    """提示：没有未完成的任务"""
    message = config.MESSAGES['no_pending'].get(task_type, config.MESSAGES['no_pending']['task'])
    return QMessageBox.information(None, '提示', message)


def update_task_row_style(table, row, is_completed):
    """更新任务行样式（根据完成状态）"""
    from PyQt6.QtGui import QColor
    color = QColor(200, 200, 200) if is_completed else QColor(255, 255, 255)
    for col in range(table.columnCount()):
        item = table.item(row, col)
        if item:
            item.setBackground(color)