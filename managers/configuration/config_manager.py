"""
配置管理器 - 负责数据库配置的读写
"""

from models.model import Config


class ConfigManager:
    """配置管理器"""

    def __init__(self, session):
        self.session = session

    def get(self, key: str, default: str = "") -> str:
        """获取配置值"""
        config = self.session.query(Config).filter(Config.key == key).first()
        return config.value if config else default

    def set(self, key: str, value: str):
        """设置配置值"""
        config = self.session.query(Config).filter(Config.key == key).first()
        if config:
            config.value = value
        else:
            config = Config(key=key, value=value)
            self.session.add(config)
        self.session.commit()
