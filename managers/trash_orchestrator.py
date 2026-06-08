"""
垃圾桶编排器 - 集中管理垃圾桶的查询、恢复与清理
通过依赖注入复用 TrashRestorationService（恢复/清空）与 TrashManager（查询）
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TrashOrchestrator:
    """垃圾桶编排器

    职责：
        - 查询垃圾桶记录（委托 TrashManager）
        - 恢复 / 永久删除 / 清空（委托 TrashRestorationService）
        - 恢复快捷入口的兼容入口（与原 DataManager.restore_shortcut 一致）
    """

    def __init__(self, trash_manager, trash_restoration_service):
        self._trash = trash_manager
        self._restoration = trash_restoration_service

    # ==================== 查询 ====================

    def get_trashed_tasks(self, task_type: Optional[str] = None):
        return self._trash.get_trashed_tasks(task_type)

    # ==================== 恢复 ====================

    def restore(self, trash_id: str) -> bool:
        """恢复垃圾桶中的任务"""
        logger.info("恢复垃圾桶任务 | request_id=restore_trash | trash_id=%s", trash_id)
        return self._restoration.restore_task(trash_id)

    def restore_shortcut(self, trash_id: str) -> bool:
        """恢复快捷入口（兼容原 DataManager.restore_shortcut）"""
        return self._restoration.restore_task(trash_id)

    # ==================== 永久删除 / 清空 ====================

    def purge(self, trash_id: str) -> None:
        logger.info("永久删除垃圾桶任务 | request_id=purge_trash | trash_id=%s", trash_id)
        self._restoration.purge_task(trash_id)

    def purge_many(self, trash_ids: List[str]) -> None:
        logger.info(
            "批量永久删除垃圾桶任务 | request_id=purge_trash_batch | count=%d",
            len(trash_ids),
        )
        self._restoration.purge_tasks(trash_ids)

    def purge_all(self, task_type: Optional[str] = None) -> None:
        logger.info(
            "清空所有垃圾桶任务 | request_id=purge_trash_all | task_type=%s",
            task_type,
        )
        self._restoration.purge_all(task_type)
