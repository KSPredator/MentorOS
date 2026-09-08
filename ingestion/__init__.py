"""
MentorOS - Ingestion Module
Handles multi-format parsing (PDF, DOCX, PPTX, TXT/MD) and token-based chunking with citation metadata.
"""

from typing import List, Union
from pathlib import Path

from ingestion.parser import DocumentParser, ParsedPage, parse_document
from ingestion.chunker import TextChunker, DocumentChunk, chunk_document


def ingest_file(
    file_path: Union[str, Path],
    target_tokens: int = 400,
    overlap_percent: float = 0.15
) -> List[DocumentChunk]:
    """
    End-to-end ingestion pipeline:
    Parses document -> Extracts page/slide numbers -> Chunks with overlap and citation metadata.
    """
    pages = parse_document(file_path)
    chunks = chunk_document(pages, target_tokens=target_tokens, overlap_percent=overlap_percent)
    return chunks


__all__ = [
    "DocumentParser",
    "ParsedPage",
    "parse_document",
    "TextChunker",
    "DocumentChunk",
    "chunk_document",
    "ingest_file",
]
