"""
SQLite helpers for MentorOS API (Phase 9).
Database: data/mentoros.db — tables: sessions, messages, files.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from api import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a connection with Row factory. Caller closes."""
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT 'New Chat',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,               -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    meta        TEXT NOT NULL DEFAULT '{}',  -- JSON blob
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT NOT NULL UNIQUE,
    ext          TEXT NOT NULL,
    size_bytes   INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'processing',  -- processing | indexed | failed
    chunk_count  INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    uploaded_at  TEXT NOT NULL
);
"""


def init_db(db_path: Optional[Path] = None) -> None:
    """Create tables if missing and mark orphaned 'processing' files as failed."""
    conn = get_conn(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.execute(
            "UPDATE files SET status='failed', error='Interrupted by server restart' "
            "WHERE status='processing'"
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #

def create_session(title: str = "New Chat") -> dict:
    conn = get_conn()
    try:
        sid = new_session_id()
        now = _now()
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (sid, title, now, now),
        )
        conn.commit()
        return {"id": sid, "title": title, "created_at": now, "updated_at": now, "message_count": 0}
    finally:
        conn.close()


def get_session(session_id: str) -> Optional[dict]:
    conn = get_conn()
    try:
        row = conn.execute(
            """SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
               FROM sessions s WHERE s.id = ?""",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_sessions() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
               FROM sessions s ORDER BY s.updated_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def rename_session(session_id: str, title: str) -> Optional[dict]:
    conn = get_conn()
    try:
        conn.execute("UPDATE sessions SET title=?, updated_at=? WHERE id=?", (title, _now(), session_id))
        conn.commit()
        return get_session(session_id)
    finally:
        conn.close()


def touch_session(session_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (_now(), session_id))
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id: str) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def auto_title(message: str) -> str:
    """Derive a session title from the first user message (no LLM call)."""
    text = " ".join(message.strip().split())
    if len(text) <= 48:
        return text or "New Chat"
    return text[:48] + "…"


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #

def add_message(session_id: str, role: str, content: str, meta: Optional[dict] = None) -> dict:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, meta, created_at) VALUES (?,?,?,?,?)",
            (session_id, role, content, json.dumps(meta or {}, ensure_ascii=False), _now()),
        )
        conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (_now(), session_id))
        conn.commit()
        return {
            "id": cur.lastrowid,
            "session_id": session_id,
            "role": role,
            "content": content,
            "meta": meta or {},
            "created_at": _now(),
        }
    finally:
        conn.close()


def list_messages(session_id: str) -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["meta"] = json.loads(d.get("meta") or "{}")
            except (json.JSONDecodeError, TypeError):
                d["meta"] = {}
            out.append(d)
        return out
    finally:
        conn.close()


def get_message(message_id: int) -> Optional[dict]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["meta"] = json.loads(d.get("meta") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["meta"] = {}
        return d
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #

def upsert_file_row(
    filename: str,
    ext: str,
    size_bytes: int,
    status: str = "processing",
    chunk_count: int = 0,
    error: Optional[str] = None,
) -> dict:
    conn = get_conn()
    try:
        now = _now()
        conn.execute(
            """
            INSERT INTO files (filename, ext, size_bytes, status, chunk_count, error, uploaded_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(filename) DO UPDATE SET
                ext=excluded.ext, size_bytes=excluded.size_bytes, status=excluded.status,
                chunk_count=excluded.chunk_count, error=excluded.error,
                uploaded_at=excluded.uploaded_at
            """,
            (filename, ext, size_bytes, status, chunk_count, error, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM files WHERE filename=?", (filename,)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def update_file_status(filename: str, status: str, chunk_count: int = 0, error: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE files SET status=?, chunk_count=?, error=? WHERE filename=?",
            (status, chunk_count, error, filename),
        )
        conn.commit()
    finally:
        conn.close()


def list_files() -> list[dict]:
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM files ORDER BY uploaded_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_file(filename: str) -> Optional[dict]:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM files WHERE filename=?", (filename,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_file_row(filename: str) -> bool:
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM files WHERE filename=?", (filename,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def count_indexed_files() -> int:
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM files WHERE status='indexed'").fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()
