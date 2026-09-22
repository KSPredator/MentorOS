"""
Reflection router (Phase 9.7): POST /api/reflection → ReflectionReport.
session_id optional — defaults to the most recently active chat session.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import db
from api.services import pipeline

router = APIRouter()


class ReflectionBody(BaseModel):
    session_id: Optional[str] = None


@router.post("/reflection")
def generate_reflection(body: ReflectionBody):
    session_id = body.session_id
    if not session_id:
        sessions = db.list_sessions()
        if not sessions:
            raise HTTPException(
                status_code=404,
                detail="No sessions yet — ask a few questions first, then reflect.",
            )
        session_id = sessions[0]["id"]

    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    try:
        store = pipeline.get_memory_store(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        # ReflectionGenerator degrades to rule-based summary if Ollama fails
        gen = pipeline.get_reflection_generator()
        report = gen.generate(store, session_id=session_id)
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reflection failed: {e}")
    finally:
        store.close()
