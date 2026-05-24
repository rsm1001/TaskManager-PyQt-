"""
Task Manager - 数据访问和管理类
处理数据库的CRUD操作、JSON导入导出、每日重置等
通过组合子管理器实现模块化架构
"""

import logging
from models.model import DailyTask, TodoTask, EntertainmentTask, Config, init_db
from datetime import datetime, date
import json
import uuid
import config.config
import sqlite3
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 导入子管理器
from managers.todo_task_manager import TodoTaskManager
from managers.entertainment_task_manager import EntertainmentTaskManager
from managers.config_manager import ConfigManager
from managers.trash_manager import TrashManager
from managers.shortcut_manager import ShortcutManager
from managers.daily_task_manager import DailyTaskManager
from managers.tag_manager import TagManager
from managers.task_type import TaskType

# 导入服务
from services.daily_reset_service import DailyResetService
from services.vacuum_service import VacuumService
from services.trash_restoration_service import TrashRestorationService
from services.service_factory import ServiceFactory


class DataManager:
    """数据管理器 - 组合子管理器实现模块化"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        self.engine, self.Session = init_db(db_path, run_migration=True)
        self.session = self.Session()
        logger.info(f"DataManager 初始化，数据库路径: {db_path}")

        # 初始化子管理器（按功能垂直划分）
        self.todo_manager = TodoTaskManager(self.session)
        self.entertainment_manager = EntertainmentTaskManager(self.session)
        self.config_manager = ConfigManager(self.session)
        self.trash_manager = TrashManager()
        self.shortcut_manager = ShortcutManager()
        self.daily_task_manager = DailyTaskManager(self.session)
        self.tag_manager = TagManager(self.config_manager)
        self.daily_reset_service = DailyResetService(self.session, self.config_manager)
        self.vacuum_service = VacuumService(self.engine, config.config.TRASH_DATABASE_PATH)
        self.trash_restoration_service = TrashRestorationService(
            session=self.session,
            shortcut_manager=self.shortcut_manager,
            trash_manager=self.trash_manager,
            vacuum_service=self.vacuum_service,
            daily_task_manager=self.daily_task_manager,
            todo_task_manager=self.todo_manager,
            entertainment_task_manager=self.entertainment_manager
        )

        # 初始化服务工厂
        self._service_factory = ServiceFactory(self)

        # 检查并执行每日重置
        self.daily_reset_service.check_and_reset()
        logger.info("DataManager 初始化完成")

    # ==================== 服务获取方法 ====================

    def _get_statistics_service(self):
        """获取统计服务"""
        return self._service_factory.get_statistics_service()

    def _get_search_service(self):
        """获取搜索服务"""
        return self._service_factory.get_search_service()

    def _get_task_limit_service(self):
        """获取任务限制服务"""
        return self._service_factory.get_task_limit_service()

    # ==================== 会话管理 ====================

    def get_session(self):
        """获取数据库会话"""
        return self.session

    def close_session(self):
        """关闭数据库会话"""
        logger.info("关闭数据库会话")
        self.session.close()
        self.trash_manager.close()
        self.shortcut_manager.close()

    def commit(self):
        """提交更改"""
        self.session.commit()

    def rollback(self):
        """回滚更改"""
        self.session.rollback()

    # ==================== DailyTask 相关方法 ====================

    def get_daily_tasks(self, weekday: Optional[str] = None,
                        status: Optional[str] = None, tag: Optional[str] = None) -> List[DailyTask]:
        return self.daily_task_manager.get_tasks(weekday=weekday, status=status, tag=tag)

    def get_daily_task_by_id(self, task_id: str) -> Optional[DailyTask]:
        return self.daily_task_manager.get_by_id(task_id)

    def create_daily_task(self, title: str, description: str = "", week_day: str = "",
                          completed: bool = False, status: str = "pending",
                          tags: str = "", shortcut_path: str = "", category: str = "") -> DailyTask:
        logger.info(f"创建每日任务: {title}")
        task = self.daily_task_manager.create(title, description, week_day, completed, status, tags, shortcut_path, category)
        self._get_task_limit_service().enforce_limit('daily', DailyTask)
        return task

    def update_daily_task(self, task_id: str, **kwargs) -> bool:
        return self.daily_task_manager.update(task_id, **kwargs)

    def delete_daily_task(self, task_id: str) -> bool:
        task_data = self.daily_task_manager.delete(task_id)
        if task_data is None:
            return False
        logger.info(f"删除每日任务: {task_id}")
        self.trash_manager.move_to_trash('daily', task_id, task_data)
        return True

    def toggle_daily_task_completion(self, task_id: str) -> bool:
        return self.daily_task_manager.toggle_completion(task_id)

    # ==================== TodoTask 委托 ====================

    def get_todo_tasks(self, status: Optional[str] = None, tag: Optional[str] = None) -> List[TodoTask]:
        return self.todo_manager.get_tasks(status=status, tag=tag)

    def get_todo_task_by_id(self, task_id: str) -> Optional[TodoTask]:
        return self.todo_manager.get_by_id(task_id)

    def create_todo_task(self, title: str, description: str = "", deadline: str = "",
                         completed: bool = False, status: str = "pending",
                         tags: str = "", shortcut_path: str = "", category: str = "") -> TodoTask:
        logger.info(f"创建待办任务: {title}")
        task = self.todo_manager.create(title, description, deadline, completed, status, tags, shortcut_path, category)
        self._get_task_limit_service().enforce_limit('todo', TodoTask)
        return task

    def update_todo_task(self, task_id: str, **kwargs) -> bool:
        return self.todo_manager.update(task_id, **kwargs)

    def delete_todo_task(self, task_id: str) -> bool:
        task = self.todo_manager.get_by_id(task_id)
        if not task:
            return False
        task_data = self.todo_manager.to_dict(task)
        logger.info(f"删除待办任务: {task_id}")
        self.trash_manager.move_to_trash('todo', task_id, task_data)
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
                                  shortcut_path: str = "", category: str = "") -> EntertainmentTask:
        logger.info(f"创建娱乐任务: {title}")
        task = self.entertainment_manager.create(title, description, fun_category, completed, status, tags, shortcut_path, category)
        self._get_task_limit_service().enforce_limit('entertainment', EntertainmentTask)
        return task

    def update_entertainment_task(self, task_id: str, **kwargs) -> bool:
        return self.entertainment_manager.update(task_id, **kwargs)

    def delete_entertainment_task(self, task_id: str) -> bool:
        task = self.entertainment_manager.get_by_id(task_id)
        if not task:
            return False
        task_data = self.entertainment_manager.to_dict(task)
        logger.info(f"删除娱乐任务: {task_id}")
        self.trash_manager.move_to_trash('entertainment', task_id, task_data)
        self.session.delete(task)
        self.session.commit()
        return True

    def toggle_entertainment_task_completion(self, task_id: str) -> bool:
        return self.entertainment_manager.toggle_completion(task_id)

    # ==================== 垃圾桶相关方法 ====================

    def get_trashed_tasks(self, task_type: str = None):
        return self.trash_manager.get_trashed_tasks(task_type)

    def restore_trashed_task(self, trash_id: str) -> bool:
        """恢复垃圾桶中的任务到主数据库"""
        logger.info(f"恢复垃圾桶任务: {trash_id}")
        return self.trash_restoration_service.restore_task(trash_id)

    def purge_trashed_task(self, trash_id: str):
        logger.info(f"永久删除垃圾桶任务: {trash_id}")
        self.trash_restoration_service.purge_task(trash_id)

    def purge_trashed_tasks(self, trash_ids: List[str]):
        logger.info(f"批量永久删除垃圾桶任务: {len(trash_ids)} 个")
        self.trash_restoration_service.purge_tasks(trash_ids)

    def purge_all_trashed(self, task_type: str = None):
        logger.info(f"清空所有垃圾桶任务，类型: {task_type}")
        self.trash_restoration_service.purge_all(task_type)

    # ==================== 快捷入口相关方法 ====================

    def get_all_shortcuts(self, tag: str = None) -> list:
        return self.shortcut_manager.get_all(tag=tag)

    def create_shortcut(self, task_type: str, title: str, shortcut_path: str, tags: str = '', action_type: str = 'open') -> bool:
        logger.info(f"创建快捷入口: {title}")
        return self.shortcut_manager.create(task_type, title, shortcut_path, tags, action_type)

    def update_shortcut(self, shortcut_id: str, title: str = None, shortcut_path: str = None, tags: str = None, action_type: str = None) -> bool:
        return self.shortcut_manager.update(shortcut_id, title, shortcut_path, tags, action_type)

    def delete_shortcut(self, shortcut_id: str) -> bool:
        shortcut_data = self.shortcut_manager.delete(shortcut_id)
        if shortcut_data is None:
            return False
        logger.info(f"删除快捷入口: {shortcut_id}")
        self.trash_manager.move_to_trash('shortcut', shortcut_id, shortcut_data)
        return True

    def restore_shortcut(self, trash_id: str) -> bool:
        """恢复快捷入口（委托给 TrashRestorationService）"""
        return self.trash_restoration_service.restore_task(trash_id)

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

    # ==================== 统计（委托给 StatisticsService） ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取所有任务的统计信息"""
        return self._get_statistics_service().get_statistics()

    # ==================== 分类管理 ====================

    def get_all_categories(self, task_type: str) -> List[str]:
        """获取指定任务类型的所有分类"""
        return self.tag_manager.get_all_categories(task_type)

    def add_category(self, category: str, task_type: str) -> bool:
        """添加任务分类"""
        return self.tag_manager.add_category(category, task_type)

    def delete_category(self, category: str, task_type: str) -> bool:
        """删除任务分类"""
        return self.tag_manager.delete_category(category, task_type)

    # ==================== 标签管理 ====================

    def get_all_tags(self, category: str) -> List[str]:
        """获取指定类别的所有标签"""
        return self.tag_manager.get_all_tags(category)

    def add_tag(self, tag: str, category: str) -> bool:
        """添加类别标签"""
        return self.tag_manager.add_tag(tag, category)

    def delete_tag(self, tag: str, category: str) -> bool:
        """删除类别标签（仅当标签未被该类别任务使用时可删除）"""
        # 构建该类别任务标签检查函数
        def check_tag_in_tasks(tag_name):
            if category == 'daily':
                for task in self.get_daily_tasks():
                    if task.tags:
                        tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                        if tag_name in tag_list:
                            return True
            elif category == 'todo':
                for task in self.get_todo_tasks():
                    if task.tags:
                        tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                        if tag_name in tag_list:
                            return True
            elif category == 'entertainment':
                for task in self.get_entertainment_tasks():
                    if task.tags:
                        tag_list = [t.strip() for t in task.tags.split(',') if t.strip()]
                        if tag_name in tag_list:
                            return True
            elif category == 'shortcut':
                for s in self.get_all_shortcuts():
                    if s.get('tags'):
                        tag_list = [t.strip() for t in s.get('tags').split(',') if t.strip()]
                        if tag_name in tag_list:
                            return True
            return False

        return self.tag_manager.delete_tag(tag, category, [check_tag_in_tasks])

    def get_or_create_tag(self, tag: str, category: str) -> bool:
        """获取或创建类别标签"""
        return self.tag_manager.get_or_create(tag, category)

    def cleanup_unused_tags(self) -> Dict[str, int]:
        """
        检测并删除所有类别中未被任务使用的标签库标签

        Returns:
            Dict[str, int]: 每个类别的清理结果，格式 {category: 删除数量}
        """
        logger.info("开始清理未使用的标签")
        categories = ['daily', 'todo', 'entertainment', 'shortcut']
        result = {}

        for category in categories:
            # 从 configs 表读取该类别的标签库
            stored_tags = set(self.tag_manager.get_all_tags(category))
            if not stored_tags:
                result[category] = 0
                continue

            # 收集该类别所有任务中实际在用的标签
            in_use_tags = set()
            if category == 'daily':
                for task in self.get_daily_tasks():
                    if task.tags:
                        for t in task.tags.split(','):
                            t = t.strip()
                            if t:
                                in_use_tags.add(t)
            elif category == 'todo':
                for task in self.get_todo_tasks():
                    if task.tags:
                        for t in task.tags.split(','):
                            t = t.strip()
                            if t:
                                in_use_tags.add(t)
            elif category == 'entertainment':
                for task in self.get_entertainment_tasks():
                    if task.tags:
                        for t in task.tags.split(','):
                            t = t.strip()
                            if t:
                                in_use_tags.add(t)
            elif category == 'shortcut':
                for s in self.get_all_shortcuts():
                    if s.get('tags'):
                        for t in s.get('tags').split(','):
                            t = t.strip()
                            if t:
                                in_use_tags.add(t)

            # 标签库中不在 in_use_tags 中的标签为未使用
            unused = stored_tags - in_use_tags
            if unused:
                remaining = stored_tags - unused
                self.tag_manager._save_tags(category, sorted(remaining))
                # 同时清理 visible_tags_{category} 中也已不存在的标签，保持标签栏显示同步
                visible_key = f'visible_tags_{category}'
                visible_val = self.config_manager.get(visible_key, '')
                if visible_val:
                    visible_tags = [t.strip() for t in visible_val.split(',') if t.strip()]
                    cleaned_visible = [t for t in visible_tags if t in remaining]
                    self.config_manager.set(visible_key, ','.join(cleaned_visible))
                result[category] = len(unused)
            else:
                result[category] = 0

        logger.info(f"标签清理完成: {result}")
        return result

    # ==================== 每日重置（兼容旧调用） ====================

    def check_daily_reset(self):
        """兼容旧调用，内部委托给 DailyResetService"""
        self.daily_reset_service.check_and_reset()

    def reset_daily_tasks(self):
        """兼容旧调用，直接触发重置"""
        self.daily_reset_service._do_reset()

    # ==================== 全局搜索（委托给 SearchService） ====================

    def search_all_tasks(self, keyword: str) -> List[Dict[str, Any]]:
        """全局搜索所有任务类型"""
        return self._get_search_service().search_all_tasks(keyword)


if __name__ == "__main__":
    dm = DataManager()
    logger.info("数据管理器初始化成功")
    logger.info(f"每日任务数量: {len(dm.get_daily_tasks())}")
    logger.info(f"待办事项数量: {len(dm.get_todo_tasks())}")
    logger.info(f"娱乐任务数量: {len(dm.get_entertainment_tasks())}")
    dm.close_session()
