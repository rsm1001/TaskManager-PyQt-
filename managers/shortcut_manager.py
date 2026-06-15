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

    def __init__(self, db_path: str = None, connection=None):
        if db_path is None:
            db_path = config.config.DATABASE_PATH
        if connection is not None:
            self._conn = connection
            self._owns_connection = False
        else:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._owns_connection = True
        self._init_db()
        self._init_history_db()

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

    def get_all(self, tag: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        """获取所有快捷入口，可按标签/关键词筛选

        Args:
            tag: 标签筛选（逗号分隔的标签中包含该值），None 不过滤
            keyword: 关键词筛选（模糊匹配 title/tags/shortcut_path/category）
        """
        conditions = []
        params = []

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                "(title LIKE ? OR tags LIKE ? OR shortcut_path LIKE ? OR category LIKE ?)"
            )
            params.extend([kw, kw, kw, kw])

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        cursor = self._conn.execute(
            f"SELECT id, title, shortcut_path, action_type, category, tags, created_at FROM shortcut_entries{where_clause} ORDER BY created_at DESC",
            params
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

    # ==================== 历史记录相关方法 ====================

    def _init_history_db(self):
        """初始化历史记录表结构"""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_history (
                id TEXT PRIMARY KEY,
                shortcut_id TEXT NOT NULL,
                shortcut_title TEXT NOT NULL DEFAULT '',
                shortcut_path TEXT NOT NULL DEFAULT '',
                action_type TEXT NOT NULL DEFAULT 'open',
                opened_at TEXT NOT NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0
            )
        """)
        # 兼容旧版本：检查并添加字段
        cursor = self._conn.execute("PRAGMA table_info(shortcut_history)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'is_pinned' not in columns:
            self._conn.execute("ALTER TABLE shortcut_history ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
        if 'action_type' not in columns:
            self._conn.execute("ALTER TABLE shortcut_history ADD COLUMN action_type TEXT NOT NULL DEFAULT 'open'")
        if 'shortcut_title' not in columns:
            self._conn.execute("ALTER TABLE shortcut_history ADD COLUMN shortcut_title TEXT NOT NULL DEFAULT ''")
        if 'shortcut_path' not in columns:
            self._conn.execute("ALTER TABLE shortcut_history ADD COLUMN shortcut_path TEXT NOT NULL DEFAULT ''")
        if 'opened_at' not in columns:
            self._conn.execute("ALTER TABLE shortcut_history ADD COLUMN opened_at TEXT NOT NULL DEFAULT ''")
        self._conn.commit()

    def get_history_limit(self) -> int:
        """获取历史记录缓存数量限制"""
        cursor = self._conn.execute(
            "SELECT value FROM configs WHERE key = ?", ('shortcut_history_limit',)
        )
        row = cursor.fetchone()
        if row and row[0]:
            return int(row[0])
        return config.config.SHORTCUT_HISTORY_DEFAULT_LIMIT

    def set_history_limit(self, limit: int) -> bool:
        """设置历史记录缓存数量限制"""
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            "SELECT id FROM configs WHERE key = ?", ('shortcut_history_limit',)
        )
        row = cursor.fetchone()
        if row:
            self._conn.execute(
                "UPDATE configs SET value = ?, updated_at = ? WHERE key = ?",
                (str(limit), now, 'shortcut_history_limit')
            )
        else:
            from models.model import BaseModel
            import uuid
            config_id = str(uuid.uuid4())
            self._conn.execute(
                "INSERT INTO configs (id, key, value, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (config_id, 'shortcut_history_limit', str(limit), now, now)
            )
        self._conn.commit()
        return True

    def get_dangerously_skip_permissions(self) -> bool:
        """获取 Claude 启动时是否放权（--dangerously-skip-permissions）"""
        cursor = self._conn.execute(
            "SELECT value FROM configs WHERE key = ?",
            (config.config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_KEY,)
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return config.config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_DEFAULT
        return str(row[0]).strip().lower() in ('1', 'true', 'yes', 'on')

    def set_dangerously_skip_permissions(self, enabled: bool) -> bool:
        """设置 Claude 启动时是否放权"""
        now = datetime.now().isoformat()
        key = config.config.CLAUDE_DANGEROUS_SKIP_PERMISSIONS_KEY
        value = '1' if enabled else '0'
        cursor = self._conn.execute(
            "SELECT id FROM configs WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row:
            self._conn.execute(
                "UPDATE configs SET value = ?, updated_at = ? WHERE key = ?",
                (value, now, key)
            )
        else:
            import uuid
            config_id = str(uuid.uuid4())
            self._conn.execute(
                "INSERT INTO configs (id, key, value, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (config_id, key, value, now, now)
            )
        self._conn.commit()
        return True

    def get_all_history(self) -> List[Dict[str, Any]]:
        """获取所有历史记录，按最后打开时间倒序"""
        cursor = self._conn.execute(
            "SELECT id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned FROM shortcut_history ORDER BY is_pinned DESC, opened_at DESC"
        )
        history = []
        for row in cursor.fetchall():
            hid, sid, title, path, action_type, opened_at, is_pinned = row
            history.append({
                'id': hid,
                'shortcut_id': sid,
                'shortcut_title': title or '',
                'shortcut_path': path or '',
                'action_type': action_type or 'open',
                'opened_at': opened_at or '',
                'is_pinned': is_pinned or 0
            })
        return history

    def get_history_by_shortcut_id(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """根据快捷入口ID获取历史记录"""
        cursor = self._conn.execute(
            "SELECT id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned FROM shortcut_history WHERE shortcut_id = ?",
            (shortcut_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        hid, sid, title, path, action_type, opened_at, is_pinned = row
        return {
            'id': hid,
            'shortcut_id': sid,
            'shortcut_title': title or '',
            'shortcut_path': path or '',
            'action_type': action_type or 'open',
            'opened_at': opened_at or '',
            'is_pinned': is_pinned or 0
        }

    def add_or_update_history(self, shortcut_id: str, shortcut_title: str, shortcut_path: str, action_type: str = 'open') -> bool:
        """添加或更新历史记录（如果已存在则更新时间戳）"""
        existing = self.get_history_by_shortcut_id(shortcut_id)
        now = datetime.now().isoformat()
        if existing:
            self._conn.execute(
                "UPDATE shortcut_history SET opened_at = ?, shortcut_title = ?, shortcut_path = ?, action_type = ? WHERE shortcut_id = ?",
                (now, shortcut_title, shortcut_path, action_type, shortcut_id)
            )
        else:
            hid = str(uuid.uuid4())
            self._conn.execute(
                "INSERT INTO shortcut_history (id, shortcut_id, shortcut_title, shortcut_path, action_type, opened_at, is_pinned) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (hid, shortcut_id, shortcut_title, shortcut_path, action_type, now)
            )
        self._conn.commit()
        return True

    def cleanup_history_except_pinned(self, keep_count: int) -> int:
        """清理最旧的非置顶历史记录，保留最近 keep_count 条，返回删除数量"""
        # 先统计非置顶记录数
        cursor = self._conn.execute("SELECT COUNT(*) FROM shortcut_history WHERE is_pinned = 0")
        total_count = cursor.fetchone()[0]
        if total_count <= keep_count:
            return 0
        # 删除最旧的多余记录（保留 keep_count 条）
        delete_count = total_count - keep_count
        self._conn.execute(
            """DELETE FROM shortcut_history WHERE id IN (
                SELECT id FROM shortcut_history WHERE is_pinned = 0
                ORDER BY opened_at ASC LIMIT ?
            )""",
            (delete_count,)
        )
        self._conn.commit()
        return delete_count

    def toggle_history_pin(self, history_id: str) -> bool:
        """切换历史记录的置顶状态"""
        cursor = self._conn.execute("SELECT is_pinned FROM shortcut_history WHERE id = ?", (history_id,))
        row = cursor.fetchone()
        if not row:
            return False
        new_pinned = 1 if row[0] == 0 else 0
        self._conn.execute("UPDATE shortcut_history SET is_pinned = ? WHERE id = ?", (new_pinned, history_id))
        self._conn.commit()
        return True

    def delete_history(self, history_id: str) -> bool:
        """删除历史记录（置顶记录不可删除）"""
        cursor = self._conn.execute("SELECT is_pinned FROM shortcut_history WHERE id = ?", (history_id,))
        row = cursor.fetchone()
        if not row:
            return False
        if row[0] == 1:
            # 置顶记录不可删除
            return False
        self._conn.execute("DELETE FROM shortcut_history WHERE id = ?", (history_id,))
        self._conn.commit()
        return True

    def clear_all_unpinned_history(self) -> int:
        """清空所有非置顶历史记录，返回删除数量"""
        cursor = self._conn.execute("SELECT COUNT(*) FROM shortcut_history WHERE is_pinned = 0")
        count = cursor.fetchone()[0]
        self._conn.execute("DELETE FROM shortcut_history WHERE is_pinned = 0")
        self._conn.commit()
        return count

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, '_conn') and self._conn and self._owns_connection:
            self._conn.close()
            self._conn = None
