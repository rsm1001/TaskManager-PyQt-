"""
Task Manager - 数据访问和管理类
处理数据库的CRUD操作、JSON导入导出、每日重置等
通过组合子管理器实现模块化架构
"""

from models.model import DailyTask, TodoTask, EntertainmentTask, Config, init_db
from datetime import datetime, date
import json
import uuid
import config.config
import sqlite3
from typing import List, Dict, Any, Optional
from enum import Enum
import config.config
import sqlite3
import os

from managers.todo_task_manager import TodoTaskManager
from managers.entertainment_task_manager import EntertainmentTaskManager
from managers.config_manager import ConfigManager


class TaskType(Enum):
    """任务类型枚举"""
    DAILY = "daily"
    TODO = "todo"
    ENTERTAINMENT = "entertainment"


class DataManager:
    """数据管理器 - 组合子管理器实现模块化"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        self.engine, self.Session = init_db(db_path, run_migration=True)
        self.session = self.Session()

        # 初始化子管理器
        self.todo_manager = TodoTaskManager(self.session)
        self.entertainment_manager = EntertainmentTaskManager(self.session)
        self.config_manager = ConfigManager(self.session)

        # 初始化垃圾桶数据库
        self._init_trash_db()

        # 初始化快捷入口数据库
        self._shortcut_conn = sqlite3.connect(config.config.DATABASE_PATH)
        self._init_shortcut_db()

        # 检查并执行每日重置
        self.check_daily_reset()

    def get_session(self):
        """获取数据库会话"""
        return self.session

    def close_session(self):
        """关闭数据库会话"""
        self.session.close()
        self.close_trash_db()
        self.close_shortcut_db()

    def close_shortcut_db(self):
        """关闭快捷入口数据库连接"""
        if hasattr(self, '_shortcut_conn') and self._shortcut_conn:
            self._shortcut_conn.close()
            self._shortcut_conn = None

    def commit(self):
        """提交更改"""
        self.session.commit()

    def rollback(self):
        """回滚更改"""
        self.session.rollback()

    # ==================== 垃圾桶管理 ====================

    def _init_trash_db(self):
        """初始化垃圾桶数据库"""
        trash_path = config.config.TRASH_DATABASE_PATH
        self.trash_conn = sqlite3.connect(trash_path)
        self.trash_conn.execute('''
            CREATE TABLE IF NOT EXISTS trashed_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                deleted_at TEXT NOT NULL
            )
        ''')
        self.trash_conn.commit()

    def _move_to_trash(self, task_type, task_id, task_data):
        """将任务移入垃圾桶"""
        trash_id = str(uuid.uuid4())
        self.trash_conn.execute(
            'INSERT INTO trashed_tasks (id, task_type, task_id, data_json, deleted_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (trash_id, task_type, task_id, json.dumps(task_data), datetime.now().isoformat())
        )
        self.trash_conn.commit()
        return trash_id

    def get_trashed_tasks(self, task_type=None):
        """获取垃圾桶中的任务列表"""
        if task_type:
            cursor = self.trash_conn.execute(
                'SELECT id, task_type, task_id, data_json, deleted_at '
                'FROM trashed_tasks WHERE task_type = ? ORDER BY deleted_at DESC',
                (task_type,)
            )
        else:
            cursor = self.trash_conn.execute(
                'SELECT id, task_type, task_id, data_json, deleted_at '
                'FROM trashed_tasks ORDER BY deleted_at DESC'
            )
        return cursor.fetchall()

    def restore_trashed_task(self, trash_id):
        """恢复垃圾桶中的任务到主数据库"""
        cursor = self.trash_conn.execute(
            'SELECT task_type, data_json FROM trashed_tasks WHERE id = ?',
            (trash_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        task_type, data_json = row
        data = json.loads(data_json)

        if task_type == 'daily':
            task = DailyTask(
                id=data.get('id', str(uuid.uuid4())),
                title=data.get('title', ''),
                description=data.get('description', ''),
                week_day=data.get('week_day', ''),
                completed=data.get('completed', False),
                status=data.get('status', 'pending'),
                tags=data.get('tags', ''),
                shortcut_path=data.get('shortcut_path', '')
            )
        elif task_type == 'todo':
            task = TodoTask(
                id=data.get('id', str(uuid.uuid4())),
                title=data.get('title', ''),
                description=data.get('description', ''),
                deadline=data.get('deadline', ''),
                completed=data.get('completed', False),
                status=data.get('status', 'pending'),
                tags=data.get('tags', ''),
                shortcut_path=data.get('shortcut_path', '')
            )
        elif task_type == 'shortcut':
            # restore_shortcut 内部会删除 trash 记录，这里只做传递
            return self.restore_shortcut(trash_id)
        elif task_type == 'entertainment':
            task = EntertainmentTask(
                id=data.get('id', str(uuid.uuid4())),
                title=data.get('title', ''),
                description=data.get('description', ''),
                fun_category=data.get('fun_category', 'general'),
                completed=data.get('completed', False),
                status=data.get('status', 'pending'),
                tags=data.get('tags', ''),
                shortcut_path=data.get('shortcut_path', '')
            )
        else:
            return False

        self.session.add(task)
        self.session.commit()
        self.trash_conn.execute('DELETE FROM trashed_tasks WHERE id = ?', (trash_id,))
        self.trash_conn.commit()
        return True

    def purge_trashed_task(self, trash_id):
        """彻底删除垃圾桶中的任务"""
        self.trash_conn.execute('DELETE FROM trashed_tasks WHERE id = ?', (trash_id,))
        self.trash_conn.commit()

    def purge_all_trashed(self, task_type=None):
        """清空垃圾桶"""
        if task_type:
            self.trash_conn.execute('DELETE FROM trashed_tasks WHERE task_type = ?', (task_type,))
        else:
            self.trash_conn.execute('DELETE FROM trashed_tasks')
        self.trash_conn.commit()

    def close_trash_db(self):
        """关闭垃圾桶数据库连接"""
        if hasattr(self, 'trash_conn') and self.trash_conn:
            self.trash_conn.close()
            self.trash_conn = None

    def _enforce_task_limit(self, task_type, task_model):
        """检查并执行任务数量上限，超出时将最老任务移入垃圾桶"""
        limit = config.config.TASK_CACHE_LIMIT
        total = self.session.query(task_model).count()
        if total <= limit:
            return

        oldest = self.session.query(task_model).order_by(task_model.created_at).first()
        if not oldest:
            return

        # 获取序列化后的任务数据
        if task_type == 'daily':
            task_data = {
                'id': oldest.id, 'title': oldest.title,
                'description': oldest.description or '', 'week_day': oldest.week_day or '',
                'completed': oldest.completed, 'status': oldest.status,
                'tags': oldest.tags or '',
                'shortcut_path': oldest.shortcut_path or '',
                'created_at': oldest.created_at.isoformat() if oldest.created_at else '',
                'updated_at': oldest.updated_at.isoformat() if oldest.updated_at else '',
            }
        elif task_type == 'todo':
            task_data = self.todo_manager.to_dict(oldest)
        elif task_type == 'entertainment':
            task_data = self.entertainment_manager.to_dict(oldest)
        else:
            return

        self._move_to_trash(task_type, oldest.id, task_data)
        self.session.delete(oldest)
        self.session.commit()

    # ==================== DailyTask 相关方法 ====================

    def get_daily_tasks(self, weekday: Optional[str] = None,
                        status: Optional[str] = None, tag: Optional[str] = None) -> List[DailyTask]:
        """获取每日任务"""
        query = self.session.query(DailyTask)

        if weekday and weekday != "all":
            if weekday == "daily":
                query = query.filter((DailyTask.week_day == "") | (DailyTask.week_day.is_(None)))
            else:
                query = query.filter(
                    (DailyTask.week_day == weekday) |
                    (DailyTask.week_day == "") |
                    (DailyTask.week_day.is_(None))
                )

        if status and status != "all":
            query = query.filter(DailyTask.status == status)

        if tag:
            query = query.filter(DailyTask.tags.contains(tag))

        return query.order_by(DailyTask.week_day, DailyTask.title).all()

    def get_daily_task_by_id(self, task_id: str) -> Optional[DailyTask]:
        """根据ID获取每日任务"""
        return self.session.query(DailyTask).filter(DailyTask.id == task_id).first()

    def create_daily_task(self, title: str, description: str = "", week_day: str = "",
                          completed: bool = False, status: str = "pending",
                          tags: str = "", shortcut_path: str = "") -> DailyTask:
        """创建每日任务"""
        task = DailyTask(
            title=title, description=description, week_day=week_day,
            completed=completed, status=status, tags=tags, shortcut_path=shortcut_path
        )
        self.session.add(task)
        self.session.commit()
        self._enforce_task_limit('daily', DailyTask)
        return task

    def update_daily_task(self, task_id: str, **kwargs) -> bool:
        """更新每日任务"""
        task = self.get_daily_task_by_id(task_id)
        if not task:
            return False

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        if 'status' in kwargs:
            task.completed = (kwargs['status'] == 'completed')
        elif 'completed' in kwargs:
            task.status = 'completed' if kwargs['completed'] else 'pending'

        self.session.commit()
        return True

    def delete_daily_task(self, task_id: str) -> bool:
        """删除每日任务（移入垃圾桶）"""
        task = self.get_daily_task_by_id(task_id)
        if not task:
            return False

        task_data = {
            'id': task.id, 'title': task.title,
            'description': task.description or '', 'week_day': task.week_day or '',
            'completed': task.completed, 'status': task.status,
            'tags': task.tags or '',
            'shortcut_path': task.shortcut_path or '',
            'created_at': task.created_at.isoformat() if task.created_at else '',
            'updated_at': task.updated_at.isoformat() if task.updated_at else '',
        }
        self._move_to_trash('daily', task_id, task_data)
        self.session.delete(task)
        self.session.commit()
        return True

    def toggle_daily_task_completion(self, task_id: str) -> bool:
        """切换每日任务完成状态"""
        task = self.get_daily_task_by_id(task_id)
        if not task:
            return False

        if task.status == "pending":
            task.status = "completed"
            task.completed = True
        elif task.status == "completed":
            task.status = "abandoned"
            task.completed = False
        else:
            task.status = "pending"
            task.completed = False

        self.session.commit()
        return True

    # ==================== TodoTask 委托 ====================

    def get_todo_tasks(self, status: Optional[str] = None, tag: Optional[str] = None) -> List[TodoTask]:
        return self.todo_manager.get_tasks(status=status, tag=tag)

    def get_todo_task_by_id(self, task_id: str) -> Optional[TodoTask]:
        return self.todo_manager.get_by_id(task_id)

    def create_todo_task(self, title: str, description: str = "", deadline: str = "",
                         completed: bool = False, status: str = "pending",
                         tags: str = "", shortcut_path: str = "") -> TodoTask:
        task = self.todo_manager.create(title, description, deadline, completed, status, tags, shortcut_path=shortcut_path)
        self._enforce_task_limit('todo', TodoTask)
        return task

    def update_todo_task(self, task_id: str, **kwargs) -> bool:
        return self.todo_manager.update(task_id, **kwargs)

    def delete_todo_task(self, task_id: str) -> bool:
        task = self.todo_manager.get_by_id(task_id)
        if not task:
            return False
        task_data = self.todo_manager.to_dict(task)
        self._move_to_trash('todo', task_id, task_data)
        self.session.delete(task)
        self.session.commit()
        return True

    def toggle_todo_task_completion(self, task_id: str) -> bool:
        return self.todo_manager.toggle_completion(task_id)

    # ==================== EntertainmentTask 委托 ====================

    def get_entertainment_tasks(self, status: Optional[str] = None,
                                tag: Optional[str] = None) -> List[EntertainmentTask]:
        return self.entertainment_manager.get_tasks(status=status, tag=tag)

    def get_entertainment_task_by_id(self, task_id: str) -> Optional[EntertainmentTask]:
        return self.entertainment_manager.get_by_id(task_id)

    def create_entertainment_task(self, title: str, description: str = "",
                                      fun_category: str = "general", completed: bool = False,
                                      status: str = "pending", tags: str = "",
                                      shortcut_path: str = "") -> EntertainmentTask:
        task = self.entertainment_manager.create(title, description, fun_category,
                                                  completed, status, tags, shortcut_path=shortcut_path)
        self._enforce_task_limit('entertainment', EntertainmentTask)
        return task

    def update_entertainment_task(self, task_id: str, **kwargs) -> bool:
        return self.entertainment_manager.update(task_id, **kwargs)

    def delete_entertainment_task(self, task_id: str) -> bool:
        task = self.entertainment_manager.get_by_id(task_id)
        if not task:
            return False
        task_data = self.entertainment_manager.to_dict(task)
        self._move_to_trash('entertainment', task_id, task_data)
        self.session.delete(task)
        self.session.commit()
        return True

    def toggle_entertainment_task_completion(self, task_id: str) -> bool:
        return self.entertainment_manager.toggle_completion(task_id)

    # ==================== 快捷入口相关方法 ====================

    def _init_shortcut_db(self):
        """确保 shortcut_entries 表存在"""
        self._shortcut_conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                shortcut_path TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'todo',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._shortcut_conn.commit()

    def get_all_shortcuts(self) -> list:
        """获取所有快捷入口"""
        cursor = self._shortcut_conn.execute(
            "SELECT id, title, shortcut_path, category, created_at FROM shortcut_entries ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        shortcuts = []
        for row in rows:
            sid, title, path, category, created = row
            shortcuts.append({
                'id': sid,
                'task_id': sid,
                'task_type': category,
                'title': title,
                'shortcut_path': path or '',
                'created_at': created or '-'
            })
        return shortcuts

    def create_shortcut(self, task_type: str, title: str, shortcut_path: str) -> bool:
        """创建快捷入口"""
        now = datetime.now().isoformat()
        sid = str(uuid.uuid4())
        self._shortcut_conn.execute(
            "INSERT INTO shortcut_entries (id, title, shortcut_path, category, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, title, shortcut_path, task_type, now, now)
        )
        self._shortcut_conn.commit()
        return True

    def update_shortcut(self, shortcut_id: str, title: str = None, shortcut_path: str = None) -> bool:
        """更新快捷入口"""
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if shortcut_path is not None:
            updates.append("shortcut_path = ?")
            params.append(shortcut_path)
        if not updates:
            return False
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(shortcut_id)
        self._shortcut_conn.execute(
            f"UPDATE shortcut_entries SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self._shortcut_conn.commit()
        return True

    def delete_shortcut(self, shortcut_id: str) -> bool:
        """删除快捷入口（移入垃圾桶）"""
        cursor = self._shortcut_conn.execute(
            "SELECT id, title, shortcut_path, category, created_at FROM shortcut_entries WHERE id = ?",
            (shortcut_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        now = datetime.now().isoformat()
        trash_id = str(uuid.uuid4())
        data = {
            'id': row[0],
            'title': row[1],
            'shortcut_path': row[2] or '',
            'category': row[3],
            'created_at': row[4],
        }
        # 移入垃圾桶
        self.trash_conn.execute(
            'INSERT INTO trashed_tasks (id, task_type, task_id, data_json, deleted_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (trash_id, 'shortcut', shortcut_id, json.dumps(data), now)
        )
        self.trash_conn.commit()
        # 从快捷入口表删除
        self._shortcut_conn.execute("DELETE FROM shortcut_entries WHERE id = ?", (shortcut_id,))
        self._shortcut_conn.commit()
        return True

    def restore_shortcut(self, trash_id: str) -> bool:
        """恢复快捷入口（从垃圾桶恢复到 shortcut_entries）"""
        cursor = self.trash_conn.execute(
            'SELECT task_type, data_json FROM trashed_tasks WHERE id = ?',
            (trash_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        task_type, data_json = row
        data = json.loads(data_json)

        now = datetime.now().isoformat()
        self._shortcut_conn.execute(
            "INSERT INTO shortcut_entries (id, title, shortcut_path, category, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data.get('id', str(uuid.uuid4())),
                data.get('title', ''),
                data.get('shortcut_path', ''),
                data.get('category', 'todo'),
                data.get('created_at', now),
                now
            )
        )
        self._shortcut_conn.commit()
        self.trash_conn.execute('DELETE FROM trashed_tasks WHERE id = ?', (trash_id,))
        self.trash_conn.commit()
        return True

    # ==================== 紧急度（委托） ====================

    def calculate_urgency_for_task(self, task: TodoTask):
        self.todo_manager._calculate_urgency(task)

    def recalculate_all_urgency(self):
        self.todo_manager.recalculate_all_urgency()

    # ==================== 配置管理（委托） ====================

    def get_config(self, key: str, default: str = "") -> str:
        return self.config_manager.get(key, default)

    def set_config(self, key: str, value: str):
        self.config_manager.set(key, value)

    # ==================== JSON 导入导出 ====================

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self.session)
        return handler.export_to_json(filepath)

    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self.session)
        return handler.import_from_json(filepath)

    # ==================== 每日重置 ====================

    def check_daily_reset(self):
        """检查并执行每日重置"""
        last_reset = self.get_config("last_reset_date", "")
        try:
            last_reset_date = datetime.strptime(last_reset, "%Y-%m-%d").date() if last_reset else date.today()
            today = date.today()
            if last_reset_date < today:
                self.reset_daily_tasks()
                self.set_config("last_reset_date", today.strftime("%Y-%m-%d"))
        except ValueError:
            self.reset_daily_tasks()
            self.set_config("last_reset_date", date.today().strftime("%Y-%m-%d"))

    def reset_daily_tasks(self):
        """重置每日任务的完成状态"""
        today_weekday = datetime.now().weekday()
        weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        today_name = weekday_names[today_weekday] if 0 <= today_weekday <= 6 else ''

        all_tasks = self.session.query(DailyTask).all()
        for task in all_tasks:
            if not task.week_day or task.week_day == today_name:
                if task.status == 'completed':
                    task.status = 'pending'
                    task.completed = False
        self.session.commit()

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        daily_tasks = self.get_daily_tasks()
        todo_tasks = self.get_todo_tasks()
        entertainment_tasks = self.get_entertainment_tasks()

        daily_completed = sum(1 for t in daily_tasks if t.completed)
        todo_completed = sum(1 for t in todo_tasks if t.completed)
        todo_expired = sum(1 for t in todo_tasks if self.todo_manager.is_expired(t))
        entertainment_completed = sum(1 for t in entertainment_tasks if t.completed)

        return {
            "daily": {"total": len(daily_tasks), "completed": daily_completed},
            "todo": {"total": len(todo_tasks), "completed": todo_completed, "expired": todo_expired},
            "entertainment": {"total": len(entertainment_tasks), "completed": entertainment_completed}
        }

    # ==================== 标签管理 ====================

    def get_all_tags(self) -> List[str]:
        """获取所有全局标签"""
        tags_str = self.get_config("global_tags", "")
        if not tags_str:
            return []
        return [t.strip() for t in tags_str.split(',') if t.strip()]

    def _save_global_tags(self, tags: List[str]):
        """保存全局标签列表"""
        tags_str = ','.join(sorted(set(tags)))
        self.set_config("global_tags", tags_str)

    def add_tag(self, tag: str) -> bool:
        """添加全局标签
        
        Args:
            tag: 标签名称
            
        Returns:
            bool: 是否添加成功（标签已存在时也返回True）
        """
        tag = tag.strip()
        if not tag:
            return False
        tags = self.get_all_tags()
        if tag not in tags:
            tags.append(tag)
            self._save_global_tags(tags)
        return True

    def delete_tag(self, tag: str) -> bool:
        """删除全局标签（仅当标签未被任何任务使用时）
        
        Args:
            tag: 标签名称
            
        Returns:
            bool: 是否删除成功
        """
        tag = tag.strip()
        if not tag:
            return False
        
        # 检查标签是否被任何任务使用
        daily_tasks = self.get_daily_tasks()
        for task in daily_tasks:
            if task.tags:
                task_tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                if tag in task_tag_list:
                    return False
        
        todo_tasks = self.get_todo_tasks()
        for task in todo_tasks:
            if task.tags:
                task_tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                if tag in task_tag_list:
                    return False
        
        entertainment_tasks = self.get_entertainment_tasks()
        for task in entertainment_tasks:
            if task.tags:
                task_tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                if tag in task_tag_list:
                    return False
        
        # 标签未被使用，可以删除
        tags = self.get_all_tags()
        if tag in tags:
            tags.remove(tag)
            self._save_global_tags(tags)
            return True
        return False

    def get_or_create_tag(self, tag: str) -> bool:
        """获取或创建标签（如果不存在则创建）"""
        return self.add_tag(tag)


if __name__ == "__main__":
    dm = DataManager()
    print("数据管理器初始化成功")
    print(f"每日任务数量: {len(dm.get_daily_tasks())}")
    print(f"待办事项数量: {len(dm.get_todo_tasks())}")
    print(f"娱乐任务数量: {len(dm.get_entertainment_tasks())}")
    dm.close_session()
