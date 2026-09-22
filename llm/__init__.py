"""
MentorOS - LLM Module
Provides local LLM integration via Ollama and the Baseline RAG pipeline.

Note: `llm.ollama_client` is stdlib-only; `llm.rag_pipeline` needs torch +
sentence-transformers + chromadb. Imports are lazy so the API can boot and
use the Ollama client even before the heavy pipeline deps are installed.
Import directly from submodules when you need a concrete class:
    from llm.ollama_client import OllamaClient
    from llm.rag_pipeline import BaselineRAG
Or use the module-level accessors below.
"""


def __getattr__(name):
    if name in ("OllamaClient",):
        from llm.ollama_client import OllamaClient
        globals()[name] = OllamaClient
        return globals()[name]
    if name in ("BaselineRAG", "RAGResponse", "Citation", "BASELINE_RAG_PROMPT_TEMPLATE"):
        from llm.rag_pipeline import (
            BaselineRAG,
            RAGResponse,
            Citation,
            BASELINE_RAG_PROMPT_TEMPLATE,
        )
        globals()["BaselineRAG"] = BaselineRAG
        globals()["RAGResponse"] = RAGResponse
        globals()["Citation"] = Citation
        globals()["BASELINE_RAG_PROMPT_TEMPLATE"] = BASELINE_RAG_PROMPT_TEMPLATE
        return globals()[name]
    raise AttributeError(f"module 'llm' has no attribute {name!r}")


__all__ = [
    "OllamaClient",
    "BaselineRAG",
    "RAGResponse",
    "Citation",
    "BASELINE_RAG_PROMPT_TEMPLATE",
]