"""
应用程序配置文件
固定参数集中管理，避免硬编码分散在代码各处
"""
import os


# 应用程序基本信息
APP_NAME = "任务管理系统"
APP_VERSION = "1.0.0"
APP_AUTHOR = "AI Assistant"

# 数据库配置
DATABASE_PATH = "taskmanager.db"

# 界面配置
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# 颜色配置
COLOR_COMPLETED = "#4CAF50"  # 绿色
COLOR_PENDING = "#2196F3"    # 蓝色
COLOR_EXPIRED = "#F44336"    # 红色
COLOR_TODAY = "#FF9800"      # 橙色

# UI 样式配置
TOAST_STYLE = """
    QLabel {
        background-color: #333333;
        color: white;
        padding: 12px 24px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: bold;
    }
"""

# 紧急程度配置
URGENCY_HIGH = 3    # 高紧急程度阈值
URGENCY_MEDIUM = 2  # 中紧急程度阈值
URGENCY_LOW = 1     # 低紧急程度阈值

# 算法配置
DEFAULT_BASE_COEFFICIENT = 1.5

# 文件路径配置
DEFAULT_EXPORT_PATH = "./exports"
DEFAULT_IMPORT_PATH = "./imports"

# 星期名称配置（用于界面显示和逻辑处理）
WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
WEEKDAY_FILTER_OPTIONS = ['全部', '每天'] + WEEKDAY_NAMES

# 任务状态配置
class TaskStatus:
    """任务状态常量"""
    PENDING = "pending"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

# 状态显示映射（界面显示用）
STATUS_DISPLAY_MAP = {
    TaskStatus.PENDING: '○',
    TaskStatus.COMPLETED: '✓',
    TaskStatus.ABANDONED: '✗'
}

# 状态筛选选项
STATUS_FILTER_OPTIONS = ['全部', '进行中', '已完成', '暂弃']
STATUS_FILTER_MAP = {
    '全部': 'all',
    '进行中': TaskStatus.PENDING,
    '已完成': TaskStatus.COMPLETED,
    '暂弃': TaskStatus.ABANDONED
}

# 消息文本配置
MESSAGES = {
    'task_added': {
        'daily': '每日任务添加成功',
        'todo': '待办事项添加成功',
        'entertainment': '娱乐任务添加成功',
    },
    'task_updated': {
        'daily': '每日任务更新成功',
        'todo': '待办事项更新成功',
        'entertainment': '娱乐任务更新成功',
    },
    'task_deleted': {
        'daily': '每日任务删除成功',
        'todo': '待办事项删除成功',
        'entertainment': '娱乐任务删除成功',
    },
    'no_pending': {
        'daily': '没有未完成的符合条件的每日任务',
        'todo': '没有未完成的待办事项',
        'entertainment': '没有未完成的娱乐任务',
        'task': '没有符合条件的任务',
    }
}

# Toast 提示配置
TOAST_DURATION_MS = 2000  # 默认显示时长（毫秒）
TOAST_FADE_STEP = 0.1     # 淡出步长
TOAST_FADE_INTERVAL = 50  # 淡出间隔（毫秒）


def ensure_directories():
    """确保所需目录存在（延迟创建，避免导入时副作用）"""
    os.makedirs(DEFAULT_EXPORT_PATH, exist_ok=True)
    os.makedirs(DEFAULT_IMPORT_PATH, exist_ok=True)