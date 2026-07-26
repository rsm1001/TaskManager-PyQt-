"""
标签清理服务
封装标签清理的业务逻辑，与 UI 解耦
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TagCleanupService:
    """标签清理服务 - 处理未使用标签的检测和删除"""

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例
        """
        self._data_manager = data_manager
        logger.info("TagCleanupService 初始化完成")

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
            cleaned = self._cleanup_category_unused_tags(category)
            result[category] = cleaned

        total = sum(result.values())
        logger.info(f"标签清理完成，总计删除 {total} 个未使用标签: {result}")
        return result

    def _cleanup_category_unused_tags(self, category: str) -> int:
        """
        清理指定类别中未被任务使用的标签

        Args:
            category: 任务类别 ('daily', 'todo', 'entertainment', 'shortcut')

        Returns:
            int: 删除的标签数量
        """
        tag_manager = self._data_manager.tag_manager

        # 从 configs 表读取该类别的标签库
        stored_tags = set(tag_manager.get_all_tags(category))
        if not stored_tags:
            return 0

        # 收集该类别所有任务中实际在用的标签
        in_use_tags = self._collect_in_use_tags(category)

        # 标签库中不在 in_use_tags 中的标签为未使用
        unused = stored_tags - in_use_tags
        if not unused:
            return 0

        remaining = stored_tags - unused
        tag_manager._save_tags(category, sorted(remaining))

        # 同时清理 visible_tags_{category} 中也已不存在的标签，保持标签栏显示同步
        self._cleanup_visible_tags(category, remaining)

        return len(unused)

    def _collect_in_use_tags(self, category: str) -> set:
        """
        收集指定类别所有任务中实际在用的标签

        Args:
            category: 任务类别

        Returns:
            set: 在用标签集合
        """
        in_use_tags = set()

        if category == 'daily':
            for task in self._data_manager.get_daily_tasks():
                if task.tags:
                    for t in task.tags.split(','):
                        t = t.strip()
                        if t:
                            in_use_tags.add(t)
        elif category == 'todo':
            for task in self._data_manager.get_todo_tasks():
                if task.tags:
                    for t in task.tags.split(','):
                        t = t.strip()
                        if t:
                            in_use_tags.add(t)
        elif category == 'entertainment':
            for task in self._data_manager.get_entertainment_tasks():
                if task.tags:
                    for t in task.tags.split(','):
                        t = t.strip()
                        if t:
                            in_use_tags.add(t)
        elif category == 'shortcut':
            for s in self._data_manager.get_all_shortcuts():
                if s.get('tags'):
                    for t in s.get('tags').split(','):
                        t = t.strip()
                        if t:
                            in_use_tags.add(t)

        return in_use_tags

    def _cleanup_visible_tags(self, category: str, remaining_tags: set):
        """
        清理 visible_tags_{category} 配置中已不存在的标签

        Args:
            category: 任务类别
            remaining_tags: 剩余的有效标签集合
        """
        visible_key = f'visible_tags_{category}'
        visible_val = self._data_manager.get_config(visible_key, '')
        if visible_val:
            visible_tags = [t.strip() for t in visible_val.split(',') if t.strip()]
            cleaned_visible = [t for t in visible_tags if t in remaining_tags]
            self._data_manager.set_config(visible_key, ','.join(cleaned_visible))
