"""
Pydantic request/response models for MentorOS API (Phase 9).
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #

class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


class ReflectionRequest(BaseModel):
    session_id: str


class QuizSubmitRequest(BaseModel):
    session_id: str
    message_id: int
    answers: List[int]


# --------------------------------------------------------------------------- #
# Response fragments
# --------------------------------------------------------------------------- #

class CitationOut(BaseModel):
    source_file: str
    page_number: int
    chunk_id: str
    score: float


class RetrievedOut(BaseModel):
    chunk_id: str
    source_file: str
    page_number: int
    score: float
    text_preview: str


class EvaluationOut(BaseModel):
    passed_gate: bool
    confidence_score: float
    faithfulness_score: float
    semantic_similarity: float
    reasoning: str
    threshold_used: float


class MemoryUpdateOut(BaseModel):
    topic: str
    confidence: float


class QuizQuestionOut(BaseModel):
    question: str
    options: List[str]
    answer_idx: int
    explanation: str


class PodcastLineOut(BaseModel):
    speaker: str  # HOST | STUDENT
    line: str


class AskResponse(BaseModel):
    session_id: str
    user_message_id: int
    assistant_message_id: int
    action: str
    route_method: str
    route_confidence: float
    type: str  # answer | refusal | quiz | memory | podcast | general
    content: str
    citations: List[CitationOut] = []
    retrieved: List[RetrievedOut] = []
    evaluation: Optional[EvaluationOut] = None
    latency_seconds: float
    model_name: str
    memory_updates: List[MemoryUpdateOut] = []
    quiz: Optional[List[QuizQuestionOut]] = None
    podcast_script: Optional[List[PodcastLineOut]] = None
    memory_stats: Optional[dict] = None
    is_refusal: bool = False


class FileOut(BaseModel):
    id: Optional[int] = None
    filename: str
    ext: str
    size_bytes: int
    status: str
    chunk_count: int
    error: Optional[str] = None
    uploaded_at: Optional[str] = None


class ChunkOut(BaseModel):
    chunk_id: str
    text: str
    source_file: str
    page_number: int
    chunk_index: int
    score: Optional[float] = None


class StatusOut(BaseModel):
    ollama_available: bool
    model_name: Optional[str]
    pipeline_ready: bool
    missing_packages: List[str] = []
    vector_store_chunks: Optional[int] = None
    files_indexed: int
    eval_threshold: float
    api_version: str


class QuizFeedbackItem(BaseModel):
    correct: bool
    your_answer: int
    correct_idx: int
    explanation: str


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    feedback: List[QuizFeedbackItem]


class ErrorOut(BaseModel):
    detail: str
    extra: Optional[Any] = None
