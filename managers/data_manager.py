"""
Task Manager - 数据管理外观（Facade）
为上层 UI/Service 提供统一的业务入口，内部按功能垂直委托给多个编排器
（Task / Shortcut / Tag / Trash / Config Orchestrator）
通过 OrchestratorFactory 工厂模式解耦编排器的创建
"""

import logging
from typing import List, Dict, Any, Optional

from models.model import DailyTask, TodoTask, EntertainmentTask

from managers.data_access import DataAccess
from managers.todo_task_manager import TodoTaskManager
from managers.entertainment_task_manager import EntertainmentTaskManager
from managers.config_manager import ConfigManager
from managers.trash_manager import TrashManager
from managers.shortcut_manager import ShortcutManager
from managers.daily_task_manager import DailyTaskManager
from managers.tag_manager import TagManager
from managers.task_type import TaskType

from services.daily_reset_service import DailyResetService
from services.vacuum_service import VacuumService
from services.trash_restoration_service import TrashRestorationService
from services.service_factory import ServiceFactory
from services.orchestrator_factory import OrchestratorFactory

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

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据管理外观"""
        # 基础设施：DB session / 连接
        self._data_access = DataAccess(db_path=db_path)
        self.session = self._data_access.get_session()
        self.engine = self._data_access.engine

        # 底层 Repository（保持对外属性名兼容）
        self._main_conn = self._data_access.get_main_connection()
        self._trash_conn = self._data_access.get_trash_connection()

        self.todo_manager = TodoTaskManager(self.session)
        self.entertainment_manager = EntertainmentTaskManager(self.session)
        self.config_manager = ConfigManager(self.session)
        self.trash_manager = TrashManager(connection=self._trash_conn)
        self.shortcut_manager = ShortcutManager(connection=self._main_conn)
        self.daily_task_manager = DailyTaskManager(self.session)
        self.tag_manager = TagManager(self.config_manager)

        # 服务层
        self.daily_reset_service = DailyResetService(self.session, self.config_manager)
        import config.config

        self.vacuum_service = VacuumService(self.engine, config.config.TRASH_DATABASE_PATH)
        self.trash_restoration_service = TrashRestorationService(
            session=self.session,
            shortcut_manager=self.shortcut_manager,
            trash_manager=self.trash_manager,
            vacuum_service=self.vacuum_service,
            daily_task_manager=self.daily_task_manager,
            todo_task_manager=self.todo_manager,
            entertainment_task_manager=self.entertainment_manager,
        )

        # 工厂：服务 + 编排器
        self._service_factory = ServiceFactory(self)
        self._orchestrator_factory = OrchestratorFactory(self)

        # 触发每日重置
        self.daily_reset_service.check_and_reset()
        logger.info("DataManager 初始化完成 | request_id=init")

    # ==================== 编排器访问器 ====================

    @property
    def task_orchestrator(self):
        return self._orchestrator_factory.get_task_orchestrator()

    @property
    def shortcut_orchestrator(self):
        return self._orchestrator_factory.get_shortcut_orchestrator()

    @property
    def tag_orchestrator(self):
        return self._orchestrator_factory.get_tag_orchestrator()

    @property
    def trash_orchestrator(self):
        return self._orchestrator_factory.get_trash_orchestrator()

    @property
    def config_orchestrator(self):
        return self._orchestrator_factory.get_config_orchestrator()

    # ==================== 服务工厂代理 ====================

    def _get_statistics_service(self):
        return self._service_factory.get_statistics_service()

    def _get_search_service(self):
        return self._service_factory.get_search_service()

    def _get_task_limit_service(self):
        return self._service_factory.get_task_limit_service()

    def _get_pomodoro_service(self):
        return self._service_factory.get_pomodoro_service()

    # ==================== 会话管理 ====================

    def get_session(self):
        return self.session

    def close_session(self):
        logger.info("关闭数据库会话 | request_id=close")
        self.trash_manager.close()
        self.shortcut_manager.close()
        self._data_access.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    # ==================== DailyTask 委托 ====================

    def get_daily_tasks(self, weekday=None, status=None, tag=None) -> List[DailyTask]:
        return self.task_orchestrator.get_daily_tasks(weekday=weekday, status=status, tag=tag)

    def get_daily_task_by_id(self, task_id: str) -> Optional[DailyTask]:
        return self.task_orchestrator.get_daily_task_by_id(task_id)

    def create_daily_task(self, title, description="", week_day="",
                          completed=False, status="pending",
                          tags="", shortcut_path="", category="",
                          priority="normal", subtasks="[]") -> DailyTask:
        return self.task_orchestrator.create_daily_task(
            title=title, description=description, week_day=week_day,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
        )

    def update_daily_task(self, task_id, **kwargs) -> bool:
        return self.task_orchestrator.update_daily_task(task_id, **kwargs)

    def delete_daily_task(self, task_id) -> bool:
        return self.task_orchestrator.delete_daily_task(task_id)

    def delete_daily_tasks_batch(self, task_ids) -> int:
        return self.task_orchestrator.delete_daily_tasks_batch(task_ids)

    def toggle_daily_task_completion(self, task_id) -> bool:
        return self.task_orchestrator.toggle_daily_task_completion(task_id)

    # ==================== TodoTask 委托 ====================

    def get_todo_tasks(self, status=None, tag=None) -> List[TodoTask]:
        return self.task_orchestrator.get_todo_tasks(status=status, tag=tag)

    def get_todo_task_by_id(self, task_id) -> Optional[TodoTask]:
        return self.task_orchestrator.get_todo_task_by_id(task_id)

    def create_todo_task(self, title, description="", deadline="",
                         completed=False, status="pending",
                         tags="", shortcut_path="", category="",
                         priority="normal", subtasks="[]") -> TodoTask:
        return self.task_orchestrator.create_todo_task(
            title=title, description=description, deadline=deadline,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
        )

    def update_todo_task(self, task_id, **kwargs) -> bool:
        return self.task_orchestrator.update_todo_task(task_id, **kwargs)

    def delete_todo_task(self, task_id) -> bool:
        return self.task_orchestrator.delete_todo_task(task_id)

    def delete_todo_tasks_batch(self, task_ids) -> int:
        return self.task_orchestrator.delete_todo_tasks_batch(task_ids)

    def toggle_todo_task_completion(self, task_id) -> bool:
        return self.task_orchestrator.toggle_todo_task_completion(task_id)

    # ==================== EntertainmentTask 委托 ====================

    def get_entertainment_tasks(self, status=None, tag=None) -> List[EntertainmentTask]:
        return self.task_orchestrator.get_entertainment_tasks(status=status, tag=tag)

    def get_entertainment_task_by_id(self, task_id) -> Optional[EntertainmentTask]:
        return self.task_orchestrator.get_entertainment_task_by_id(task_id)

    def create_entertainment_task(self, title, description="",
                                  fun_category="general", completed=False,
                                  status="pending", tags="",
                                  shortcut_path="", category="",
                                  priority="normal", subtasks="[]") -> EntertainmentTask:
        return self.task_orchestrator.create_entertainment_task(
            title=title, description=description, fun_category=fun_category,
            completed=completed, status=status, tags=tags,
            shortcut_path=shortcut_path, category=category,
            priority=priority, subtasks=subtasks,
        )

    def update_entertainment_task(self, task_id, **kwargs) -> bool:
        return self.task_orchestrator.update_entertainment_task(task_id, **kwargs)

    def delete_entertainment_task(self, task_id) -> bool:
        return self.task_orchestrator.delete_entertainment_task(task_id)

    def delete_entertainment_tasks_batch(self, task_ids) -> int:
        return self.task_orchestrator.delete_entertainment_tasks_batch(task_ids)

    def toggle_entertainment_task_completion(self, task_id) -> bool:
        return self.task_orchestrator.toggle_entertainment_task_completion(task_id)

    # ==================== 垃圾桶 ====================

    def get_trashed_tasks(self, task_type=None):
        return self.trash_orchestrator.get_trashed_tasks(task_type)

    def restore_trashed_task(self, trash_id) -> bool:
        return self.trash_orchestrator.restore(trash_id)

    def purge_trashed_task(self, trash_id):
        self.trash_orchestrator.purge(trash_id)

    def purge_trashed_tasks(self, trash_ids):
        self.trash_orchestrator.purge_many(trash_ids)

    def purge_all_trashed(self, task_type=None):
        self.trash_orchestrator.purge_all(task_type)

    # ==================== 快捷入口 ====================

    def get_all_shortcuts(self, tag=None) -> list:
        return self.shortcut_orchestrator.get_all(tag=tag)

    def create_shortcut(self, task_type, title, shortcut_path, tags="", action_type="open") -> bool:
        return self.shortcut_orchestrator.create(task_type, title, shortcut_path, tags, action_type)

    def update_shortcut(self, shortcut_id, title=None, shortcut_path=None,
                        tags=None, action_type=None) -> bool:
        return self.shortcut_orchestrator.update(
            shortcut_id, title=title, shortcut_path=shortcut_path,
            tags=tags, action_type=action_type,
        )

    def delete_shortcut(self, shortcut_id) -> bool:
        return self.shortcut_orchestrator.delete(shortcut_id)

    def restore_shortcut(self, trash_id) -> bool:
        return self.trash_orchestrator.restore_shortcut(trash_id)

    # ==================== 快捷入口历史 ====================

    def get_history_limit(self) -> int:
        return self.shortcut_orchestrator.get_history_limit()

    def set_history_limit(self, limit) -> bool:
        return self.shortcut_orchestrator.set_history_limit(limit)

    def get_dangerously_skip_permissions(self) -> bool:
        return self.shortcut_orchestrator.get_dangerously_skip_permissions()

    def set_dangerously_skip_permissions(self, enabled: bool) -> bool:
        return self.shortcut_orchestrator.set_dangerously_skip_permissions(enabled)

    def get_all_history(self) -> list:
        return self.shortcut_orchestrator.get_all_history()

    def add_or_update_history(self, shortcut_id, shortcut_title, shortcut_path,
                              action_type="open") -> bool:
        return self.shortcut_orchestrator.add_or_update_history(
            shortcut_id, shortcut_title, shortcut_path, action_type,
        )

    def toggle_history_pin(self, history_id) -> bool:
        return self.shortcut_orchestrator.toggle_history_pin(history_id)

    def delete_history(self, history_id) -> bool:
        return self.shortcut_orchestrator.delete_history(history_id)

    def clear_all_unpinned_history(self) -> int:
        return self.shortcut_orchestrator.clear_all_unpinned_history()

    # ==================== 紧急度 ====================

    def calculate_urgency_for_task(self, task: TodoTask):
        self.task_orchestrator.calculate_urgency_for_task(task)

    def recalculate_all_urgency(self):
        self.task_orchestrator.recalculate_all_urgency()

    # ==================== 配置 ====================

    def get_config(self, key, default="") -> str:
        return self.config_orchestrator.get(key, default)

    def set_config(self, key, value):
        self.config_orchestrator.set(key, value)

    # ==================== JSON 导入导出 ====================

    def export_to_json(self, filepath="tasks_export.json") -> bool:
        return self.task_orchestrator.export_to_json(filepath)

    def import_from_json(self, filepath="tasks_export.json") -> bool:
        return self.task_orchestrator.import_from_json(filepath)

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        return self._get_statistics_service().get_statistics()

    # ==================== 分类 ====================

    def get_all_categories(self, task_type) -> List[str]:
        return self.tag_orchestrator.get_all_categories(task_type)

    def add_category(self, category, task_type) -> bool:
        return self.tag_orchestrator.add_category(category, task_type)

    def delete_category(self, category, task_type) -> bool:
        return self.tag_orchestrator.delete_category(category, task_type)

    # ==================== 标签 ====================

    def get_all_tags(self, category) -> List[str]:
        return self.tag_orchestrator.get_all_tags(category)

    def add_tag(self, tag, category) -> bool:
        return self.tag_orchestrator.add_tag(tag, category)

    def delete_tag(self, tag, category) -> bool:
        return self.tag_orchestrator.delete_tag(tag, category)

    def get_or_create_tag(self, tag, category) -> bool:
        return self.tag_orchestrator.get_or_create_tag(tag, category)

    def cleanup_unused_tags(self) -> Dict[str, int]:
        return self.tag_orchestrator.cleanup_unused_tags()

    # ==================== 每日重置（兼容旧调用） ====================

    def check_daily_reset(self):
        self.daily_reset_service.check_and_reset()

    def reset_daily_tasks(self):
        self.daily_reset_service._do_reset()

    # ==================== 全局搜索 ====================

    def search_all_tasks(self, keyword) -> List[Dict[str, Any]]:
        return self._get_search_service().search_all_tasks(keyword)


if __name__ == "__main__":
    dm = DataManager()
    logger.info("数据管理器初始化成功")
    logger.info("每日任务数量: %d", len(dm.get_daily_tasks()))
    logger.info("待办事项数量: %d", len(dm.get_todo_tasks()))
    logger.info("娱乐任务数量: %d", len(dm.get_entertainment_tasks()))
    dm.close_session()
