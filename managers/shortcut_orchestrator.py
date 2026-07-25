"""
快捷入口编排器 - 集中管理快捷入口及其历史记录
通过依赖注入复用 ShortcutManager 仓储层
"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ShortcutOrchestrator:
    """快捷入口编排器

    职责：
        - 快捷入口 CRUD
        - 历史记录的增删改、置顶与清理
        - 删除时统一移入垃圾桶
    """

    def __init__(self, shortcut_manager, trash_manager):
        self._shortcut = shortcut_manager
        self._trash = trash_manager

    # ==================== 快捷入口 CRUD ====================

    def get_all(self, tag: Optional[str] = None, keyword: Optional[str] = None) -> list:
        return self._shortcut.get_all(tag=tag, keyword=keyword)

    def create(
        self,
        task_type: str,
        title: str,
        shortcut_path: str,
        tags: str = "",
        action_type: str = "open",
    ) -> bool:
        logger.info(
            "创建快捷入口 | request_id=create_shortcut | title=%s task_type=%s",
            title,
            task_type,
        )
        return self._shortcut.create(task_type, title, shortcut_path, tags, action_type)

    def update(
        self,
        shortcut_id: str,
        title: Optional[str] = None,
        shortcut_path: Optional[str] = None,
        tags: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> bool:
        return self._shortcut.update(shortcut_id, title, shortcut_path, tags, action_type)

    def delete(self, shortcut_id: str) -> bool:
        """删除快捷入口并移入垃圾桶"""
        shortcut_data = self._shortcut.delete(shortcut_id)
        if shortcut_data is None:
            return False
        logger.info(
            "删除快捷入口并入垃圾桶 | request_id=delete_shortcut | shortcut_id=%s",
            shortcut_id,
        )
        self._trash.move_to_trash("shortcut", shortcut_id, shortcut_data)
        return True

    # ==================== 历史记录 ====================

    def get_history_limit(self) -> int:
        return self._shortcut.get_history_limit()

    def set_history_limit(self, limit: int) -> bool:
        return self._shortcut.set_history_limit(limit)

    # ==================== Claude 启动放权设置 ====================

    def get_dangerously_skip_permissions(self) -> bool:
        return self._shortcut.get_dangerously_skip_permissions()

    def set_dangerously_skip_permissions(self, enabled: bool) -> bool:
        return self._shortcut.set_dangerously_skip_permissions(enabled)

    def get_codex_dangerously_skip_permissions(self) -> bool:
        return self._shortcut.get_codex_dangerously_skip_permissions()

    def set_codex_dangerously_skip_permissions(self, enabled: bool) -> bool:
        return self._shortcut.set_codex_dangerously_skip_permissions(enabled)

    def get_all_history(self) -> list:
        return self._shortcut.get_all_history()

    def add_or_update_history(
        self,
        shortcut_id: str,
        shortcut_title: str,
        shortcut_path: str,
        action_type: str = "open",
    ) -> bool:
        """添加或更新历史记录，并在超出限制时自动清理非置顶记录"""
        result = self._shortcut.add_or_update_history(
            shortcut_id, shortcut_title, shortcut_path, action_type
        )
        if result:
            limit = self.get_history_limit()
            removed = self._shortcut.cleanup_history_except_pinned(limit)
            if removed:
                logger.info(
                    "历史记录清理完成 | request_id=cleanup_history | removed=%d limit=%d",
                    removed,
                    limit,
                )
        return result

    def toggle_history_pin(self, history_id: str) -> bool:
        return self._shortcut.toggle_history_pin(history_id)

    def delete_history(self, history_id: str) -> bool:
        return self._shortcut.delete_history(history_id)

    def clear_all_unpinned_history(self) -> int:
        return self._shortcut.clear_all_unpinned_history()
