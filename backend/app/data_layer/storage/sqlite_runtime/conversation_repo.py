from __future__ import annotations

import sqlite3

from ._types import ConversationMessage, ConversationSession


class SQLiteConversationRepo:
    """SQLite-backed repository for conversation sessions and messages."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Create tables if they do not exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT '',
                sources_json TEXT,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSession]:
        rows = self._conn.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM conversation_sessions
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [
            ConversationSession(
                session_id=r[0],
                title=r[1],
                created_at=r[2],
                updated_at=r[3],
            )
            for r in rows
        ]

    def upsert_session(self, session: ConversationSession) -> None:
        self._conn.execute(
            """
            INSERT INTO conversation_sessions (session_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                title = excluded.title,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            """,
            (
                session.session_id,
                session.title,
                session.created_at,
                session.updated_at,
            ),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> ConversationSession | None:
        row = self._conn.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM conversation_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return ConversationSession(
            session_id=row[0],
            title=row[1],
            created_at=row[2],
            updated_at=row[3],
        )

    def delete_session(self, session_id: str) -> None:
        self._conn.execute(
            "DELETE FROM conversation_messages WHERE session_id = ?",
            (session_id,),
        )
        self._conn.execute(
            "DELETE FROM conversation_sessions WHERE session_id = ?",
            (session_id,),
        )
        self._conn.commit()

    def rename_session(self, session_id: str, title: str) -> bool:
        """重命名会话，返回是否成功"""
        from ._types import utc_now_iso
        cursor = self._conn.execute(
            """
            UPDATE conversation_sessions
            SET title = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (title, utc_now_iso(), session_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def search_sessions(self, keyword: str, limit: int = 20) -> list[ConversationSession]:
        """按标题搜索会话"""
        rows = self._conn.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM conversation_sessions
            WHERE title LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (f"%{keyword}%", limit),
        ).fetchall()
        return [
            ConversationSession(
                session_id=r[0],
                title=r[1],
                created_at=r[2],
                updated_at=r[3],
            )
            for r in rows
        ]

    def search_messages(self, keyword: str, session_id: str | None = None, limit: int = 20) -> list[ConversationMessage]:
        """按内容搜索消息，可选限定会话"""
        if session_id:
            rows = self._conn.execute(
                """
                SELECT id, session_id, role, content, created_at, sources_json
                FROM conversation_messages
                WHERE content LIKE ? AND session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{keyword}%", session_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, session_id, role, content, created_at, sources_json
                FROM conversation_messages
                WHERE content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{keyword}%", limit),
            ).fetchall()
        return [
            ConversationMessage(
                id=r[0],
                session_id=r[1],
                role=r[2],
                content=r[3],
                created_at=r[4],
                sources_json=r[5],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def get_messages(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ConversationMessage]:
        rows = self._conn.execute(
            """
            SELECT id, session_id, role, content, created_at, sources_json
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [
            ConversationMessage(
                id=r[0],
                session_id=r[1],
                role=r[2],
                content=r[3],
                created_at=r[4],
                sources_json=r[5],
            )
            for r in reversed(rows)
        ]

    def save_message(self, msg: ConversationMessage | dict) -> int:
        """插入消息，返回新消息 id。兼容 ConversationMessage 和 dict。"""
        if isinstance(msg, dict):
            msg = ConversationMessage(
                session_id=msg.get("session_id", ""),
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                created_at=msg.get("created_at", ""),
                sources_json=msg.get("sources_json"),
            )
        cursor = self._conn.execute(
            """
            INSERT INTO conversation_messages
                (session_id, role, content, created_at, sources_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                msg.session_id,
                msg.role,
                msg.content,
                msg.created_at,
                msg.sources_json,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def delete_message(self, message_id: int) -> bool:
        """删除单条消息，返回是否成功"""
        cursor = self._conn.execute(
            "DELETE FROM conversation_messages WHERE id = ?",
            (message_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def update_message(self, message_id: int, content: str) -> bool:
        """编辑消息内容，返回是否成功"""
        cursor = self._conn.execute(
            "UPDATE conversation_messages SET content = ? WHERE id = ?",
            (content, message_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0
