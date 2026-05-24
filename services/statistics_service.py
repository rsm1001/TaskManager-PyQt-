"""
Statistics Service - 统计服务模块
提供各类型任务的统计功能，与数据层解耦
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StatisticsService:
    """任务统计服务"""

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例，用于获取各类型任务数据
        """
        self._dm = data_manager
        logger.debug("StatisticsService 初始化完成")

    def get_statistics(self) -> Dict[str, Any]:
        """获取所有任务的统计信息

        Returns:
            Dict: 包含各任务类型的统计数据
        """
        logger.info("开始获取任务统计信息")
        daily_tasks = self._dm.get_daily_tasks()
        todo_tasks = self._dm.get_todo_tasks()
        entertainment_tasks = self._dm.get_entertainment_tasks()

        daily_completed = sum(1 for t in daily_tasks if t.completed)
        todo_completed = sum(1 for t in todo_tasks if t.completed)
        todo_expired = sum(1 for t in todo_tasks if self._dm.todo_manager.is_expired(t))
        entertainment_completed = sum(1 for t in entertainment_tasks if t.completed)

        stats = {
            "daily": {"total": len(daily_tasks), "completed": daily_completed},
            "todo": {"total": len(todo_tasks), "completed": todo_completed, "expired": todo_expired},
            "entertainment": {"total": len(entertainment_tasks), "completed": entertainment_completed}
        }

        logger.info(f"统计完成: {stats}")
        return stats
