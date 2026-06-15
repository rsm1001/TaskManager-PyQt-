"""
每日任务管理器 - 封装 DailyTask 模型的所有数据库操作
遵循 Repository 模式，使用 ORM 操作数据库
"""

from models.model import DailyTask
from typing import List, Optional
import uuid


class DailyTaskManager:
    """每日任务管理器，负责 DailyTask 的所有 CRUD 操作"""

    def __init__(self, session):
        self.session = session

    def get_tasks(self, weekday: str = None, status: str = None, tag: str = None, keyword: str = None) -> List[DailyTask]:
        """获取每日任务列表

        Args:
            weekday: 星期筛选，None 不过滤
            status: 状态筛选，None/'all' 不过滤
            tag: 标签筛选（模糊包含），None 不过滤
            keyword: 关键词筛选（模糊匹配 title/description/tags/category），None 不过滤
        """
        query = self.session.query(DailyTask)

        if weekday and weekday != "all":
            if weekday == "daily":
                query = query.filter((DailyTask.week_day == "") | (DailyTask.week_day.is_(None)))
            else:
                query = query.filter(
                    (DailyTask.week_day == weekday) |
                    (DailyTask.week_day == "") |
                    (DailyTask.week_day.is_(None))
                )

        if status and status != "all":
            query = query.filter(DailyTask.status == status)

        if tag:
            query = query.filter(DailyTask.tags.contains(tag))

        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                (DailyTask.title.ilike(kw)) |
                (DailyTask.description.ilike(kw)) |
                (DailyTask.tags.ilike(kw)) |
                (DailyTask.category.ilike(kw))
            )

        return query.order_by(DailyTask.week_day, DailyTask.title).all()

    def get_by_id(self, task_id: str) -> Optional[DailyTask]:
        """根据ID获取每日任务"""
        return self.session.query(DailyTask).filter(DailyTask.id == task_id).first()

    def create(self, title: str, description: str = "", week_day: str = "",
               completed: bool = False, status: str = "pending",
               tags: str = "", shortcut_path: str = "", category: str = "",
               priority: str = "normal", subtasks: str = "[]") -> DailyTask:
        """创建每日任务"""
        task = DailyTask(
            title=title, description=description, week_day=week_day,
            completed=completed, status=status, tags=tags, shortcut_path=shortcut_path,
            category=category, priority=priority, subtasks=subtasks
        )
        self.session.add(task)
        self.session.commit()
        return task

    def update(self, task_id: str, **kwargs) -> bool:
        """更新每日任务"""
        task = self.get_by_id(task_id)
        if not task:
            return False

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        if 'status' in kwargs:
            task.completed = (kwargs['status'] == 'completed')
        elif 'completed' in kwargs:
            task.status = 'completed' if kwargs['completed'] else 'pending'

        self.session.commit()
        return True

    def to_dict(self, task: DailyTask) -> dict:
        """将任务序列化为字典"""
        return {
            'id': task.id, 'title': task.title,
            'description': task.description or '',
            'week_day': task.week_day or '',
            'completed': task.completed,
            'status': task.status,
            'tags': task.tags or '',
            'shortcut_path': task.shortcut_path or '',
            'category': task.category or '',
            'priority': task.priority or 'normal',
            'subtasks': task.subtasks or '[]',
            'created_at': task.created_at.isoformat() if task.created_at else '',
            'updated_at': task.updated_at.isoformat() if task.updated_at else '',
        }

    def delete(self, task_id: str) -> Optional[dict]:
        """删除每日任务（返回序列化数据供垃圾箱使用）"""
        task = self.get_by_id(task_id)
        if not task:
            return None
        task_data = self.to_dict(task)
        self.session.delete(task)
        self.session.commit()
        return task_data

    def delete_batch(self, task_ids: list) -> list:
        """批量删除每日任务（不commit，返回供垃圾箱序列化的数据列表）"""
        if not task_ids:
            return []
        tasks = self.session.query(DailyTask).filter(DailyTask.id.in_(task_ids)).all()
        result = []
        for task in tasks:
            result.append(('daily', task.id, self.to_dict(task)))
        for task in tasks:
            self.session.delete(task)
        return result

    def toggle_completion(self, task_id: str) -> bool:
        """切换每日任务完成状态"""
        task = self.get_by_id(task_id)
        if not task:
            return False

        if task.status == "pending":
            task.status = "completed"
            task.completed = True
        elif task.status == "completed":
            task.status = "abandoned"
            task.completed = False
        else:
            task.status = "pending"
            task.completed = False

        self.session.commit()
        return True

    def reset_all_pending(self):
        """重置所有已完成任务的pending状态（每日重置时调用）"""
        today_weekday = 0  # 由调用方注入
        # 此方法已废弃，reset 逻辑统一在 DailyResetService 中处理
        pass

    def get_all(self) -> List[DailyTask]:
        """获取所有每日任务（不带过滤）"""
        return self.session.query(DailyTask).all()
