"""
Task Type Enumeration - 任务类型枚举定义
与其他模块解耦，单独定义任务类型枚举
"""

from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    DAILY = "daily"
    TODO = "todo"
    ENTERTAINMENT = "entertainment"
