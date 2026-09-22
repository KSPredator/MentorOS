"""
SQLite-backed persistence layer for MentorOS chat history.

Tables:
  sessions      — tracks known session IDs and creation timestamps
  chat_history  — per-session question/answer log with optional JSON metadata
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MentorOS.APIDatabase")

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mentoros_api.db"

_CREATE_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL,
    last_active  TEXT NOT NULL
);
"""

_CREATE_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS chat_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT    NOT NULL,
    role         TEXT    NOT NULL,   -- 'user' or 'assistant'
    content      TEXT    NOT NULL,
    timestamp    TEXT    NOT NULL,
    metadata     TEXT    DEFAULT NULL  -- JSON blob (planner decision, citations, etc.)
);
"""

_CREATE_HISTORY_IDX = """
CREATE INDEX IF NOT EXISTS idx_chat_history_session
ON chat_history(session_id, timestamp DESC);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatDB:
    """Thread-safe (check_same_thread=False) SQLite wrapper for MentorOS API history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._conn:
            self._conn.execute(_CREATE_SESSIONS_SQL)
            self._conn.execute(_CREATE_HISTORY_SQL)
            self._conn.execute(_CREATE_HISTORY_IDX)

    # ------------------------------------------------------------------ #
    # Session management                                                  #
    # ------------------------------------------------------------------ #

    def ensure_session(self, session_id: str) -> None:
        """Upsert a session record, updating last_active on each call."""
        now = _now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO sessions (session_id, created_at, last_active)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET last_active = excluded.last_active
                """,
                (session_id, now, now),
            )

    # ------------------------------------------------------------------ #
    # Chat history write                                                  #
    # ------------------------------------------------------------------ #

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a chat message and return its auto-generated row ID."""
        self.ensure_session(session_id)
        meta_json = json.dumps(metadata) if metadata else None
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO chat_history (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, _now_iso(), meta_json),
            )
        return cursor.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Chat history read                                                   #
    # ------------------------------------------------------------------ #

    def get_history(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[sqlite3.Row]:
        """Return recent messages for a session (newest last)."""
        rows = self._conn.execute(
            """
            SELECT * FROM (
                SELECT * FROM chat_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ) ORDER BY timestamp ASC
            """,
            (session_id, limit, offset),
        ).fetchall()
        return rows

    def delete_history(self, session_id: str) -> int:
        """Delete all messages for a session. Returns deleted row count."""
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM chat_history WHERE session_id = ?",
                (session_id,),
            )
        return cursor.rowcount  # type: ignore[return-value]

    def close(self) -> None:
        self._conn.close()


# Module-level singleton — reused across all request handlers
_db_instance: Optional[ChatDB] = None


def get_db() -> ChatDB:
    """Return (or create) the shared ChatDB singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ChatDB()
    return _db_instance
