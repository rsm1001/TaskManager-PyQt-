"""
任务编排器 - 集中管理 Daily / Todo / Entertainment 三类任务的 CRUD
与紧急度计算业务逻辑
通过依赖注入复用底层 Repository（DailyTaskManager / TodoTaskManager / EntertainmentTaskManager）
符合单一职责：编排器只做组合，仓储层只做数据访问
"""

import logging
from typing import List, Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from models.model import TodoTask, EntertainmentTask
    from managers.daily_task_manager import DailyTaskManager
    from managers.todo_task_manager import TodoTaskManager
    from managers.entertainment_task_manager import EntertainmentTaskManager
    from managers.trash_manager import TrashManager

from models.model import DailyTask, TodoTask

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
        session: "Session",
        daily_task_manager: "DailyTaskManager",
        todo_task_manager: "TodoTaskManager",
        entertainment_task_manager: "EntertainmentTaskManager",
        trash_manager: "TrashManager",
        task_limit_service_factory: Callable[[], Any],
        shortcut_manager: Any = None,
    ) -> None:
        self._session: "Session" = session
        self._daily: "DailyTaskManager" = daily_task_manager
        self._todo: "TodoTaskManager" = todo_task_manager
        self._entertainment: "EntertainmentTaskManager" = entertainment_task_manager
        self._trash: "TrashManager" = trash_manager
        self._limit_service_factory: Callable[[], Any] = task_limit_service_factory
        self._shortcut = shortcut_manager

    # ==================== DailyTask ====================

    def get_daily_tasks(
        self,
        weekday: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        time_period_id: Optional[str] = None,
    ) -> List["DailyTask"]:
        """获取每日任务列表"""
        return self._daily.get_tasks(
            weekday=weekday,
            status=status,
            tag=tag,
            keyword=keyword,
            time_period_id=time_period_id,
        )  # type: ignore[no-any-return]

    def get_daily_task_by_id(self, task_id: str) -> Optional["DailyTask"]:
        return self._daily.get_by_id(task_id)  # type: ignore[no-any-return]

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
        estimated_duration: int = 0,
        time_period_id: Optional[str] = None,
    ) -> "DailyTask":
        """创建每日任务，并校验数量上限"""
        logger.info(
            "创建每日任务 | request_id=create_daily | title=%s week_day=%s time_period_id=%s",
            title, week_day, time_period_id,
        )
        task = self._daily.create(
            title, description, week_day, completed, status,
            tags, shortcut_path, category, priority, subtasks,
            estimated_duration, time_period_id,
        )
        self._limit_service_factory().enforce_limit("daily", DailyTask)
        return task  # type: ignore[no-any-return]

    def update_daily_task(self, task_id: str, **kwargs: Any) -> bool:
        return self._daily.update(task_id, **kwargs)  # type: ignore[no-any-return]

    def delete_daily_task(self, task_id: str) -> bool:
        """删除单个每日任务并移入垃圾桶"""
        task_data = self._daily.delete(task_id)
        if task_data is None:
            return False
        logger.info("删除每日任务并入垃圾桶 | request_id=delete_daily | task_id=%s", task_id)
        try:
            self._trash.move_to_trash("daily", task_id, task_data)
        except Exception:
            logger.error(
                "垃圾桶操作失败（主库已提交），每日任务已删除但未入垃圾箱 | "
                "request_id=delete_daily | task_id=%s",
                task_id, exc_info=True,
            )
        return True

    def delete_daily_tasks_batch(self, task_ids: List[str]) -> int:
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
        return self._daily.toggle_completion(task_id)  # type: ignore[no-any-return]

    # ==================== TodoTask ====================

    def get_todo_tasks(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        time_period_id: Optional[str] = None,
    ) -> List["TodoTask"]:
        return self._todo.get_tasks(
            status=status, tag=tag, keyword=keyword,
            time_period_id=time_period_id,
        )  # type: ignore[no-any-return]

    def get_todo_task_by_id(self, task_id: str) -> Optional["TodoTask"]:
        return self._todo.get_by_id(task_id)  # type: ignore[no-any-return]

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
        estimated_duration: int = 0,
        time_period_id: Optional[str] = None,
    ) -> "TodoTask":
        logger.info(
            "创建待办任务 | request_id=create_todo | title=%s deadline=%s time_period_id=%s",
            title, deadline, time_period_id,
        )
        task = self._todo.create(
            title, description, deadline, completed, status,
            tags, shortcut_path, category, priority, subtasks,
            estimated_duration, time_period_id,
        )
        self._limit_service_factory().enforce_limit("todo", TodoTask)
        return task  # type: ignore[no-any-return]

    def update_todo_task(self, task_id: str, **kwargs: Any) -> bool:
        return self._todo.update(task_id, **kwargs)  # type: ignore[no-any-return]

    def delete_todo_task(self, task_id: str) -> bool:
        """删除待办任务并移入垃圾桶"""
        task = self._todo.get_by_id(task_id)
        if not task:
            return False
        task_data = self._todo.to_dict(task)
        logger.info("删除待办任务并入垃圾桶 | request_id=delete_todo | task_id=%s", task_id)
        try:
            trash_id = self._trash.move_to_trash("todo", task_id, task_data)
        except Exception:
            logger.error(
                "垃圾桶操作失败，放弃删除 | request_id=delete_todo | task_id=%s",
                task_id, exc_info=True,
            )
            return False
        self._session.delete(task)
        try:
            self._session.commit()
        except Exception:
            logger.error(
                "主库提交失败，补偿移除垃圾桶记录 | request_id=delete_todo | task_id=%s",
                task_id, exc_info=True,
            )
            self._session.rollback()
            try:
                self._trash.delete_trash_record(trash_id)
            except Exception:
                logger.error(
                    "补偿失败，垃圾桶与主库状态不一致 | request_id=delete_todo | task_id=%s | trash_id=%s",
                    task_id, trash_id, exc_info=True,
                )
            return False
        return True

    def delete_todo_tasks_batch(self, task_ids: List[str]) -> int:
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
        return self._todo.toggle_completion(task_id)  # type: ignore[no-any-return]

    # ==================== EntertainmentTask ====================

    def get_entertainment_tasks(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        keyword: Optional[str] = None,
        time_period_id: Optional[str] = None,
    ) -> List["EntertainmentTask"]:
        return self._entertainment.get_tasks(
            status=status, tag=tag, keyword=keyword,
            time_period_id=time_period_id,
        )  # type: ignore[no-any-return]

    def get_entertainment_task_by_id(self, task_id: str) -> Optional["EntertainmentTask"]:
        return self._entertainment.get_by_id(task_id)  # type: ignore[no-any-return]

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
        estimated_duration: int = 0,
        time_period_id: Optional[str] = None,
    ) -> "EntertainmentTask":
        logger.info(
            "创建娱乐任务 | request_id=create_entertainment | title=%s fun_category=%s time_period_id=%s",
            title, fun_category, time_period_id,
        )
        task = self._entertainment.create(
            title, description, fun_category, completed, status,
            tags, shortcut_path, category, priority, subtasks,
            estimated_duration, time_period_id,
        )
        self._limit_service_factory().enforce_limit("entertainment", EntertainmentTask)
        return task  # type: ignore[no-any-return]

    def update_entertainment_task(self, task_id: str, **kwargs: Any) -> bool:
        return self._entertainment.update(task_id, **kwargs)  # type: ignore[no-any-return]

    def delete_entertainment_task(self, task_id: str) -> bool:
        """删除娱乐任务并移入垃圾桶"""
        task = self._entertainment.get_by_id(task_id)
        if not task:
            return False
        task_data = self._entertainment.to_dict(task)
        logger.info(
            "删除娱乐任务并入垃圾桶 | request_id=delete_entertainment | task_id=%s",
            task_id,
        )
        try:
            trash_id = self._trash.move_to_trash("entertainment", task_id, task_data)
        except Exception:
            logger.error(
                "垃圾桶操作失败，放弃删除 | request_id=delete_entertainment | task_id=%s",
                task_id, exc_info=True,
            )
            return False
        self._session.delete(task)
        try:
            self._session.commit()
        except Exception:
            logger.error(
                "主库提交失败，补偿移除垃圾桶记录 | request_id=delete_entertainment | task_id=%s",
                task_id, exc_info=True,
            )
            self._session.rollback()
            try:
                self._trash.delete_trash_record(trash_id)
            except Exception:
                logger.error(
                    "补偿失败，垃圾桶与主库状态不一致 | request_id=delete_entertainment | task_id=%s | trash_id=%s",
                    task_id, trash_id, exc_info=True,
                )
            return False
        return True

    def delete_entertainment_tasks_batch(self, task_ids: List[str]) -> int:
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
        return self._entertainment.toggle_completion(task_id)  # type: ignore[no-any-return]

    # ==================== 紧急度（TodoTask 专有） ====================

    def calculate_urgency_for_task(self, task: "TodoTask") -> None:
        self._todo._calculate_urgency(task)

    def recalculate_all_urgency(self) -> None:
        self._todo.recalculate_all_urgency()

    # ==================== JSON 导入导出 ====================

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self._session, self._shortcut)
        result = handler.export_to_json(filepath)
        logger.info("导出 JSON | request_id=export_json | path=%s ok=%s", filepath, result)
        return result  # type: ignore[no-any-return]

    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self._session, self._shortcut)
        result = handler.import_from_json(filepath)
        logger.info("导入 JSON | request_id=import_json | path=%s ok=%s", filepath, result)
        return result  # type: ignore[no-any-return]
