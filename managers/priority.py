"""
任务优先级集中定义（5 档）

所有优先级相关的元数据（标签、颜色、权重、排序 rank）都在这一个文件里维护。
下游模块（config、随机服务、UI 等）**禁止**直接写字典，全部从本模块派生。

设计原则：
- rank 从高到低排序（urgent=5 > idle=1）
- weight 用于"随机选一个任务"的加权（idle=0.0 = 不参与随机抽取）
- 颜色来自 Material Design 调色板 50-200 段（背景）+ 700-900 段（文字）
- 数据库列保持 String(20)，不引入新枚举类型，老数据 100% 兼容
"""

# 5 档优先级元数据（按 rank 从高到低排序）
PRIORITY_LEVELS = [
    {
        'key': 'urgent',
        'label': '紧急',
        'rank': 5,
        'weight': 5.0,
        'bg': '#FF8A80',  # Material Red A100
        'fg': '#B71C1C',  # Material Red 900
    },
    {
        'key': 'high',
        'label': '重要',
        'rank': 4,
        'weight': 3.0,
        'bg': '#FFE0B2',  # Material Orange 100
        'fg': '#BF360C',  # Material Deep Orange 900
    },
    {
        'key': 'normal',
        'label': '普通',
        'rank': 3,
        'weight': 1.0,
        'bg': '#E3F2FD',  # Material Blue 50
        'fg': '#0D47A1',  # Material Blue 900
    },
    {
        'key': 'low',
        'label': '低',
        'rank': 2,
        'weight': 0.3,
        'bg': '#C8E6C9',  # Material Green 100
        'fg': '#1B5E20',  # Material Green 900
    },
    {
        'key': 'idle',
        'label': '闲置',
        'rank': 1,
        'weight': 0.0,  # 闲置任务不参与随机抽取
        'bg': '#ECEFF1',  # Material Blue Grey 50
        'fg': '#546E7A',  # Material Blue Grey 700
    },
]

# ==================== 派生字典 ====================
# 下游模块统一从这些派生量取值，**不**再手写字典

# UI 下拉框顺序（按 rank 从高到低）
PRIORITY_KEYS = [p['key'] for p in PRIORITY_LEVELS]
PRIORITY_LABELS = [p['label'] for p in PRIORITY_LEVELS]

# 排序键：5 档下不能用字符串字典序（"high" < "idle" 字典序错乱）
PRIORITY_RANK = {p['key']: p['rank'] for p in PRIORITY_LEVELS}

# 随机抽取权重（idle = 0.0 自动排除）
PRIORITY_WEIGHTS = {p['key']: p['weight'] for p in PRIORITY_LEVELS}

# 行背景 / 文字色
PRIORITY_BG_COLORS = {p['key']: p['bg'] for p in PRIORITY_LEVELS}
PRIORITY_TEXT_COLORS = {p['key']: p['fg'] for p in PRIORITY_LEVELS}

# key → 显示文本（重要 / 普通 / …）
PRIORITY_DISPLAY_MAP = {p['key']: p['label'] for p in PRIORITY_LEVELS}

# 显示文本 → key（用于 UI 提交时反向查）
LABEL_TO_KEY = {p['label']: p['key'] for p in PRIORITY_LEVELS}

# 默认值（兼容旧调用方的 priority='normal' 写法）
DEFAULT_PRIORITY = 'normal'


# ==================== 工具函数 ====================

def get_priority_label(key: str) -> str:
    """获取某个 key 对应的中文标签，未知值回落普通。"""
    return PRIORITY_DISPLAY_MAP.get(key, PRIORITY_DISPLAY_MAP[DEFAULT_PRIORITY])


def get_priority_rank(key: str) -> int:
    """获取某个 key 的排序 rank，未知值回落普通。"""
    return PRIORITY_RANK.get(key, PRIORITY_RANK[DEFAULT_PRIORITY])


def get_priority_weight(key: str) -> float:
    """获取某个 key 的随机抽取权重，未知值回落 1.0。"""
    return PRIORITY_WEIGHTS.get(key, 1.0)
