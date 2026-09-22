"""
MentorOS FastAPI Application — Phase 9 Backend
================================================
Exposes the full MentorOS pipeline via REST API:

  GET  /status           — Health check (Ollama, indexed docs)
  POST /upload           — Ingest PDF/DOCX/PPTX into ChromaDB
  POST /ask              — Planner-routed QA (JSON response)
  POST /ask/stream       — Planner-routed QA (SSE streaming)
  GET  /history          — Chat history for a session
  DEL  /history          — Clear chat history for a session
  GET  /memory           — Full learning memory snapshot
  GET  /memory/weak      — Weak topics for a session
  POST /memory/update    — Manually update topic confidence
  DEL  /memory           — Reset session memory
  GET  /reflection       — Generate session reflection report

Run with:
  python run_api.py
  — or —
  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on the path when running via `uvicorn api.main:app`
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ask, history, memory, reflection, status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("MentorOS.API")

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────

app = FastAPI(
    title="MentorOS API",
    description=(
        "AI-powered study tutor backend. "
        "Upload documents, ask questions, track learning progress, "
        "and generate session reflections."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow all origins during development — tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────

app.include_router(status.router)
app.include_router(ask.router)
app.include_router(history.router)
app.include_router(memory.router)
app.include_router(reflection.router)

# Upload router registered separately to keep multipart handling isolated
from api.routes import upload as upload_module  # noqa: E402
app.include_router(upload_module.router)


# ──────────────────────────────────────────────
# Root redirect to docs
# ──────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.on_event("startup")
def startup_event():
    logger.info("MentorOS API starting up...")
    # Pre-warm the DB connection
    from api.database import get_db
    get_db()
    logger.info("MentorOS API ready. Visit http://localhost:8000/docs")


@app.on_event("shutdown")
def shutdown_event():
    from api.database import get_db
    try:
        get_db().close()
    except Exception:
        pass
    logger.info("MentorOS API shut down.")
