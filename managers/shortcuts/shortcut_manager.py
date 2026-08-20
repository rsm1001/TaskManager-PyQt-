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
        """Initialize shortcut schema and migrate legacy databases."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_entries (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                shortcut_path TEXT NOT NULL DEFAULT '',
                action_type TEXT NOT NULL DEFAULT 'open',
                category TEXT NOT NULL DEFAULT 'todo',
                tags TEXT NOT NULL DEFAULT '',
                parent_id TEXT,
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor = self._conn.execute("PRAGMA table_info(shortcut_entries)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'tags' not in columns:
            self._conn.execute(
                "ALTER TABLE shortcut_entries ADD COLUMN tags TEXT NOT NULL DEFAULT ''"
            )
        if 'action_type' not in columns:
            self._conn.execute(
                "ALTER TABLE shortcut_entries ADD COLUMN action_type TEXT NOT NULL DEFAULT 'open'"
            )
        if 'parent_id' not in columns:
            self._conn.execute(
                "ALTER TABLE shortcut_entries ADD COLUMN parent_id TEXT"
            )
        if 'order_index' not in columns:
            self._conn.execute(
                "ALTER TABLE shortcut_entries ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0"
            )

        # The first release supports two levels only. Invalid legacy relations
        # are safely promoted to root entries.
        self._conn.execute("""
            UPDATE shortcut_entries
               SET parent_id = NULL
             WHERE parent_id IS NOT NULL
               AND (parent_id = id OR parent_id NOT IN (
                   SELECT id FROM shortcut_entries WHERE parent_id IS NULL
               ))
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shortcut_entries_parent_id "
            "ON shortcut_entries(parent_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_shortcut_entries_order "
            "ON shortcut_entries(parent_id, order_index, created_at)"
        )
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_repository_profiles (
                parent_shortcut_id TEXT PRIMARY KEY,
                repository_root TEXT NOT NULL,
                remote_name TEXT NOT NULL DEFAULT 'origin',
                base_ref TEXT NOT NULL DEFAULT '',
                launch_script TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shortcut_agent_workspaces (
                shortcut_id TEXT PRIMARY KEY,
                parent_shortcut_id TEXT NOT NULL,
                worktree_path TEXT NOT NULL,
                branch_name TEXT NOT NULL DEFAULT '',
                base_ref TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'active',
                feature_name TEXT NOT NULL DEFAULT '',
                is_pinned INTEGER NOT NULL DEFAULT 0,
                runtime_state TEXT NOT NULL DEFAULT 'stopped',
                last_recycled_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        workspace_columns = {
            row[1] for row in self._conn.execute(
                "PRAGMA table_info(shortcut_agent_workspaces)"
            ).fetchall()
        }
        if 'runtime_state' not in workspace_columns:
            self._conn.execute(
                "ALTER TABLE shortcut_agent_workspaces "
                "ADD COLUMN runtime_state TEXT NOT NULL DEFAULT 'stopped'"
            )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_workspaces_parent_state "
            "ON shortcut_agent_workspaces(parent_shortcut_id, state, updated_at)"
        )
        # Migrate only the old auto-generated labels. User-entered shortcut
        # names remain untouched, while timestamp-heavy agent labels no longer
        # consume most of the tree's name column.
        rows = self._conn.execute(
            """SELECT entries.id, entries.parent_id, entries.title
                 FROM shortcut_entries AS entries
                 JOIN shortcut_agent_workspaces AS workspaces
                   ON workspaces.shortcut_id = entries.id
                 ORDER BY entries.parent_id, entries.order_index, entries.created_at"""
        ).fetchall()
        slot_numbers = {}
        for shortcut_id, parent_id, title in rows:
            slot_numbers[parent_id] = slot_numbers.get(parent_id, 0) + 1
            if (title or '').startswith('🤖 智能体-'):
                self._conn.execute(
                    "UPDATE shortcut_entries SET title = ? WHERE id = ?",
                    ('🤖 子类 {}'.format(slot_numbers[parent_id]), shortcut_id),
                )
        self._conn.commit()

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert a database row while preserving the legacy API fields."""
        sid, title, path, action_type, category, tags, parent_id, order_index, created = row
        return {
            'id': sid,
            'task_id': sid,
            'task_type': category,
            'title': title,
            'shortcut_path': path or '',
            'action_type': action_type or 'open',
            'category': category or '',
            'tags': tags or '',
            'parent_id': parent_id,
            'order_index': order_index or 0,
            'created_at': created or '-',
        }

    def _select_rows(self, where_clause: str = '', params=None) -> List[Dict[str, Any]]:
        params = params or []
        cursor = self._conn.execute(
            "SELECT id, title, shortcut_path, action_type, category, tags, "
            "parent_id, order_index, created_at "
            "FROM shortcut_entries "
            f"{where_clause} "
            "ORDER BY CASE WHEN parent_id IS NULL THEN 0 ELSE 1 END, "
            "COALESCE(parent_id, ''), order_index, created_at DESC",
            params,
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all(self, tag: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        """Get all shortcuts, optionally filtered by tag or keyword."""
        conditions = []
        params = []
        tag_value = tag.strip() if tag else None
        if keyword:
            kw = f"%{keyword}%"
            conditions.append(
                "(title LIKE ? OR tags LIKE ? OR shortcut_path LIKE ? OR category LIKE ?)"
            )
            params.extend([kw, kw, kw, kw])
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ''
        rows = self._select_rows(where_clause, params)
        if tag_value:
            # Tags are comma-separated. Strip only whitespace surrounding each
            # token so internal spaces such as ``project files`` are preserved.
            rows = [
                row for row in rows
                if any(part.strip() == tag_value for part in row.get('tags', '').split(','))
            ]
        return rows

    def get_tree(self, tag: str = None) -> List[Dict[str, Any]]:
        """Get entries for the tree and retain parent context during filtering."""
        all_items = self.get_all()
        if not tag:
            return all_items
        normalized = tag.strip()
        matched_ids = {
            item['id'] for item in all_items
            if normalized in [part.strip() for part in item.get('tags', '').split(',') if part.strip()]
        }
        if not matched_ids:
            return []
        parent_ids = {
            item['parent_id'] for item in all_items
            if item['id'] in matched_ids and item.get('parent_id')
        }
        matched_root_ids = {
            item['id'] for item in all_items
            if item['id'] in matched_ids and not item.get('parent_id')
        }
        child_ids = {
            item['id'] for item in all_items
            if item.get('parent_id') in matched_root_ids
        }
        visible_ids = matched_ids | parent_ids | child_ids
        return [item for item in all_items if item['id'] in visible_ids]

    def get_children(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get direct children of a root shortcut."""
        return self._select_rows("WHERE parent_id = ?", [parent_id])

    def _validate_parent_id(self, shortcut_id: Optional[str], parent_id: Optional[str]) -> bool:
        if parent_id is None:
            return True
        if shortcut_id and parent_id == shortcut_id:
            return False
        row = self._conn.execute(
            "SELECT parent_id FROM shortcut_entries WHERE id = ?", (parent_id,)
        ).fetchone()
        # Two-level hierarchy: a parent must itself be a root entry.
        return row is not None and row[0] is None

    def create(
        self,
        task_type: str,
        title: str,
        shortcut_path: str,
        tags: str = '',
        action_type: str = 'open',
        parent_id: Optional[str] = None,
        order_index: Optional[int] = None,
    ) -> bool:
        """Create a root or child shortcut."""
        if not self._validate_parent_id(None, parent_id):
            return False
        now = datetime.now().isoformat()
        sid = str(uuid.uuid4())
        if order_index is None:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(order_index), -1) + 1 "
                "FROM shortcut_entries WHERE parent_id IS ?", (parent_id,)
            ).fetchone()
            order_index = int(row[0] if row and row[0] is not None else 0)
        self._conn.execute(
            "INSERT INTO shortcut_entries "
            "(id, title, shortcut_path, action_type, category, tags, parent_id, order_index, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, title, shortcut_path, action_type, task_type, tags,
             parent_id, order_index, now, now),
        )
        self._conn.commit()
        return True

    _UNSET = object()

    def update(
        self,
        shortcut_id: str,
        title: str = None,
        shortcut_path: str = None,
        tags: str = None,
        action_type: str = None,
        parent_id=_UNSET,
        order_index: Optional[int] = None,
    ) -> bool:
        """Update a shortcut; omitted parent_id keeps the existing parent."""
        workspace_row = self._conn.execute(
            """SELECT parent_shortcut_id, worktree_path
                 FROM shortcut_agent_workspaces WHERE shortcut_id = ?""",
            (shortcut_id,),
        ).fetchone()
        if workspace_row:
            # A worktree child has a second source of truth. It can be renamed
            # or retagged, but ordinary shortcut edits must never move it or
            # point it at a different directory.
            if shortcut_path is not None and shortcut_path != workspace_row[1]:
                return False
            if parent_id is not self._UNSET and parent_id != workspace_row[0]:
                return False
            if action_type is not None and action_type != 'open':
                return False
        profile_row = self._conn.execute(
            "SELECT 1 FROM shortcut_repository_profiles WHERE parent_shortcut_id = ?",
            (shortcut_id,),
        ).fetchone()
        if profile_row and (
            shortcut_path is not None or parent_id is not self._UNSET
        ):
            # Repository location and root status are managed through the
            # Git-profile workflow, never the generic shortcut editor.
            return False
        if parent_id is not self._UNSET:
            if not self._validate_parent_id(shortcut_id, parent_id):
                return False
            if parent_id is not None:
                current = self._conn.execute(
                    "SELECT parent_id FROM shortcut_entries WHERE id = ?", (shortcut_id,)
                ).fetchone()
                child_count = self._conn.execute(
                    "SELECT COUNT(*) FROM shortcut_entries WHERE parent_id = ?", (shortcut_id,)
                ).fetchone()[0]
                # A root with children cannot itself become a child in the two-level model.
                if current is not None and current[0] is None and child_count:
                    return False
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
        if parent_id is not self._UNSET:
            updates.append("parent_id = ?")
            params.append(parent_id)
        if order_index is not None:
            updates.append("order_index = ?")
            params.append(order_index)
        if not updates:
            return False
        updates.append("updated_at = ?")
        params.extend([datetime.now().isoformat(), shortcut_id])
        cursor = self._conn.execute(
            f"UPDATE shortcut_entries SET {', '.join(updates)} WHERE id = ?", params
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_by_id(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Get one shortcut by ID."""
        rows = self._select_rows("WHERE id = ?", [shortcut_id])
        return rows[0] if rows else None

    def get_tree_by_id(self, shortcut_id: str) -> List[Dict[str, Any]]:
        """Get an entry and its direct children for bundled delete/restore."""
        root = self.get_by_id(shortcut_id)
        if not root:
            return []
        children = self.get_children(shortcut_id)
        return [root] + children

    def delete_tree(self, shortcut_id: str) -> List[Dict[str, Any]]:
        """Delete an entry and its direct children and return the snapshot."""
        entries = self.get_tree_by_id(shortcut_id)
        if not entries:
            return []
        # The trash payload is the authoritative recovery snapshot. Keep the
        # root's Git configuration with it; otherwise restoring a repository
        # shortcut would restore only its path and silently lose its launcher
        # and integration-branch settings.
        profile = self.get_repository_profile(shortcut_id)
        if profile:
            entries[0]['_repository_profile'] = profile
        ids = [entry['id'] for entry in entries]
        placeholders = ','.join('?' for _ in ids)
        self._conn.execute(
            f"DELETE FROM shortcut_agent_workspaces WHERE shortcut_id IN ({placeholders})", ids
        )
        self._conn.execute(
            f"DELETE FROM shortcut_repository_profiles WHERE parent_shortcut_id IN ({placeholders})", ids
        )
        self._conn.execute(
            f"DELETE FROM shortcut_entries WHERE id IN ({placeholders})", ids
        )
        self._conn.commit()
        return entries

    def delete(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Legacy delete API; deleting a root also deletes its direct children."""
        entries = self.delete_tree(shortcut_id)
        if not entries:
            return None
        root = dict(entries[0])
        if len(entries) > 1:
            root['_children'] = entries[1:]
        return root

    # ==================== 智能体 Git 工作区 ====================

    def save_repository_profile(
        self,
        parent_shortcut_id: str,
        repository_root: str,
        remote_name: str = 'origin',
        base_ref: str = '',
        launch_script: str = '',
    ) -> None:
        """Persist Git settings for a root shortcut without changing normal shortcuts."""
        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO shortcut_repository_profiles
               (parent_shortcut_id, repository_root, remote_name, base_ref, launch_script, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(parent_shortcut_id) DO UPDATE SET
                 repository_root=excluded.repository_root,
                 remote_name=excluded.remote_name,
                 base_ref=excluded.base_ref,
                 launch_script=excluded.launch_script,
                 updated_at=excluded.updated_at""",
            (parent_shortcut_id, repository_root, remote_name, base_ref, launch_script, now),
        )
        self._conn.commit()

    def get_repository_profile(self, parent_shortcut_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            """SELECT parent_shortcut_id, repository_root, remote_name, base_ref,
                      launch_script, updated_at
                 FROM shortcut_repository_profiles WHERE parent_shortcut_id = ?""",
            (parent_shortcut_id,),
        ).fetchone()
        if not row:
            return None
        return {
            'parent_shortcut_id': row[0], 'repository_root': row[1],
            'remote_name': row[2] or 'origin', 'base_ref': row[3] or '',
            'launch_script': row[4] or '', 'updated_at': row[5] or '',
        }

    def create_agent_workspace(
        self,
        parent_shortcut_id: str,
        title: str,
        worktree_path: str,
        branch_name: str,
        base_ref: str,
        feature_name: str,
    ) -> Dict[str, Any]:
        """Create a child shortcut and its worktree metadata as one DB transaction."""
        now = datetime.now().isoformat()
        shortcut_id = str(uuid.uuid4())
        row = self._conn.execute(
            "SELECT COALESCE(MAX(order_index), -1) + 1 FROM shortcut_entries WHERE parent_id = ?",
            (parent_shortcut_id,),
        ).fetchone()
        order_index = int(row[0] if row else 0)
        try:
            self._conn.execute(
                """INSERT INTO shortcut_entries
                   (id, title, shortcut_path, action_type, category, tags, parent_id,
                    order_index, created_at, updated_at)
                   VALUES (?, ?, ?, 'open', 'workspace', '', ?, ?, ?, ?)""",
                (shortcut_id, title, worktree_path, parent_shortcut_id,
                 order_index, now, now),
            )
            self._conn.execute(
                """INSERT INTO shortcut_agent_workspaces
                   (shortcut_id, parent_shortcut_id, worktree_path, branch_name, base_ref,
                    state, feature_name, is_pinned, runtime_state, last_recycled_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?, 0, 'stopped', '', ?)""",
                (shortcut_id, parent_shortcut_id, worktree_path, branch_name,
                 base_ref, feature_name, now),
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return self.get_by_id(shortcut_id)

    def get_agent_workspace(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            """SELECT shortcut_id, parent_shortcut_id, worktree_path, branch_name, base_ref,
                      state, feature_name, is_pinned, runtime_state, last_recycled_at, updated_at
                 FROM shortcut_agent_workspaces WHERE shortcut_id = ?""",
            (shortcut_id,),
        ).fetchone()
        if not row:
            return None
        keys = ('shortcut_id', 'parent_shortcut_id', 'worktree_path', 'branch_name',
                'base_ref', 'state', 'feature_name', 'is_pinned', 'runtime_state',
                'last_recycled_at', 'updated_at')
        return dict(zip(keys, row))

    def get_idle_agent_workspaces(self, parent_shortcut_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT shortcut_id FROM shortcut_agent_workspaces
                 WHERE parent_shortcut_id = ? AND state = 'idle' AND is_pinned = 0
                 ORDER BY updated_at ASC""",
            (parent_shortcut_id,),
        ).fetchall()
        return [self.get_agent_workspace(row[0]) for row in rows]

    def has_agent_workspaces(self, parent_shortcut_id: str) -> bool:
        """Return whether a repository still owns any managed worktree child."""
        row = self._conn.execute(
            "SELECT 1 FROM shortcut_agent_workspaces WHERE parent_shortcut_id = ? LIMIT 1",
            (parent_shortcut_id,),
        ).fetchone()
        return row is not None

    def count_active_agent_workspaces(self, parent_shortcut_id: str) -> int:
        """Count active children so an optional concurrent-agent cap can apply."""
        row = self._conn.execute(
            """SELECT COUNT(*) FROM shortcut_agent_workspaces
                 WHERE parent_shortcut_id = ? AND state = 'active'""",
            (parent_shortcut_id,),
        ).fetchone()
        return int(row[0] if row else 0)

    def count_agent_workspaces(self, parent_shortcut_id: str) -> int:
        """Count all slots, including idle ones, for a stable short display name."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM shortcut_agent_workspaces WHERE parent_shortcut_id = ?",
            (parent_shortcut_id,),
        ).fetchone()
        return int(row[0] if row else 0)

    def update_agent_workspace(self, shortcut_id: str, **values: Any) -> bool:
        allowed = {
            'worktree_path', 'branch_name', 'base_ref', 'state', 'feature_name',
            'is_pinned', 'runtime_state', 'last_recycled_at',
        }
        updates = []
        params = []
        for key, value in values.items():
            if key in allowed:
                updates.append(f"{key} = ?")
                params.append(value)
        if not updates:
            return False
        updates.append("updated_at = ?")
        params.extend([datetime.now().isoformat(), shortcut_id])
        cursor = self._conn.execute(
            f"UPDATE shortcut_agent_workspaces SET {', '.join(updates)} WHERE shortcut_id = ?",
            params,
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def remove_agent_workspace(self, shortcut_id: str) -> bool:
        """Remove metadata and its child shortcut after Git removed the worktree."""
        self._conn.execute("DELETE FROM shortcut_agent_workspaces WHERE shortcut_id = ?", (shortcut_id,))
        cursor = self._conn.execute("DELETE FROM shortcut_entries WHERE id = ?", (shortcut_id,))
        self._conn.commit()
        return cursor.rowcount > 0

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

    def get_codex_dangerously_skip_permissions(self) -> bool:
        """获取 Codex 启动时是否放权（--dangerously-skip-permissions）"""
        cursor = self._conn.execute(
            "SELECT value FROM configs WHERE key = ?",
            (config.config.CODEX_DANGEROUS_SKIP_PERMISSIONS_KEY,)
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return config.config.CODEX_DANGEROUS_SKIP_PERMISSIONS_DEFAULT
        return str(row[0]).strip().lower() in ('1', 'true', 'yes', 'on')

    def set_codex_dangerously_skip_permissions(self, enabled: bool) -> bool:
        """设置 Codex 启动时是否放权"""
        now = datetime.now().isoformat()
        key = config.config.CODEX_DANGEROUS_SKIP_PERMISSIONS_KEY
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
