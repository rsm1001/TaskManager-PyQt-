"""
配置编排器 - 集中管理基于 Config 表的键值对配置读写
通过依赖注入复用 ConfigManager 仓储层
"""

import logging

logger = logging.getLogger(__name__)


class ConfigOrchestrator:
    """配置编排器

    职责：
        - 简单的 get / set 包装（保留原 DataManager 接口签名）
        - 写入时输出结构化日志
    """

    def __init__(self, config_manager):
        self._config = config_manager

    def get(self, key: str, default: str = "") -> str:
        return self._config.get(key, default)

    def set(self, key: str, value: str) -> None:
        logger.info("写入配置 | request_id=set_config | key=%s", key)
        self._config.set(key, value)
