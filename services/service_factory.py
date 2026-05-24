"""
Service Factory - 服务工厂模块
使用工厂模式统一管理服务的创建与管理
"""

import logging

logger = logging.getLogger(__name__)


class ServiceFactory:
    """服务工厂类 - 统一管理业务服务的创建"""

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例
        """
        self._dm = data_manager
        self._services = {}
        logger.debug("ServiceFactory 初始化完成")

    def get_statistics_service(self):
        """获取统计服务（单例）"""
        if 'statistics' not in self._services:
            from services.statistics_service import StatisticsService
            self._services['statistics'] = StatisticsService(self._dm)
            logger.info("StatisticsService 已创建")
        return self._services['statistics']

    def get_search_service(self):
        """获取搜索服务（单例）"""
        if 'search' not in self._services:
            from services.search_service import SearchService
            self._services['search'] = SearchService(self._dm)
            logger.info("SearchService 已创建")
        return self._services['search']

    def get_task_limit_service(self):
        """获取任务限制服务（单例）"""
        if 'task_limit' not in self._services:
            from services.task_limit_service import TaskLimitService
            self._services['task_limit'] = TaskLimitService(
                self._dm,
                self._dm.trash_manager,
                self._dm.vacuum_service
            )
            logger.info("TaskLimitService 已创建")
        return self._services['task_limit']
