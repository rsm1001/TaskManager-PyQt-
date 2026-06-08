"""
数据访问层 - 集中管理数据库连接与会话生命周期
为上层业务编排器（Orchestrator）提供低层基础设施
遵循 Repository 模式：将基础设施（数据库连接）与业务逻辑解耦
"""

import logging
import sqlite3
from typing import Optional

import config.config
from models.model import init_db

logger = logging.getLogger(__name__)


class DataAccess:
    """数据访问对象

    职责：
        - 初始化 SQLAlchemy 引擎与 Session
        - 维护主库、垃圾桶库的 sqlite3 原生连接（供非 ORM 仓储使用）
        - 统一管理连接与 Session 的关闭
    """

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库连接

        Args:
            db_path: 主数据库路径，默认读取 config.config.DATABASE_PATH
        """
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        self.db_path = db_path
        self.trash_db_path = config.config.TRASH_DATABASE_PATH

        # ORM 引擎与 Session 工厂
        self.engine, self.Session = init_db(db_path, run_migration=True)
        self.session = self.Session()
        logger.info(
            "DataAccess 初始化完成 | request_id=init | db_path=%s",
            db_path,
        )

        # 共享的 sqlite3 原生连接（避免文件锁争用）
        self._main_conn: Optional[sqlite3.Connection] = sqlite3.connect(
            self.db_path, check_same_thread=False
        )
        self._trash_conn: Optional[sqlite3.Connection] = sqlite3.connect(
            self.trash_db_path, check_same_thread=False
        )

    def get_main_connection(self) -> sqlite3.Connection:
        """获取主数据库的 sqlite3 原生连接"""
        return self._main_conn

    def get_trash_connection(self) -> sqlite3.Connection:
        """获取垃圾桶数据库的 sqlite3 原生连接"""
        return self._trash_conn

    def get_session(self):
        """获取 ORM Session"""
        return self.session

    def commit(self):
        """提交当前事务"""
        self.session.commit()

    def rollback(self):
        """回滚当前事务"""
        self.session.rollback()

    def close(self):
        """统一关闭所有连接与 Session"""
        logger.info("DataAccess 开始关闭资源 | request_id=close")
        try:
            if self.session:
                self.session.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("关闭 ORM Session 失败: %s", exc)

        try:
            if self._main_conn:
                self._main_conn.close()
                self._main_conn = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("关闭主数据库连接失败: %s", exc)

        try:
            if self._trash_conn:
                self._trash_conn.close()
                self._trash_conn = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("关闭垃圾桶连接失败: %s", exc)
        logger.info("DataAccess 资源已释放 | request_id=close")
