"""
services/service_factory.py 单元测试
"""
import pytest
from unittest.mock import MagicMock, patch

from services.service_factory import ServiceFactory


class TestServiceFactory:
    """ServiceFactory 单例逻辑测试"""

    def test_get_statistics_service_returns_same_instance(self):
        """同一 DataManager 多次调用 get_statistics_service 返回同一实例（单例）"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_statistics_service()
        svc2 = factory.get_statistics_service()

        assert svc1 is svc2

    def test_get_search_service_returns_same_instance(self):
        """get_search_service 单例"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_search_service()
        svc2 = factory.get_search_service()

        assert svc1 is svc2

    def test_get_task_limit_service_returns_same_instance(self):
        """get_task_limit_service 单例"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_task_limit_service()
        svc2 = factory.get_task_limit_service()

        assert svc1 is svc2

    def test_get_pomodoro_service_returns_same_instance(self):
        """get_pomodoro_service 单例"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_pomodoro_service()
        svc2 = factory.get_pomodoro_service()

        assert svc1 is svc2

    def test_get_shortcut_operation_service_returns_same_instance(self):
        """get_shortcut_operation_service 单例"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_shortcut_operation_service()
        svc2 = factory.get_shortcut_operation_service()

        assert svc1 is svc2

    def test_get_tag_cleanup_service_returns_same_instance(self):
        """get_tag_cleanup_service 单例"""
        mock_dm = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_tag_cleanup_service()
        svc2 = factory.get_tag_cleanup_service()

        assert svc1 is svc2

    def test_get_search_coordinator_returns_new_instance_each_time(self):
        """get_search_coordinator 每次返回新实例（因为需要持有 window 引用）"""
        mock_dm = MagicMock()
        mock_window = MagicMock()
        factory = ServiceFactory(mock_dm)

        svc1 = factory.get_search_coordinator(mock_window)
        svc2 = factory.get_search_coordinator(mock_window)

        assert svc1 is not svc2
