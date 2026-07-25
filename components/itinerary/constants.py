"""行程组件的共享常量。"""

WEEKDAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
WEEKDAY_FULL = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
HOUR_BLOCKS = [(0, '凌晨'), (4, '早晨'), (8, '上午'), (12, '下午'), (16, '傍晚'), (20, '晚上')]
BLOCK_COLORS = {
    '凌晨': '#1A1A2E', '早晨': '#E8B4B8', '上午': '#A8D8EA',
    '下午': '#F9F9C5', '傍晚': '#FFB6B9', '晚上': '#6C5B7B',
}
STATUS_TO_KEY = {'○': 'pending', '✓': 'completed', '✕': 'abandoned'}
KEY_TO_STATUS = {'pending': '○', 'completed': '✓', 'abandoned': '✕'}
BLOCK_HEADER_HEIGHT = 30
HOUR_HEADER_HEIGHT = 28
TASK_ROW_HEIGHT = 34
DAY_BUTTON_HEIGHT = 36
