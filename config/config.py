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

# 紧急程度配置
URGENCY_HIGH = 3    # 高紧急程度阈值
URGENCY_MEDIUM = 2  # 中紧急程度阈值
URGENCY_LOW = 1     # 低紧急程度阈值

# 算法配置
DEFAULT_BASE_COEFFICIENT = 1.5

# 文件路径配置
DEFAULT_EXPORT_PATH = "./exports"
DEFAULT_IMPORT_PATH = "./imports"


def ensure_directories():
    """确保所需目录存在（延迟创建，避免导入时副作用）"""
    os.makedirs(DEFAULT_EXPORT_PATH, exist_ok=True)
    os.makedirs(DEFAULT_IMPORT_PATH, exist_ok=True)