"""
测试配置文件 - pytest fixtures
"""
import sys
import os
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.model import Base


@pytest.fixture
def in_memory_engine():
    """创建一个内存 SQLite 引擎，用于测试。"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_engine) -> sessionmaker:
    """返回 session 工厂。"""
    return sessionmaker(bind=in_memory_engine)


@pytest.fixture
def db_session(session_factory) -> Generator[Session, None, None]:
    """返回一个数据库会话，用完自动回滚。"""
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_data_manager(mocker):
    """返回一个 mock 的 DataManager。"""
    mock_dm = mocker.MagicMock()
    return mock_dm
