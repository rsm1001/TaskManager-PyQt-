"""
Task Type Enumeration - 任务类型枚举定义
与其他模块解耦，单独定义任务类型枚举
"""

from enum import Enum


class TaskType(Enum):
    """任务类型枚举

    用于标识任务所属的业务领域，便于统一路由和分发处理。

    Attributes:
        DAILY: 每日必做任务
        TODO:  待办事项
        ENTERTAINMENT: 娱乐任务
    """
    DAILY = "daily"
    TODO = "todo"
    ENTERTAINMENT = "entertainment"
