"""
Task Manager - JSON导入导出模块
将原来的JSON导入导出功能从data_manager.py中分离出来以实现解耦
"""
import json
import uuid
import logging
from datetime import datetime, date
from models.model import DailyTask, TodoTask, EntertainmentTask, Config, TimePeriod

logger = logging.getLogger(__name__)


class JsonExportImportHandler:
    """JSON导入导出处理器"""

    def __init__(self, session, shortcut_manager=None):
        self.session = session
        self.shortcut_manager = shortcut_manager

    def _snapshot_shortcut_database(self):
        """Snapshot rows so a cross-connection import can be restored on failure."""
        if not self.shortcut_manager:
            return None
        conn = self.shortcut_manager._conn
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        snapshot = {}
        for table in tables:
            columns = [
                row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            snapshot[table] = (columns, rows)
        return snapshot

    def _restore_shortcut_database(self, snapshot):
        """Restore a snapshot after an import failed across DB connections."""
        if not snapshot or not self.shortcut_manager:
            return
        conn = self.shortcut_manager._conn
        self.session.rollback()
        conn.rollback()
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            for table in snapshot:
                conn.execute(f"DELETE FROM {table}")
            for table, (columns, rows) in snapshot.items():
                if not rows:
                    continue
                placeholders = ",".join("?" for _ in columns)
                column_sql = ",".join(columns)
                conn.executemany(
                    f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                    rows,
                )
            conn.commit()
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        self.session.expire_all()

    @staticmethod
    def _validate_import_shape(data):
        """Validate conversions that can otherwise fail after destructive work."""
        for period in data.get("time_periods", []):
            int(period.get("order_index", 0) or 0)
        for shortcut in data.get("shortcuts", []):
            int(shortcut.get("order_index", 0) or 0)

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        """导出数据到JSON文件"""
        try:
            data = {
                "daily": [],
                "todo": [],
                "entertainment": [],
                "shortcuts": [],
                "history": [],
                "config": {},
                "time_periods": [],
            }

            # 导出时段
            for period in self.session.query(TimePeriod).all():
                data["time_periods"].append({
                    "id": period.id,
                    "name": period.name,
                    "start_time": period.start_time or "",
                    "end_time": period.end_time or "",
                    "order_index": period.order_index or 0,
                    "color": period.color or "",
                    "created_at": period.created_at.strftime("%Y-%m-%d") if period.created_at else "",
                    "updated_at": period.updated_at.strftime("%Y-%m-%d") if period.updated_at else "",
                })

            # 导出每日任务
            for task in self.session.query(DailyTask).all():
                data["daily"].append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description or "",
                    "completed": task.completed,
                    "created_at": task.created_at.strftime("%Y-%m-%d"),
                    "category": task.category,
                    "week_day": task.week_day or "",
                    "status": task.status or "pending",
                    "tags": task.tags or "",
                    "priority": getattr(task, 'priority', 'normal'),
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]',
                    "estimated_duration": getattr(task, 'estimated_duration', 0) or 0,
                    "time_period_id": getattr(task, 'time_period_id', None) or "",
                })

            # 导出待办事项
            for task in self.session.query(TodoTask).all():
                data["todo"].append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description or "",
                    "completed": task.completed,
                    "created_at": task.created_at.strftime("%Y-%m-%d"),
                    "deadline": task.deadline or "",
                    "urgency_score": task.urgency_score,
                    "category": task.category,
                    "status": task.status or "pending",
                    "tags": task.tags or "",
                    "priority": getattr(task, 'priority', 'normal'),
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]',
                    "estimated_duration": getattr(task, 'estimated_duration', 0) or 0,
                    "time_period_id": getattr(task, 'time_period_id', None) or "",
                })

            # 导出娱乐任务
            for task in self.session.query(EntertainmentTask).all():
                data["entertainment"].append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description or "",
                    "completed": task.completed,
                    "created_at": task.created_at.strftime("%Y-%m-%d"),
                    "fun_category": task.fun_category,
                    "category": task.category,
                    "status": task.status or "pending",
                    "tags": task.tags or "",
                    "priority": getattr(task, 'priority', 'normal'),
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]',
                    "estimated_duration": getattr(task, 'estimated_duration', 0) or 0,
                    "time_period_id": getattr(task, 'time_period_id', None) or "",
                })

            # 导出快捷入口
            if self.shortcut_manager:
                for row in self.shortcut_manager._conn.execute(
                    "SELECT id, title, shortcut_path, action_type, category, tags, parent_id, order_index, created_at, updated_at FROM shortcut_entries"
                ).fetchall():
                    data["shortcuts"].append({
                        "id": row[0],
                        "title": row[1],
                        "shortcut_path": row[2] or "",
                        "action_type": row[3] or "open",
                        "category": row[4] or "todo",
                        "tags": row[5] or "",
                        "parent_id": row[6],
                        "order_index": row[7] or 0,
                        "created_at": row[8] or "",
                        "updated_at": row[9] or "",
                    })

                # 导出历史记录
                for row in self.shortcut_manager._conn.execute(
                    "SELECT id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned FROM shortcut_history"
                ).fetchall():
                    data["history"].append({
                        "id": row[0],
                        "shortcut_id": row[1],
                        "shortcut_title": row[2] or "",
                        "shortcut_path": row[3] or "",
                        "action_type": row[4] or "open",
                        "opened_at": row[5] or "",
                        "is_pinned": row[6],
                    })

            # 导出配置
            configs = self.session.query(Config).all()
            for config in configs:
                data["config"][config.key] = config.value
            
            # 写入JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"导出JSON失败: {str(e)}", exc_info=True)
            return False

    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        """从JSON文件导入数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 清空现有数据
            self._validate_import_shape(data)
            snapshot = self._snapshot_shortcut_database()

            self.session.query(DailyTask).delete()
            self.session.query(TodoTask).delete()
            self.session.query(EntertainmentTask).delete()
            self.session.query(TimePeriod).delete()
            self.session.query(Config).delete()

            # Release the ORM write lock only when a second sqlite connection
            # is going to be used for shortcut data. Without that connection,
            # the ORM transaction remains rollback-safe until the final commit.
            if self.shortcut_manager:
                self.session.commit()

            # JSON import is a full replacement. Git workspace metadata is not
            # part of the portable shortcut export, so retaining it could bind
            # a reused shortcut ID to an unrelated imported repository path.
            if self.shortcut_manager:
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_agent_workspaces")
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_repository_profiles")
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_entries")
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_history")
                self.shortcut_manager._conn.commit()

            # 1. 先导入时段，构建旧 id -> 新 id 的映射（保持任务引用一致）
            old_period_id_to_new = {}
            for period_data in data.get("time_periods", []):
                created_at_str = period_data.get("created_at", "")
                try:
                    created_at = datetime.strptime(created_at_str, "%Y-%m-%d") if created_at_str else datetime.now()
                except ValueError:
                    created_at = datetime.now()
                period = TimePeriod(
                    id=period_data.get("id") or str(uuid.uuid4()),
                    name=period_data.get("name", ""),
                    start_time=period_data.get("start_time", "") or "",
                    end_time=period_data.get("end_time", "") or "",
                    order_index=int(period_data.get("order_index", 0) or 0),
                    color=period_data.get("color", "") or "",
                    created_at=created_at,
                )
                self.session.add(period)
                old_period_id_to_new[period.id] = period.id
            self.session.flush()

            def _resolve_period_id(value):
                """根据导入数据还原 time_period_id；旧 id 找不到则置空"""
                if not value:
                    return None
                return old_period_id_to_new.get(value, None)

            # 导入每日任务
            if "daily" in data:
                for task_data in data["daily"]:
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()

                    task = DailyTask(
                        id=task_data.get("id", str(uuid.uuid4())),
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        week_day=task_data.get("week_day", ""),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]"),
                        estimated_duration=task_data.get("estimated_duration", 0) or 0,
                        time_period_id=_resolve_period_id(task_data.get("time_period_id")),
                    )
                    self.session.add(task)

            # 导入待办事项
            if "todo" in data:
                for task_data in data["todo"]:
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()

                    task = TodoTask(
                        id=task_data.get("id", str(uuid.uuid4())),
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        deadline=task_data.get("deadline", ""),
                        urgency_score=task_data.get("urgency_score", 0),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]"),
                        estimated_duration=task_data.get("estimated_duration", 0) or 0,
                        time_period_id=_resolve_period_id(task_data.get("time_period_id")),
                    )
                    self.session.add(task)

            # 导入娱乐任务
            if "entertainment" in data:
                for task_data in data["entertainment"]:
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()

                    task = EntertainmentTask(
                        id=task_data.get("id", str(uuid.uuid4())),
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        fun_category=task_data.get("fun_category", "general"),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]"),
                        estimated_duration=task_data.get("estimated_duration", 0) or 0,
                        time_period_id=_resolve_period_id(task_data.get("time_period_id")),
                    )
                    self.session.add(task)

            # 导入快捷入口
            if "shortcuts" in data and self.shortcut_manager:
                shortcut_rows = list(data.get("shortcuts", []))
                known_ids = {item.get("id") for item in shortcut_rows if item.get("id")}
                root_rows = [
                    item for item in shortcut_rows
                    if item.get("parent_id") not in known_ids
                ]
                child_rows = [
                    item for item in shortcut_rows
                    if item.get("parent_id") in known_ids
                ]
                ordered_rows = root_rows + child_rows
                assigned_ids = {}
                root_ids = set()
                for sc_data in ordered_rows:
                    original_id = sc_data.get("id") or str(uuid.uuid4())
                    entry_id = original_id
                    if entry_id in assigned_ids.values():
                        entry_id = str(uuid.uuid4())
                    raw_parent_id = sc_data.get("parent_id")
                    parent_id = assigned_ids.get(raw_parent_id)
                    if parent_id not in root_ids:
                        parent_id = None
                    self.shortcut_manager._conn.execute(
                        "INSERT INTO shortcut_entries (id, title, shortcut_path, action_type, category, tags, parent_id, order_index, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            entry_id,
                            sc_data.get("title", ""),
                            sc_data.get("shortcut_path", ""),
                            sc_data.get("action_type", "open"),
                            sc_data.get("category", "todo"),
                            sc_data.get("tags", ""),
                            parent_id,
                            sc_data.get("order_index", 0) or 0,
                            sc_data.get("created_at", datetime.now().isoformat()),
                            sc_data.get("updated_at", datetime.now().isoformat()),
                        ),
                    )
                    assigned_ids[original_id] = entry_id
                    if parent_id is None:
                        root_ids.add(entry_id)

                for hist_data in data.get("history", []):
                    self.shortcut_manager._conn.execute(
                        "INSERT INTO shortcut_history (id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            hist_data.get("id", str(uuid.uuid4())),
                            hist_data.get("shortcut_id", ""),
                            hist_data.get("shortcut_title", ""),
                            hist_data.get("shortcut_path", ""),
                            hist_data.get("action_type", "open"),
                            hist_data.get("opened_at", datetime.now().isoformat()),
                            hist_data.get("is_pinned", 0),
                        )
                    )
                self.shortcut_manager._conn.commit()

            # 导入配置
            if "config" in data:
                for key, value in data["config"].items():
                    config = Config(key=key, value=value)
                    self.session.add(config)
            
            self.session.commit()
            return True
        except FileNotFoundError:
            logger.warning(f"文件未找到: {filepath}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"JSON格式错误: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"JSON import failed: {str(e)}", exc_info=True)
            self.session.rollback()
            try:
                self._restore_shortcut_database(locals().get("snapshot"))
            except Exception:
                logger.error("Failed to restore the pre-import database snapshot", exc_info=True)
            return False
