"""
POST /ask            — Full RAG pipeline (planner-routed), returns JSON.
POST /ask/stream     — Same pipeline but streams the LLM answer via SSE.

Routing logic (PlannerAgent):
  RETRIEVE  → BaselineRAG (retrieve → evaluate → answer)
  MEMORY    → LearningMemoryStore query → formatted answer
  QUIZ      → RAG with a quiz-generation prompt
  PODCAST   → RAG with podcast script prompt (text only, no TTS at this phase)
  GENERAL   → Direct Ollama call (no retrieval needed)
"""

import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agents.planner_agent import PlannerAgent, PlannerAction
from api.database import get_db
from api.models import (
    AskRequest,
    AskResponse,
    CitationOut,
    EvaluationOut,
    PlannerDecisionOut,
)
from embeddings import get_vector_store
from llm.ollama_client import OllamaClient
from llm.rag_pipeline import BaselineRAG
from memory.memory_store import LearningMemoryStore

logger = logging.getLogger("MentorOS.API.Ask")

router = APIRouter()

# ──────────────────────────────────────────────────────────────
# Shared singleton initialisation (lazy, on first request)
# ──────────────────────────────────────────────────────────────

_ollama_client: Optional[OllamaClient] = None
_planner: Optional[PlannerAgent] = None
_rag: Optional[BaselineRAG] = None


def _get_ollama() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def _get_planner() -> PlannerAgent:
    global _planner
    if _planner is None:
        _planner = PlannerAgent(ollama_client=_get_ollama())
    return _planner


def _get_rag(threshold: Optional[float] = None) -> BaselineRAG:
    global _rag
    if _rag is None:
        _rag = BaselineRAG(
            vector_store=get_vector_store(),
            ollama_client=_get_ollama(),
        )
    if threshold is not None:
        _rag.eval_threshold = threshold
    return _rag


# ──────────────────────────────────────────────────────────────
# Quiz and general prompts
# ──────────────────────────────────────────────────────────────

QUIZ_PROMPT_TEMPLATE = """You are MentorOS, an AI tutor. Generate a multiple-choice quiz question based ONLY on the context below.

Context:
{context_text}

Topic hinted by student: {user_question}

Format your response EXACTLY as:
Question: <question text>
A) <option>
B) <option>
C) <option>
D) <option>
Correct Answer: <letter>
Explanation: <brief explanation citing the source>"""

GENERAL_SYSTEM_PROMPT = """You are MentorOS, a helpful and encouraging AI study tutor.
Answer the student's greeting or general question warmly and briefly.
If they ask what you can do, explain you can: answer questions from uploaded documents,
quiz them on topics, show their learning progress, and generate session summaries."""

PODCAST_PROMPT_TEMPLATE = """You are writing a 2-person educational podcast script explaining the following material to a curious student.

Speakers:
- HOST: an enthusiastic tutor who explains clearly and uses analogies
- STUDENT: a curious learner who asks follow-up questions

Use ONLY the material below as your source of truth. Do not introduce facts not present in it.

Material:
{context_text}

Topic requested: {user_question}

Write a natural back-and-forth dialogue, 8–12 exchanges. Format each line as:
HOST: ...
STUDENT: ..."""


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _topic_from_query(query: str) -> str:
    """Extract a short topic label from the query for memory updates."""
    words = query.strip().split()
    return " ".join(words[:6]).lower().rstrip("?.!")


def _update_memory(session_id: str, topic: str, passed: bool, confidence: float) -> None:
    """Nudge learning memory based on evaluation result."""
    try:
        store = LearningMemoryStore(session_id=session_id)
        store.update(
            topic=topic,
            eval_confidence=confidence,
            made_mistake=not passed,
        )
        store.close()
    except Exception as e:
        logger.warning(f"Memory update failed: {e}")


