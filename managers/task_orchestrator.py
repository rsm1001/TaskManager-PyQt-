"""
任务编排器 - 集中管理 Daily / Todo / Entertainment 三类任务的 CRUD
与紧急度计算业务逻辑
通过依赖注入复用底层 Repository（DailyTaskManager / TodoTaskManager / EntertainmentTaskManager）
符合单一职责：编排器只做组合，仓储层只做数据访问
"""

import logging
from typing import List, Optional

from models.model import DailyTask, TodoTask, EntertainmentTask

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """任务编排器

    职责：
        - 跨任务类型的统一入口（创建/更新/删除/批量删除/切换完成态）
        - 在写操作后触发任务数量上限校验
        - 在删除时统一委托垃圾桶
    """

    # 任务类型 -> 上限校验 key 映射
    _LIMIT_KEY_MAP = {
        "daily": "daily",
        "todo": "todo",
        "entertainment": "entertainment",
    }

    def __init__(
        self,
        session,
        daily_task_manager,
        todo_task_manager,
        entertainment_task_manager,
        trash_manager,
        task_limit_service_factory,
    ):
        """初始化任务编排器

        Args:
            session: SQLAlchemy Session
            daily_task_manager: 每日任务仓储
            todo_task_manager: 待办任务仓储
            entertainment_task_manager: 娱乐任务仓储
            trash_manager: 垃圾桶仓储
            task_limit_service_factory: 返回任务上限服务的可调用对象
        """
        self._session = session
        self._daily = daily_task_manager
        self._todo = todo_task_manager
        self._entertainment = entertainment_task_manager
        self._trash = trash_manager
        self._limit_service_factory = task_limit_service_factory

    # ==================== DailyTask ====================

    def get_daily_tasks(
        self,
        weekday: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[DailyTask]:
        """获取每日任务列表"""
        return self._daily.get_tasks(weekday=weekday, status=status, tag=tag)

    def get_daily_task_by_id(self, task_id: str) -> Optional[DailyTask]:
        return self._daily.get_by_id(task_id)

    def create_daily_task(
        self,
        title: str,
        description: str = "",
        week_day: str = "",
        completed: bool = False,
        status: str = "pending",
        tags: str = "",
        shortcut_path: str = "",
        category: str = "",
        priority: str = "normal",
        subtasks: str = "[]",
    ) -> DailyTask:
        """创建每日任务，并校验数量上限"""
        logger.info(
            "创建每日任务 | request_id=create_daily | title=%s week_day=%s",
            title,
            week_day,
        )
        task = self._daily.create(
            title, description, week_day, completed, status,
            tags, shortcut_path, category, priority, subtasks,
        )
        self._limit_service_factory().enforce_limit("daily", DailyTask)
        return task

    def update_daily_task(self, task_id: str, **kwargs) -> bool:
        return self._daily.update(task_id, **kwargs)

    def delete_daily_task(self, task_id: str) -> bool:
        """删除单个每日任务并移入垃圾桶"""
        task_data = self._daily.delete(task_id)
        if task_data is None:
            return False
        logger.info("删除每日任务并入垃圾桶 | request_id=delete_daily | task_id=%s", task_id)
        self._trash.move_to_trash("daily", task_id, task_data)
        return True

    def delete_daily_tasks_batch(self, task_ids: list) -> int:
        """批量删除每日任务（单次事务）"""
        if not task_ids:
            return 0
        entries = self._daily.delete_batch(task_ids)
        if entries:
            self._trash.move_many_to_trash(entries)
            self._session.commit()
            logger.info(
                "批量删除每日任务 | request_id=delete_daily_batch | count=%d",
                len(entries),
            )
        return len(entries)

    def toggle_daily_task_completion(self, task_id: str) -> bool:
        return self._daily.toggle_completion(task_id)

    # ==================== TodoTask ====================

    def get_todo_tasks(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[TodoTask]:
        return self._todo.get_tasks(status=status, tag=tag)

    def get_todo_task_by_id(self, task_id: str) -> Optional[TodoTask]:
        return self._todo.get_by_id(task_id)

    def create_todo_task(
        self,
        title: str,
        description: str = "",
        deadline: str = "",
        completed: bool = False,
        status: str = "pending",
        tags: str = "",
        shortcut_path: str = "",
        category: str = "",
        priority: str = "normal",
        subtasks: str = "[]",
    ) -> TodoTask:
        logger.info(
            "创建待办任务 | request_id=create_todo | title=%s deadline=%s",
            title,
            deadline,
        )
        task = self._todo.create(
            title, description, deadline, completed, status,
            tags, shortcut_path, category, priority, subtasks,
        )
        self._limit_service_factory().enforce_limit("todo", TodoTask)
        return task

    def update_todo_task(self, task_id: str, **kwargs) -> bool:
        return self._todo.update(task_id, **kwargs)

    def delete_todo_task(self, task_id: str) -> bool:
        """删除待办任务并移入垃圾桶"""
        task = self._todo.get_by_id(task_id)
        if not task:
            return False
        task_data = self._todo.to_dict(task)
        logger.info("删除待办任务并入垃圾桶 | request_id=delete_todo | task_id=%s", task_id)
        self._trash.move_to_trash("todo", task_id, task_data)
        self._session.delete(task)
        self._session.commit()
        return True

    def delete_todo_tasks_batch(self, task_ids: list) -> int:
        if not task_ids:
            return 0
        entries = self._todo.delete_batch(task_ids)
        if entries:
            self._trash.move_many_to_trash(entries)
            self._session.commit()
            logger.info(
                "批量删除待办任务 | request_id=delete_todo_batch | count=%d",
                len(entries),
            )
        return len(entries)

    def toggle_todo_task_completion(self, task_id: str) -> bool:
        return self._todo.toggle_completion(task_id)

    # ==================== EntertainmentTask ====================

    def get_entertainment_tasks(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[EntertainmentTask]:
        return self._entertainment.get_tasks(status=status, tag=tag)

    def get_entertainment_task_by_id(self, task_id: str) -> Optional[EntertainmentTask]:
        return self._entertainment.get_by_id(task_id)

    def create_entertainment_task(
        self,
        title: str,
        description: str = "",
        fun_category: str = "general",
        completed: bool = False,
        status: str = "pending",
        tags: str = "",
        shortcut_path: str = "",
        category: str = "",
        priority: str = "normal",
        subtasks: str = "[]",
    ) -> EntertainmentTask:
        logger.info(
            "创建娱乐任务 | request_id=create_entertainment | title=%s fun_category=%s",
            title,
            fun_category,
        )
        task = self._entertainment.create(
            title, description, fun_category, completed, status,
            tags, shortcut_path, category, priority, subtasks,
        )
        self._limit_service_factory().enforce_limit("entertainment", EntertainmentTask)
        return task

    def update_entertainment_task(self, task_id: str, **kwargs) -> bool:
        return self._entertainment.update(task_id, **kwargs)

    def delete_entertainment_task(self, task_id: str) -> bool:
        task = self._entertainment.get_by_id(task_id)
        if not task:
            return False
        task_data = self._entertainment.to_dict(task)
        logger.info(
            "删除娱乐任务并入垃圾桶 | request_id=delete_entertainment | task_id=%s",
            task_id,
        )
        self._trash.move_to_trash("entertainment", task_id, task_data)
        self._session.delete(task)
        self._session.commit()
        return True

    def delete_entertainment_tasks_batch(self, task_ids: list) -> int:
        if not task_ids:
            return 0
        entries = self._entertainment.delete_batch(task_ids)
        if entries:
            self._trash.move_many_to_trash(entries)
            self._session.commit()
            logger.info(
                "批量删除娱乐任务 | request_id=delete_entertainment_batch | count=%d",
                len(entries),
            )
        return len(entries)

    def toggle_entertainment_task_completion(self, task_id: str) -> bool:
        return self._entertainment.toggle_completion(task_id)

    # ==================== 紧急度（TodoTask 专有） ====================

    def calculate_urgency_for_task(self, task: TodoTask):
        self._todo._calculate_urgency(task)

    def recalculate_all_urgency(self):
        self._todo.recalculate_all_urgency()

    # ==================== JSON 导入导出 ====================

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        """导出全部任务到 JSON 文件"""
        from handlers.json_handler import JsonExportImportHandler

        handler = JsonExportImportHandler(self._session)
        result = handler.export_to_json(filepath)
        logger.info("导出 JSON | request_id=export_json | path=%s ok=%s", filepath, result)
        return result

    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        """从 JSON 文件导入任务"""
        from handlers.json_handler import JsonExportImportHandler

        handler = JsonExportImportHandler(self._session)
        result = handler.import_from_json(filepath)
        logger.info("导入 JSON | request_id=import_json | path=%s ok=%s", filepath, result)
        return result
