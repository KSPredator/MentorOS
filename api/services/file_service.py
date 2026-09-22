"""
File service (Phase 9.3): upload → ingest → embed → index, plus deletion.
Reuses ingestion.ingest_file and embeddings.VectorStore from the existing pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from api import config, db
from api.services import pipeline

logger = logging.getLogger("MentorOS.FileService")


class FileValidationError(ValueError):
    """415/413-class validation error with HTTP status hint."""

    def __init__(self, message: str, status_code: int = 415):
        super().__init__(message)
        self.status_code = status_code


def _validate(filename: str, size_bytes: int) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}",
            status_code=415,
        )
    if config.MAX_UPLOAD_MB > 0 and size_bytes > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise FileValidationError(
            f"File exceeds {config.MAX_UPLOAD_MB}MB limit.", status_code=413
        )
    if not filename.strip():
        raise FileValidationError("Filename is empty.", status_code=400)
    return ext


def ingest_upload(filename: str, data: bytes) -> Dict:
    """
    Full pipeline: validate → save → mark processing → parse/chunk/embed → indexed.
    Re-ingesting an existing file deletes its old chunks first (clean replace).
    """
    pipeline.ensure_ready()
    ext = _validate(filename, len(data))

    safe_name = Path(filename).name  # strip any client-side path
    dest = config.UPLOAD_DIR / safe_name
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    existing = db.get_file(safe_name)
    if existing and existing.get("status") == "processing":
        raise FileValidationError(
            f"'{safe_name}' is currently being processed. Retry shortly.",
            status_code=409,
        )

    # Save bytes
    dest.write_bytes(data)
    db.upsert_file_row(safe_name, ext, len(data), status="processing", chunk_count=0)

    try:
        # Clean replace: remove old chunks for this source first
        if existing:
            store = pipeline.get_vector_store()
            store.collection.delete(where={"source_file": safe_name})

        from ingestion import ingest_file  # type: ignore

        chunks = ingest_file(dest)
        store = pipeline.get_vector_store()
        count = store.add_chunks(chunks) if chunks else 0

        if count == 0:
            db.update_file_status(safe_name, "failed", 0, "No text could be extracted.")
            raise FileValidationError("No text could be extracted from this file.", status_code=422)

        db.update_file_status(safe_name, "indexed", count)
        logger.info(f"Indexed {safe_name}: {count} chunks")
        return db.get_file(safe_name) or {}
    except FileValidationError:
        raise
    except Exception as e:
        logger.exception(f"Ingestion failed for {safe_name}")
        db.update_file_status(safe_name, "failed", 0, str(e))
        raise RuntimeError(f"Ingestion failed: {e}") from e


def delete_file(filename: str) -> bool:
    """Remove chunks from Chroma, file from disk, row from SQLite."""
    safe_name = Path(filename).name
    row = db.get_file(safe_name)
    if row is None:
        return False

    if pipeline.pipeline_ready():
        try:
            store = pipeline.get_vector_store()
            store.collection.delete(where={"source_file": safe_name})
        except Exception as e:
            logger.warning(f"Chroma delete failed for {safe_name}: {e}")

    path = config.UPLOAD_DIR / safe_name
    if path.exists():
        try:
            path.unlink()
        except OSError as e:
            logger.warning(f"Disk delete failed for {safe_name}: {e}")

    return db.delete_file_row(safe_name)


def delete_all_files() -> int:
    """Bulk delete used by Settings → Clear knowledge base."""
    rows = db.list_files()
    removed = 0
    for row in rows:
        if delete_file(row["filename"]):
            removed += 1
    return removed


def get_chunk(chunk_id: str) -> Optional[dict]:
    """Fetch one chunk by id for citation click-through preview."""
    pipeline.ensure_ready()
    store = pipeline.get_vector_store()
    res = store.collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not res or not res.get("ids"):
        return None
    meta = (res.get("metadatas") or [{}])[0] or {}
    return {
        "chunk_id": res["ids"][0],
        "text": (res.get("documents") or [""])[0],
        "source_file": meta.get("source_file", "unknown"),
        "page_number": int(meta.get("page_number", 1)),
        "chunk_index": int(meta.get("chunk_index", 0)),
    }


def list_files_out() -> List[dict]:
    return db.list_files()
