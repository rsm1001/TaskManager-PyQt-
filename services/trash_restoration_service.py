"""
垃圾恢复服务 - 负责处理从垃圾桶恢复任务的复杂逻辑
将跨实体类型的恢复操作从 DataManager 中解耦出来
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from models.model import DailyTask, TodoTask, EntertainmentTask

logger = logging.getLogger(__name__)


class TrashRestorationService:
    """垃圾恢复服务 - 处理从垃圾桶恢复任务的业务逻辑"""

    def __init__(self, session, shortcut_manager, trash_manager, vacuum_service,
                 daily_task_manager, todo_task_manager, entertainment_task_manager):
        """
        初始化垃圾恢复服务

        Args:
            session: 数据库会话
            shortcut_manager: 快捷入口管理器
            trash_manager: 垃圾桶管理器
            vacuum_service: 真空服务
            daily_task_manager: 每日任务管理器
            todo_task_manager: 待办任务管理器
            entertainment_task_manager: 娱乐任务管理器
        """
        self.session = session
        self.shortcut_manager = shortcut_manager
        self.trash_manager = trash_manager
        self.vacuum_service = vacuum_service
        self.daily_task_manager = daily_task_manager
        self.todo_task_manager = todo_task_manager
        self.entertainment_task_manager = entertainment_task_manager

    def restore_task(self, trash_id: str) -> bool:
        """
        从垃圾桶恢复任务

        Args:
            trash_id: 垃圾桶记录ID

        Returns:
            bool: 恢复是否成功
        """
        logger.info(f"开始恢复垃圾任务: trash_id={trash_id}")
        record = self.trash_manager.get_by_id(trash_id)
        if not record:
            logger.warning(f"垃圾桶记录不存在: trash_id={trash_id}")
            return False

        task_type = record['task_type']
        data = record['data']

        if task_type == 'daily':
            result = self._restore_daily_task(data)
        elif task_type == 'todo':
            result = self._restore_todo_task(data)
        elif task_type == 'shortcut':
            result = self._restore_shortcut(trash_id, data)
        elif task_type == 'entertainment':
            result = self._restore_entertainment_task(data)
        else:
            logger.error(f"未知任务类型无法恢复: task_type={task_type}")
            return False

        if result:
            self.trash_manager.delete_trash_record(trash_id)
            logger.info(f"任务恢复成功并删除垃圾桶记录: trash_id={trash_id}")
        return result

    def _restore_daily_task(self, data: Dict[str, Any]) -> bool:
        """恢复每日任务"""
        task = DailyTask(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            description=data.get('description', ''),
            week_day=data.get('week_day', ''),
            completed=data.get('completed', False),
            status=data.get('status', 'pending'),
            tags=data.get('tags', ''),
            shortcut_path=data.get('shortcut_path', ''),
            priority=data.get('priority', 'normal')
        )
        self.session.add(task)
        self.session.commit()
        logger.debug(f"每日任务已恢复: id={task.id}, title={task.title}")
        return True

    def _restore_todo_task(self, data: Dict[str, Any]) -> bool:
        """恢复待办任务"""
        task = TodoTask(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            description=data.get('description', ''),
            deadline=data.get('deadline', ''),
            completed=data.get('completed', False),
            status=data.get('status', 'pending'),
            tags=data.get('tags', ''),
            shortcut_path=data.get('shortcut_path', ''),
            priority=data.get('priority', 'normal')
        )
        self.session.add(task)
        self.session.commit()
        logger.debug(f"待办任务已恢复: id={task.id}, title={task.title}")
        return True

    def _restore_entertainment_task(self, data: Dict[str, Any]) -> bool:
        """恢复娱乐任务"""
        task = EntertainmentTask(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            description=data.get('description', ''),
            fun_category=data.get('fun_category', 'general'),
            completed=data.get('completed', False),
            status=data.get('status', 'pending'),
            tags=data.get('tags', ''),
            shortcut_path=data.get('shortcut_path', ''),
            priority=data.get('priority', 'normal')
        )
        self.session.add(task)
        self.session.commit()
        logger.debug(f"娱乐任务已恢复: id={task.id}, title={task.title}")
        return True

    def _restore_shortcut(self, trash_id: str, data: Dict[str, Any]) -> bool:
        """恢复快捷入口"""
        now = datetime.now().isoformat()
        self.shortcut_manager._conn.execute(
            "INSERT INTO shortcut_entries (id, title, shortcut_path, category, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data.get('id', str(uuid.uuid4())),
                data.get('title', ''),
                data.get('shortcut_path', ''),
                data.get('category', 'todo'),
                data.get('tags', ''),
                data.get('created_at', now),
                now
            )
        )
        self.shortcut_manager._conn.commit()
        self.trash_manager.delete_trash_record(trash_id)
        logger.debug(f"快捷入口已恢复: id={data.get('id')}")
        return True

    def purge_task(self, trash_id: str) -> None:
        """永久删除垃圾桶中的任务"""
        logger.info(f"永久删除垃圾桶任务: trash_id={trash_id}")
        self.trash_manager.delete_trash_record(trash_id)
        self.vacuum_service.on_tasks_deleted(1)

    def purge_tasks(self, trash_ids: List[str]) -> None:
        """批量永久删除垃圾桶任务"""
        logger.info(f"批量永久删除垃圾桶任务: count={len(trash_ids)}")
        self.trash_manager.delete_trash_records(trash_ids)
        self.vacuum_service.on_tasks_deleted(len(trash_ids))

    def purge_all(self, task_type: str = None) -> int:
        """
        清空所有垃圾桶任务

        Args:
            task_type: 可选的任务类型过滤

        Returns:
            int: 删除的任务数量
        """
        before = self.trash_manager.get_trashed_tasks(task_type)
        count = len(before)
        if count > 0:
            logger.info(f"清空垃圾桶: task_type={task_type}, count={count}")
            self.trash_manager.purge_all(task_type)
            self.vacuum_service.on_tasks_deleted(count)
        return count
