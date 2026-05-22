"""
快捷入口管理器 - 封装快捷入口数据库的所有操作
隔离外部系统（快捷入口DB），遵循仓储模式
"""

from datetime import datetime
import uuid
import sqlite3
import config.config
from typing import List, Dict, Any, Optional


class ShortcutManager:
    """快捷入口管理器，负责 shortcut_entries 表的所有操作"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """初始化快捷入口表结构"""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                shortcut_path TEXT NOT NULL DEFAULT '',
                action_type TEXT NOT NULL DEFAULT 'open',
                category TEXT NOT NULL DEFAULT 'todo',
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # 兼容旧版本：如果 tags 列不存在，则添加
        cursor = self._conn.execute("PRAGMA table_info(shortcut_entries)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'tags' not in columns:
            self._conn.execute("ALTER TABLE shortcut_entries ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        # 兼容旧版本：如果 action_type 列不存在，则添加
        if 'action_type' not in columns:
            self._conn.execute("ALTER TABLE shortcut_entries ADD COLUMN action_type TEXT NOT NULL DEFAULT 'open'")
        self._conn.commit()

    def get_all(self, tag: str = None) -> List[Dict[str, Any]]:
        """获取所有快捷入口，可按标签筛选"""
        if tag:
            cursor = self._conn.execute(
                "SELECT id, title, shortcut_path, action_type, category, tags, created_at FROM shortcut_entries WHERE tags LIKE ? ORDER BY created_at DESC",
                (f'%{tag}%',)
            )
        else:
            cursor = self._conn.execute(
                "SELECT id, title, shortcut_path, action_type, category, tags, created_at FROM shortcut_entries ORDER BY created_at DESC"
            )
        shortcuts = []
        for row in cursor.fetchall():
            sid, title, path, action_type, category, tags, created = row
            shortcuts.append({
                'id': sid,
                'task_id': sid,
                'task_type': category,
                'title': title,
                'shortcut_path': path or '',
                'action_type': action_type or 'open',
                'tags': tags or '',
                'created_at': created or '-'
            })
        return shortcuts

    def create(self, task_type: str, title: str, shortcut_path: str, tags: str = '', action_type: str = 'open') -> bool:
        """创建快捷入口

        Args:
            task_type: 任务类型
            title: 标题
            shortcut_path: 快捷路径
            tags: 标签（逗号分隔）
            action_type: 操作类型 ('open' 或 'script')
        """
        now = datetime.now().isoformat()
        sid = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO shortcut_entries (id, title, shortcut_path, action_type, category, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, title, shortcut_path, action_type, task_type, tags, now, now)
        )
        self._conn.commit()
        return True

    def update(self, shortcut_id: str, title: str = None, shortcut_path: str = None, tags: str = None, action_type: str = None) -> bool:
        """更新快捷入口

        Args:
            shortcut_id: 快捷入口ID
            title: 标题（可选）
            shortcut_path: 路径（可选）
            tags: 标签（可选，逗号分隔）
            action_type: 操作类型（可选，'open' 或 'script'）
        """
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if shortcut_path is not None:
            updates.append("shortcut_path = ?")
            params.append(shortcut_path)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        if action_type is not None:
            updates.append("action_type = ?")
            params.append(action_type)
        if not updates:
            return False
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(shortcut_id)
        self._conn.execute(
            f"UPDATE shortcut_entries SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self._conn.commit()
        return True

    def get_by_id(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取快捷入口"""
        cursor = self._conn.execute(
            "SELECT id, title, shortcut_path, action_type, category, tags, created_at FROM shortcut_entries WHERE id = ?",
            (shortcut_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        sid, title, path, action_type, category, tags, created = row
        return {
            'id': sid, 'title': title, 'shortcut_path': path or '',
            'action_type': action_type or 'open',
            'category': category, 'tags': tags or '', 'created_at': created
        }

    def delete(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """删除快捷入口（返回删除的数据供垃圾箱使用）"""
        shortcut = self.get_by_id(shortcut_id)
        if not shortcut:
            return None
        self._conn.execute("DELETE FROM shortcut_entries WHERE id = ?", (shortcut_id,))
        self._conn.commit()
        return shortcut

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.close()
            self._conn = None
