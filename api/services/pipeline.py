"""
Lazy pipeline access layer (Phase 9 integration).

Why lazy: the API must boot even when heavy pipeline deps (torch,
sentence-transformers, chromadb) are not installed yet. Heavy singletons
are created on first use; readiness is reported via status().
"""

import importlib.util
from pathlib import Path
from typing import List, Optional

from api import config


class PipelineUnavailableError(RuntimeError):
    """Raised when a pipeline dependency is missing."""

    def __init__(self, missing: List[str], message: Optional[str] = None):
        self.missing = missing
        super().__init__(
            message
            or f"Pipeline dependencies missing: {', '.join(missing)}. "
            f"Install requirements.txt to enable the full RAG pipeline."
        )


_REQUIRED = {
    "torch": "torch",
    "sentence_transformers": "sentence-transformers",
    "chromadb": "chromadb",
    "pypdf": "pypdf",
}

_ollama_cls = None
_ollama_instance = None
_vector_store = None
_rag = None
_planner = None


def missing_packages() -> List[str]:
    missing = []
    for module, pkg in _REQUIRED.items():
        if importlib.util.find_spec(module) is None:
            missing.append(pkg)
    return missing


def pipeline_ready() -> bool:
    return not missing_packages()


def _load_ollama_client_cls():
    """Load OllamaClient; fall back to file-load to bypass llm/__init__ heavy imports."""
    global _ollama_cls
    if _ollama_cls is not None:
        return _ollama_cls
    try:
        from llm.ollama_client import OllamaClient  # type: ignore

        _ollama_cls = OllamaClient
    except Exception:
        path = Path(config.BASE_DIR) / "llm" / "ollama_client.py"
        spec = importlib.util.spec_from_file_location("_mentoros_ollama_client", path)
        if spec is None or spec.loader is None:
            raise PipelineUnavailableError(["ollama_client"], "Cannot load llm/ollama_client.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ollama_cls = mod.OllamaClient
    return _ollama_cls


def get_ollama():
    """Cached OllamaClient instance (stdlib-only — always available)."""
    global _ollama_instance
    if _ollama_instance is None:
        cls = _load_ollama_client_cls()
        _ollama_instance = cls(base_url="http://localhost:11434", timeout=120)
    return _ollama_instance


def ensure_ready() -> None:
    """Raise PipelineUnavailableError if heavy deps are missing."""
    missing = missing_packages()
    if missing:
        raise PipelineUnavailableError(missing)


def get_vector_store():
    """Cached VectorStore (requires chromadb + sentence-transformers)."""
    global _vector_store
    if _vector_store is None:
        ensure_ready()
        from embeddings import EmbeddingModel, VectorStore  # type: ignore

        embedder = EmbeddingModel()
        _vector_store = VectorStore(
            persist_dir=str(config.CHROMA_DIR),
            collection_name=config.CHROMA_COLLECTION,
            embedder=embedder,
        )
    return _vector_store


def get_shared_embedder():
    """Embedding model shared by vector store + evaluation agent (one load)."""
    vs = get_vector_store()
    return vs.embedder


def get_rag():
    """Cached BaselineRAG with shared embedder and configured threshold."""
    global _rag
    if _rag is None:
        ensure_ready()
        from llm.rag_pipeline import BaselineRAG  # type: ignore
        from agents.evaluation_agent import EvaluationAgent  # type: ignore

        client = get_ollama()
        vs = get_vector_store()
        eval_agent = EvaluationAgent(
            ollama_client=client,
            embedder=vs.embedder,
            threshold=config.EVAL_THRESHOLD,
        )
        _rag = BaselineRAG(
            vector_store=vs,
            ollama_client=client,
            evaluation_agent=eval_agent,
            top_k=config.DEFAULT_TOP_K,
            eval_threshold=config.EVAL_THRESHOLD,
        )
    return _rag


def get_planner():
    """Cached PlannerAgent."""
    global _planner
    if _planner is None:
        ensure_ready()
        from agents.planner_agent import PlannerAgent  # type: ignore

        _planner = PlannerAgent(ollama_client=get_ollama())
    return _planner


def get_memory_store(session_id: str):
    """LearningMemoryStore (stdlib SQLite — always available)."""
    from memory.memory_store import LearningMemoryStore  # type: ignore

    return LearningMemoryStore(session_id=session_id, db_path=config.MEMORY_DB_PATH)


def get_reflection_generator():
    """ReflectionGenerator wired to our Ollama client (no llm/__init__ import)."""
    from memory.reflection_generator import ReflectionGenerator  # type: ignore

    return ReflectionGenerator(ollama_client=get_ollama())


def status_dict() -> dict:
    """Build /api/status payload without raising."""
    client = get_ollama()
    ollama_ok = client.is_available()
    model_name = None
    chunks = None
    missing = missing_packages()

    if ollama_ok:
        try:
            model_name = client.model_name or (client.list_models() or [None])[0]
        except Exception:
            model_name = None

    if not missing:
        try:
            chunks = get_vector_store().count()
        except Exception:
            chunks = None

    from api import db

    return {
        "ollama_available": ollama_ok,
        "model_name": model_name,
        "pipeline_ready": not missing,
        "missing_packages": missing,
        "vector_store_chunks": chunks,
        "files_indexed": db.count_indexed_files(),
        "eval_threshold": config.EVAL_THRESHOLD,
        "api_version": config.API_VERSION,
    }
