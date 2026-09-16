"""
Vector Store module for MentorOS.
Wraps ChromaDB persistent client for document indexing and top-k cosine similarity retrieval.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from embeddings.embedder import EmbeddingModel
from ingestion.chunker import DocumentChunk


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with relevance score and citation metadata."""
    chunk_id: str
    text: str
    source_file: str
    page_number: int
    chunk_index: int
    score: float  # Cosine similarity score (0.0 to 1.0, higher is better)
    metadata: dict


class VectorStore:
    """ChromaDB-backed vector database for storing and retrieving document embeddings."""

    DEFAULT_COLLECTION_NAME = "mentoros_collection"
    DEFAULT_DB_DIR = "chroma_db"

    def __init__(
        self,
        persist_dir: Union[str, Path] = DEFAULT_DB_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedder: Optional[EmbeddingModel] = None,
    ):
        if chromadb is None:
            raise ImportError("chromadb is required. Please install it using `pip install chromadb`.")

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedder = embedder or EmbeddingModel()

        # Initialize persistent Chroma client with cosine similarity distance metric
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Embed and upsert a list of DocumentChunks into the vector store."""
        if not chunks:
            return 0

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[dict] = []

        for c in chunks:
            ids.append(c.chunk_id)
            documents.append(c.text)
            metadatas.append({
                "source_file": c.source_file,
                "page_number": int(c.page_number),
                "chunk_index": int(c.chunk_index),
                "token_count": int(c.token_count),
            })

        embeddings = self.embedder.embed_documents(documents)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(ids)

    def retrieve(self, query: str, k: int = 5) -> List[RetrievedChunk]:
        """
        Embed query, perform cosine-similarity search, and return top-k chunks with metadata.
        """
        query = query.strip()
        if not query or self.collection.count() == 0:
            return []

        # Clamp k to available document count
        total_docs = self.collection.count()
        n_results = min(k, total_docs)

        query_embedding = self.embedder.embed_text(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        retrieved: List[RetrievedChunk] = []

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
            # Chroma returns cosine distance (0.0 = identical, 2.0 = opposite).
            # Convert cosine distance to cosine similarity score: 1.0 - distance
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
                )
            )

        # Sort by highest similarity score first
        retrieved.sort(key=lambda x: x.score, reverse=True)
        return retrieved

    def count(self) -> int:
        """Return the total number of indexed chunks in the collection."""
        return self.collection.count()

    def get_sources(self) -> List[str]:
        """Return a list of unique source filenames currently indexed."""
        if self.count() == 0:
            return []
        data = self.collection.get(include=["metadatas"])
        sources = set(m.get("source_file") for m in data.get("metadatas", []) if m and "source_file" in m)
        return sorted(list(sources))

    def clear(self) -> None:
        """Clear all indexed chunks from the current collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
