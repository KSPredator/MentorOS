"""
GET /status — Health check endpoint.
Returns Ollama availability, available models, and indexed document count.
"""

from fastapi import APIRouter
from embeddings import get_vector_store
from llm.ollama_client import OllamaClient
from api.models import StatusResponse

router = APIRouter()

API_VERSION = "1.0.0"


@router.get("/status", response_model=StatusResponse, tags=["System"])
def get_status() -> StatusResponse:
    """
    Health check: confirms Ollama is reachable and reports indexed document statistics.
    """
    client = OllamaClient()
    ollama_ok = client.is_available()
    models = client.list_models() if ollama_ok else []
    model_name = client.model_name

    try:
        vs = get_vector_store()
        chunk_count = vs.count()
        sources = vs.get_sources()
    except Exception:
        chunk_count = 0
        sources = []

    return StatusResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_available=ollama_ok,
        ollama_model=model_name,
        available_models=models,
        indexed_chunks=chunk_count,
        indexed_sources=sources,
        api_version=API_VERSION,
    )
