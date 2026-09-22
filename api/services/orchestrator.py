"""
Orchestrator (Phase 9.5 — the integration heart).

Flow: persist user message → PlannerAgent.route → dispatch handler →
persist assistant message → emit SSE stages/events → return AskResponse dict.

Handlers:
  RETRIEVE → BaselineRAG (retrieve → prompt → Ollama → EvaluationAgent gate)
              + LearningMemoryStore.update (Phase 6 wiring)
  MEMORY   → LearningMemoryStore snapshot + Ollama narrative
  QUIZ     → quiz_service (MCQs grounded in retrieved chunks)
  PODCAST  → podcast_service (HOST/STUDENT script; TTS = Phase 12b)
  GENERAL  → plain Ollama conversation (no retrieval)

emit(event_name, data) is invoked only when streaming; pass None for JSON mode.
"""

import logging
import time
from typing import Callable, Optional

from api import config, db
from api.services import file_service, pipeline, podcast_service, quiz_service, topic_extractor

logger = logging.getLogger("MentorOS.Orchestrator")

Emit = Optional[Callable[[str, dict], None]]

REFUSAL_FALLBACK = (
    "I couldn't find enough evidence in the uploaded documents to answer this safely. "
    "Please upload more material on this topic."
)

MEMORY_NARRATION_SYSTEM = """You are MentorOS, an AI tutor summarising a student's
learning memory for the current session. Be concise, warm, and specific.
2-4 short paragraphs maximum. Use markdown with **bold** for topic names.
End with one concrete next-step suggestion."""

GENERAL_SYSTEM = """You are MentorOS, a friendly local AI study tutor.
Answer briefly and clearly (2-5 sentences unless more is genuinely needed).
You have NO document context for this message — do not invent document facts.
If the student asks a content question about their notes, tell them to rephrase
so it can search their uploaded documents (e.g. start with "Explain…")."""


