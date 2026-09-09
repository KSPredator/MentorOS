"""
MentorOS - Embeddings & Vector Store Module
Handles embedding generation (SentenceTransformers) and persistent vector storage/retrieval (ChromaDB).
"""

from embeddings.embedder import EmbeddingModel
from embeddings.vector_store import VectorStore, RetrievedChunk


def get_vector_store(persist_dir: str = "chroma_db", collection_name: str = "mentoros_collection") -> VectorStore:
    """Convenience factory function to get or initialize the default VectorStore."""
    return VectorStore(persist_dir=persist_dir, collection_name=collection_name)


__all__ = [
    "EmbeddingModel",
    "VectorStore",
    "RetrievedChunk",
    "get_vector_store",
]
