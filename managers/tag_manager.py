"""
标签管理器 - 负责各类别独立标签的增删查改
每个类别（daily/todo/entertainment/shortcut）有独立的标签库
"""

from typing import List


class TagManager:
    """标签管理器，负责各类别独立标签的 CRUD 操作"""

    def __init__(self, config_manager):
        """
        Args:
            config_manager: ConfigManager 实例，用于读写各类别标签配置
        """
        self._config_manager = config_manager

    def _get_config_key(self, category: str) -> str:
        """获取类别对应的配置键"""
        return f"tags_{category}"

    def get_all_tags(self, category: str) -> List[str]:
        """
        获取指定类别的所有标签

        Args:
            category: 类别标识（如 'daily', 'todo', 'entertainment', 'shortcut'）
        """
        key = self._get_config_key(category)
        tags_str = self._config_manager.get(key, "")
        if not tags_str:
            return []
        return [t.strip() for t in tags_str.split(',') if t.strip()]

    def _save_tags(self, category: str, tags: List[str]):
        """保存类别标签列表（内部使用）"""
        key = self._get_config_key(category)
        tags_str = ','.join(sorted(set(tags)))
        self._config_manager.set(key, tags_str)

    def add_tag(self, tag: str, category: str) -> bool:
        """
        添加类别标签

        Args:
            tag: 标签名称
            category: 类别标识

        Returns:
            bool: 是否添加成功（标签已存在时也返回True）
        """
        tag = tag.strip()
        if not tag:
            return False
        tags = self.get_all_tags(category)
        if tag not in tags:
            tags.append(tag)
            self._save_tags(category, tags)
        return True

    def delete_tag(self, tag: str, category: str, task_checkers: List[callable] = None) -> bool:
        """
        删除类别标签（仅当标签未被该类别任务使用时可删除）

        Args:
            tag: 标签名称
            category: 类别标识
            task_checkers: 任务标签检查函数列表，每个函数(tag)返回是否被使用

        Returns:
            bool: 是否删除成功
        """
        tag = tag.strip()
        if not tag:
            return False

        # 检查标签是否被任何任务使用
        if task_checkers:
            for checker in task_checkers:
                if checker(tag):
                    return False

        # 标签未被使用，可以删除
        tags = self.get_all_tags(category)
        if tag in tags:
            tags.remove(tag)
            self._save_tags(category, tags)
            return True
        return False

    def get_or_create(self, tag: str, category: str) -> bool:
        """获取或创建标签（如果不存在则创建）"""
        return self.add_tag(tag, category)

    # ==================== 分类管理 ====================

    def _get_category_config_key(self, task_type: str) -> str:
        """获取任务类型对应的分类配置键"""
        return f"categories_{task_type}"

    def get_all_categories(self, task_type: str) -> List[str]:
        """
        获取指定任务类型的所有分类

        Args:
            task_type: 任务类型（如 'daily', 'todo', 'entertainment'）
        """
        key = self._get_category_config_key(task_type)
        cats_str = self._config_manager.get(key, "")
        if not cats_str:
            return []
        return [c.strip() for c in cats_str.split(',') if c.strip()]

    def _save_categories(self, task_type: str, categories: List[str]):
        """保存任务类型分类列表（内部使用）"""
        key = self._get_category_config_key(task_type)
        cats_str = ','.join(sorted(set(categories)))
        self._config_manager.set(key, cats_str)

    def add_category(self, category: str, task_type: str) -> bool:
        """
        添加任务分类

        Args:
            category: 分类名称
            task_type: 任务类型

        Returns:
            bool: 是否添加成功（分类已存在时也返回True）
        """
        category = category.strip()
        if not category:
            return False
        categories = self.get_all_categories(task_type)
        if category not in categories:
            categories.append(category)
            self._save_categories(task_type, categories)
        return True

    def delete_category(self, category: str, task_type: str) -> bool:
        """
        删除任务分类

        Args:
            category: 分类名称
            task_type: 任务类型

        Returns:
            bool: 是否删除成功
        """
        category = category.strip()
        if not category:
            return False
        categories = self.get_all_categories(task_type)
        if category in categories:
            categories.remove(category)
            self._save_categories(task_type, categories)
            return True
        return False
