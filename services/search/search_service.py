"""
Search Service - 搜索服务模块
提供全局搜索功能，支持模糊匹配多种任务类型
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SearchService:
    """全局搜索服务"""

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例，用于获取各类型任务数据
        """
        self._dm = data_manager
        logger.debug("SearchService 初始化完成")

    def search_all_tasks(self, keyword: str) -> List[Dict[str, Any]]:
        """全局搜索所有任务类型

        Args:
            keyword: 搜索关键词（支持模糊匹配）

        Returns:
            List[Dict]: 包含所有匹配的任务，附加 task_type 字段标识来源
        """
        if not keyword:
            logger.debug("搜索关键词为空，返回空结果")
            return []

        keyword_stripped = keyword.lower().strip()
        logger.info(f"开始全局搜索，关键词: {keyword_stripped}")

        # 关键词已下推到 SQL 层，各方法仅返回匹配记录
        results = []

        # 1. 搜索每日任务
        for task in self._dm.get_daily_tasks(keyword=keyword_stripped):
            task_dict = self._dm.daily_task_manager.to_dict(task)
            task_dict['task_type'] = 'daily'
            results.append(task_dict)
            logger.debug(f"匹配每日任务: {task.title}")

        # 2. 搜索待办任务
        for task in self._dm.get_todo_tasks(keyword=keyword_stripped):
            task_dict = self._dm.todo_manager.to_dict(task)
            task_dict['task_type'] = 'todo'
            results.append(task_dict)
            logger.debug(f"匹配待办任务: {task.title}")

        # 3. 搜索娱乐任务
        for task in self._dm.get_entertainment_tasks(keyword=keyword_stripped):
            task_dict = self._dm.entertainment_manager.to_dict(task)
            task_dict['task_type'] = 'entertainment'
            results.append(task_dict)
            logger.debug(f"匹配娱乐任务: {task.title}")

        # 4. 搜索快捷入口
        for shortcut in self._dm.get_all_shortcuts(keyword=keyword_stripped):
            shortcut_copy = shortcut.copy()
            shortcut_copy['task_type'] = 'shortcut'
            results.append(shortcut_copy)
            logger.debug(f"匹配快捷入口: {shortcut.get('title')}")

        # 按创建时间降序排序
        results.sort(key=lambda x: x.get('created_at', '') or '', reverse=True)
        logger.info(f"搜索完成，共找到 {len(results)} 条结果")
        return results

    def _task_matches(self, task, keyword: str, fields: List[str]) -> bool:
        """检查任务是否匹配关键词（已废弃，关键词下推到 SQL 层）"""
        return False

    def _shortcut_matches(self, shortcut: Dict, keyword: str) -> bool:
        """检查快捷入口是否匹配关键词（已废弃，关键词下推到 SQL 层）"""
        return False
