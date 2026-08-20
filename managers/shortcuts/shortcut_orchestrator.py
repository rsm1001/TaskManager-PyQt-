"""
快捷入口编排器 - 集中管理快捷入口及其历史记录
通过依赖注入复用 ShortcutManager 仓储层
"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)
_UNSET = object()


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

    # ==================== Shortcut CRUD ====================

    def get_all(self, tag: Optional[str] = None, keyword: Optional[str] = None) -> list:
        return self._shortcut.get_all(tag=tag, keyword=keyword)

    def get_tree(self, tag: Optional[str] = None) -> list:
        return self._shortcut.get_tree(tag=tag)

    def get_children(self, parent_id: str) -> list:
        return self._shortcut.get_children(parent_id)

    def create(
        self,
        task_type: str,
        title: str,
        shortcut_path: str,
        tags: str = "",
        action_type: str = "open",
        parent_id: Optional[str] = None,
        order_index: Optional[int] = None,
    ) -> bool:
        logger.info(
            "Creating shortcut | request_id=create_shortcut | title=%s parent_id=%s",
            title,
            parent_id,
        )
        return self._shortcut.create(
            task_type, title, shortcut_path, tags, action_type,
            parent_id=parent_id, order_index=order_index,
        )

    def update(
        self,
        shortcut_id: str,
        title: Optional[str] = None,
        shortcut_path: Optional[str] = None,
        tags: Optional[str] = None,
        action_type: Optional[str] = None,
        parent_id=_UNSET,
        order_index: Optional[int] = None,
    ) -> bool:
        kwargs = {
            'title': title,
            'shortcut_path': shortcut_path,
            'tags': tags,
            'action_type': action_type,
            'order_index': order_index,
        }
        if parent_id is not _UNSET:
            kwargs['parent_id'] = parent_id
        return self._shortcut.update(shortcut_id, **kwargs)

    def delete(self, shortcut_id: str) -> bool:
        """Delete an entry and its direct children as one trash bundle."""
        entries = self._shortcut.delete_tree(shortcut_id)
        if not entries:
            return False
        root = entries[0]
        trash_data = dict(root)
        if len(entries) > 1:
            trash_data['_children'] = entries[1:]
        logger.info(
            "Deleted shortcut bundle | request_id=delete_shortcut | shortcut_id=%s count=%d",
            shortcut_id,
            len(entries),
        )
        self._trash.move_to_trash("shortcut", shortcut_id, trash_data)
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
