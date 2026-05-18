"""
垃圾桶管理器 - 封装垃圾桶数据库的所有操作
隔离外部系统（垃圾桶DB），遵循仓储模式
"""

from datetime import datetime
import uuid
import json
import sqlite3
import config.config
from typing import List, Optional, Dict, Any


class TrashManager:
    """垃圾桶管理器，负责 trashed_tasks 表的所有操作"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.config.TRASH_DATABASE_PATH
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """初始化垃圾桶表结构"""
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS trashed_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                data_json TEXT NOT NULL,
                deleted_at TEXT NOT NULL
            )
        ''')
        self._conn.commit()

    def move_to_trash(self, task_type: str, task_id: str, task_data: Dict[str, Any]) -> str:
        """将任务移入垃圾桶"""
        trash_id = str(uuid.uuid4())
        self._conn.execute(
            'INSERT INTO trashed_tasks (id, task_type, task_id, data_json, deleted_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (trash_id, task_type, task_id, json.dumps(task_data, ensure_ascii=False), datetime.now().isoformat())
        )
        self._conn.commit()
        return trash_id

    def get_trashed_tasks(self, task_type: str = None) -> List[tuple]:
        """获取垃圾桶中的任务列表"""
        if task_type:
            cursor = self._conn.execute(
                'SELECT id, task_type, task_id, data_json, deleted_at '
                'FROM trashed_tasks WHERE task_type = ? ORDER BY deleted_at DESC',
                (task_type,)
            )
        else:
            cursor = self._conn.execute(
                'SELECT id, task_type, task_id, data_json, deleted_at '
                'FROM trashed_tasks ORDER BY deleted_at DESC'
            )
        return cursor.fetchall()

    def get_by_id(self, trash_id: str) -> Optional[Dict[str, Any]]:
        """根据垃圾记录ID获取原始任务数据"""
        cursor = self._conn.execute(
            'SELECT task_type, data_json FROM trashed_tasks WHERE id = ?',
            (trash_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {'task_type': row[0], 'data': json.loads(row[1])}

    def delete_trash_record(self, trash_id: str):
        """删除垃圾桶记录"""
        self._conn.execute('DELETE FROM trashed_tasks WHERE id = ?', (trash_id,))
        self._conn.commit()

    def delete_trash_records(self, trash_ids: List[str]):
        """批量删除垃圾桶记录"""
        if not trash_ids:
            return
        placeholders = ','.join('?' * len(trash_ids))
        self._conn.execute(
            f'DELETE FROM trashed_tasks WHERE id IN ({placeholders})',
            trash_ids
        )
        self._conn.commit()

    def purge_all(self, task_type: str = None):
        """清空垃圾桶"""
        if task_type:
            self._conn.execute('DELETE FROM trashed_tasks WHERE task_type = ?', (task_type,))
        else:
            self._conn.execute('DELETE FROM trashed_tasks')
        self._conn.commit()

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.close()
            self._conn = None
