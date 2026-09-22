"""
Chat router (Phase 9.4/9.6): sessions CRUD, /ask, /ask/stream (SSE), quiz submit.
"""

import json
import queue
import threading
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from api import db
from api.models import AskRequest, QuizSubmitRequest, QuizSubmitResponse, RenameSessionRequest
from api.services import pipeline
from api.services.orchestrator import Orchestrator, PipelineNotRunning

router = APIRouter()
_orchestrator = Orchestrator()


# --------------------------------------------------------------------------- #
# Sessions                                                                     #
# --------------------------------------------------------------------------- #

@router.get("/sessions")
def list_sessions():
    return db.list_sessions()


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str):
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session": session, "messages": db.list_messages(session_id)}


@router.patch("/sessions/{session_id}")
def rename_session(session_id: str, body: RenameSessionRequest):
    updated = db.rename_session(session_id, body.title.strip())
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return updated


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if not db.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": session_id}


# --------------------------------------------------------------------------- #
# Ask (JSON)                                                                   #
# --------------------------------------------------------------------------- #

@router.post("/ask")
def ask(body: AskRequest):
    try:
        result = _orchestrator.ask(body.message, session_id=body.session_id, emit=None)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PipelineNotRunning as e:
        raise HTTPException(status_code=503, detail=str(e))
    except pipeline.PipelineUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# --------------------------------------------------------------------------- #
# Ask (SSE stream)                                                             #
# --------------------------------------------------------------------------- #

@router.post("/ask/stream")
def ask_stream(body: AskRequest):
    """
    SSE endpoint. Events: meta, stage, token, citations, evaluation, final, error.
    Runs the orchestrator on a worker thread; events flow through a queue.
    """
    # Fail fast on obviously bad input / dead Ollama before opening the stream
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")
    client = pipeline.get_ollama()
    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start it with `ollama serve`.",
        )

    q: "queue.Queue" = queue.Queue(maxsize=512)
    session_id = body.session_id
    message = body.message

    def _emit(name: str, data: dict) -> None:
        q.put((name, data))

    def _run() -> None:
        try:
            _orchestrator.ask(message, session_id=session_id, emit=_emit)
        except Exception as e:
            try:
                q.put(("error", {"message": str(e)}))
            except Exception:
                pass
        finally:
            q.put((None, None))  # sentinel → close stream

    threading.Thread(target=_run, daemon=True, name="mentoros-ask").start()

    def _generator():
        while True:
            name, data = q.get()
            if name is None:
                break
            yield {
                "event": name,
                "data": json.dumps(data, ensure_ascii=False, default=str),
            }

    return EventSourceResponse(_generator(), media_type="text/event-stream")


# --------------------------------------------------------------------------- #
# Quiz submit                                                                  #
# --------------------------------------------------------------------------- #

@router.post("/quiz/submit")
def quiz_submit(body: QuizSubmitRequest):
    # Return the full orchestrator dict (score/total/feedback/
    # assistant_message_id/content/memory_updates) to the frontend.
    try:
        return _orchestrator.submit_quiz(body.session_id, body.message_id, body.answers)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Keep JSONResponse import referenced for consistent exception surface
_ = JSONResponse
_ = Optional
_ = List
