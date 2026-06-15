"""
Orchestrator Factory - 编排器工厂
使用工厂模式统一创建与缓存业务编排器（Orchestrator）
与 ServiceFactory 风格保持一致：单例缓存 + 结构化日志
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OrchestratorFactory:
    """编排器工厂

    通过依赖注入统一创建 TaskOrchestrator / ShortcutOrchestrator /
    TagOrchestrator / TrashOrchestrator / ConfigOrchestrator 五个业务编排器
    """

    def __init__(self, data_manager):
        """
        Args:
            data_manager: DataManager 实例（提供底层 Repository 与服务）
        """
        self._dm = data_manager
        self._instances: Dict[str, Any] = {}
        logger.debug("OrchestratorFactory 初始化完成 | request_id=init")

    def get_task_orchestrator(self):
        """获取任务编排器（单例）"""
        if "task" not in self._instances:
            from managers.task_orchestrator import TaskOrchestrator

            self._instances["task"] = TaskOrchestrator(
                session=self._dm.get_session(),
                daily_task_manager=self._dm.daily_task_manager,
                todo_task_manager=self._dm.todo_manager,
                entertainment_task_manager=self._dm.entertainment_manager,
                trash_manager=self._dm.trash_manager,
                task_limit_service_factory=self._dm._get_task_limit_service,
                shortcut_manager=self._dm.shortcut_manager,
            )
            logger.info("TaskOrchestrator 已创建 | request_id=create_orchestrator")
        return self._instances["task"]

    def get_shortcut_orchestrator(self):
        """获取快捷入口编排器（单例）"""
        if "shortcut" not in self._instances:
            from managers.shortcut_orchestrator import ShortcutOrchestrator

            self._instances["shortcut"] = ShortcutOrchestrator(
                shortcut_manager=self._dm.shortcut_manager,
                trash_manager=self._dm.trash_manager,
            )
            logger.info("ShortcutOrchestrator 已创建 | request_id=create_orchestrator")
        return self._instances["shortcut"]

    def get_tag_orchestrator(self):
        """获取标签编排器（单例）"""
        if "tag" not in self._instances:
            from managers.tag_orchestrator import TagOrchestrator

            self._instances["tag"] = TagOrchestrator(
                tag_manager=self._dm.tag_manager,
                config_manager=self._dm.config_manager,
                task_provider=self._collect_tasks_by_category,
            )
            logger.info("TagOrchestrator 已创建 | request_id=create_orchestrator")
        return self._instances["tag"]

    def get_trash_orchestrator(self):
        """获取垃圾桶编排器（单例）"""
        if "trash" not in self._instances:
            from managers.trash_orchestrator import TrashOrchestrator

            self._instances["trash"] = TrashOrchestrator(
                trash_manager=self._dm.trash_manager,
                trash_restoration_service=self._dm.trash_restoration_service,
            )
            logger.info("TrashOrchestrator 已创建 | request_id=create_orchestrator")
        return self._instances["trash"]

    def get_config_orchestrator(self):
        """获取配置编排器（单例）"""
        if "config" not in self._instances:
            from managers.config_orchestrator import ConfigOrchestrator

            self._instances["config"] = ConfigOrchestrator(
                config_manager=self._dm.config_manager,
            )
            logger.info("ConfigOrchestrator 已创建 | request_id=create_orchestrator")
        return self._instances["config"]

    # ==================== 跨编排器辅助 ====================

    def _collect_tasks_by_category(self, category: str):
        """按类别收集任务/快捷入口（供 TagOrchestrator 复用）

        Args:
            category: 任务类别 ('daily' / 'todo' / 'entertainment' / 'shortcut')

        Yields:
            任务对象或快捷入口 dict
        """
        if category == "daily":
            yield from self._dm.get_daily_tasks()
        elif category == "todo":
            yield from self._dm.get_todo_tasks()
        elif category == "entertainment":
            yield from self._dm.get_entertainment_tasks()
        elif category == "shortcut":
            yield from self._dm.get_all_shortcuts()
