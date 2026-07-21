"""
Task Manager - 数据库模型
使用 SQLAlchemy ORM 定义数据模型
"""

import logging
from typing import Any, Optional, Tuple
from datetime import datetime
import uuid

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import Engine
from typing import Any

logger = logging.getLogger(__name__)

# SQLAlchemy declarative_base() 的返回值 mypy 无法识别为类型，用 Any 绕过
Base: Any = declarative_base()


class BaseModel(Base):
    """基础模型类

    Attributes:
        id: UUID 主键
        created_at: 创建时间戳
        updated_at: 更新时间戳
    """
    __abstract__ = True

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TimePeriod(BaseModel):
    """时段模型

    一个时段描述"某段时间归属"（如 早晨 / 上午 / 下午 / 晚上 / 深夜 等）。
    任务通过 time_period_id 外键引用本表，因此重命名一个时段后，
    全部任务的显示文本会跟随更新。

    Attributes:
        name: 时段名称（界面显示文本）
        start_time: 起始时间（HH:MM 字符串，可空）
        end_time: 结束时间（HH:MM 字符串，可空）
        order_index: 列表排序权重，越小越靠前
        color: 单元格底色（可空）
    """
    __tablename__ = 'time_periods'

    name = Column(String(50), nullable=False, unique=True)
    start_time = Column(String(10), default='')
    end_time = Column(String(10), default='')
    order_index = Column(Integer, default=0)
    color = Column(String(20), default='')


class DailyTask(BaseModel):
    """每日任务模型

    Attributes:
        title: 任务标题
        description: 任务描述
        completed: 是否已完成
        week_day: 星期几（如 "Monday"，空表示每天）
        category: 用户分类标签
        status: 状态（pending/completed/abandoned）
        tags: 逗号分隔的标签字符串
        shortcut_path: 快捷入口路径，非空表示快捷入口
        priority: 优先级（urgent/high/normal/low/idle）
        subtasks: 子任务 JSON 字符串
        estimated_duration: 用时预估（分钟）
    """
    __tablename__ = 'daily_tasks'

    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    week_day = Column(String(20))  # 如"Monday", "Tuesday", 或留空表示每天
    category = Column(String(50), default="daily")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"工作,紧急,项目A"
    shortcut_path = Column(String(1000), default="")  # 快捷入口路径，非空表示快捷入口
    priority = Column(String(20), default="normal")  # high, normal, low
    subtasks = Column(Text, default='[]')  # 子任务（检查项）JSON 字符串，list of {id, title, completed}
    estimated_duration = Column(Integer, default=0)  # 用时预估（分钟）
    time_period_id = Column(String(50))  # 时段 ID（外键引用 time_periods.id）


class TodoTask(BaseModel):
    """待办事项模型

    Attributes:
        title: 任务标题
        description: 任务描述
        completed: 是否已完成
        deadline: 截止日期（YYYY-MM-DD）
        urgency_score: 紧急度评分
        category: 用户分类标签
        status: 状态（pending/completed/abandoned）
        tags: 逗号分隔的标签字符串
        shortcut_path: 快捷入口路径
        priority: 优先级
        subtasks: 子任务 JSON 字符串
        estimated_duration: 用时预估（分钟）
    """
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
    priority = Column(String(20), default="normal")  # high, normal, low
    subtasks = Column(Text, default='[]')  # 子任务（检查项）JSON 字符串，list of {id, title, completed}
    estimated_duration = Column(Integer, default=0)  # 用时预估（分钟）
    time_period_id = Column(String(50))  # 时段 ID（外键引用 time_periods.id）


class EntertainmentTask(BaseModel):
    """娱乐任务模型

    Attributes:
        title: 任务标题
        description: 任务描述
        completed: 是否已完成
        fun_category: 娱乐分类（如"游戏"）
        category: 用户分类标签
        status: 状态
        tags: 逗号分隔的标签
        shortcut_path: 快捷入口路径
        priority: 优先级
        subtasks: 子任务 JSON 字符串
        estimated_duration: 用时预估（分钟）
    """
    __tablename__ = 'entertainment_tasks'

    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    fun_category = Column(String(50), default="general")
    category = Column(String(50), default="entertainment")
    status = Column(String(20), default="pending")  # pending, completed, abandoned
    tags = Column(String(500), default="")  # 逗号分隔的标签，如"游戏,周末,多人"
    shortcut_path = Column(String(1000), default="")  # 快捷入口路径，非空表示快捷入口
    priority = Column(String(20), default="normal")  # high, normal, low
    subtasks = Column(Text, default='[]')  # 子任务（检查项）JSON 字符串，list of {id, title, completed}
    estimated_duration = Column(Integer, default=0)  # 用时预估（分钟）
    time_period_id = Column(String(50))  # 时段 ID（外键引用 time_periods.id）


