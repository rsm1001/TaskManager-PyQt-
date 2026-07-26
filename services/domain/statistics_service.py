"""
Statistics Service - 统计服务模块
提供各类型任务的统计功能，与数据层解耦
"""

import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from managers.application.data_manager import DataManager

logger = logging.getLogger(__name__)


class StatisticsService:
    """任务统计服务"""

    def __init__(self, data_manager: "DataManager") -> None:
        """
        Args:
            data_manager: DataManager 实例，用于获取各类型任务数据
        """
        self._dm: "DataManager" = data_manager
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
        daily_paused = sum(1 for t in daily_tasks if t.status == "abandoned")
        daily_pending = sum(1 for t in daily_tasks if t.status == "pending")
        daily_pending_duration = sum(t.estimated_duration or 0 for t in daily_tasks if t.status == "pending")
        daily_total = len(daily_tasks) - daily_paused  # 总数不含暂弃
        todo_completed = sum(1 for t in todo_tasks if t.completed)
        todo_paused = sum(1 for t in todo_tasks if t.status == "abandoned")
        todo_expired = sum(1 for t in todo_tasks if self._dm.todo_manager.is_expired(t))
        todo_total = len(todo_tasks) - todo_paused  # 总数不含暂弃
        entertainment_completed = sum(1 for t in entertainment_tasks if t.completed)
        entertainment_paused = sum(1 for t in entertainment_tasks if t.status == "abandoned")
        entertainment_total = len(entertainment_tasks) - entertainment_paused  # 总数不含暂弃

        stats: Dict[str, Any] = {
            "daily": {
                "total": daily_total,
                "completed": daily_completed,
                "pending": daily_pending,
                "pending_duration": daily_pending_duration,
                "paused": daily_paused
            },
            "todo": {
                "total": todo_total,
                "completed": todo_completed,
                "expired": todo_expired,
                "paused": todo_paused,
            },
            "entertainment": {
                "total": entertainment_total,
                "completed": entertainment_completed,
                "paused": entertainment_paused,
            },
        }

        logger.info(f"统计完成: {stats}")
        return stats
