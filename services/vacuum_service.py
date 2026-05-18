"""
Vacuum 服务 - 封装 SQLite 数据库 VACUUM 逻辑
定期自动回收磁盘空间，优化数据库访问速度
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


class VacuumService:
    """Vacuum 服务，负责检测 DELETE 操作并触发 VACUUM"""

    def __init__(self, engine, trash_db_path: str):
        """
        Args:
            engine: SQLAlchemy engine，用于主数据库
            trash_db_path: 垃圾桶数据库路径
        """
        self._engine = engine
        self._trash_db_path = trash_db_path
        self._delete_count = 0
        self._vacuum_threshold = 100

    def set_threshold(self, threshold: int):
        """设置触发 VACUUM 的 DELETE 次数阈值"""
        self._vacuum_threshold = threshold

    def on_tasks_deleted(self, count: int = 1):
        """通知有 DELETE 操作发生，累加计数器并检查是否需要 VACUUM"""
        self._delete_count += count
        if self._delete_count >= self._vacuum_threshold:
            self.vacuum_if_needed()

    def vacuum_if_needed(self):
        """检查计数器，超过阈值则执行 VACUUM"""
        if self._delete_count < self._vacuum_threshold:
            return False

        logger.info(f"DELETE 计数达到阈值 ({self._delete_count})，开始执行 VACUUM...")
        self._do_vacuum()
        self._delete_count = 0
        return True

    def vacuum_now(self):
        """手动立即执行 VACUUM"""
        logger.info("手动触发执行 VACUUM...")
        self._do_vacuum()
        self._delete_count = 0

    def _do_vacuum(self):
        """对主数据库和垃圾桶数据库分别执行 VACUUM"""
        try:
            self._vacuum_main_db()
            self._vacuum_trash_db()
            logger.info("VACUUM 执行完成")
        except Exception as e:
            logger.error(f"VACUUM 执行失败: {e}")

    def _vacuum_main_db(self):
        """对主数据库执行 VACUUM"""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("PRAGMA vacuum"))
                conn.commit()
            logger.info("主数据库 VACUUM 完成")
        except Exception as e:
            logger.warning(f"主数据库 VACUUM 失败: {e}")

    def _vacuum_trash_db(self):
        """对垃圾桶数据库执行 VACUUM"""
        import sqlite3
        import os
        if not os.path.exists(self._trash_db_path):
            return
        try:
            conn = sqlite3.connect(self._trash_db_path)
            conn.execute("PRAGMA vacuum")
            conn.commit()
            conn.close()
            logger.info("垃圾桶数据库 VACUUM 完成")
        except Exception as e:
            logger.warning(f"垃圾桶数据库 VACUUM 失败: {e}")