class ItineraryTask(BaseModel):
    """行程任务模型

    用于在主界面的行程面板中按星期和时间规划任务。
    支持从主任务拖拽关联。

    Attributes:
        task_id: 关联的原任务ID（可为空，表示手动创建的行程）
        task_type: 关联的任务类型（daily/todo/entertainment/空）
        day_of_week: 星期几（1-7，1=周一）
        hour: 小时（0-23）
        title: 行程标题
        description: 行程描述
        color: 显示颜色
    """
    __tablename__ = 'itinerary_tasks'

    task_id = Column(String(100), default="")
    task_type = Column(String(20), default="")
    day_of_week = Column(Integer, default=1)
    hour = Column(Integer, default=0)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    color = Column(String(20), default="#3498DB")


class Config(BaseModel):
    """配置模型

    Attributes:
        key: 配置键（唯一）
        value: 配置值
    """
    __tablename__ = 'configs'

    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)


class ShortcutHistory(BaseModel):
    """快捷入口历史记录模型

    Attributes:
        shortcut_id: 关联的快捷入口 ID
        shortcut_title: 快照标题
        shortcut_path: 快照路径
        action_type: 操作类型
        is_pinned: 是否置顶
    """
    __tablename__ = 'shortcut_history'

    shortcut_id = Column(String(100), nullable=False)  # 关联的快捷入口ID
    shortcut_title = Column(String(255), nullable=False, default='')  # 快照标题
    shortcut_path = Column(String(1000), default='')  # 快照路径
    action_type = Column(String(20), default='open')  # 操作类型
    is_pinned = Column(Integer, default=0)  # 是否置顶


def migrate_db(engine: Engine) -> None:
    """数据库迁移：添加新字段

    Args:
        engine: SQLAlchemy Engine 实例
    """
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
    todo_columns_dict = {col['name']: col for col in inspector.get_columns('todo_tasks')}
    if 'urgency_score' in todo_columns_dict and 'INTEGER' in str(todo_columns_dict['urgency_score']['type']).upper():
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

    # 检查并添加 priority 字段
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'priority' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal'"))
            conn.commit()
        logger.info("已添加 daily_tasks.priority 字段")

    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'priority' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal'"))
            conn.commit()
        logger.info("已添加 todo_tasks.priority 字段")

    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'priority' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal'"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.priority 字段")

    # 检查并添加 todo_tasks.subtasks 字段
    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'subtasks' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN subtasks TEXT DEFAULT '[]'"))
            conn.commit()
        logger.info("已添加 todo_tasks.subtasks 字段")

    # 检查并添加 daily_tasks.subtasks 字段
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'subtasks' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN subtasks TEXT DEFAULT '[]'"))
            conn.commit()
        logger.info("已添加 daily_tasks.subtasks 字段")

    # 检查并添加 entertainment_tasks.subtasks 字段
    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'subtasks' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN subtasks TEXT DEFAULT '[]'"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.subtasks 字段")

    # 检查并添加 estimated_duration 字段（用时预估）
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'estimated_duration' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN estimated_duration INTEGER DEFAULT 0"))
            conn.commit()
        logger.info("已添加 daily_tasks.estimated_duration 字段")

    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'estimated_duration' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN estimated_duration INTEGER DEFAULT 0"))
            conn.commit()
        logger.info("已添加 todo_tasks.estimated_duration 字段")

    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'estimated_duration' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN estimated_duration INTEGER DEFAULT 0"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.estimated_duration 字段")

    # 检查并添加 time_period_id 字段（三类任务引用 time_periods.id）
    daily_columns = [col['name'] for col in inspector.get_columns('daily_tasks')]
    if 'time_period_id' not in daily_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE daily_tasks ADD COLUMN time_period_id VARCHAR(50)"))
            conn.commit()
        logger.info("已添加 daily_tasks.time_period_id 字段")

    todo_columns = [col['name'] for col in inspector.get_columns('todo_tasks')]
    if 'time_period_id' not in todo_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE todo_tasks ADD COLUMN time_period_id VARCHAR(50)"))
            conn.commit()
        logger.info("已添加 todo_tasks.time_period_id 字段")

    entertainment_columns = [col['name'] for col in inspector.get_columns('entertainment_tasks')]
    if 'time_period_id' not in entertainment_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE entertainment_tasks ADD COLUMN time_period_id VARCHAR(50)"))
            conn.commit()
        logger.info("已添加 entertainment_tasks.time_period_id 字段")

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
def init_db(
    db_path: str = "taskmanager.db",
    run_migration: bool = False,
) -> Tuple[Engine, sessionmaker]:
    """初始化数据库

    Args:
        db_path: 数据库文件路径，默认为 "taskmanager.db"
        run_migration: 是否执行数据库迁移，默认为 False

    Returns:
        Tuple[Engine, sessionmaker]: (SQLAlchemy引擎, Session工厂)
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