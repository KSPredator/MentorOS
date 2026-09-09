"""
Test script for Phase 2 (Embeddings + Vector Store).
Indexes documents from data/uploads/ and runs test similarity search queries.

Usage:
    # 1. Index documents in data/uploads/ and run a test query:
    python embeddings/test_embeddings.py --query "What is machine learning?"

    # 2. Interactive sanity check loop:
    python embeddings/test_embeddings.py --interactive
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion import ingest_file
from embeddings import VectorStore, EmbeddingModel


def index_uploads(store: VectorStore, uploads_dir: Path = Path("data/uploads")) -> int:
    """Finds all supported documents in data/uploads/ and indexes them into Chroma."""
    supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    files = [f for f in uploads_dir.iterdir() if f.suffix.lower() in supported_exts] if uploads_dir.exists() else []

    if not files:
        print(f"[Warning] No documents found in '{uploads_dir}'.")
        return 0

    total_indexed = 0
    print(f"\n--- Ingesting & Indexing {len(files)} file(s) into ChromaDB ---")
    for file_path in files:
        print(f"Processing: {file_path.name} ...")
        chunks = ingest_file(file_path)
        if chunks:
            count = store.add_chunks(chunks)
            print(f"  -> Added {count} chunks to vector store.")
            total_indexed += count
        else:
            print(f"  -> No chunks extracted from {file_path.name}.")

    print(f"Total chunks now in vector store: {store.count()}")
    return total_indexed


def test_query(store: VectorStore, query: str, k: int = 5):
    """Run a query and display retrieved chunks with similarity scores and page citations."""
    print(f"\n========================================================")
    print(f"Query: '{query}' (top-k={k})")
    print(f"========================================================")

    results = store.retrieve(query, k=k)

    if not results:
        print("No matching chunks retrieved. (Is the vector store empty?)")
        return

    for rank, chunk in enumerate(results, start=1):
        print(f"\n[Rank #{rank}] Similarity Score: {chunk.score:.4f} ({chunk.score * 100:.1f}%)")
        print(f"  Citation   : {chunk.source_file} -> Page {chunk.page_number} (Chunk #{chunk.chunk_index})")
        print(f"  Chunk ID   : {chunk.chunk_id}")
        print(f"  Excerpt    : {chunk.text[:200].replace(chr(10), ' ')}...")


def main():
    parser = argparse.ArgumentParser(description="MentorOS Phase 2 Vector Store & Embeddings Sanity Check")
    parser.add_argument("--query", type=str, help="Search query to test retrieval")
    parser.add_argument("-k", type=int, default=3, help="Number of top chunks to retrieve (default: 3)")
    parser.add_argument("--reindex", action="store_true", help="Clear and re-index all files in data/uploads/")
    parser.add_argument("--interactive", action="store_true", help="Run interactive search prompt loop")
    args = parser.parse_args()

    print("Initializing EmbeddingModel and Chroma VectorStore ...")
    embedder = EmbeddingModel()
    print(f"  Embedding device: {embedder.device.upper()} (Model: {embedder.model_name})")

    store = VectorStore(embedder=embedder)
    print(f"  Vector store loaded. Current chunk count: {store.count()}")

    # Reindex if requested or if store is empty
    if args.reindex or store.count() == 0:
        if args.reindex:
            print("Clearing vector store collection...")
            store.clear()
        index_uploads(store)

    if args.query:
        test_query(store, args.query, k=args.k)
    elif args.interactive:
        print("\n--- Interactive Retrieval Sanity Check --- (Type 'exit' to quit)")
        while True:
            try:
                user_q = input("\nEnter query: ").strip()
                if not user_q or user_q.lower() in {"exit", "quit"}:
                    break
                test_query(store, user_q, k=args.k)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        # Default sanity check query
        default_query = "What is engineering scientific software?"
        test_query(store, default_query, k=args.k)


if __name__ == "__main__":
    main()
