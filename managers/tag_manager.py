"""
标签管理器 - 负责全局标签的增删查改
"""

from typing import List


class TagManager:
    """标签管理器，负责全局标签的 CRUD 操作"""

    def __init__(self, config_manager):
        """
        Args:
            config_manager: ConfigManager 实例，用于读写 global_tags 配置
        """
        self._config_manager = config_manager

    def get_all_tags(self) -> List[str]:
        """获取所有全局标签"""
        tags_str = self._config_manager.get("global_tags", "")
        if not tags_str:
            return []
        return [t.strip() for t in tags_str.split(',') if t.strip()]

    def _save_tags(self, tags: List[str]):
        """保存全局标签列表（内部使用）"""
        tags_str = ','.join(sorted(set(tags)))
        self._config_manager.set("global_tags", tags_str)

    def add_tag(self, tag: str) -> bool:
        """
        添加全局标签

        Args:
            tag: 标签名称

        Returns:
            bool: 是否添加成功（标签已存在时也返回True）
        """
        tag = tag.strip()
        if not tag:
            return False
        tags = self.get_all_tags()
        if tag not in tags:
            tags.append(tag)
            self._save_tags(tags)
        return True

    def delete_tag(self, tag: str, task_checkers: List[callable] = None) -> bool:
        """
        删除全局标签（仅当标签未被任何任务使用时可删除）

        Args:
            tag: 标签名称
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
        tags = self.get_all_tags()
        if tag in tags:
            tags.remove(tag)
            self._save_tags(tags)
            return True
        return False

    def get_or_create(self, tag: str) -> bool:
        """获取或创建标签（如果不存在则创建）"""
        return self.add_tag(tag)
