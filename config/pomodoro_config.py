"""
Pomodoro Configuration - 番茄钟配置模块
"""

# 默认番茄钟设置
DEFAULT_WORK_DURATION = 25 * 60  # 工作时长（秒），默认25分钟
DEFAULT_SHORT_BREAK = 5 * 60    # 短休息时长（秒），默认5分钟
DEFAULT_LONG_BREAK = 15 * 60    # 长休息时长（秒），默认15分钟
LONG_BREAK_INTERVAL = 4         # 经过多少个番茄钟后触发长休息

# 配置项key
CONFIG_WORK_DURATION = "pomodoro_work_duration"
CONFIG_SHORT_BREAK = "pomodoro_short_break"
CONFIG_LONG_BREAK = "pomodoro_long_break"
CONFIG_AUTO_START_BREAK = "pomodoro_auto_start_break"
CONFIG_AUTO_START_WORK = "pomodoro_auto_start_work"
CONFIG_SOUND_ENABLED = "pomodoro_sound_enabled"
CONFIG_NOTIFICATION_ENABLED = "pomodoro_notification_enabled"
