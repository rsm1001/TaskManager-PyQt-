"""
随机任务选择服务
从 main.py 解耦独立，提供按权重/条件随机抽取任务的功能
"""

import random

# 优先级权重映射
PRIORITY_WEIGHTS = {
    'high': 3.0,
    'normal': 1.0,
    'low': 0.3
}


def pick_random_daily_task(data_manager, weekday_filter, status_filter):
    """随机抽取每日任务（根据筛选条件）

    参数:
        data_manager: 数据管理器实例
        weekday_filter: 星期筛选 ('all'/'daily'/'星期一'等)
        status_filter: 状态筛选 ('all'/'pending'/'completed')

    返回:
        随机选中的任务对象，无符合条件任务时返回 None
    """
    tasks = data_manager.get_daily_tasks(weekday=weekday_filter, status=status_filter)
    pending_tasks = [t for t in tasks if not t.completed]

    if not pending_tasks:
        return None

    # 按优先级权重随机选择
    weights = [PRIORITY_WEIGHTS.get(getattr(t, 'priority', 'normal'), 1.0) for t in pending_tasks]
    total_weight = sum(weights)

    if total_weight <= 0:
        return random.choice(pending_tasks)

    rand_val = random.uniform(0, total_weight)
    cum_weight = 0
    for i, w in enumerate(weights):
        cum_weight += w
        if rand_val <= cum_weight:
            return pending_tasks[i]

    return pending_tasks[-1]


def pick_random_todo_task(data_manager):
    """按权重随机抽取待办事项

    根据紧急度分数和优先级权重进行选择，紧急度高且优先级高的任务被选中概率越大。

    参数:
        data_manager: 数据管理器实例

    返回:
        随机选中的任务对象，无待完成任务时返回 None
    """
    tasks = data_manager.get_todo_tasks()
    pending_tasks = [t for t in tasks if not t.completed]

    if not pending_tasks:
        return None

    # 按紧急度*优先级权重随机选择
    weights = []
    for t in pending_tasks:
        urgency = max(1, getattr(t, 'urgency_score', 1))
        priority_weight = PRIORITY_WEIGHTS.get(getattr(t, 'priority', 'normal'), 1.0)
        weights.append(urgency * priority_weight)

    total_weight = sum(weights)

    if total_weight <= 0:
        return random.choice(pending_tasks)

    rand_val = random.uniform(0, total_weight)
    cum_weight = 0
    for i, w in enumerate(weights):
        cum_weight += w
        if rand_val <= cum_weight:
            return pending_tasks[i]

    return pending_tasks[-1]  # 防止索引越界


def pick_random_entertainment_task(data_manager):
    """随机抽取娱乐任务

    根据优先级权重进行选择，优先级高的任务被选中概率越大。

    参数:
        data_manager: 数据管理器实例

    返回:
        随机选中的任务对象，无待完成任务时返回 None
    """
    tasks = data_manager.get_entertainment_tasks()
    pending_tasks = [t for t in tasks if not t.completed]

    if not pending_tasks:
        return None

    # 按优先级权重随机选择
    weights = [PRIORITY_WEIGHTS.get(getattr(t, 'priority', 'normal'), 1.0) for t in pending_tasks]
    total_weight = sum(weights)

    if total_weight <= 0:
        return random.choice(pending_tasks)

    rand_val = random.uniform(0, total_weight)
    cum_weight = 0
    for i, w in enumerate(weights):
        cum_weight += w
        if rand_val <= cum_weight:
            return pending_tasks[i]

    return pending_tasks[-1]
