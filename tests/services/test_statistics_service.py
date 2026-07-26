"""
services/statistics_service.py 单元测试
"""
import pytest
from unittest.mock import MagicMock

from services.domain.statistics_service import StatisticsService


class TestStatisticsService:
    """StatisticsService 业务逻辑测试"""

    def _make_mock_dm(self, daily_tasks, todo_tasks, entertainment_tasks):
        """构造一个含有所需方法的 mock DataManager。"""
        mock_dm = MagicMock()
        mock_dm.get_daily_tasks.return_value = daily_tasks
        mock_dm.get_todo_tasks.return_value = todo_tasks
        mock_dm.get_entertainment_tasks.return_value = entertainment_tasks
        return mock_dm

    def test_get_statistics_all_zeros(self):
        """三种任务数量均为 0 时，统计结果全为 0"""
        mock_dm = self._make_mock_dm([], [], [])
        service = StatisticsService(mock_dm)

        stats = service.get_statistics()

        assert stats["daily"]["total"] == 0
        assert stats["daily"]["completed"] == 0
        assert stats["todo"]["total"] == 0
        assert stats["todo"]["completed"] == 0
        assert stats["todo"]["expired"] == 0
        assert stats["entertainment"]["total"] == 0
        assert stats["entertainment"]["completed"] == 0

    def test_get_statistics_counts_correctly(self):
        """统计任务总数和完成数正确"""
        # 构造已完成的每日任务
        daily1 = self._make_task("daily", completed=True)
        daily2 = self._make_task("daily", completed=False)
        # 构造已过期且完成的待办
        todo1 = self._make_task("todo", completed=True, deadline="2020-01-01")  # 已过期
        todo2 = self._make_task("todo", completed=False, deadline="2099-01-01")  # 未过期
        # 构造娱乐任务
        ent1 = self._make_task("entertainment", completed=True)

        mock_dm = self._make_mock_dm(
            daily_tasks=[daily1, daily2],
            todo_tasks=[todo1, todo2],
            entertainment_tasks=[ent1],
        )
        # Mock todo_manager.is_expired
        mock_dm.todo_manager.is_expired.side_effect = lambda t: t.deadline == "2020-01-01"

        service = StatisticsService(mock_dm)
        stats = service.get_statistics()

        assert stats["daily"]["total"] == 2
        assert stats["daily"]["completed"] == 1
        assert stats["todo"]["total"] == 2
        assert stats["todo"]["completed"] == 1
        assert stats["todo"]["expired"] == 1
        assert stats["entertainment"]["total"] == 1
        assert stats["entertainment"]["completed"] == 1

    def test_get_statistics_no_todo_expired(self):
        """没有过期任务时 expired 为 0"""
        todo1 = self._make_task("todo", completed=False, deadline="2099-01-01")
        mock_dm = self._make_mock_dm([], [todo1], [])
        mock_dm.todo_manager.is_expired.return_value = False

        service = StatisticsService(mock_dm)
        stats = service.get_statistics()

        assert stats["todo"]["expired"] == 0

    def test_get_statistics_empty_todo_deadline(self):
        """deadline 为 None 的任务不报错"""
        todo1 = self._make_task("todo", completed=False, deadline=None)
        mock_dm = self._make_mock_dm([], [todo1], [])
        mock_dm.todo_manager.is_expired.return_value = False

        service = StatisticsService(mock_dm)
        stats = service.get_statistics()

        assert stats["todo"]["total"] == 1
        assert stats["todo"]["expired"] == 0

    # ---------- 辅助方法 ----------

    @staticmethod
    def _make_task(task_type, completed=False, deadline=None):
        """构造一个简易 mock Task 对象。"""
        task = MagicMock()
        task.completed = completed
        task.deadline = deadline
        return task