# ──────────────────────────────────────────────────────────────
# POST /ask
# ──────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse, tags=["QA"])
def ask(body: AskRequest) -> AskResponse:
    """
    Route the student's question through the Planner Agent, then execute the
    appropriate handler (RAG, Memory, Quiz, Podcast, General).
    Persists the Q&A exchange to chat history and updates learning memory.
    """
    db = get_db()
    ollama = _get_ollama()
    planner = _get_planner()

    # 1. Route
    decision = planner.route(body.question)

    # 2. Persist user message
    user_msg_id = db.add_message(
        session_id=body.session_id,
        role="user",
        content=body.question,
        metadata={"planner_action": decision.action.value},
    )

    # Defaults for non-RAG paths
    answer = ""
    citations = []
    confidence_score = 1.0
    passed_gate = True
    is_refusal = False
    latency = 0.0
    model_name = ollama.model_name
    eval_out: Optional[EvaluationOut] = None

    # 3. Dispatch
    if decision.action == PlannerAction.RETRIEVE:
        rag = _get_rag(threshold=body.eval_threshold)
        result = rag.answer_question(
            query=body.question,
            k=body.top_k,
            threshold=body.eval_threshold,
        )
        answer = result.answer
        latency = result.latency_seconds
        model_name = result.model_name
        confidence_score = result.confidence_score
        passed_gate = result.passed_gate
        is_refusal = result.is_refusal
        citations = [
            CitationOut(
                source_file=c.source_file,
                page_number=c.page_number,
                chunk_id=c.chunk_id,
                score=c.score,
            )
            for c in result.citations
        ]
        if result.evaluation:
            eval_out = EvaluationOut(
                passed_gate=result.evaluation.passed_gate,
                confidence_score=result.evaluation.confidence_score,
                faithfulness_score=result.evaluation.faithfulness_score,
                semantic_similarity=result.evaluation.semantic_similarity,
                reasoning=result.evaluation.reasoning,
                threshold_used=result.evaluation.threshold_used,
            )
        _update_memory(body.session_id, _topic_from_query(body.question), passed_gate, confidence_score)

    elif decision.action == PlannerAction.QUIZ:
        # Retrieve context, build quiz prompt, call LLM directly
        vs = get_vector_store()
        chunks = vs.retrieve(body.question, k=body.top_k)
        if chunks:
            context_text = "\n\n".join(
                f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}"
                for c in chunks
            )
            prompt = QUIZ_PROMPT_TEMPLATE.format(
                context_text=context_text,
                user_question=body.question,
            )
            answer = ollama.generate(prompt=prompt, temperature=0.4)
            citations = [
                CitationOut(
                    source_file=c.source_file,
                    page_number=c.page_number,
                    chunk_id=c.chunk_id,
                    score=c.score,
                )
                for c in chunks
            ]
        else:
            answer = (
                "I don't have enough uploaded material to generate a quiz question on this topic. "
                "Please upload relevant documents first."
            )

    elif decision.action == PlannerAction.PODCAST:
        vs = get_vector_store()
        chunks = vs.retrieve(body.question, k=body.top_k)
        if chunks:
            context_text = "\n\n".join(
                f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}"
                for c in chunks
            )
            prompt = PODCAST_PROMPT_TEMPLATE.format(
                context_text=context_text,
                user_question=body.question,
            )
            answer = ollama.generate(prompt=prompt, temperature=0.5)
            citations = [
                CitationOut(
                    source_file=c.source_file,
                    page_number=c.page_number,
                    chunk_id=c.chunk_id,
                    score=c.score,
                )
                for c in chunks
            ]
        else:
            answer = (
                "No documents are uploaded yet. Please upload some material and "
                "then ask for a podcast explainer."
            )

    elif decision.action == PlannerAction.MEMORY:
        try:
            store = LearningMemoryStore(session_id=body.session_id)
            snapshot = store.export_snapshot()
            store.close()

            weak = snapshot["weak_topics"]
            strong = snapshot["strong_topics"]
            total = snapshot["topic_count"]

            if total == 0:
                answer = (
                    "I don't have any learning history for this session yet. "
                    "Ask me some questions from your documents first!"
                )
            else:
                weak_str = ", ".join(weak) if weak else "none identified yet"
                strong_str = ", ".join(strong) if strong else "none yet"
                answer = (
                    f"📊 **Learning Memory ({body.session_id})**\n\n"
                    f"Topics studied: {total}\n"
                    f"✅ Strong topics: {strong_str}\n"
                    f"⚠️ Needs revision: {weak_str}\n\n"
                    "Ask me for a **/reflection** to get a full study summary and recommendations."
                )
        except Exception as e:
            logger.warning(f"Memory query failed: {e}")
            answer = "I couldn't retrieve your learning memory right now. Please try again."

    else:  # GENERAL
        answer = ollama.generate(
            prompt=body.question,
            system_prompt=GENERAL_SYSTEM_PROMPT,
            temperature=0.5,
        )

    # 4. Persist assistant message
    assistant_msg_id = db.add_message(
        session_id=body.session_id,
        role="assistant",
        content=answer,
        metadata={
            "planner_action": decision.action.value,
            "confidence_score": confidence_score,
            "passed_gate": passed_gate,
            "citations": [c.model_dump() for c in citations],
        },
    )

    return AskResponse(
        session_id=body.session_id,
        question=body.question,
        answer=answer,
        planner=PlannerDecisionOut(
            action=decision.action.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            route_method=decision.route_method,
        ),
        evaluation=eval_out,
        citations=citations,
        confidence_score=confidence_score,
        passed_gate=passed_gate,
        is_refusal=is_refusal,
        latency_seconds=latency,
        model_name=model_name,
        message_id=assistant_msg_id,
    )


