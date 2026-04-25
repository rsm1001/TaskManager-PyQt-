"""
Task Manager - 数据库模型
使用 SQLAlchemy ORM 定义数据模型
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

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


class TodoTask(BaseModel):
    """待办事项模型"""
    __tablename__ = 'todo_tasks'
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    deadline = Column(String(20))  # YYYY-MM-DD格式
    urgency_score = Column(Integer, default=0)
    category = Column(String(50), default="todo")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"工作,紧急,项目A"


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
        print("已添加 daily_tasks.tags 字段")
    
    # 检查并添加 todo_tasks.tags 字段
    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'tags' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
        print("已添加 todo_tasks.tags 字段")
    
    # 检查并添加 entertainment_tasks.tags 字段
    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'tags' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
        print("已添加 entertainment_tasks.tags 字段")


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
    print("数据库初始化完成")