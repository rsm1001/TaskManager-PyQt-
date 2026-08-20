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
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]')
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
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]')
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
            priority=data.get('priority', 'normal'),
            subtasks=data.get('subtasks', '[]')
        )
        self.session.add(task)
        self.session.commit()
        logger.debug(f"娱乐任务已恢复: id={task.id}, title={task.title}")
        return True

    def _restore_shortcut(self, trash_id: str, data: Dict[str, Any]) -> bool:
        """Restore a shortcut or an entire root/child shortcut bundle."""
        now = datetime.now().isoformat()
        entries = [dict(data)]
        children = data.get('_children', [])
        if isinstance(children, list):
            entries.extend(dict(item) for item in children)
        requested_ids = {item.get('id') for item in entries if item.get('id')}
        existing_ids = {
            row[0] for row in self.shortcut_manager._conn.execute(
                "SELECT id FROM shortcut_entries"
            ).fetchall()
        }
        id_map = {}
        for item in entries:
            original_id = item.get('id') or str(uuid.uuid4())
            item['_restore_original_id'] = original_id
            id_map[original_id] = original_id if original_id not in existing_ids else str(uuid.uuid4())

        root_original_id = entries[0].get('_restore_original_id')
        root_id = id_map.get(root_original_id)
        for item in entries:
            original_parent = item.get('parent_id')
            if len(entries) == 1 and original_parent:
                # An individually deleted child keeps its original parent when
                # that root still exists. If the root was deleted meanwhile,
                # restore the child as a root rather than creating a dangling FK.
                parent_row = self.shortcut_manager._conn.execute(
                    "SELECT parent_id FROM shortcut_entries WHERE id = ?",
                    (original_parent,),
                ).fetchone()
                parent_id = (
                    original_parent
                    if parent_row is not None and parent_row[0] is None
                    else None
                )
            else:
                parent_id = id_map.get(original_parent) if original_parent in requested_ids else None
                # Children are allowed only below the restored root.
                if item is entries[0]:
                    parent_id = None
            self.shortcut_manager._conn.execute(
                "INSERT INTO shortcut_entries "
                "(id, title, shortcut_path, action_type, category, tags, parent_id, order_index, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    id_map[item.get('_restore_original_id')],
                    item.get('title', ''),
                    item.get('shortcut_path', ''),
                    item.get('action_type', 'open'),
                    item.get('category', 'todo'),
                    item.get('tags', ''),
                    parent_id,
                    item.get('order_index', 0) or 0,
                    item.get('created_at', now),
                    item.get('updated_at', now),
                ),
            )
        profile = data.get('_repository_profile')
        if isinstance(profile, dict) and root_id:
            self.shortcut_manager._conn.execute(
                """INSERT INTO shortcut_repository_profiles
                   (parent_shortcut_id, repository_root, remote_name, base_ref, launch_script, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(parent_shortcut_id) DO UPDATE SET
                     repository_root=excluded.repository_root,
                     remote_name=excluded.remote_name,
                     base_ref=excluded.base_ref,
                     launch_script=excluded.launch_script,
                     updated_at=excluded.updated_at""",
                (
                    root_id,
                    profile.get('repository_root', data.get('shortcut_path', '')),
                    profile.get('remote_name', 'origin'),
                    profile.get('base_ref', ''),
                    profile.get('launch_script', ''),
                    profile.get('updated_at', now) or now,
                ),
            )
        self.shortcut_manager._conn.commit()
        logger.debug("Shortcut bundle restored: id=%s", root_id)
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