# ──────────────────────────────────────────────────────────────
# POST /ask/stream — Server-Sent Events streaming
# ──────────────────────────────────────────────────────────────

async def _sse_generator(body: AskRequest) -> AsyncGenerator[str, None]:
    """
    Streaming SSE generator.
    Yields:
      - data: {"type": "planner", ...}        — routing decision
      - data: {"type": "token", "token": "…"} — LLM token stream
      - data: {"type": "done", ...}            — final metadata
    """
    ollama = _get_ollama()
    planner = _get_planner()
    db = get_db()

    decision = planner.route(body.question)

    db.add_message(
        session_id=body.session_id,
        role="user",
        content=body.question,
        metadata={"planner_action": decision.action.value},
    )

    # Emit planner decision
    yield f"data: {json.dumps({'type': 'planner', 'action': decision.action.value, 'reasoning': decision.reasoning})}\n\n"

    full_answer = ""

    if decision.action in (PlannerAction.RETRIEVE, PlannerAction.QUIZ, PlannerAction.PODCAST):
        vs = get_vector_store()
        chunks = vs.retrieve(body.question, k=body.top_k)
        if not chunks:
            msg = "No relevant documents found. Please upload study material first."
            yield f"data: {json.dumps({'type': 'token', 'token': msg})}\n\n"
            full_answer = msg
        else:
            context_text = "\n\n".join(
                f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}"
                for c in chunks
            )
            if decision.action == PlannerAction.QUIZ:
                prompt = QUIZ_PROMPT_TEMPLATE.format(
                    context_text=context_text, user_question=body.question
                )
                sys_prompt = None
                temp = 0.4
            elif decision.action == PlannerAction.PODCAST:
                prompt = PODCAST_PROMPT_TEMPLATE.format(
                    context_text=context_text, user_question=body.question
                )
                sys_prompt = None
                temp = 0.5
            else:
                from llm.rag_pipeline import BASELINE_RAG_PROMPT_TEMPLATE
                prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(
                    context_text=context_text,
                    user_question=body.question,
                )
                sys_prompt = None
                temp = 0.2

            for token in ollama.generate_stream(
                prompt=prompt, system_prompt=sys_prompt, temperature=temp
            ):
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

    elif decision.action == PlannerAction.GENERAL:
        for token in ollama.generate_stream(
            prompt=body.question,
            system_prompt=GENERAL_SYSTEM_PROMPT,
            temperature=0.5,
        ):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

    else:  # MEMORY — not streamable in meaningful way, just emit full response
        store = LearningMemoryStore(session_id=body.session_id)
        snapshot = store.export_snapshot()
        store.close()
        weak = snapshot["weak_topics"]
        strong = snapshot["strong_topics"]
        full_answer = (
            f"Strong: {', '.join(strong) or 'none yet'} | "
            f"Needs revision: {', '.join(weak) or 'none yet'}"
        )
        yield f"data: {json.dumps({'type': 'token', 'token': full_answer})}\n\n"

    # Persist assistant message
    db.add_message(
        session_id=body.session_id,
        role="assistant",
        content=full_answer,
        metadata={"planner_action": decision.action.value, "streamed": True},
    )

    yield f"data: {json.dumps({'type': 'done', 'session_id': body.session_id})}\n\n"


@router.post("/ask/stream", tags=["QA"])
async def ask_stream(body: AskRequest) -> StreamingResponse:
    """
    Stream the LLM answer token-by-token using Server-Sent Events (SSE).
    Connect with: EventSource / fetch with ReadableStream.
    """
    return StreamingResponse(
        _sse_generator(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
