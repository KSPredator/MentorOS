"""
GET /reflection — Generate a session-end learning reflection report.
"""

import logging

from fastapi import APIRouter, Query

from api.models import ReflectionResponse
from memory.memory_store import LearningMemoryStore
from memory.reflection_generator import ReflectionGenerator

logger = logging.getLogger("MentorOS.API.Reflection")

router = APIRouter()


@router.get("/reflection", response_model=ReflectionResponse, tags=["Memory"])
def get_reflection(
    session_id: str = Query(default="default", description="Session identifier"),
) -> ReflectionResponse:
    """
    Generate a structured end-of-session reflection using the LLM.

    Reads the session's topic confidence data from LearningMemoryStore,
    feeds it to ReflectionGenerator (calls Ollama), and returns a
    ReflectionReport with:
      - learned_well:         high-confidence topics
      - needs_revision:       low-confidence topics
      - recommended_session:  actionable next-step paragraph
      - full_summary:         encouraging narrative summary
    """
    store = LearningMemoryStore(session_id=session_id)
    try:
        gen = ReflectionGenerator()
        report = gen.generate(memory_store=store, session_id=session_id)
        logger.info(
            f"Reflection generated for session '{session_id}' | "
            f"topics={report.topic_count} strong={report.strong_count} weak={report.weak_count}"
        )
        return ReflectionResponse(
            session_id=report.session_id,
            generated_at=report.generated_at,
            learned_well=report.learned_well,
            needs_revision=report.needs_revision,
            recommended_session=report.recommended_session,
            full_summary=report.full_summary,
            topic_count=report.topic_count,
            strong_count=report.strong_count,
            weak_count=report.weak_count,
        )
    finally:
        store.close()
