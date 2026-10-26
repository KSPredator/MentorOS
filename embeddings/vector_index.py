"""
Vector Index abstraction interface and ChromaDB implementation for MentorOS.
Provides unified interface:
    VectorIndex.upsert()
    VectorIndex.query()
    VectorIndex.delete()
    VectorIndex.count()
    VectorIndex.clear()

Supports multi-course collection isolation:
    course_<id>__<embed_model>__v<n>
    course_<id>__concepts__v<n>
"""

from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

try:
    import chromadb
except ImportError:
    chromadb = None

from embeddings.embedder import EmbeddingModel
from embeddings.vector_store import RetrievedChunk
from ingestion.chunker import DocumentChunk


def sanitize_collection_name(name: str) -> str:
    """Ensure collection name meets Chroma naming constraints (3-63 chars, alphanumeric, _ or -)."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", name).strip("_-")
    if len(clean) < 3:
        clean = f"col_{clean}"
    return clean[:63]


def get_course_collection_name(
    course_id: str = "default",
    embed_model: str = "all-MiniLM-L6-v2",
    version: int = 1,
    is_concepts: bool = False,
) -> str:
    """
    Format per-course Chroma collection name per spec:
        course_<id>__<embed_model>__v<n>
        course_<id>__concepts__v<n>
    """
    tag = "concepts" if is_concepts else embed_model
    raw = f"course_{course_id}__{tag}__v{version}"
    return sanitize_collection_name(raw)


class VectorIndex(ABC):
    """Abstract Vector Index Interface allowing seamless backend swapping (Chroma, Qdrant, pgvector)."""

    @abstractmethod
    def upsert(self, chunks: List[DocumentChunk]) -> int:
        """Embed and upsert document chunks into the index."""
        pass

    @abstractmethod
    def query(
        self,
        query_text: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Perform semantic similarity search."""
        pass

    @abstractmethod
    def delete(self, where: Dict[str, Any]) -> None:
        """Delete entries matching metadata filter."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total vectors indexed."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries in this index."""
        pass


class ChromaVectorIndex(VectorIndex):
    """ChromaDB implementation of VectorIndex interface with cosine space."""

    def __init__(
        self,
        collection_name: str,
        persist_dir: Union[str, Path] = "chroma_db",
        embedder: Optional[EmbeddingModel] = None,
    ):
        if chromadb is None:
            raise ImportError("chromadb is required. Install with pip install chromadb.")

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedder = embedder or EmbeddingModel()

        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: List[DocumentChunk]) -> int:
        if not chunks:
            return 0

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[dict] = []

        for c in chunks:
            slug = getattr(c, "doc_slug", "") or (
                c.metadata.get("doc_slug", "")
                if hasattr(c, "metadata") and isinstance(c.metadata, dict)
                else ""
            )
            ids.append(c.chunk_id)
            documents.append(c.text)
            metadatas.append({
                "source_file": c.source_file,
                "doc_slug": slug,
                "unit": getattr(c, "unit", "page"),
                "unit_no": int(getattr(c, "unit_no", c.page_number)),
                "page_number": int(c.page_number),
                "chunk_index": int(c.chunk_index),
                "token_count": int(c.token_count),
                "text_hash": getattr(c, "text_hash", ""),
                "legacy_id": getattr(c, "legacy_id", ""),
                "chunk_id": c.chunk_id,
            })

        embeddings = self.embedder.embed_documents(documents)
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def query(
        self,
        query_text: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        query_text = query_text.strip()
        total_docs = self.collection.count()
        if not query_text or total_docs == 0:
            return []

        n_results = min(k, total_docs)
        query_embedding = self.embedder.embed_text(query_text)

        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        retrieved: List[RetrievedChunk] = []
        for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=doc,
                    source_file=meta.get("source_file", "unknown"),
                    page_number=int(meta.get("page_number", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    score=round(similarity, 4),
                    metadata=meta,
                    doc_slug=meta.get("doc_slug", ""),
                )
            )

        retrieved.sort(key=lambda x: x.score, reverse=True)
        return retrieved

    def delete(self, where: Dict[str, Any]) -> None:
        self.collection.delete(where=where)

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