class Orchestrator:
    """Routes a user message through the multi-agent pipeline."""

    def ask(self, message: str, session_id: Optional[str] = None, emit: Emit = None) -> dict:
        start = time.time()
        message = (message or "").strip()
        if not message:
            raise ValueError("Message must not be empty.")

        # Fail fast BEFORE persisting anything when Ollama is down
        client = pipeline.get_ollama()
        if not client.is_available():
            raise PipelineNotRunning("Ollama is not running. Start it with `ollama serve`.")

        # ---- 1. Session ----
        created_new = False
        session = db.get_session(session_id) if session_id else None
        if session is None:
            session = db.create_session(title=db.auto_title(message))
            created_new = True
            session_id = session["id"]
        elif session["title"] == "New Chat" and session["message_count"] == 0:
            db.rename_session(session_id, db.auto_title(message))

        user_msg = db.add_message(session_id, "user", message, meta={})

        def _emit(name: str, data: dict) -> None:
            if emit is not None:
                try:
                    emit(name, data)
                except Exception as e:  # never break the pipeline on a UI emit
                    logger.warning(f"emit({name}) failed: {e}")

        # ---- 2. Plan ----
        _emit("stage", {"stage": "planning"})
        decision = pipeline.get_planner().route(message)
        action = decision.action.value

        # ---- 3. Dispatch ----
        result: dict
        if action == "RETRIEVE":
            result = self._handle_retrieve(message, session_id, emit=_emit)
        elif action == "MEMORY":
            result = self._handle_memory(session_id, emit=_emit)
        elif action == "QUIZ":
            result = self._handle_quiz(message, emit=_emit)
        elif action == "PODCAST":
            result = self._handle_podcast(message, emit=_emit)
        else:
            result = self._handle_general(message, emit=_emit)

        # ---- 4. Common fields from planner ----
        result.update(
            {
                "session_id": session_id,
                "user_message_id": user_msg["id"],
                "action": action,
                "route_method": decision.route_method,
                "route_confidence": decision.confidence,
                "model_name": client.model_name,
            }
        )

        _emit(
            "meta",
            {
                "session_id": session_id,
                "action": action,
                "route_method": decision.route_method,
                "route_confidence": decision.confidence,
                "type": result.get("type", "answer"),
                "user_message_id": user_msg["id"],
            },
        )

        # ---- 5. Persist assistant message ----
        meta = {
            "type": result.get("type", "answer"),
            "action": action,
            "route_method": decision.route_method,
            "route_confidence": decision.confidence,
            "citations": result.get("citations", []),
            "retrieved": result.get("retrieved", []),
            "evaluation": result.get("evaluation"),
            "memory_updates": result.get("memory_updates", []),
            "quiz": result.get("quiz"),
            "podcast_script": result.get("podcast_script"),
            "memory_stats": result.get("memory_stats"),
            "is_refusal": result.get("is_refusal", False),
            "model_name": client.model_name,
        }
        asst_msg = db.add_message(session_id, "assistant", result.get("content", ""), meta=meta)

        result["assistant_message_id"] = asst_msg["id"]
        result["latency_seconds"] = round(time.time() - start, 3)
        if created_new:
            result["session_created"] = True

        # ---- 6. Tail events ----
        if result.get("citations") is not None:
            _emit("citations", {"citations": result["citations"], "retrieved": result.get("retrieved", [])})
        if result.get("evaluation"):
            _emit("evaluation", result["evaluation"])
        _emit("final", result)
        _emit("stage", {"stage": "done"})

        return result

    # ------------------------------------------------------------------ #
    # Handlers                                                            #
    # ------------------------------------------------------------------ #

    def _handle_retrieve(self, message: str, session_id: str, emit: Emit) -> dict:
        rag = pipeline.get_rag()

        _emit("stage", {"stage": "retrieving"})
        chunks = rag.vector_store.retrieve(message, k=rag.top_k)

        if not chunks:
            evaluation = {
                "passed_gate": False,
                "confidence_score": 0.0,
                "faithfulness_score": 0.0,
                "semantic_similarity": 0.0,
                "reasoning": "No context retrieved from vector store.",
                "threshold_used": rag.eval_threshold,
            }
            _emit("evaluation", evaluation)
            return {
                "type": "refusal",
                "content": REFUSAL_FALLBACK,
                "citations": [],
                "retrieved": [],
                "evaluation": evaluation,
                "is_refusal": True,
                "memory_updates": [],
            }

        # Format context exactly like BaselineRAG
        context_text = rag._format_context(chunks)
        from llm.rag_pipeline import BASELINE_RAG_PROMPT_TEMPLATE  # type: ignore

        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(
            context_text=context_text, user_question=message.strip()
        )

        # Generate (streaming tokens when emit is active)
        _emit("stage", {"stage": "generating"})
        if emit is not None:
            parts = []
            try:
                for tok in rag.ollama_client.generate_stream(prompt=prompt, temperature=rag.temperature):
                    parts.append(tok)
                    emit("token", {"delta": tok})
            except Exception:
                # Fall back to non-streaming on any stream failure mid-way
                if parts:
                    raw_answer = "".join(parts)
                else:
                    raw_answer = rag.ollama_client.generate(prompt=prompt, temperature=rag.temperature)
            else:
                raw_answer = "".join(parts)
        else:
            raw_answer = rag.ollama_client.generate(prompt=prompt, temperature=rag.temperature)

        # Evaluate (hallucination gate)
        _emit("stage", {"stage": "evaluating"})
        ev = rag.evaluation_agent.evaluate(
            query=message,
            answer=raw_answer,
            retrieved_chunks=chunks,
            threshold=rag.eval_threshold,
        )
        evaluation = {
            "passed_gate": ev.passed_gate,
            "confidence_score": ev.confidence_score,
            "faithfulness_score": ev.faithfulness_score,
            "semantic_similarity": ev.semantic_similarity,
            "reasoning": ev.reasoning,
            "threshold_used": ev.threshold_used,
        }

        citations = [
            {
                "source_file": c.source_file,
                "page_number": c.page_number,
                "chunk_id": c.chunk_id,
                "score": c.score,
            }
            for c in chunks
        ]
        retrieved = [
            {
                "chunk_id": c.chunk_id,
                "source_file": c.source_file,
                "page_number": c.page_number,
                "score": c.score,
                "text_preview": c.text[:240],
            }
            for c in chunks
        ]

        # Phase 6 wiring: update learning memory from gate outcome
        memory_updates = []
        try:
            topic = topic_extractor.extract(message, ollama_client=rag.ollama_client)
            store = pipeline.get_memory_store(session_id)
            if ev.passed_gate:
                rec = store.update(topic, eval_confidence=ev.confidence_score)
            else:
                rec = store.update(topic, made_mistake=True)
            memory_updates = [{"topic": rec.topic, "confidence": rec.confidence}]
            store.close()
        except Exception as e:
            logger.warning(f"Memory update skipped: {e}")

        passed = ev.passed_gate
        return {
            "type": "answer" if passed else "refusal",
            "content": ev.filtered_answer if ev.filtered_answer else (raw_answer if passed else REFUSAL_FALLBACK),
            "citations": citations,
            "retrieved": retrieved,
            "evaluation": evaluation,
            "is_refusal": not passed,
            "memory_updates": memory_updates,
        }

    def _handle_memory(self, session_id: str, emit: Emit) -> dict:
        _emit("stage", {"stage": "retrieving"})
        store = pipeline.get_memory_store(session_id)
        snapshot = store.export_snapshot()
        store.close()

        _emit("stage", {"stage": "generating"})
        client = pipeline.get_ollama()
        stats = snapshot
        if not snapshot.get("topics"):
            content = (
                "**No learning memory yet for this session.**\n\n"
                "Ask questions about your uploaded documents — MentorOS tracks "
                "topic confidence after every answer, and this dashboard fills in automatically."
            )
        else:
            lines = ["Topic | Confidence | Mistakes | Interactions", "-" * 48]
            for t in snapshot["topics"]:
                lines.append(
                    f"{t['topic']} | {round(t['confidence']*100)}% | "
                    f"{t['mistake_count']} | {t['interaction_count']}"
                )
            table = "\n".join(lines)
            try:
                content = client.generate(
                    prompt=(
                        f"Session: {session_id}\n\n{table}\n\n"
                        "Summarise this student's learning memory: strengths, weaknesses, next step."
                    ),
                    system_prompt=MEMORY_NARRATION_SYSTEM,
                    temperature=0.4,
                )
            except Exception:
                content = "### Your learning memory\n\n```\n" + table + "\n```"

        return {
            "type": "memory",
            "content": content.strip(),
            "citations": [],
            "retrieved": [],
            "evaluation": None,
            "is_refusal": False,
            "memory_stats": stats,
            "memory_updates": [],
        }

    def _handle_quiz(self, message: str, emit: Emit) -> dict:
        _emit("stage", {"stage": "retrieving"})
        rag = pipeline.get_rag()
        chunks = rag.vector_store.retrieve(message, k=rag.top_k)

        if not chunks:
            content = (
                "**I can't build a quiz yet** — no documents are indexed. "
                "Upload your lecture PDF/DOCX/PPTX first, then ask again."
            )
            return {
                "type": "refusal",
                "content": content,
                "citations": [],
                "retrieved": [],
                "evaluation": None,
                "is_refusal": True,
                "quiz": None,
                "memory_updates": [],
            }

        context_text = rag._format_context(chunks)
        _emit("stage", {"stage": "generating"})
        quiz = quiz_service.generate(message, context_text)

        if not quiz:
            content = (
                "I couldn't form quiz questions from the retrieved material. "
                "Try a more specific topic (e.g. *“Quiz me on memory paging”*)."
            )
            return {
                "type": "refusal",
                "content": content,
                "citations": [],
                "retrieved": [],
                "evaluation": None,
                "is_refusal": True,
                "quiz": None,
                "memory_updates": [],
            }

        retrieved = [
            {
                "chunk_id": c.chunk_id,
                "source_file": c.source_file,
                "page_number": c.page_number,
                "score": c.score,
                "text_preview": c.text[:240],
            }
            for c in chunks
        ]
        content = f"## 📝 Quiz — {len(quiz)} questions\n\nAnswer below, then hit **Submit**."
        return {
            "type": "quiz",
            "content": content,
            "citations": [],
            "retrieved": retrieved,
            "evaluation": None,
            "is_refusal": False,
            "quiz": quiz,
            "memory_updates": [],
        }

    def _handle_podcast(self, message: str, emit: Emit) -> dict:
        _emit("stage", {"stage": "retrieving"})
        rag = pipeline.get_rag()
        chunks = rag.vector_store.retrieve(message, k=rag.top_k)

        if not chunks:
            content = "**No indexed material for a podcast yet.** Upload documents first."
            return {
                "type": "refusal",
                "content": content,
                "citations": [],
                "retrieved": [],
                "evaluation": None,
                "is_refusal": True,
                "podcast_script": None,
                "memory_updates": [],
            }

        context_text = rag._format_context(chunks)
        _emit("stage", {"stage": "generating"})
        script = podcast_service.generate(message, context_text)

        if not script:
            content = "I couldn't write a podcast script from this material. Try another topic."
            return {
                "type": "refusal",
                "content": content,
                "citations": [],
                "retrieved": [],
                "evaluation": None,
                "is_refusal": True,
                "podcast_script": None,
                "memory_updates": [],
            }

        content = podcast_service.script_to_markdown(script)
        retrieved = [
            {
                "chunk_id": c.chunk_id,
                "source_file": c.source_file,
                "page_number": c.page_number,
                "score": c.score,
                "text_preview": c.text[:240],
            }
            for c in chunks
        ]
        return {
            "type": "podcast",
            "content": content,
            "citations": [],
            "retrieved": retrieved,
            "evaluation": None,
            "is_refusal": False,
            "podcast_script": script,
            "memory_updates": [],
        }

    def _handle_general(self, message: str, emit: Emit) -> dict:
        _emit("stage", {"stage": "generating"})
        client = pipeline.get_ollama()
        content = client.generate(
            prompt=message, system_prompt=GENERAL_SYSTEM, temperature=0.5
        )
        return {
            "type": "general",
            "content": content.strip() or "…",
            "citations": [],
            "retrieved": [],
            "evaluation": None,
            "is_refusal": False,
            "memory_updates": [],
        }

    # ------------------------------------------------------------------ #
    # Quiz submission                                                     #
    # ------------------------------------------------------------------ #

    def submit_quiz(self, session_id: str, message_id: int, answers: list) -> dict:
        msg = db.get_message(message_id)
        if msg is None or msg.get("session_id") != session_id:
            raise LookupError("Quiz message not found.")
        quiz = (msg.get("meta") or {}).get("quiz") or []
        if not quiz:
            raise ValueError("Message has no quiz to grade.")

        feedback = quiz_service.grade(quiz, answers)
        score = sum(1 for f in feedback if f["correct"])

        graded_quiz = []
        for q, fb in zip(quiz, feedback):
            gq = dict(q)
            gq["_feedback"] = fb
            graded_quiz.append(gq)
        content = quiz_service.format_quiz_markdown(graded_quiz, score=score)

        # Memory nudges per question (keyed by chat session)
        memory_updates = []
        try:
            store = pipeline.get_memory_store(session_id)
            topic = "quiz practice"
            if score == len(quiz):
                rec = store.update(topic, eval_confidence=0.90)
            elif score == 0:
                rec = store.update(topic, made_mistake=True)
            else:
                rec = store.update(topic, eval_confidence=0.65)
            memory_updates = [{"topic": rec.topic, "confidence": rec.confidence}]
            store.close()
        except Exception as e:
            logger.warning(f"Quiz memory update skipped: {e}")

        fb_meta = {
            "type": "quiz_result",
            "quiz": graded_quiz,
            "score": score,
            "total": len(quiz),
            "memory_updates": memory_updates,
        }
        asst = db.add_message(session_id, "assistant", content, meta=fb_meta)

        return {
            "score": score,
            "total": len(quiz),
            "feedback": feedback,
            "assistant_message_id": asst["id"],
            "content": content,
            "memory_updates": memory_updates,
        }


class PipelineNotRunning(RuntimeError):
    """Ollama server not reachable."""
