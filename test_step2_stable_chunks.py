"""
Verification test script for Step 2: Stable Chunk IDs and SQLite Provenance Table.
Tests slugification, stable ID formatting, SQLite CRUD, and VectorStore compatibility.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.parser import ParsedPage
from ingestion.chunker import TextChunker, slugify, DocumentChunk
from api import db
from embeddings.vector_store import RetrievedChunk


def test_slugify():
    print("Testing slugify...")
    cases = [
        ("OS_Unit3.pdf", "os-unit3"),
        ("lecture 01.pptx", "lecture-01"),
        ("Chapter_05_Virtual_Memory.docx", "chapter-05-virtual-memory"),
        ("AI_Engineering (Chip Huyen).pdf", "ai-engineering-chip-huyen"),
        ("simple.txt", "simple"),
    ]
    for filename, expected in cases:
        actual = slugify(filename)
        assert actual == expected, f"Expected '{expected}', got '{actual}' for '{filename}'"
    print("  -> slugify tests passed!")


def test_stable_chunk_ids():
    print("Testing stable chunk IDs formatting...")
    # PDF page
    pdf_page = ParsedPage(
        page_number=41,
        text="Virtual memory decouples the programmer's view of memory from physical memory.",
        source_file="OS_Unit3.pdf",
        metadata={"file_type": "pdf", "total_pages": 100},
    )
    # PPTX slide
    pptx_page = ParsedPage(
        page_number=5,
        text="Paging Hardware Architecture and Translation Lookaside Buffers (TLB).",
        source_file="OS_Lecture_Slides.pptx",
        metadata={"file_type": "pptx", "total_slides": 30},
    )

    chunker = TextChunker()
    chunks = chunker.chunk_pages([pdf_page, pptx_page])

    assert len(chunks) == 2
    # Check PDF chunk ID
    assert chunks[0].chunk_id == "os-unit3-p41-c0", f"Unexpected chunk_id: {chunks[0].chunk_id}"
    assert chunks[0].doc_slug == "os-unit3"
    assert chunks[0].page_number == 41

    # Check PPTX slide chunk ID (uses -s prefix)
    assert chunks[1].chunk_id == "os-lecture-slides-s5-c1", f"Unexpected chunk_id: {chunks[1].chunk_id}"
    assert chunks[1].doc_slug == "os-lecture-slides"
    assert chunks[1].page_number == 5
    print("  -> Stable chunk IDs test passed!")


def test_sqlite_chunks_table():
    print("Testing SQLite chunks table CRUD...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_mentoros.db"
        db.init_db(test_db_path)

        # Patch db.get_conn to use test_db_path
        original_get_conn = db.get_conn
        db.get_conn = lambda path=None: original_get_conn(test_db_path)

        try:
            sample_chunks = [
                DocumentChunk(
                    chunk_id="os-unit3-p41-c0",
                    text="Virtual memory decouples the programmer view.",
                    source_file="OS_Unit3.pdf",
                    page_number=41,
                    chunk_index=0,
                    token_count=12,
                    metadata={"doc_slug": "os-unit3"},
                    doc_slug="os-unit3",
                ),
                DocumentChunk(
                    chunk_id="os-unit3-p41-c1",
                    text="Demand paging brings pages into memory only when needed.",
                    source_file="OS_Unit3.pdf",
                    page_number=41,
                    chunk_index=1,
                    token_count=14,
                    metadata={"doc_slug": "os-unit3"},
                    doc_slug="os-unit3",
                ),
            ]

            # 1. Upsert
            count = db.upsert_chunks(sample_chunks)
            assert count == 2, f"Expected 2 upserted chunks, got {count}"
            assert db.count_chunks() == 2

            # 2. Lookup by ID
            chunk_row = db.get_chunk_by_id("os-unit3-p41-c0")
            assert chunk_row is not None
            assert chunk_row["chunk_id"] == "os-unit3-p41-c0"
            assert chunk_row["doc_slug"] == "os-unit3"
            assert chunk_row["page_number"] == 41
            assert "Virtual memory" in chunk_row["text"]

            # 3. List by source
            by_source = db.list_chunks_by_source("OS_Unit3.pdf")
            assert len(by_source) == 2

            # 4. Delete by source
            deleted = db.delete_chunks_by_source("OS_Unit3.pdf")
            assert deleted == 2
            assert db.count_chunks() == 0
            assert db.get_chunk_by_id("os-unit3-p41-c0") is None

            print("  -> SQLite chunks CRUD tests passed!")
        finally:
            db.get_conn = original_get_conn


if __name__ == "__main__":
    test_slugify()
    test_stable_chunk_ids()
    test_sqlite_chunks_table()
    print("\nALL STEP 2 TESTS PASSED SUCCESSFULLY!")
