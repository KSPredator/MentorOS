"""
Memory router (Phase 9.7): LearningMemoryStore HTTP wrappers.
session_id optional — omitted aggregates all sessions (dashboard default view).
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.services import pipeline

router = APIRouter()


def _store(session_id: str):
    return pipeline.get_memory_store(session_id)


def _aggregate_all() -> dict:
    """Merge every session's topics: keep the freshest row per topic name."""
    from datetime import datetime

    # Discover session ids present in the DB
    probe = _store("__probe__")
    try:
        sessions = probe.get_all_sessions()
    finally:
        probe.close()

    by_topic: dict = {}
    for sid in sessions:
        if sid == "__probe__":
            continue
        s = _store(sid)
        try:
            for rec in s.get_all():
                prev = by_topic.get(rec.topic)
                if prev is None or rec.last_seen > prev["last_seen"]:
                    by_topic[rec.topic] = rec.to_dict()
        finally:
            s.close()

    topics = sorted(by_topic.values(), key=lambda t: t["last_seen"], reverse=True)
    weak = [t["topic"] for t in topics if t["confidence"] < 0.60]
    strong = [t["topic"] for t in topics if t["confidence"] >= 0.70]
    return {
        "session_id": "*all*",
        "exported_at": datetime.utcnow().isoformat() + "Z" if topics else "",
        "topic_count": len(topics),
        "topics": topics,
        "weak_topics": weak,
        "strong_topics": strong,
    }


@router.get("/memory")
def get_memory(session_id: Optional[str] = Query(default=None)):
    if session_id:
        store = _store(session_id)
        try:
            return store.export_snapshot()
        finally:
            store.close()
    return _aggregate_all()


@router.get("/memory/weak")
def weak_topics(
    session_id: Optional[str] = Query(default=None),
    n: int = Query(default=5, ge=1, le=50),
):
    if session_id:
        store = _store(session_id)
        try:
            return [r.to_dict() for r in store.get_weak_topics(n=n)]
        finally:
            store.close()
    snap = _aggregate_all()
    return [t for t in snap["topics"] if t["confidence"] < 0.60][:n]


@router.get("/memory/strong")
def strong_topics(
    session_id: Optional[str] = Query(default=None),
    n: int = Query(default=5, ge=1, le=50),
):
    if session_id:
        store = _store(session_id)
        try:
            return [r.to_dict() for r in store.get_strong_topics(n=n)]
        finally:
            store.close()
    snap = _aggregate_all()
    return [t for t in snap["topics"] if t["confidence"] >= 0.70][:n]


@router.delete("/memory")
def reset_memory(session_id: str = Query(...)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required for reset.")
    store = _store(session_id)
    try:
        store.reset_session()
    finally:
        store.close()
    return {"reset": session_id}
