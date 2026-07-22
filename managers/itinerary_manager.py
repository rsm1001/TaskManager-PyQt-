"""
行程任务管理器
负责 itinerary_tasks 表的 CRUD 操作
"""

import logging
from typing import List, Optional

from models.model import ItineraryTask

logger = logging.getLogger(__name__)


class ItineraryManager:
    """行程任务管理器"""

    def __init__(self, session):
        self.session = session

    def get_all(self, day_of_week: Optional[int] = None) -> List[ItineraryTask]:
        """获取所有行程任务，可按星期筛选"""
        query = self.session.query(ItineraryTask)
        if day_of_week is not None:
            query = query.filter(ItineraryTask.day_of_week == day_of_week)
        return query.order_by(ItineraryTask.day_of_week, ItineraryTask.hour).all()

    def get_task_refs(self, task_type: Optional[str] = None) -> set[tuple[str, str]]:
        """获取已安排任务引用集合，元素为 (task_type, task_id)。"""
        query = self.session.query(ItineraryTask.task_type, ItineraryTask.task_id)
        if task_type is not None:
            query = query.filter(ItineraryTask.task_type == task_type)
        return {
            (row.task_type, row.task_id)
            for row in query.all()
            if row.task_type and row.task_id
        }

    def has_task_ref(self, task_id: str, task_type: str) -> bool:
        """判断某个任务是否已安排到行程（全局，不限星期）。"""
        if not task_id or not task_type:
            return False
        return self.session.query(ItineraryTask).filter(
            ItineraryTask.task_id == task_id,
            ItineraryTask.task_type == task_type,
        ).first() is not None

    def has_task_ref_for_day(self, task_id: str, task_type: str, day_of_week: int) -> bool:
        """判断某个任务是否已安排到指定星期。每个周几独立去重。"""
        if not task_id or not task_type:
            return False
        return self.session.query(ItineraryTask).filter(
            ItineraryTask.task_id == task_id,
            ItineraryTask.task_type == task_type,
            ItineraryTask.day_of_week == day_of_week,
        ).first() is not None

    def get_by_id(self, itinerary_id: str) -> Optional[ItineraryTask]:
        """根据 ID 获取行程任务"""
        return self.session.query(ItineraryTask).filter(ItineraryTask.id == itinerary_id).first()

    def create(
        self,
        title: str,
        day_of_week: int = 1,
        hour: int = 0,
        task_id: str = "",
        task_type: str = "",
        description: str = "",
        color: str = "#3498DB",
    ) -> ItineraryTask:
        """创建行程任务"""
        task = ItineraryTask(
            title=title,
            day_of_week=day_of_week,
            hour=hour,
            task_id=task_id,
            task_type=task_type,
            description=description,
            color=color,
        )
        self.session.add(task)
        self.session.commit()
        logger.info(f"行程任务创建成功: {task.id} | {title} | 星期{day_of_week} {hour}:00")
        return task

    def update(self, task_id: str, **kwargs) -> bool:
        """更新行程任务"""
        task = self.get_by_id(task_id)
        if not task:
            return False
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self.session.commit()
        logger.info(f"行程任务更新成功: {task_id}")
        return True

    def delete(self, task_id: str) -> bool:
        """删除行程任务"""
        task = self.get_by_id(task_id)
        if not task:
            return False
        self.session.delete(task)
        self.session.commit()
        logger.info(f"行程任务删除成功: {task_id}")
        return True

    def delete_by_task_ref(self, task_id: str, task_type: str) -> int:
        """根据关联的任务 ID 和类型删除所有引用"""
        count = (
            self.session.query(ItineraryTask)
            .filter(ItineraryTask.task_id == task_id)
            .filter(ItineraryTask.task_type == task_type)
            .delete()
        )
        self.session.commit()
        logger.info(f"行程任务引用清理: {task_id} ({task_type}) 共 {count} 条")
        return count
