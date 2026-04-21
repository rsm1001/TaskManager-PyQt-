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


class EntertainmentTask(BaseModel):
    """娱乐任务模型"""
    __tablename__ = 'entertainment_tasks'
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    fun_category = Column(String(50), default="general")
    category = Column(String(50), default="entertainment")
    status = Column(String(20), default="pending")  # pending, completed, abandoned


class Config(BaseModel):
    """配置模型"""
    __tablename__ = 'configs'
    
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)


# 数据库连接和会话管理
def init_db(db_path: str = "taskmanager.db"):
    """初始化数据库"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


# 如果直接运行此文件，创建数据库
if __name__ == "__main__":
    engine, Session = init_db()
    print("数据库初始化完成")