"""
MentorOS - LLM Module
Provides local LLM integration via Ollama and Baseline RAG execution pipeline.
"""

from llm.ollama_client import OllamaClient
from llm.rag_pipeline import BaselineRAG, RAGResponse, Citation, BASELINE_RAG_PROMPT_TEMPLATE


__all__ = [
    "OllamaClient",
    "BaselineRAG",
    "RAGResponse",
    "Citation",
    "BASELINE_RAG_PROMPT_TEMPLATE",
]
