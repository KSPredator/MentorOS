"""
MentorOS FastAPI application entrypoint (Phase 9).

Run:
    uvicorn api.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import config
from api.db import init_db

logger = logging.getLogger("MentorOS.API")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init SQLite, reconcile orphaned upload states."""
    logger.info("MentorOS API starting…")
    init_db()
    logger.info(f"DB ready at {config.DB_PATH}")
    yield
    logger.info("MentorOS API shutting down.")


app = FastAPI(
    title=config.APP_TITLE,
    version=config.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})


# Routers (import after app creation to keep module load order clear)
from api.routers import chat, files, memory, reflection, system  # noqa: E402

app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(memory.router, prefix="/api", tags=["memory"])
app.include_router(reflection.router, prefix="/api", tags=["reflection"])


@app.get("/")
async def root():
    return {"name": config.APP_TITLE, "version": config.API_VERSION, "docs": "/docs"}
