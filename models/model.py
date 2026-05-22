"""
Task Manager - 数据库模型
使用 SQLAlchemy ORM 定义数据模型
"""

import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()

class BaseModel(Base):
    """基础模型类"""
    __abstract__ = True
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DailyTask(BaseModel):
    """每日任务模型"""
    __tablename__ = 'daily_tasks'
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    week_day = Column(String(20))  # 如"Monday", "Tuesday", 或留空表示每天
    category = Column(String(50), default="daily")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"工作,紧急,项目A"
    shortcut_path = Column(String(1000), default="")  # 快捷入口路径，非空表示快捷入口


class TodoTask(BaseModel):
    """待办事项模型"""
    __tablename__ = 'todo_tasks'
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    deadline = Column(String(20))  # YYYY-MM-DD格式
    urgency_score = Column(Float, default=0.0)
    category = Column(String(50), default="todo")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"工作,紧急,项目A"
    shortcut_path = Column(String(1000), default="")  # 快捷入口路径，非空表示快捷入口


class EntertainmentTask(BaseModel):
    """娱乐任务模型"""
    __tablename__ = 'entertainment_tasks'
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    fun_category = Column(String(50), default="general")
    category = Column(String(50), default="entertainment")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"游戏,周末,多人"
    shortcut_path = Column(String(1000), default="")  # 快捷入口路径，非空表示快捷入口


class Config(BaseModel):
    """配置模型"""
    __tablename__ = 'configs'
    
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)


def migrate_db(engine):
    """数据库迁移：添加新字段"""
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    
    # 检查并添加 daily_tasks.tags 字段
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'tags' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 daily_tasks.tags 字段")

    # 检查并添加 todo_tasks.tags 字段
    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'tags' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 todo_tasks.tags 字段")

    # 检查并添加 entertainment_tasks.tags 字段
    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'tags' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.tags 字段")

    # 检查并添加 daily_tasks.shortcut_path 字段
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'shortcut_path' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN shortcut_path VARCHAR(1000) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 daily_tasks.shortcut_path 字段")

    # 检查并添加 todo_tasks.shortcut_path 字段
    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'shortcut_path' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN shortcut_path VARCHAR(1000) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 todo_tasks.shortcut_path 字段")

    # 迁移 urgency_score 从 Integer 到 Float（SQLite 不支持 MODIFY，需重建列）
    todo_columns = {col['name']: col for col in inspector.get_columns('todo_tasks')}
    if 'urgency_score' in todo_columns and 'INTEGER' in str(todo_columns['urgency_score']['type']).upper():
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN urgency_score_new REAL DEFAULT 0.0"))
            conn.execute(text("UPDATE todo_tasks SET urgency_score_new = CAST(urgency_score AS REAL)"))
            conn.execute(text("ALTER TABLE todo_tasks DROP COLUMN urgency_score"))
            conn.execute(text("ALTER TABLE todo_tasks RENAME COLUMN urgency_score_new TO urgency_score"))
            conn.commit()
        logger.info("已迁移 urgency_score 从 INTEGER 到 REAL")

    # 检查并添加 entertainment_tasks.shortcut_path 字段
    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'shortcut_path' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN shortcut_path VARCHAR(1000) DEFAULT ''"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.shortcut_path 字段")

    # 清理 category 字段中的旧数据（之前用于存储任务类型，现改为用户分类）
    # 将值为 'daily', 'todo', 'entertainment' 的记录清空
    for table_name, type_val in [('daily_tasks', 'daily'), ('todo_tasks', 'todo'), ('entertainment_tasks', 'entertainment')]:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"UPDATE {table_name} SET category = '' WHERE category = '{type_val}'"))
                conn.commit()
            logger.info(f"已清理 {table_name} 中的旧 category 值")
        except Exception as e:
            logger.warning(f"清理 {table_name} category 时出错: {e}")


# 数据库连接和会话管理
def init_db(db_path: str = "taskmanager.db", run_migration: bool = False):
    """初始化数据库
    
    Args:
        db_path: 数据库文件路径，默认为 "taskmanager.db"
        run_migration: 是否执行数据库迁移，默认为 False
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    # 仅在手动调用时执行迁移
    if run_migration:
        migrate_db(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


# 如果直接运行此文件，创建数据库
if __name__ == "__main__":
    engine, Session = init_db()
    logger.info("数据库初始化完成")