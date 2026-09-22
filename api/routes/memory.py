"""
GET    /memory           — Full memory snapshot for a session.
GET    /memory/weak      — Top-n weak topics for a session.
POST   /memory/update    — Manually update a topic's confidence (testing/admin).
DELETE /memory           — Reset all learning memory for a session.
"""

import logging

from fastapi import APIRouter, Query

from api.models import (
    DeleteResponse,
    MemorySnapshotResponse,
    MemoryUpdateRequest,
    MemoryUpdateResponse,
    TopicRecordOut,
)
from memory.memory_store import LearningMemoryStore

logger = logging.getLogger("MentorOS.API.Memory")

router = APIRouter()


def _record_to_out(record) -> TopicRecordOut:
    return TopicRecordOut(
        topic=record.topic,
        session_id=record.session_id,
        confidence=record.confidence,
        confidence_pct=record.confidence_pct(),
        mistake_count=record.mistake_count,
        interaction_count=record.interaction_count,
        last_seen=record.last_seen,
    )


@router.get("/memory", response_model=MemorySnapshotResponse, tags=["Memory"])
def get_memory(
    session_id: str = Query(default="default", description="Session identifier"),
) -> MemorySnapshotResponse:
    """Return a full snapshot of the student's learning memory for a session."""
    store = LearningMemoryStore(session_id=session_id)
    try:
        snapshot = store.export_snapshot()
        topics_out = [_record_to_out(r) for r in store.get_all()]
        return MemorySnapshotResponse(
            session_id=snapshot["session_id"],
            exported_at=snapshot["exported_at"],
            topic_count=snapshot["topic_count"],
            topics=topics_out,
            weak_topics=snapshot["weak_topics"],
            strong_topics=snapshot["strong_topics"],
        )
    finally:
        store.close()


@router.get("/memory/weak", response_model=list[TopicRecordOut], tags=["Memory"])
def get_weak_topics(
    session_id: str = Query(default="default", description="Session identifier"),
    n: int = Query(default=5, ge=1, le=50, description="Number of weak topics to return"),
    threshold: float = Query(default=0.60, ge=0.0, le=1.0, description="Confidence threshold"),
) -> list[TopicRecordOut]:
    """Return the top-n weakest topics (lowest confidence) for a session."""
    store = LearningMemoryStore(session_id=session_id)
    try:
        records = store.get_weak_topics(n=n, threshold=threshold)
        return [_record_to_out(r) for r in records]
    finally:
        store.close()


@router.post("/memory/update", response_model=MemoryUpdateResponse, tags=["Memory"])
def update_memory(body: MemoryUpdateRequest) -> MemoryUpdateResponse:
    """
    Manually update a topic's confidence in learning memory.
    Useful for testing or admin corrections.
    """
    store = LearningMemoryStore(session_id=body.session_id)
    try:
        updated = store.update(
            topic=body.topic,
            eval_confidence=body.eval_confidence,
            made_mistake=body.made_mistake,
            asked_simpler=body.asked_simpler,
        )
        return MemoryUpdateResponse(
            topic=updated.topic,
            session_id=updated.session_id,
            updated_record=_record_to_out(updated),
        )
    finally:
        store.close()


@router.delete("/memory", response_model=DeleteResponse, tags=["Memory"])
def reset_memory(
    session_id: str = Query(default="default", description="Session identifier"),
) -> DeleteResponse:
    """Reset (delete) all learning memory for a session."""
    store = LearningMemoryStore(session_id=session_id)
    try:
        before = len(store.get_all())
        store.reset_session()
        logger.info(f"Reset memory for session '{session_id}' ({before} records deleted)")
        return DeleteResponse(
            session_id=session_id,
            deleted_count=before,
            message=f"Cleared {before} topic record(s) for session '{session_id}'.",
        )
    finally:
        store.close()
