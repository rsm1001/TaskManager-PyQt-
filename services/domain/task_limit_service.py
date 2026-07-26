"""
Task Limit Service - 任务限制服务模块
检查并执行各类型任务的数量上限，超出时将最老任务移入垃圾桶
"""

import logging
import config.config

logger = logging.getLogger(__name__)


class TaskLimitService:
    """任务数量限制服务"""

    def __init__(self, data_manager, trash_manager, vacuum_service):
        """
        Args:
            data_manager: DataManager 实例
            trash_manager: TrashManager 实例
            vacuum_service: VacuumService 实例
        """
        self._dm = data_manager
        self._trash_manager = trash_manager
        self._vacuum_service = vacuum_service
        logger.debug("TaskLimitService 初始化完成")

    def enforce_limit(self, task_type: str, task_model):
        """检查并执行任务数量上限，超出时将最老任务移入垃圾桶

        Args:
            task_type: 任务类型字符串
            task_model: 任务模型类
        """
        limit = config.config.TASK_CACHE_LIMIT
        total = self._dm.session.query(task_model).count()

        if total <= limit:
            logger.debug(f"{task_type} 任务数量 ({total}) 未超过限制 ({limit})")
            return

        oldest = self._dm.session.query(task_model).order_by(task_model.created_at).first()
        if not oldest:
            logger.warning(f"{task_type} 任务列表为空但数量超过限制")
            return

        logger.info(f"{task_type} 任务数量 ({total}) 超过限制 ({limit})，将移动最旧任务到垃圾桶")

        if task_type == 'daily':
            task_data = self._dm.daily_task_manager.to_dict(oldest)
        elif task_type == 'todo':
            task_data = self._dm.todo_manager.to_dict(oldest)
        elif task_type == 'entertainment':
            task_data = self._dm.entertainment_manager.to_dict(oldest)
        else:
            logger.error(f"未知的任务类型: {task_type}")
            return

        self._trash_manager.move_to_trash(task_type, oldest.id, task_data)
        self._dm.session.delete(oldest)
        self._dm.session.commit()
        self._vacuum_service.on_tasks_deleted(1)
        logger.info(f"已移动最旧任务到垃圾桶: {oldest.id}")
