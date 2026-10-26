"""
Script to re-ingest and re-index uploaded documents with stable chunk IDs and populate the SQLite chunks table.

Usage:
    # Re-index into the current collection and populate SQLite chunks table:
    python scripts/reindex_stable_chunks.py

    # Re-index into a separate collection (recommended per Step 2):
    python scripts/reindex_stable_chunks.py --collection mentoros_okf_collection
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api import config, db
from api.db import init_db, upsert_chunks, count_chunks
from ingestion import ingest_file
from embeddings import VectorStore, EmbeddingModel


def reindex(collection_name: str = config.CHROMA_COLLECTION, uploads_dir: Path = config.UPLOAD_DIR):
    print(f"==================================================")
    print(f"MentorOS Stable Chunk Re-indexing (Step 2)")
    print(f"Target Collection: {collection_name}")
    print(f"Uploads Directory: {uploads_dir}")
    print(f"SQLite DB:         {config.DB_PATH}")
    print(f"==================================================")

    init_db()

    supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    files = [f for f in uploads_dir.iterdir() if f.suffix.lower() in supported_exts] if uploads_dir.exists() else []

    if not files:
        print(f"No documents found in '{uploads_dir}'.")
        return

    print(f"Found {len(files)} file(s) to process.\n")

    store = VectorStore(
        persist_dir=config.CHROMA_DIR,
        collection_name=collection_name,
    )

    total_chunks = 0
    for idx, file_path in enumerate(files, start=1):
        print(f"[{idx}/{len(files)}] Parsing & chunking: {file_path.name}")
        chunks = ingest_file(file_path)
        if not chunks:
            print(f"  -> No text chunks extracted.")
            continue

        # Sample preview of first chunk ID
        print(f"  -> Extracted {len(chunks)} chunks (e.g., ID '{chunks[0].chunk_id}', slug '{chunks[0].doc_slug}')")

        # 1. Upsert into SQLite chunks table
        sqlite_count = upsert_chunks(chunks)
        print(f"  -> Saved {sqlite_count} chunks to SQLite 'chunks' table.")

        # 2. Add to ChromaDB vector store
        added_chroma = store.add_chunks(chunks)
        print(f"  -> Indexed {added_chroma} chunks in Chroma collection '{collection_name}'.")

        total_chunks += len(chunks)

    print(f"\nRe-indexing complete!")
    print(f"Total chunks processed: {total_chunks}")
    print(f"Total chunks now in SQLite: {count_chunks()}")
    print(f"Total chunks in Chroma '{collection_name}': {store.count()}")


def main():
    parser = argparse.ArgumentParser(description="Reindex documents with stable chunk IDs.")
    parser.add_argument(
        "--collection",
        default=config.CHROMA_COLLECTION,
        help="ChromaDB collection name (default: from config)",
    )
    args = parser.parse_args()
    reindex(collection_name=args.collection)


if __name__ == "__main__":
    main()
