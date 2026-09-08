"""
Quick CLI test script for Phase 1 (Document Ingestion).
Run this script to test parsing and chunking on any PDF/DOCX/PPTX file:

Usage:
    python ingestion/test_ingestion.py path/to/lecture.pdf
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion import ingest_file, parse_document


def main():
    if len(sys.argv) < 2:
        uploads_dir = Path("data/uploads")
        test_files = list(uploads_dir.glob("*.pdf")) + list(uploads_dir.glob("*.docx")) + list(uploads_dir.glob("*.pptx"))
        
        if not test_files:
            print("No test file provided and data/uploads/ is empty.")
            print("Usage: python ingestion/test_ingestion.py <path_to_document>")
            return
        file_path = test_files[0]
        print(f"Testing with file found in uploads: {file_path}")
    else:
        file_path = Path(sys.argv[1])

    print(f"\n--- 1. Testing DocumentParser on '{file_path}' ---")
    pages = parse_document(file_path)
    print(f"Extracted {len(pages)} page(s)/slide(s).")
    for p in pages[:3]:
        print(f"\n[Page/Slide {p.page_number}] ({len(p.text)} chars):")
        preview = p.text[:150].replace("\n", " ")
        print(f"  {preview}...")

    print(f"\n--- 2. Testing TextChunker (300-500 tokens, 15% overlap) ---")
    chunks = ingest_file(file_path, target_tokens=400, overlap_percent=0.15)
    print(f"Total chunks created: {len(chunks)}")
    
    for c in chunks[:3]:
        print(f"\n[Chunk {c.chunk_index}] ID: {c.chunk_id}")
        print(f"  Source: {c.source_file} | Page: {c.page_number} | Tokens: ~{c.token_count}")
        print(f"  Snippet: {c.text[:120]}...")

    print("\nIngestion test completed successfully!")


if __name__ == "__main__":
    main()
