"""
SQLite helpers for MentorOS API (Phase 9).
Database: data/mentoros.db — tables: sessions, messages, files.
"""

import hashlib
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

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     TEXT PRIMARY KEY,
    source_file  TEXT NOT NULL,
    doc_slug     TEXT NOT NULL,
    page_number  INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    text         TEXT NOT NULL,
    token_count  INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_file);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_slug ON chunks(doc_slug);
"""


def init_db(db_path: Optional[Path] = None) -> None:
    """Create tables if missing and mark orphaned 'processing' files as failed."""
    conn = get_conn(db_path)
    try:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(chunks)").fetchall()]
        if cols:
            if "doc_slug" not in cols:
                conn.execute("ALTER TABLE chunks ADD COLUMN doc_slug TEXT NOT NULL DEFAULT ''")
            if "page_number" not in cols:
                conn.execute("ALTER TABLE chunks ADD COLUMN page_number INTEGER NOT NULL DEFAULT 1")
            if "doc_id" in cols and "unit_no" in cols:
                conn.execute("UPDATE chunks SET doc_slug = doc_id, page_number = unit_no WHERE doc_slug = ''")
            conn.commit()

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


# --------------------------------------------------------------------------- #
# Chunks (Step 2: Stable chunk IDs and SQLite provenance table)
# --------------------------------------------------------------------------- #

def upsert_chunks(chunks: list) -> int:
    """Upsert document chunks into SQLite chunks table for O(1) ID lookups."""
    if not chunks:
        return 0
    conn = get_conn()
    try:
        now = _now()
        cols = [c[1] for c in conn.execute("PRAGMA table_info(chunks)").fetchall()]
        has_doc_id = "doc_id" in cols

        # If relational documents table is present, ensure parent documents exist
        if has_doc_id:
            doc_table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'").fetchone()
            if doc_table:
                course_table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='courses'").fetchone()
                if course_table:
                    conn.execute(
                        "INSERT OR IGNORE INTO courses (course_id, name, bundle_path, embed_model, created_at) "
                        "VALUES ('default', 'Default Course', 'bundle/default', 'all-MiniLM-L6-v2', ?)",
                        (now,)
                    )

                doc_pairs = set()
                for c in chunks:
                    sfile = getattr(c, "source_file", "") or (c.get("source_file", "") if isinstance(c, dict) else "")
                    slug = getattr(c, "doc_slug", "") or (
                        c.metadata.get("doc_slug", "")
                        if hasattr(c, "metadata") and isinstance(c.metadata, dict)
                        else (c.get("doc_slug", "") or c.get("metadata", {}).get("doc_slug", "") if isinstance(c, dict) else "")
                    ) or (sfile.rsplit(".", 1)[0].lower() if sfile else "default-doc")
                    if slug:
                        doc_pairs.add((slug, sfile))

                for slug, sfile in doc_pairs:
                    conn.execute(
                        "INSERT OR IGNORE INTO documents (doc_id, course_id, slug, filename, content_hash, version, status, created_at, updated_at) "
                        "VALUES (?, 'default', ?, ?, 'hash', 1, 'indexed', ?, ?)",
                        (slug, slug, sfile, now, now)
                    )
                conn.commit()

        if has_doc_id:
            records = []
            for c in chunks:
                if hasattr(c, "chunk_id"):
                    cid = c.chunk_id
                    sfile = c.source_file
                    slug = getattr(c, "doc_slug", "") or (
                        c.metadata.get("doc_slug", "")
                        if hasattr(c, "metadata") and isinstance(c.metadata, dict)
                        else ""
                    ) or (sfile.rsplit(".", 1)[0].lower() if sfile else "default-doc")
                    pnum = getattr(c, "page_number", 1)
                    cidx = getattr(c, "chunk_index", 0)
                    txt = getattr(c, "text", "")
                    toks = getattr(c, "token_count", 0)
                    doc_version = getattr(c, "doc_version", 1) or 1
                    unit = getattr(c, "unit", "page") or "page"
                    unit_no = getattr(c, "unit_no", pnum) or pnum
                    thash = getattr(c, "text_hash", "") or hashlib.sha256(txt.strip().encode("utf-8")).hexdigest()
                    legacy_id = getattr(c, "legacy_id", None)
                elif isinstance(c, dict):
                    cid = c.get("chunk_id", "")
                    sfile = c.get("source_file", "")
                    slug = c.get("doc_slug", "") or (
                        c.get("metadata", {}).get("doc_slug", "")
                        if isinstance(c.get("metadata"), dict)
                        else ""
                    ) or (sfile.rsplit(".", 1)[0].lower() if sfile else "default-doc")
                    pnum = c.get("page_number", 1)
                    cidx = c.get("chunk_index", 0)
                    txt = c.get("text", "")
                    toks = c.get("token_count", 0)
                    doc_version = c.get("doc_version", 1) or 1
                    unit = c.get("unit", "page") or "page"
                    unit_no = c.get("unit_no", pnum) or pnum
                    thash = c.get("text_hash", "") or hashlib.sha256(txt.strip().encode("utf-8")).hexdigest()
                    legacy_id = c.get("legacy_id")
                else:
                    continue

                records.append((
                    cid, slug, int(doc_version), unit, int(unit_no), int(cidx),
                    thash, txt, int(toks), sfile, legacy_id, now, slug, int(pnum)
                ))

            if not records:
                return 0

            conn.executemany(
                """
                INSERT INTO chunks (
                    chunk_id, doc_id, doc_version, unit, unit_no, chunk_index,
                    text_hash, text, token_count, source_file, legacy_id, created_at,
                    doc_slug, page_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    doc_id=excluded.doc_id,
                    doc_version=excluded.doc_version,
                    unit=excluded.unit,
                    unit_no=excluded.unit_no,
                    chunk_index=excluded.chunk_index,
                    text_hash=excluded.text_hash,
                    text=excluded.text,
                    token_count=excluded.token_count,
                    source_file=excluded.source_file,
                    legacy_id=excluded.legacy_id,
                    created_at=excluded.created_at,
                    doc_slug=excluded.doc_slug,
                    page_number=excluded.page_number
                """,
                records,
            )
        else:
            records = []
            for c in chunks:
                if hasattr(c, "chunk_id"):
                    cid = c.chunk_id
                    sfile = c.source_file
                    slug = getattr(c, "doc_slug", "") or (
                        c.metadata.get("doc_slug", "")
                        if hasattr(c, "metadata") and isinstance(c.metadata, dict)
                        else ""
                    )
                    pnum = c.page_number
                    cidx = c.chunk_index
                    txt = c.text
                    toks = c.token_count
                elif isinstance(c, dict):
                    cid = c.get("chunk_id", "")
                    sfile = c.get("source_file", "")
                    slug = c.get("doc_slug", "") or (
                        c.get("metadata", {}).get("doc_slug", "")
                        if isinstance(c.get("metadata"), dict)
                        else ""
                    )
                    pnum = c.get("page_number", 1)
                    cidx = c.get("chunk_index", 0)
                    txt = c.get("text", "")
                    toks = c.get("token_count", 0)
                else:
                    continue

                records.append((cid, sfile, slug, int(pnum), int(cidx), txt, int(toks), now))

            if not records:
                return 0

            conn.executemany(
                """
                INSERT INTO chunks (chunk_id, source_file, doc_slug, page_number, chunk_index, text, token_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    source_file=excluded.source_file,
                    doc_slug=excluded.doc_slug,
                    page_number=excluded.page_number,
                    chunk_index=excluded.chunk_index,
                    text=excluded.text,
                    token_count=excluded.token_count,
                    created_at=excluded.created_at
                """,
                records,
            )

        conn.commit()
        return len(records)
    finally:
        conn.close()


def get_chunk_by_id(chunk_id: str) -> Optional[dict]:
    """Look up a single chunk by its stable ID directly from SQLite."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_chunks_by_source(source_file: str) -> int:
    """Delete all chunks belonging to a source file."""
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM chunks WHERE source_file = ?", (source_file,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def list_chunks_by_source(source_file: str) -> list[dict]:
    """Retrieve all chunks for a source file ordered by page and chunk index."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE source_file = ? ORDER BY page_number ASC, chunk_index ASC",
            (source_file,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_chunks() -> int:
    """Return total number of chunks stored in SQLite."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()

