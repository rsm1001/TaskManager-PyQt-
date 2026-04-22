"""
Task Manager - 数据访问和管理类
处理数据库的CRUD操作以及JSON导入导出功能
"""

from models.model import DailyTask, TodoTask, EntertainmentTask, Config, init_db
from datetime import datetime, date
import json
import uuid
from typing import List, Dict, Any, Optional
from enum import Enum
import config.config


class TaskType(Enum):
    """任务类型枚举"""
    DAILY = "daily"
    TODO = "todo"
    ENTERTAINMENT = "entertainment"


class DataManager:
    """数据管理器 - 处理数据库操作和JSON导入导出"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        self.engine, self.Session = init_db(db_path)
        self.session = self.Session()
        
        # 检查并执行每日重置
        self.check_daily_reset()
    
    def get_session(self):
        """获取数据库会话"""
        return self.session
    
    def close_session(self):
        """关闭数据库会话"""
        self.session.close()
    
    def commit(self):
        """提交更改"""
        self.session.commit()
    
    def rollback(self):
        """回滚更改"""
        self.session.rollback()
    
    # DailyTask 相关方法
    def get_daily_tasks(self, weekday: Optional[str] = None, status: Optional[str] = None) -> List[DailyTask]:
        """获取每日任务"""
        query = self.session.query(DailyTask)
        
        # 按星期筛选
        if weekday and weekday != "all":
            if weekday == "daily":  # 表示每天的任务
                query = query.filter((DailyTask.week_day == "") | (DailyTask.week_day.is_(None)))
            else:
                # 如果选择了特定星期几，显示该星期几的任务和每天都有的任务
                query = query.filter(
                    (DailyTask.week_day == weekday) | 
                    (DailyTask.week_day == "") | 
                    (DailyTask.week_day.is_(None))
                )
        
        # 按状态筛选
        if status and status != "all":
            if status == "completed":
                query = query.filter(DailyTask.status == "completed")
            elif status == "pending":
                query = query.filter(DailyTask.status == "pending")
            elif status == "abandoned":
                query = query.filter(DailyTask.status == "abandoned")
        
        return query.order_by(DailyTask.week_day, DailyTask.title).all()
    
    def get_daily_task_by_id(self, task_id: str) -> Optional[DailyTask]:
        """根据ID获取每日任务"""
        return self.session.query(DailyTask).filter(DailyTask.id == task_id).first()
    
    def create_daily_task(self, title: str, description: str = "", week_day: str = "", 
                         completed: bool = False, status: str = "pending") -> DailyTask:
        """创建每日任务"""
        task = DailyTask(
            title=title,
            description=description,
            week_day=week_day,
            completed=completed,
            status=status
        )
        self.session.add(task)
        self.session.commit()
        return task
    
    def update_daily_task(self, task_id: str, **kwargs) -> bool:
        """更新每日任务"""
        task = self.get_daily_task_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            # 同步 completed 和 status 字段
            if 'status' in kwargs:
                task.completed = (kwargs['status'] == 'completed')
            elif 'completed' in kwargs:
                task.status = 'completed' if kwargs['completed'] else 'pending'
            self.session.commit()
            return True
        return False
    
    def delete_daily_task(self, task_id: str) -> bool:
        """删除每日任务"""
        task = self.get_daily_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
    def toggle_daily_task_completion(self, task_id: str) -> bool:
        """切换每日任务完成状态"""
        task = self.get_daily_task_by_id(task_id)
        if task:
            # 循环切换: pending -> completed -> abandoned -> pending
            if task.status == "pending":
                task.status = "completed"
                task.completed = True
            elif task.status == "completed":
                task.status = "abandoned"
                task.completed = False
            else:  # abandoned
                task.status = "pending"
                task.completed = False
            self.session.commit()
            return True
        return False
    
    # TodoTask 相关方法
    def get_todo_tasks(self, status: Optional[str] = None) -> List[TodoTask]:
        """获取待办事项"""
        query = self.session.query(TodoTask)
        
        # 按状态筛选
        if status and status != "all":
            if status == "completed":
                query = query.filter(TodoTask.status == "completed")
            elif status == "pending":
                query = query.filter(TodoTask.status == "pending")
            elif status == "abandoned":
                query = query.filter(TodoTask.status == "abandoned")
        
        return query.order_by(TodoTask.deadline.desc(), TodoTask.urgency_score.desc()).all()
    
    def get_todo_task_by_id(self, task_id: str) -> Optional[TodoTask]:
        """根据ID获取待办事项"""
        return self.session.query(TodoTask).filter(TodoTask.id == task_id).first()
    
    def create_todo_task(self, title: str, description: str = "", deadline: str = "", 
                        completed: bool = False, status: str = "pending") -> TodoTask:
        """创建待办事项"""
        task = TodoTask(
            title=title,
            description=description,
            deadline=deadline,
            completed=completed,
            status=status
        )
        self.session.add(task)
        self.session.commit()
        # 重新计算紧急度
        self.calculate_urgency_for_task(task)
        self.session.commit()
        return task
    
    def update_todo_task(self, task_id: str, **kwargs) -> bool:
        """更新待办事项"""
        task = self.get_todo_task_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            # 同步 completed 和 status 字段
            if 'status' in kwargs:
                task.completed = (kwargs['status'] == 'completed')
            elif 'completed' in kwargs:
                task.status = 'completed' if kwargs['completed'] else 'pending'
            self.calculate_urgency_for_task(task)
            self.session.commit()
            return True
        return False
    
    def delete_todo_task(self, task_id: str) -> bool:
        """删除待办事项"""
        task = self.get_todo_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
    def toggle_todo_task_completion(self, task_id: str) -> bool:
        """切换待办事项完成状态"""
        task = self.get_todo_task_by_id(task_id)
        if task:
            # 循环切换: pending -> completed -> abandoned -> pending
            if task.status == "pending":
                task.status = "completed"
                task.completed = True
            elif task.status == "completed":
                task.status = "abandoned"
                task.completed = False
            else:  # abandoned
                task.status = "pending"
                task.completed = False
            self.calculate_urgency_for_task(task)
            self.session.commit()
            return True
        return False
    
    # EntertainmentTask 相关方法
    def get_entertainment_tasks(self, status: Optional[str] = None) -> List[EntertainmentTask]:
        """获取娱乐任务"""
        query = self.session.query(EntertainmentTask)
        
        # 按状态筛选
        if status and status != "all":
            if status == "completed":
                query = query.filter(EntertainmentTask.status == "completed")
            elif status == "pending":
                query = query.filter(EntertainmentTask.status == "pending")
            elif status == "abandoned":
                query = query.filter(EntertainmentTask.status == "abandoned")
        
        return query.order_by(EntertainmentTask.fun_category, EntertainmentTask.title).all()
    
    def get_entertainment_task_by_id(self, task_id: str) -> Optional[EntertainmentTask]:
        """根据ID获取娱乐任务"""
        return self.session.query(EntertainmentTask).filter(EntertainmentTask.id == task_id).first()
    
    def create_entertainment_task(self, title: str, description: str = "", 
                                fun_category: str = "general", completed: bool = False,
                                status: str = "pending") -> EntertainmentTask:
        """创建娱乐任务"""
        task = EntertainmentTask(
            title=title,
            description=description,
            fun_category=fun_category,
            completed=completed,
            status=status
        )
        self.session.add(task)
        self.session.commit()
        return task
    
    def update_entertainment_task(self, task_id: str, **kwargs) -> bool:
        """更新娱乐任务"""
        task = self.get_entertainment_task_by_id(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            # 同步 completed 和 status 字段
            if 'status' in kwargs:
                task.completed = (kwargs['status'] == 'completed')
            elif 'completed' in kwargs:
                task.status = 'completed' if kwargs['completed'] else 'pending'
            self.session.commit()
            return True
        return False
    
    def delete_entertainment_task(self, task_id: str) -> bool:
        """删除娱乐任务"""
        task = self.get_entertainment_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
    def toggle_entertainment_task_completion(self, task_id: str) -> bool:
        """切换娱乐任务完成状态"""
        task = self.get_entertainment_task_by_id(task_id)
        if task:
            # 循环切换: pending -> completed -> abandoned -> pending
            if task.status == "pending":
                task.status = "completed"
                task.completed = True
            elif task.status == "completed":
                task.status = "abandoned"
                task.completed = False
            else:  # abandoned
                task.status = "pending"
                task.completed = False
            self.session.commit()
            return True
        return False
    
    # 紧急度计算
    def calculate_urgency_for_task(self, task: TodoTask):
        """为单个任务计算紧急度"""
        if task.completed:
            task.urgency_score = 0
            return
        
        if not task.deadline:
            task.urgency_score = 1
            return
        
        try:
            deadline_date = datetime.strptime(task.deadline, "%Y-%m-%d").date()
            today = date.today()
            
            if deadline_date < today:
                # 已过期：高权重
                days_overdue = (today - deadline_date).days
                task.urgency_score = 3 + days_overdue
            elif deadline_date == today:
                # 今天截止：较高权重
                task.urgency_score = 2
            else:
                # 未来截止：根据剩余天数计算权重
                days_remaining = (deadline_date - today).days
                if days_remaining <= 7:
                    task.urgency_score = max(1, 2 - (days_remaining / 7))
                else:
                    task.urgency_score = 1
        except ValueError:
            task.urgency_score = 1
    
    def recalculate_all_urgency(self):
        """重新计算所有待办事项的紧急度"""
        tasks = self.get_todo_tasks()
        for task in tasks:
            self.calculate_urgency_for_task(task)
        self.session.commit()
    
    # 配置管理
    def get_config(self, key: str, default: str = "") -> str:
        """获取配置值"""
        config = self.session.query(Config).filter(Config.key == key).first()
        if config:
            return config.value
        return default
    
    def set_config(self, key: str, value: str):
        """设置配置值"""
        config = self.session.query(Config).filter(Config.key == key).first()
        if config:
            config.value = value
        else:
            config = Config(key=key, value=value)
            self.session.add(config)
        self.session.commit()
    
    # JSON导入导出功能
    def export_to_json(self, filepath: str = "tasks_export.json") -> bool:
        """导出数据到JSON文件"""
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self.session)
        return handler.export_to_json(filepath)
    
    def import_from_json(self, filepath: str = "tasks_export.json") -> bool:
        """从JSON文件导入数据"""
        from handlers.json_handler import JsonExportImportHandler
        handler = JsonExportImportHandler(self.session)
        return handler.import_from_json(filepath)
    
    # 每日重置功能
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
            # 如果日期格式错误，则重置
            self.reset_daily_tasks()
            self.set_config("last_reset_date", date.today().strftime("%Y-%m-%d"))
    
    def reset_daily_tasks(self):
        """重置每日任务的完成状态，只重置今天应该完成的任务"""
        # 获取今天的星期几
        today_weekday = datetime.now().weekday()  # 0是星期一，6是星期日
        weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        today_name = weekday_names[today_weekday] if 0 <= today_weekday <= 6 else ''
        
        # 获取所有每日任务
        all_tasks = self.session.query(DailyTask).all()
        for task in all_tasks:
            # 如果任务的星期设置为空（表示每天）或者等于今天，就重置
            if not task.week_day or task.week_day == today_name:
                # 只重置状态为 completed 的任务，因为还有 pending/abandoned 等其他状态
                if task.status == 'completed':
                    task.status = 'pending'
                    task.completed = False
        self.session.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        daily_tasks = self.get_daily_tasks()
        todo_tasks = self.get_todo_tasks()
        entertainment_tasks = self.get_entertainment_tasks()
        
        # 每日任务统计
        daily_completed = sum(1 for t in daily_tasks if t.completed)
        
        # 待办事项统计
        todo_completed = sum(1 for t in todo_tasks if t.completed)
        todo_expired = sum(1 for t in todo_tasks if self._is_task_expired(t))
        
        # 娱乐任务统计
        entertainment_completed = sum(1 for t in entertainment_tasks if t.completed)
        
        return {
            "daily": {
                "total": len(daily_tasks),
                "completed": daily_completed
            },
            "todo": {
                "total": len(todo_tasks),
                "completed": todo_completed,
                "expired": todo_expired
            },
            "entertainment": {
                "total": len(entertainment_tasks),
                "completed": entertainment_completed
            }
        }
    
    def _is_task_expired(self, task: TodoTask) -> bool:
        """判断待办事项是否过期"""
        if not task.deadline or task.completed:
            return False
        
        try:
            deadline_date = datetime.strptime(task.deadline, "%Y-%m-%d").date()
            return deadline_date < date.today()
        except ValueError:
            return False


# 如果作为模块直接运行，测试功能
if __name__ == "__main__":
    dm = DataManager()
    print("数据管理器初始化成功")
    print(f"每日任务数量: {len(dm.get_daily_tasks())}")
    print(f"待办事项数量: {len(dm.get_todo_tasks())}")
    print(f"娱乐任务数量: {len(dm.get_entertainment_tasks())}")
    dm.close_session()