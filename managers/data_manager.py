"""
Task Manager - 数据管理外观（Facade）
为上层 UI/Service 提供统一的业务入口，内部按功能垂直委托给多个编排器
（Task / Shortcut / Tag / Trash / Config Orchestrator）
通过 OrchestratorFactory 工厂模式解耦编排器的创建
"""

import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from managers.task_type import TaskType  # noqa: F401 供外部 from managers.data_manager import TaskType
from managers.data_access import DataAccess
from managers.todo_task_manager import TodoTaskManager
from managers.entertainment_task_manager import EntertainmentTaskManager
from managers.config_manager import ConfigManager
from managers.trash_manager import TrashManager
from managers.shortcut_manager import ShortcutManager
from managers.daily_task_manager import DailyTaskManager
from managers.tag_manager import TagManager
from managers.time_period_manager import TimePeriodManager
from managers.time_period_orchestrator import TimePeriodOrchestrator
from services.service_factory import ServiceFactory

if TYPE_CHECKING:
    from services.orchestrator_factory import OrchestratorFactory

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlalchemy.engine import Engine
    from models.model import DailyTask, TodoTask, EntertainmentTask

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理外观

    通过编排器（Orchestrator）解耦各业务领域：
        - task_orchestrator: 任务 CRUD + 紧急度 + JSON 导入导出
        - shortcut_orchestrator: 快捷入口 + 历史记录
        - tag_orchestrator: 标签 + 分类 + 清理
        - trash_orchestrator: 垃圾桶查询 / 恢复 / 清理
        - config_orchestrator: 配置 get / set
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """初始化数据管理外观"""
        # 基础设施：DB session / 连接
        self._data_access: "DataAccess" = DataAccess(db_path=db_path)
        self.session: "Session" = self._data_access.get_session()
        self.engine: "Engine" = self._data_access.engine

        # 底层 Repository（保持对外属性名兼容）
        self._main_conn = self._data_access.get_main_connection()
        self._trash_conn = self._data_access.get_trash_connection()

        self.todo_manager: "TodoTaskManager" = TodoTaskManager(self.session)
        self.entertainment_manager: "EntertainmentTaskManager" = EntertainmentTaskManager(self.session)
        self.config_manager: "ConfigManager" = ConfigManager(self.session)
        self.trash_manager: "TrashManager" = TrashManager(connection=self._trash_conn)
        self.shortcut_manager: "ShortcutManager" = ShortcutManager(connection=self._main_conn)
        self.daily_task_manager: "DailyTaskManager" = DailyTaskManager(self.session)
        self.tag_manager: "TagManager" = TagManager(self.config_manager)
        self.time_period_manager: "TimePeriodManager" = TimePeriodManager(self.session)
        self.time_period_orchestrator: "TimePeriodOrchestrator" = TimePeriodOrchestrator(
            self.time_period_manager,
            self.daily_task_manager,
            self.todo_manager,
            self.entertainment_manager,
        )

        # 服务层
        self.daily_reset_service = self._make_daily_reset_service()
        import config.config

        self.vacuum_service = self._make_vacuum_service()
        self.trash_restoration_service = self._make_trash_restoration_service()

        # 工厂：服务 + 编排器（延迟导入避免循环依赖）
        from services.service_factory import ServiceFactory  # noqa: PLC0415
        from services.orchestrator_factory import OrchestratorFactory  # noqa: PLC0415
        self._service_factory: "ServiceFactory" = ServiceFactory(self)
        self._orchestrator_factory: "OrchestratorFactory" = OrchestratorFactory(self)

        # 触发每日重置
        self.daily_reset_service.check_and_reset()
        logger.info("DataManager 初始化完成 | request_id=init")

    # ==================== 内部工厂方法 ====================

    def _make_daily_reset_service(self) -> Any:
        from services.daily_reset_service import DailyResetService
        return DailyResetService(self.session, self.config_manager)

    def _make_vacuum_service(self) -> Any:
        from services.vacuum_service import VacuumService
        import config.config
        return VacuumService(self.engine, config.config.TRASH_DATABASE_PATH)

    def _make_trash_restoration_service(self) -> Any:
        from services.trash_restoration_service import TrashRestorationService
        return TrashRestorationService(
            session=self.session,
            shortcut_manager=self.shortcut_manager,
            trash_manager=self.trash_manager,
            vacuum_service=self.vacuum_service,
            daily_task_manager=self.daily_task_manager,
            todo_task_manager=self.todo_manager,
            entertainment_task_manager=self.entertainment_manager,
        )

    # ==================== 编排器访问器 ====================

    @property
    def task_orchestrator(self) -> Any:
        return self._orchestrator_factory.get_task_orchestrator()

    @property
    def shortcut_orchestrator(self) -> Any:
        return self._orchestrator_factory.get_shortcut_orchestrator()

    @property
    def tag_orchestrator(self) -> Any:
        return self._orchestrator_factory.get_tag_orchestrator()

    @property
    def trash_orchestrator(self) -> Any:
        return self._orchestrator_factory.get_trash_orchestrator()

    @property
    def config_orchestrator(self) -> Any:
        return self._orchestrator_factory.get_config_orchestrator()

    # ==================== 服务工厂代理 ====================

    def _get_statistics_service(self) -> Any:
        return self._service_factory.get_statistics_service()

    def _get_search_service(self) -> Any:
        return self._service_factory.get_search_service()

    def _get_task_limit_service(self) -> Any:
        return self._service_factory.get_task_limit_service()

    def _get_pomodoro_service(self) -> Any:
        return self._service_factory.get_pomodoro_service()

    # ==================== 会话管理 ====================

    def get_session(self) -> "Session":
        return self.session

    def close_session(self) -> None:
        logger.info("关闭数据库会话 | request_id=close")
        self.trash_manager.close()
        self.shortcut_manager.close()
        self._data_access.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    # ==================== DailyTask 委托 ====================

    def get_daily_tasks(self, weekday: Optional[str] = None, status: Optional[str] = None,
                        tag: Optional[str] = None, keyword: Optional[str] = None,
                        time_period_id: Optional[str] = None) -> List["DailyTask"]:
        return self.task_orchestrator.get_daily_tasks(
            weekday=weekday, status=status, tag=tag, keyword=keyword,
            time_period_id=time_period_id,
        )

    def get_daily_task_by_id(self, task_id: str) -> Optional["DailyTask"]:
        return self.task_orchestrator.get_daily_task_by_id(task_id)

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
        return self.task_orchestrator.create_daily_task(
            title=title, description=description, week_day=week_day,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
            estimated_duration=estimated_duration,
            time_period_id=time_period_id,
        )

    def update_daily_task(self, task_id: str, **kwargs: Any) -> bool:
        return self.task_orchestrator.update_daily_task(task_id, **kwargs)

    def delete_daily_task(self, task_id: str) -> bool:
        return self.task_orchestrator.delete_daily_task(task_id)

    def delete_daily_tasks_batch(self, task_ids: List[str]) -> int:
        return self.task_orchestrator.delete_daily_tasks_batch(task_ids)

    def toggle_daily_task_completion(self, task_id: str) -> bool:
        return self.task_orchestrator.toggle_daily_task_completion(task_id)

    # ==================== TodoTask 委托 ====================

    def get_todo_tasks(self, status: Optional[str] = None, tag: Optional[str] = None,
                       keyword: Optional[str] = None,
                       time_period_id: Optional[str] = None) -> List["TodoTask"]:
        return self.task_orchestrator.get_todo_tasks(
            status=status, tag=tag, keyword=keyword,
            time_period_id=time_period_id,
        )

    def get_todo_task_by_id(self, task_id: str) -> Optional["TodoTask"]:
        return self.task_orchestrator.get_todo_task_by_id(task_id)

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
        return self.task_orchestrator.create_todo_task(
            title=title, description=description, deadline=deadline,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
            estimated_duration=estimated_duration,
            time_period_id=time_period_id,
        )

    def update_todo_task(self, task_id: str, **kwargs: Any) -> bool:
        return self.task_orchestrator.update_todo_task(task_id, **kwargs)

    def delete_todo_task(self, task_id: str) -> bool:
        return self.task_orchestrator.delete_todo_task(task_id)

    def delete_todo_tasks_batch(self, task_ids: List[str]) -> int:
        return self.task_orchestrator.delete_todo_tasks_batch(task_ids)

    def toggle_todo_task_completion(self, task_id: str) -> bool:
        return self.task_orchestrator.toggle_todo_task_completion(task_id)

    # ==================== EntertainmentTask 委托 ====================

    def get_entertainment_tasks(self, status: Optional[str] = None, tag: Optional[str] = None,
                                keyword: Optional[str] = None,
                                time_period_id: Optional[str] = None) -> List["EntertainmentTask"]:
        return self.task_orchestrator.get_entertainment_tasks(
            status=status, tag=tag, keyword=keyword,
            time_period_id=time_period_id,
        )

    def get_entertainment_task_by_id(self, task_id: str) -> Optional["EntertainmentTask"]:
        return self.task_orchestrator.get_entertainment_task_by_id(task_id)

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
        return self.task_orchestrator.create_entertainment_task(
            title=title, description=description, fun_category=fun_category,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
            estimated_duration=estimated_duration,
            time_period_id=time_period_id,
        )

    # ==================== 时段 ====================

    def get_all_time_periods(self) -> List[Any]:
        """获取所有时段（按排序与名称）"""
        return self.time_period_orchestrator.get_all()

    def get_time_period_by_id(self, period_id: Optional[str]) -> Any:
        return self.time_period_orchestrator.get_by_id(period_id)

    def create_time_period(self, name: str, start_time: str = "",
                           end_time: str = "", order_index: int = 0,
                           color: str = "") -> Any:
        return self.time_period_orchestrator.create(
            name=name, start_time=start_time, end_time=end_time,
            order_index=order_index, color=color,
        )

    def update_time_period(self, period_id: str, **kwargs: Any) -> bool:
        return self.time_period_orchestrator.update(period_id, **kwargs)

    def delete_time_period(self, period_id: str) -> bool:
        return self.time_period_orchestrator.delete(period_id)

    def get_time_period_id_to_name_map(self) -> dict:
        """{id: name} 字典，供渲染层批量反查"""
        return self.time_period_orchestrator.get_id_to_name_map()

    def resolve_time_period_label(self, period_id: Optional[str]) -> str:
        """反查展示文本，未设/已删除有专用文案"""
        return self.time_period_orchestrator.resolve_period_label(period_id)

    def resolve_time_period_display(self, period_id: Optional[str]) -> str:
        """反查「名称 起止」复合显示串，供表格时段列使用"""
        return self.time_period_orchestrator.resolve_period_display(period_id)

    def get_time_period_filter_options(self) -> list:
        """[(显示文本, 对应id/None), ...]，供筛选下拉框"""
        return self.time_period_orchestrator.get_filter_options()

    def update_entertainment_task(self, task_id: str, **kwargs: Any) -> bool:
        return self.task_orchestrator.update_entertainment_task(task_id, **kwargs)

    def delete_entertainment_task(self, task_id: str) -> bool:
        return self.task_orchestrator.delete_entertainment_task(task_id)

    def delete_entertainment_tasks_batch(self, task_ids: List[str]) -> int:
        return self.task_orchestrator.delete_entertainment_tasks_batch(task_ids)

    def toggle_entertainment_task_completion(self, task_id: str) -> bool:
        return self.task_orchestrator.toggle_entertainment_task_completion(task_id)

    # ==================== 垃圾桶 ====================

    def get_trashed_tasks(self, task_type: Optional[str] = None) -> List[Any]:
        return self.trash_orchestrator.get_trashed_tasks(task_type)

    def restore_trashed_task(self, trash_id: str) -> bool:
        return self.trash_orchestrator.restore(trash_id)

    def purge_trashed_task(self, trash_id: str) -> None:
        self.trash_orchestrator.purge(trash_id)

    def purge_trashed_tasks(self, trash_ids: List[str]) -> None:
        self.trash_orchestrator.purge_many(trash_ids)

    def purge_all_trashed(self, task_type: Optional[str] = None) -> None:
        self.trash_orchestrator.purge_all(task_type)

    # ==================== 快捷入口 ====================

    def get_all_shortcuts(self, tag: Optional[str] = None, keyword: Optional[str] = None) -> List[Any]:
        return self.shortcut_orchestrator.get_all(tag=tag, keyword=keyword)

    def create_shortcut(
        self,
        task_type: str,
        title: str,
        shortcut_path: str,
        tags: str = "",
        action_type: str = "open",
    ) -> bool:
        return self.shortcut_orchestrator.create(task_type, title, shortcut_path, tags, action_type)

    def update_shortcut(
        self,
        shortcut_id: str,
        title: Optional[str] = None,
        shortcut_path: Optional[str] = None,
        tags: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> bool:
        return self.shortcut_orchestrator.update(
            shortcut_id, title=title, shortcut_path=shortcut_path,
            tags=tags, action_type=action_type,
        )

    def delete_shortcut(self, shortcut_id: str) -> bool:
        return self.shortcut_orchestrator.delete(shortcut_id)

    def restore_shortcut(self, trash_id: str) -> bool:
        return self.trash_orchestrator.restore_shortcut(trash_id)

    # ==================== 快捷入口历史 ====================

    def get_history_limit(self) -> int:
        return self.shortcut_orchestrator.get_history_limit()

    def set_history_limit(self, limit: int) -> bool:
        return self.shortcut_orchestrator.set_history_limit(limit)

    def get_dangerously_skip_permissions(self) -> bool:
        return self.shortcut_orchestrator.get_dangerously_skip_permissions()

    def set_dangerously_skip_permissions(self, enabled: bool) -> bool:
        return self.shortcut_orchestrator.set_dangerously_skip_permissions(enabled)

    def get_all_history(self) -> List[Any]:
        return self.shortcut_orchestrator.get_all_history()

    def add_or_update_history(
        self,
        shortcut_id: str,
        shortcut_title: str,
        shortcut_path: str,
        action_type: str = "open",
    ) -> bool:
        return self.shortcut_orchestrator.add_or_update_history(
            shortcut_id, shortcut_title, shortcut_path, action_type,
        )

    def toggle_history_pin(self, history_id: str) -> bool:
        return self.shortcut_orchestrator.toggle_history_pin(history_id)

    def delete_history(self, history_id: str) -> bool:
        return self.shortcut_orchestrator.delete_history(history_id)

    def clear_all_unpinned_history(self) -> int:
        return self.shortcut_orchestrator.clear_all_unpinned_history()

    # ==================== 紧急度 ====================

    def calculate_urgency_for_task(self, task: "TodoTask") -> None:
        self.task_orchestrator.calculate_urgency_for_task(task)

    def recalculate_all_urgency(self) -> None:
        self.task_orchestrator.recalculate_all_urgency()

    # ==================== 配置 ====================

    def get_config(self, key: str, default: str = "") -> str:
        return self.config_orchestrator.get(key, default)

    def set_config(self, key: str, value: str) -> None:
        self.config_orchestrator.set(key, value)

    # ==================== JSON 导入导出 ====================

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        return self.task_orchestrator.export_to_json(filepath)

    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        return self.task_orchestrator.import_from_json(filepath)

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        return self._get_statistics_service().get_statistics()

    # ==================== 分类 ====================

    def get_all_categories(self, task_type: str) -> List[str]:
        return self.tag_orchestrator.get_all_categories(task_type)

    def add_category(self, category: str, task_type: str) -> bool:
        return self.tag_orchestrator.add_category(category, task_type)

    def delete_category(self, category: str, task_type: str) -> bool:
        return self.tag_orchestrator.delete_category(category, task_type)

    # ==================== 标签 ====================

    def get_all_tags(self, category: str) -> List[str]:
        return self.tag_orchestrator.get_all_tags(category)

    def add_tag(self, tag: str, category: str) -> bool:
        return self.tag_orchestrator.add_tag(tag, category)

    def delete_tag(self, tag: str, category: str) -> bool:
        return self.tag_orchestrator.delete_tag(tag, category)

    def get_or_create_tag(self, tag: str, category: str) -> bool:
        return self.tag_orchestrator.get_or_create_tag(tag, category)

    def cleanup_unused_tags(self) -> Dict[str, int]:
        return self.tag_orchestrator.cleanup_unused_tags()

    # ==================== 每日重置（兼容旧调用） ====================

    def check_daily_reset(self) -> None:
        self.daily_reset_service.check_and_reset()

    def reset_daily_tasks(self) -> None:
        self.daily_reset_service._do_reset()

    # ==================== 全局搜索 ====================

    def search_all_tasks(self, keyword: str) -> List[Dict[str, Any]]:
        return self._get_search_service().search_all_tasks(keyword)


if __name__ == "__main__":
    dm = DataManager()
    logger.info("数据管理器初始化成功")
    logger.info("每日任务数量: %d", len(dm.get_daily_tasks()))
    logger.info("待办事项数量: %d", len(dm.get_todo_tasks()))
    logger.info("娱乐任务数量: %d", len(dm.get_entertainment_tasks()))
    dm.close_session()
