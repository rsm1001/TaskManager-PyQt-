"""
娱乐任务管理器 - 负责 EntertainmentTask 的CRUD操作
"""

from models.model import EntertainmentTask
from typing import List, Optional


class EntertainmentTaskManager:
    """娱乐任务管理器"""

    def __init__(self, session):
        self.session = session

    # ==================== 查询 ====================

    def get_tasks(self, status: Optional[str] = None, tag: Optional[str] = None) -> List[EntertainmentTask]:
        """获取娱乐任务列表"""
        query = self.session.query(EntertainmentTask)

        if status and status != "all":
            query = query.filter(EntertainmentTask.status == status)

        if tag:
            query = query.filter(EntertainmentTask.tags.contains(tag))

        return query.order_by(EntertainmentTask.fun_category, EntertainmentTask.title).all()

    def get_by_id(self, task_id: str) -> Optional[EntertainmentTask]:
        """根据ID获取任务"""
        return self.session.query(EntertainmentTask).filter(EntertainmentTask.id == task_id).first()

    # ==================== 增删改 ====================

    def create(self, title: str, description: str = "", fun_category: str = "general",
               completed: bool = False, status: str = "pending", tags: str = "",
               shortcut_path: str = "", category: str = "",
               priority: str = "normal", subtasks: str = "[]") -> EntertainmentTask:
        """创建娱乐任务"""
        task = EntertainmentTask(
            title=title, description=description, fun_category=fun_category,
            completed=completed, status=status, tags=tags, shortcut_path=shortcut_path,
            category=category, priority=priority, subtasks=subtasks
        )
        self.session.add(task)
        self.session.commit()
        return task

    def update(self, task_id: str, **kwargs) -> bool:
        """更新娱乐任务"""
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

    def delete(self, task_id: str) -> Optional[EntertainmentTask]:
        """删除任务并返回任务对象（调用方负责移入垃圾桶）"""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
        return task

    def delete_batch(self, task_ids: list) -> list:
        """批量删除任务（不commit，返回供垃圾箱序列化的数据列表）"""
        if not task_ids:
            return []
        tasks = self.session.query(EntertainmentTask).filter(EntertainmentTask.id.in_(task_ids)).all()
        result = []
        for task in tasks:
            result.append(('entertainment', task.id, self.to_dict(task)))
        for task in tasks:
            self.session.delete(task)
        return result

    def toggle_completion(self, task_id: str) -> bool:
        """切换完成状态: pending -> completed -> abandoned -> pending"""
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

    # ==================== 序列化 ====================

    def to_dict(self, task: EntertainmentTask) -> dict:
        """将任务对象转为字典（用于垃圾桶序列化）"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description or '',
            'fun_category': task.fun_category or 'general',
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
