"""
Pydantic request/response schemas for the MentorOS FastAPI backend.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# /upload
# ──────────────────────────────────────────────

class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    sources: List[str]
    message: str


# ──────────────────────────────────────────────
# /ask
# ──────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The student's question")
    session_id: str = Field(default="default", description="Session identifier")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    eval_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Override hallucination gate threshold (default 0.60)"
    )


class CitationOut(BaseModel):
    source_file: str
    page_number: int
    chunk_id: str
    score: float


class PlannerDecisionOut(BaseModel):
    action: str
    confidence: float
    reasoning: str
    route_method: str


class EvaluationOut(BaseModel):
    passed_gate: bool
    confidence_score: float
    faithfulness_score: float
    semantic_similarity: float
    reasoning: str
    threshold_used: float


class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    planner: PlannerDecisionOut
    evaluation: Optional[EvaluationOut]
    citations: List[CitationOut]
    confidence_score: float
    passed_gate: bool
    is_refusal: bool
    latency_seconds: float
    model_name: str
    message_id: int


# ──────────────────────────────────────────────
# /history
# ──────────────────────────────────────────────

class HistoryMessage(BaseModel):
    id: int
    session_id: str
    role: str          # "user" or "assistant"
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]
    count: int


class DeleteResponse(BaseModel):
    session_id: str
    deleted_count: int
    message: str


# ──────────────────────────────────────────────
# /memory
# ──────────────────────────────────────────────

class TopicRecordOut(BaseModel):
    topic: str
    session_id: str
    confidence: float
    confidence_pct: str
    mistake_count: int
    interaction_count: int
    last_seen: str


class MemorySnapshotResponse(BaseModel):
    session_id: str
    exported_at: str
    topic_count: int
    topics: List[TopicRecordOut]
    weak_topics: List[str]
    strong_topics: List[str]


class MemoryUpdateRequest(BaseModel):
    session_id: str = "default"
    topic: str
    eval_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0
    )
    made_mistake: bool = False
    asked_simpler: bool = False


class MemoryUpdateResponse(BaseModel):
    topic: str
    session_id: str
    updated_record: TopicRecordOut


# ──────────────────────────────────────────────
# /reflection
# ──────────────────────────────────────────────

class ReflectionResponse(BaseModel):
    session_id: str
    generated_at: str
    learned_well: List[str]
    needs_revision: List[str]
    recommended_session: str
    full_summary: str
    topic_count: int
    strong_count: int
    weak_count: int


# ──────────────────────────────────────────────
# /status
# ──────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str               # "ok" or "degraded"
    ollama_available: bool
    ollama_model: str
    available_models: List[str]
    indexed_chunks: int
    indexed_sources: List[str]
    api_version: str
