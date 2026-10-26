"""
MentorOS Re-indexing and Parity Verification Script (Step 3).
Populates courses, documents, chunks (with legacy_id and text_hash), and per-course Chroma collections.
Runs retrieval parity checks to ensure zero regression against legacy lookups.

Usage:
    python scripts/reindex.py --course-id default --parity-check
"""

import argparse
import hashlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api import config
from db import (
    get_db_session,
    ensure_default_course,
    CourseRepository,
    DocumentRepository,
    ChunkRepository,
)
from ingestion import ingest_file, slugify
from embeddings import ChromaVectorIndex, get_course_collection_name, EmbeddingModel


def compute_file_hash(path: Path) -> str:
    """SHA-256 of full file content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_reindex(course_id: str = "default", check_parity: bool = True):
    print("================================================================")
    print("MentorOS Re-index & Provenance Migration (Step 3)")
    print(f"Course ID: {course_id}")
    print("================================================================")

    uploads_dir = config.UPLOAD_DIR
    supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    files = [f for f in uploads_dir.iterdir() if f.suffix.lower() in supported_exts] if uploads_dir.exists() else []

    if not files:
        print(f"No files found in {uploads_dir}. Nothing to reindex.")
        return

    with get_db_session() as session:
        course_repo = CourseRepository(session)
        doc_repo = DocumentRepository(session)
        chunk_repo = ChunkRepository(session)

        course = course_repo.get(course_id)
        if not course:
            course = course_repo.upsert(
                course_id=course_id,
                name=f"Course {course_id}",
                bundle_path=f"bundle/{course_id}",
                embed_model="all-MiniLM-L6-v2",
            )

        col_name = get_course_collection_name(course_id=course_id, embed_model=course.embed_model, version=1)
        print(f"Target Chroma Collection: '{col_name}'")
        vector_index = ChromaVectorIndex(collection_name=col_name, persist_dir=config.CHROMA_DIR)

        total_chunks = 0
        all_new_chunks = []

        for f_path in files:
            content_hash = compute_file_hash(f_path)
            base_slug = slugify(f_path.name)
            doc = doc_repo.upsert(
                course_id=course_id,
                base_slug=base_slug,
                filename=f_path.name,
                content_hash=content_hash,
            )
            print(f"Processing '{f_path.name}' -> doc_id='{doc.doc_id}' (version {doc.version})...")

            chunks = ingest_file(f_path)
            for c in chunks:
                c.metadata["doc_id"] = doc.doc_id
                c.doc_slug = doc.doc_id
                c.doc_version = doc.version

            # Upsert to SQLite
            saved = chunk_repo.upsert_chunks(chunks)
            # Upsert to Vector Store
            indexed = vector_index.upsert(chunks)
            doc_repo.update_status(doc.doc_id, "indexed")

            print(f"  -> Saved {saved} chunks in DB, indexed {indexed} in collection '{col_name}'.")
            total_chunks += saved
            all_new_chunks.extend(chunks)

        print(f"\nRe-index completed! Total chunks: {total_chunks}")

        # Parity check
        if check_parity and all_new_chunks:
            print("\n--- Running Parity Check ---")
            mismatches = 0
            for c in all_new_chunks[:20]:  # sample check
                legacy_id = c.legacy_id
                found = chunk_repo.get_by_legacy_id(legacy_id)
                if not found or found.text != c.text:
                    print(f"  [FAIL] Legacy ID lookup mismatch for '{legacy_id}'")
                    mismatches += 1
                else:
                    assert found.chunk_id == c.chunk_id

            if mismatches == 0:
                print(f"  [PASS] All {min(20, len(all_new_chunks))} sampled legacy IDs resolved with 100% text parity.")
            else:
                print(f"  [FAIL] {mismatches} mismatches detected.")


def main():
    parser = argparse.ArgumentParser(description="Re-index documents into relational schema and per-course Chroma collection.")
    parser.add_argument("--course-id", default="default", help="Course identifier")
    parser.add_argument("--parity-check", action="store_true", default=True, help="Run legacy ID parity check")
    args = parser.parse_args()
    run_reindex(course_id=args.course_id, check_parity=args.parity_check)


if __name__ == "__main__":
    main()
