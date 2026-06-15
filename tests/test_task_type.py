"""
managers/task_type.py 单元测试
测试任务类型枚举的正确性
"""
import pytest
from managers.task_type import TaskType


class TestTaskType:
    """TaskType 枚举完整性测试"""

    def test_task_type_values(self):
        """三个枚举成员值正确"""
        assert TaskType.DAILY.value == "daily"
        assert TaskType.TODO.value == "todo"
        assert TaskType.ENTERTAINMENT.value == "entertainment"

    def test_task_type_count(self):
        """枚举成员数量为 3"""
        assert len(TaskType) == 3

    def test_task_type_iteration(self):
        """枚举可遍历，顺序固定"""
        members = list(TaskType)
        assert len(members) == 3
        assert members[0] == TaskType.DAILY
        assert members[1] == TaskType.TODO
        assert members[2] == TaskType.ENTERTAINMENT

    def test_task_type_from_value(self):
        """通过 value 获取枚举成员"""
        assert TaskType("daily") == TaskType.DAILY
        assert TaskType("todo") == TaskType.TODO
        assert TaskType("entertainment") == TaskType.ENTERTAINMENT

    def test_task_type_invalid_value(self):
        """无效 value 抛出 ValueError"""
        with pytest.raises(ValueError):
            TaskType("invalid")
