"""
标签编排器 - 集中管理标签库、分类、未使用标签清理
通过依赖注入复用 TagManager 与 TaskOrchestrator
"""

import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class TagOrchestrator:
    """标签编排器

    职责：
        - 标签库 CRUD（委托 TagManager）
        - 任务分类管理
        - 删除标签前的占用检查（避免在编排器内堆积大段 if/elif）
        - 清理未使用标签（拆分自原 DataManager 内联实现）
    """

    SUPPORTED_CATEGORIES = ("daily", "todo", "entertainment", "shortcut")

    def __init__(self, tag_manager, config_manager, task_provider: Callable):
        """初始化

        Args:
            tag_manager: 标签仓储
            config_manager: 配置仓储（用于清理 visible_tags_*）
            task_provider: 提供按类别获取任务数据的可调用对象
                接口签名：get_tasks(category: str) -> Iterable[Task]
        """
        self._tag_manager = tag_manager
        self._config_manager = config_manager
        self._task_provider = task_provider

    # ==================== 标签库 ====================

    def get_all_tags(self, category: str) -> List[str]:
        return self._tag_manager.get_all_tags(category)

    def add_tag(self, tag: str, category: str) -> bool:
        return self._tag_manager.add_tag(tag, category)

    def get_or_create_tag(self, tag: str, category: str) -> bool:
        return self._tag_manager.get_or_create(tag, category)

    def delete_tag(self, tag: str, category: str) -> bool:
        """删除标签前进行占用检查"""
        checker = self._make_tag_usage_checker(category)
        return self._tag_manager.delete_tag(tag, category, [checker])

    # ==================== 分类 ====================

    def get_all_categories(self, task_type: str) -> List[str]:
        return self._tag_manager.get_all_categories(task_type)

    def add_category(self, category: str, task_type: str) -> bool:
        return self._tag_manager.add_category(category, task_type)

    def delete_category(self, category: str, task_type: str) -> bool:
        return self._tag_manager.delete_category(category, task_type)

    # ==================== 清理未使用标签 ====================

    def cleanup_unused_tags(self) -> Dict[str, int]:
        """检测并删除所有类别中未被任务使用的标签"""
        logger.info("开始清理未使用标签 | request_id=cleanup_tags")
        result: Dict[str, int] = {}
        for category in self.SUPPORTED_CATEGORIES:
            result[category] = self._cleanup_category_unused_tags(category)
        total = sum(result.values())
        logger.info(
            "标签清理完成 | request_id=cleanup_tags | total=%d details=%s",
            total,
            result,
        )
        return result

    # ==================== 内部辅助 ====================

    def _cleanup_category_unused_tags(self, category: str) -> int:
        stored = set(self._tag_manager.get_all_tags(category))
        if not stored:
            return 0

        in_use = self._collect_in_use_tags(category)
        unused = stored - in_use
        if not unused:
            return 0

        remaining = sorted(stored - unused)
        self._tag_manager._save_tags(category, remaining)
        self._cleanup_visible_tags(category, set(remaining))
        return len(unused)

    def _collect_in_use_tags(self, category: str) -> set:
        in_use: set = set()
        for item in self._task_provider(category):
            tags_value = None
            if isinstance(item, dict):
                tags_value = item.get("tags")
            else:
                tags_value = getattr(item, "tags", None)
            if not tags_value:
                continue
            for raw in tags_value.split(","):
                tag = raw.strip()
                if tag:
                    in_use.add(tag)
        return in_use

    def _cleanup_visible_tags(self, category: str, remaining_tags: set) -> None:
        visible_key = f"visible_tags_{category}"
        visible_val = self._config_manager.get(visible_key, "")
        if not visible_val:
            return
        visible_tags = [t.strip() for t in visible_val.split(",") if t.strip()]
        cleaned = [t for t in visible_tags if t in remaining_tags]
        self._config_manager.set(visible_key, ",".join(cleaned))

    def _make_tag_usage_checker(self, category: str) -> Callable[[str], bool]:
        """构造占用检查函数，按类别查询任务并解析 tags 字段"""
        def _check(tag_name: str) -> bool:
            for item in self._task_provider(category):
                tags_value = None
                if isinstance(item, dict):
                    tags_value = item.get("tags")
                else:
                    tags_value = getattr(item, "tags", None)
                if not tags_value:
                    continue
                tag_list = [t.strip() for t in tags_value.split(",") if t.strip()]
                if tag_name in tag_list:
                    return True
            return False

        return _check
