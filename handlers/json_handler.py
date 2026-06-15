"""
Task Manager - JSON导入导出模块
将原来的JSON导入导出功能从data_manager.py中分离出来以实现解耦
"""
import json
import uuid
import logging
from datetime import datetime, date
from models.model import DailyTask, TodoTask, EntertainmentTask, Config

logger = logging.getLogger(__name__)


class JsonExportImportHandler:
    """JSON导入导出处理器"""

    def __init__(self, session, shortcut_manager=None):
        self.session = session
        self.shortcut_manager = shortcut_manager

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        """导出数据到JSON文件"""
        try:
            data = {
                "daily": [],
                "todo": [],
                "entertainment": [],
                "shortcuts": [],
                "history": [],
                "config": {}
            }
            
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
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]'
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
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]'
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
                    "subtasks": getattr(task, 'subtasks', '[]') or '[]'
                })

            # 导出快捷入口
            if self.shortcut_manager:
                for row in self.shortcut_manager._conn.execute(
                    "SELECT id, title, shortcut_path, action_type, category, tags, created_at, updated_at FROM shortcut_entries"
                ).fetchall():
                    data["shortcuts"].append({
                        "id": row[0],
                        "title": row[1],
                        "shortcut_path": row[2] or "",
                        "action_type": row[3] or "open",
                        "category": row[4] or "todo",
                        "tags": row[5] or "",
                        "created_at": row[6] or "",
                        "updated_at": row[7] or "",
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
            self.session.query(DailyTask).delete()
            self.session.query(TodoTask).delete()
            self.session.query(EntertainmentTask).delete()
            self.session.query(Config).delete()

            # 清空快捷入口和历史记录（使用原生连接）
            if self.shortcut_manager:
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_entries")
                self.shortcut_manager._conn.execute("DELETE FROM shortcut_history")
                self.shortcut_manager._conn.commit()
            
            # 导入每日任务
            if "daily" in data:
                for task_data in data["daily"]:
                    # 使用合理的默认值
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()
                        
                    task = DailyTask(
                        id=task_data.get("id", str(uuid.uuid4())),  # 生成新ID以防冲突
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        week_day=task_data.get("week_day", ""),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]")
                    )
                    self.session.add(task)

            # 导入待办事项
            if "todo" in data:
                for task_data in data["todo"]:
                    # 使用合理的默认值
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()

                    task = TodoTask(
                        id=task_data.get("id", str(uuid.uuid4())),  # 生成新ID以防冲突
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        deadline=task_data.get("deadline", ""),
                        urgency_score=task_data.get("urgency_score", 0),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]")
                    )
                    self.session.add(task)

            # 导入娱乐任务
            if "entertainment" in data:
                for task_data in data["entertainment"]:
                    # 使用合理的默认值
                    created_at_str = task_data.get("created_at", date.today().strftime("%Y-%m-%d"))
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                    except ValueError:
                        created_at = datetime.now()

                    task = EntertainmentTask(
                        id=task_data.get("id", str(uuid.uuid4())),  # 生成新ID以防冲突
                        title=task_data.get("title", ""),
                        description=task_data.get("description", ""),
                        completed=task_data.get("completed", False),
                        fun_category=task_data.get("fun_category", "general"),
                        created_at=created_at,
                        status=task_data.get("status", "pending"),
                        tags=task_data.get("tags", ""),
                        priority=task_data.get("priority", "normal"),
                        subtasks=task_data.get("subtasks", "[]")
                    )
                    self.session.add(task)

            # 导入快捷入口
            if "shortcuts" in data and self.shortcut_manager:
                for sc_data in data["shortcuts"]:
                    self.shortcut_manager._conn.execute(
                        "INSERT INTO shortcut_entries (id, title, shortcut_path, action_type, category, tags, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            sc_data.get("id", str(uuid.uuid4())),
                            sc_data.get("title", ""),
                            sc_data.get("shortcut_path", ""),
                            sc_data.get("action_type", "open"),
                            sc_data.get("category", "todo"),
                            sc_data.get("tags", ""),
                            sc_data.get("created_at", datetime.now().isoformat()),
                            sc_data.get("updated_at", datetime.now().isoformat()),
                        )
                    )

                # 导入历史记录
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
            logger.error(f"导入JSON失败: {str(e)}", exc_info=True)
            self.session.rollback()
            return False