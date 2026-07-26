"""
managers/data_access.py 单元测试
测试数据访问层的连接与会话管理
"""
import sqlite3
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models.model import Base


class TestDataAccess:
    """DataAccess 基础功能测试"""

    def _make_da(self, engine: Any) -> "DataAccess":
        """构造一个最小化的 DataAccess 测试替身（不启动真实 init_db）。"""
        from managers.infrastructure.data_access import DataAccess

        SessionCls = sessionmaker(bind=engine)

        class TestDataAccess(DataAccess):
            def __init__(self):
                self.engine = engine
                self.Session = SessionCls
                self.session = SessionCls()
                self.db_path = ":memory:"
                self.trash_db_path = ":memory:"
                self._main_conn = sqlite3.connect(":memory:")
                self._trash_conn = sqlite3.connect(":memory:")

        return TestDataAccess()

    def test_get_session_returns_orm_session(self, in_memory_engine):
        """get_session 返回 SQLAlchemy Session 对象"""
        da = self._make_da(in_memory_engine)
        session = da.get_session()
        assert isinstance(session, Session)
        da.close()

    def test_get_main_connection_returns_sqlite_connection(self, in_memory_engine):
        """get_main_connection 返回 sqlite3.Connection"""
        da = self._make_da(in_memory_engine)
        conn = da.get_main_connection()
        assert isinstance(conn, sqlite3.Connection)
        da.close()

    def test_get_trash_connection_returns_sqlite_connection(self, in_memory_engine):
        """get_trash_connection 返回 sqlite3.Connection"""
        da = self._make_da(in_memory_engine)
        conn = da.get_trash_connection()
        assert isinstance(conn, sqlite3.Connection)
        da.close()

    def test_close_cleans_up_all_resources(self, in_memory_engine):
        """close 方法关闭 session 和所有 sqlite3 连接"""
        da = self._make_da(in_memory_engine)
        da.close()
        # 关闭后连接应为 None（避免 use-after-close）
        assert da._main_conn is None
        assert da._trash_conn is None

    def test_commit_calls_session_commit(self, in_memory_engine):
        """commit 委托给 session.commit（无异常即通过）"""
        da = self._make_da(in_memory_engine)
        da.commit()  # 无异常即通过
        da.close()

    def test_rollback_calls_session_rollback(self, in_memory_engine):
        """rollback 委托给 session.rollback（无异常即通过）"""
        da = self._make_da(in_memory_engine)
        da.rollback()  # 无异常即通过
        da.close()

    def test_init_db_with_memory_engine(self):
        """使用真实 init_db 创建内存引擎，确认所有组件正常"""
        from models.model import init_db

        engine, Session = init_db(db_path=":memory:", run_migration=False)
        Base.metadata.create_all(engine)

        session = Session()
        assert session is not None
        session.close()
