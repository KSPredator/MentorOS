"""
GET    /history          — Retrieve chat history for a session.
DELETE /history          — Clear chat history for a session.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Query

from api.database import get_db
from api.models import DeleteResponse, HistoryMessage, HistoryResponse

logger = logging.getLogger("MentorOS.API.History")

router = APIRouter()


@router.get("/history", response_model=HistoryResponse, tags=["History"])
def get_history(
    session_id: str = Query(default="default", description="Session identifier"),
    limit: int = Query(default=50, ge=1, le=500, description="Max messages to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> HistoryResponse:
    """
    Return recent chat messages for a session (oldest first within the page).
    """
    db = get_db()
    rows = db.get_history(session_id=session_id, limit=limit, offset=offset)

    messages = []
    for row in rows:
        meta = None
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                meta = None

        messages.append(
            HistoryMessage(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=meta,
            )
        )

    return HistoryResponse(
        session_id=session_id,
        messages=messages,
        count=len(messages),
    )


@router.delete("/history", response_model=DeleteResponse, tags=["History"])
def delete_history(
    session_id: str = Query(default="default", description="Session identifier"),
) -> DeleteResponse:
    """
    Delete all chat history for a session.
    """
    db = get_db()
    deleted = db.delete_history(session_id=session_id)
    logger.info(f"Deleted {deleted} history messages for session '{session_id}'")

    return DeleteResponse(
        session_id=session_id,
        deleted_count=deleted,
        message=f"Deleted {deleted} message(s) for session '{session_id}'.",
    )
