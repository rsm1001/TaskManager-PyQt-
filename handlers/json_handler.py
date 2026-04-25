"""
Task Manager - JSON导入导出模块
将原来的JSON导入导出功能从data_manager.py中分离出来以实现解耦
"""
import json
import uuid
from datetime import datetime, date
from models.model import DailyTask, TodoTask, EntertainmentTask, Config


class JsonExportImportHandler:
    """JSON导入导出处理器"""
    
    def __init__(self, session):
        self.session = session

    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        """导出数据到JSON文件"""
        try:
            data = {
                "daily": [],
                "todo": [],
                "entertainment": [],
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
                    "tags": task.tags or ""
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
                    "tags": task.tags or ""
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
                    "tags": task.tags or ""
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
            print(f"导出JSON失败: {str(e)}")
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
                        tags=task_data.get("tags", "")
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
                        tags=task_data.get("tags", "")
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
                        tags=task_data.get("tags", "")
                    )
                    self.session.add(task)
            
            # 导入配置
            if "config" in data:
                for key, value in data["config"].items():
                    config = Config(key=key, value=value)
                    self.session.add(config)
            
            self.session.commit()
            return True
        except FileNotFoundError:
            print(f"文件未找到: {filepath}")
            return False
        except json.JSONDecodeError as e:
            print(f"JSON格式错误: {str(e)}")
            return False
        except Exception as e:
            print(f"导入JSON失败: {str(e)}")
            self.session.rollback()
            return False