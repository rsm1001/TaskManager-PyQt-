"""
待办任务管理器 - 负责 TodoTask 的CRUD操作与紧急度计算
"""

from datetime import datetime, date
from models.model import TodoTask
from typing import List, Optional


class TodoTaskManager:
    """待办任务管理器"""

    def __init__(self, session):
        self.session = session

    # ==================== 查询 ====================

    def get_tasks(self, status: Optional[str] = None, tag: Optional[str] = None, keyword: Optional[str] = None) -> List[TodoTask]:
        """获取待办任务列表

        Args:
            status: 筛选状态，'all' 时不过滤；'expired' 时筛选已过期任务；
                    其他值（pending/completed/abandoned）精确匹配 status 字段
            tag: 标签过滤（模糊包含）
            keyword: 关键词筛选（模糊匹配 title/description/tags/category）
        """
        query = self.session.query(TodoTask)

        if status and status != "all":
            if status == "expired":
                # 已过期：deadline 不为空、未完成、且截止日期早于今天
                today = date.today()
                query = query.filter(
                    (TodoTask.deadline.isnot(None)) &
                    (TodoTask.deadline != "") &
                    (TodoTask.deadline < today.strftime("%Y-%m-%d")) &
                    (TodoTask.status != "completed")
                )
            else:
                query = query.filter(TodoTask.status == status)

        if tag:
            query = query.filter(TodoTask.tags.contains(tag))

        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                (TodoTask.title.ilike(kw)) |
                (TodoTask.description.ilike(kw)) |
                (TodoTask.tags.ilike(kw)) |
                (TodoTask.category.ilike(kw))
            )

        return query.order_by(TodoTask.deadline.desc(), TodoTask.urgency_score.desc()).all()

    def get_by_id(self, task_id: str) -> Optional[TodoTask]:
        """根据ID获取任务"""
        return self.session.query(TodoTask).filter(TodoTask.id == task_id).first()

    # ==================== 增删改 ====================

    def create(self, title: str, description: str = "", deadline: str = "",
               completed: bool = False, status: str = "pending", tags: str = "",
               shortcut_path: str = "", category: str = "",
               priority: str = "normal", subtasks: str = "[]") -> TodoTask:
        """创建待办任务"""
        task = TodoTask(
            title=title, description=description, deadline=deadline,
            completed=completed, status=status, tags=tags, shortcut_path=shortcut_path,
            category=category, priority=priority, subtasks=subtasks
        )
        self.session.add(task)
        self.session.commit()
        self._calculate_urgency(task)
        self.session.commit()
        return task

    def update(self, task_id: str, **kwargs) -> bool:
        """更新待办任务"""
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

        self._calculate_urgency(task)
        self.session.commit()
        return True

    def delete(self, task_id: str) -> Optional[TodoTask]:
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
        tasks = self.session.query(TodoTask).filter(TodoTask.id.in_(task_ids)).all()
        result = []
        for task in tasks:
            result.append(('todo', task.id, self.to_dict(task)))
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

        self._calculate_urgency(task)
        self.session.commit()
        return True

    # ==================== 紧急度计算 ====================

    def _calculate_urgency(self, task: TodoTask):
        """计算单个任务的紧急度"""
        if task.completed:
            task.urgency_score = 0
            return

        if not task.deadline:
            task.urgency_score = 1
            return

        try:
            deadline_date = datetime.strptime(task.deadline, "%Y-%m-%d").date()
            today = date.today()

            if deadline_date < today:
                days_overdue = (today - deadline_date).days
                task.urgency_score = 3 + days_overdue
            elif deadline_date == today:
                task.urgency_score = 2
            else:
                days_remaining = (deadline_date - today).days
                if days_remaining <= 7:
                    task.urgency_score = max(1, 2 - (days_remaining / 7))
                else:
                    task.urgency_score = 1
        except ValueError:
            task.urgency_score = 1

    def recalculate_all_urgency(self):
        """重新计算所有待办任务的紧急度"""
        for task in self.get_tasks():
            self._calculate_urgency(task)
        self.session.commit()

    # ==================== 序列化 ====================

    def to_dict(self, task: TodoTask) -> dict:
        """将任务对象转为字典（用于垃圾桶序列化）"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description or '',
            'deadline': task.deadline or '',
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

    def is_expired(self, task: TodoTask) -> bool:
        """判断任务是否过期"""
        if not task.deadline or task.completed:
            return False
        try:
            deadline_date = datetime.strptime(task.deadline, "%Y-%m-%d").date()
            return deadline_date < date.today()
        except ValueError:
            return False
