"""
Service Factory - 服务工厂模块
使用工厂模式统一管理服务的创建与管理
"""
from __future__ import annotations

import logging
from typing import Dict, Any, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from managers.application.data_manager import DataManager
    # 服务类型仅用于类型注解，运行时在方法体内导入以避免循环依赖
    from services.domain.statistics_service import StatisticsService
    from services.search.search_service import SearchService
    from services.domain.task_limit_service import TaskLimitService
    from services.pomodoro.pomodoro_service import PomodoroService
    from services.shortcuts.shortcut_operation_service import ShortcutOperationService
    from services.domain.tag_cleanup_service import TagCleanupService
    from services.search.search_coordinator import SearchCoordinator

logger = logging.getLogger(__name__)


class ServiceFactory:
    """服务工厂类 - 统一管理业务服务的创建"""

    def __init__(self, data_manager: "DataManager") -> None:
        """
        Args:
            data_manager: DataManager 实例
        """
        self._dm: "DataManager" = data_manager
        self._services: Dict[str, Any] = {}
        logger.debug("ServiceFactory 初始化完成")

    def get_statistics_service(self) -> "StatisticsService":
        """获取统计服务（单例）"""
        if "statistics" not in self._services:
            from services.domain.statistics_service import StatisticsService

            self._services["statistics"] = StatisticsService(self._dm)
            logger.info("StatisticsService 已创建")
        return cast("StatisticsService", self._services["statistics"])

    def get_search_service(self) -> "SearchService":
        """获取搜索服务（单例）"""
        if "search" not in self._services:
            from services.search.search_service import SearchService

            self._services["search"] = SearchService(self._dm)
            logger.info("SearchService 已创建")
        return cast("SearchService", self._services["search"])

    def get_task_limit_service(self) -> "TaskLimitService":
        """获取任务限制服务（单例）"""
        if "task_limit" not in self._services:
            from services.domain.task_limit_service import TaskLimitService

            self._services["task_limit"] = TaskLimitService(
                self._dm,
                self._dm.trash_manager,
                self._dm.vacuum_service,
            )
            logger.info("TaskLimitService 已创建")
        return cast("TaskLimitService", self._services["task_limit"])

    def get_pomodoro_service(self) -> "PomodoroService":
        """获取番茄钟服务（单例）"""
        if "pomodoro" not in self._services:
            from services.pomodoro.pomodoro_service import PomodoroService

            self._services["pomodoro"] = PomodoroService(self._dm)
            logger.info("PomodoroService 已创建")
        return cast("PomodoroService", self._services["pomodoro"])

    def get_shortcut_operation_service(self) -> "ShortcutOperationService":
        """获取快捷入口操作服务（单例）"""
        if "shortcut_operation" not in self._services:
            from services.shortcuts.shortcut_operation_service import ShortcutOperationService

            self._services["shortcut_operation"] = ShortcutOperationService(self._dm)
            logger.info("ShortcutOperationService 已创建")
        return cast("ShortcutOperationService", self._services["shortcut_operation"])

    def get_tag_cleanup_service(self) -> "TagCleanupService":
        """获取标签清理服务（单例）"""
        if "tag_cleanup" not in self._services:
            from services.domain.tag_cleanup_service import TagCleanupService

            self._services["tag_cleanup"] = TagCleanupService(self._dm)
            logger.info("TagCleanupService 已创建")
        return cast("TagCleanupService", self._services["tag_cleanup"])

    def get_search_coordinator(self, window: Any) -> "SearchCoordinator":
        """获取搜索协调器（每次返回新实例，因为需要持有 window 引用）"""
        from services.search.search_coordinator import SearchCoordinator

        return SearchCoordinator(window)
