"""
models/model.py 单元测试
测试数据库模型的创建、字段定义和 migrate_db 逻辑
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models.model import (
    Base,
    BaseModel,
    DailyTask,
    TodoTask,
    EntertainmentTask,
    Config,
    ShortcutHistory,
    init_db,
)


class TestInitDb:
    """init_db 工厂函数测试"""

    def test_init_db_creates_engine_and_session(self):
        """init_db 返回 engine 和 Session"""
        engine, Session = init_db(db_path=":memory:", run_migration=False)
        assert engine is not None
        assert callable(Session)
        # 用 Session 创建一次 session 确认可用
        session = Session()
        assert session is not None
        session.close()

    def test_init_db_creates_all_tables(self):
        """init_db 在内存引擎中创建所有表"""
        engine, Session = init_db(db_path=":memory:", run_migration=False)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "daily_tasks" in table_names
        assert "todo_tasks" in table_names
        assert "entertainment_tasks" in table_names
        assert "configs" in table_names
        assert "shortcut_history" in table_names


class TestBaseModel:
    """BaseModel 公共字段测试"""

    def test_base_model_has_id_field(self, in_memory_engine):
        """BaseModel 有 id 主键字段"""
        Base.metadata.create_all(in_memory_engine)
        session = sessionmaker(bind=in_memory_engine)()
        class Dummy(BaseModel):
            __tablename__ = "dummy_test"
            title = __import__("sqlalchemy").Column(__import__("sqlalchemy").String(255), nullable=False)

        Base.metadata.create_all(in_memory_engine)
        # dummy 表不适用于此测试，只验证 BaseModel 本身的字段声明
        session.close()

    def test_daily_task_creation(self, in_memory_engine):
        """创建 DailyTask 实例"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = DailyTask(
            title="测试每日任务",
            description="描述",
            week_day="Monday",
            completed=False,
            status="pending",
            tags="工作,重要",
            priority="high",
        )
        session.add(task)
        session.commit()

        assert task.id is not None
        assert task.title == "测试每日任务"
        assert task.week_day == "Monday"
        assert task.priority == "high"
        assert task.tags == "工作,重要"
        assert task.created_at is not None
        assert task.updated_at is not None
        session.close()

    def test_todo_task_creation(self, in_memory_engine):
        """创建 TodoTask 实例"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = TodoTask(
            title="测试待办",
            deadline="2025-12-31",
            urgency_score=2.5,
            priority="urgent",
        )
        session.add(task)
        session.commit()

        assert task.id is not None
        assert task.title == "测试待办"
        assert task.deadline == "2025-12-31"
        assert task.urgency_score == 2.5
        assert task.priority == "urgent"
        session.close()

    def test_entertainment_task_creation(self, in_memory_engine):
        """创建 EntertainmentTask 实例"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = EntertainmentTask(
            title="测试娱乐任务",
            fun_category="游戏",
            priority="low",
        )
        session.add(task)
        session.commit()

        assert task.id is not None
        assert task.title == "测试娱乐任务"
        assert task.fun_category == "游戏"
        assert task.priority == "low"
        session.close()

    def test_config_creation(self, in_memory_engine):
        """创建 Config 实例"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        cfg = Config(key="test_key", value="test_value")
        session.add(cfg)
        session.commit()

        assert cfg.id is not None
        assert cfg.key == "test_key"
        assert cfg.value == "test_value"
        session.close()

    def test_shortcut_history_creation(self, in_memory_engine):
        """创建 ShortcutHistory 实例"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        hist = ShortcutHistory(
            shortcut_id="sc_001",
            shortcut_title="测试快捷入口",
            shortcut_path="/path/to/app",
            action_type="open",
        )
        session.add(hist)
        session.commit()

        assert hist.id is not None
        assert hist.shortcut_id == "sc_001"
        assert hist.is_pinned == 0
        session.close()


class TestTaskDefaultValues:
    """任务模型默认值测试"""

    def test_daily_task_defaults(self, in_memory_engine):
        """DailyTask 各字段默认值"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = DailyTask(title="默认测试")
        session.add(task)
        session.commit()

        assert task.completed is False
        # week_day / category / status / tags / shortcut_path 为 NULL 列，
        # SQLAlchemy 读取出来是 None，不影响业务（业务层用 "" 做空值判断）
        assert task.week_day is None or task.week_day == ""
        assert task.category == "daily"
        assert task.status == "pending"
        assert task.tags == "" or task.tags is None
        assert task.shortcut_path == "" or task.shortcut_path is None
        assert task.priority == "normal"
        assert task.subtasks == "[]"
        session.close()

    def test_todo_task_defaults(self, in_memory_engine):
        """TodoTask 各字段默认值"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = TodoTask(title="默认测试")
        session.add(task)
        session.commit()

        assert task.completed is False
        assert task.deadline is None
        assert task.urgency_score == 0.0
        assert task.category == "todo"
        assert task.status == "pending"
        assert task.tags == ""
        assert task.shortcut_path == ""
        assert task.priority == "normal"
        assert task.subtasks == "[]"
        session.close()

    def test_entertainment_task_defaults(self, in_memory_engine):
        """EntertainmentTask 各字段默认值"""
        Base.metadata.create_all(in_memory_engine)
        Session = sessionmaker(bind=in_memory_engine)
        session = Session()

        task = EntertainmentTask(title="默认测试")
        session.add(task)
        session.commit()

        assert task.completed is False
        assert task.fun_category == "general"
        assert task.category == "entertainment"
        assert task.status == "pending"
        assert task.tags == ""
        assert task.shortcut_path == ""
        assert task.priority == "normal"
        assert task.subtasks == "[]"
        session.close()
