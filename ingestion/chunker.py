"""
Text chunking module for MentorOS.
Splits parsed document pages into semantically coherent chunks (300-500 tokens)
with ~15% overlap while preserving citation metadata (source file, page number, chunk index).
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
import re
from ingestion.parser import ParsedPage

#return format
@dataclass
class DocumentChunk:
    """Represents a text chunk with citation and provenance metadata for Explainable AI."""
    chunk_id: str
    text: str
    source_file: str
    page_number: int
    chunk_index: int
    token_count: int
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


class TextChunker:
    """
    Splits text into chunks of target token size with overlap.
    Default: 400 tokens per chunk (~1400 chars) with 15% overlap (~60 tokens).
    """

    def __init__(
        self,
        target_tokens: int = 400,
        min_tokens: int = 100,
        max_tokens: int = 500,
        overlap_percent: float = 0.15
    ):
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = int(target_tokens * overlap_percent)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimation: ~0.75 words per token (or ~4 chars per token)."""
        words = text.split()
        return max(1, int(len(words) * 1.3))

    def chunk_pages(self, pages: List[ParsedPage]) -> List[DocumentChunk]:
        """Split a list of ParsedPage objects into DocumentChunks with citation metadata."""
        all_chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            page_chunks = self._chunk_text(
                text=page.text,
                source_file=page.source_file,
                page_number=page.page_number,
                start_index=global_chunk_idx
            )
            all_chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        return all_chunks

    def _chunk_text(
        self,
        text: str,
        source_file: str,
        page_number: int,
        start_index: int = 0
    ) -> List[DocumentChunk]:
        """Split a single text block into overlapping chunks."""
        text = text.strip()
        if not text:
            return []

        # If text is already within max token limits, return as single chunk
        est_tokens = self.estimate_tokens(text)
        if est_tokens <= self.max_tokens:
            chunk_id = f"{source_file}_p{page_number}_c{start_index}"
            return [
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=text,
                    source_file=source_file,
                    page_number=page_number,
                    chunk_index=start_index,
                    token_count=est_tokens,
                    metadata={"char_length": len(text)}
                )
            ]

        # Recursive splitting by natural boundaries: paragraphs -> sentences -> words
        chunks_text = self._recursive_split(
            text=text,
            target_tokens=self.target_tokens,
            overlap_tokens=self.overlap_tokens
        )

        result: List[DocumentChunk] = []
        for offset, chunk_str in enumerate(chunks_text):
            chunk_idx = start_index + offset
            c_tokens = self.estimate_tokens(chunk_str)
            chunk_id = f"{source_file}_p{page_number}_c{chunk_idx}"
            result.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=chunk_str,
                    source_file=source_file,
                    page_number=page_number,
                    chunk_index=chunk_idx,
                    token_count=c_tokens,
                    metadata={"char_length": len(chunk_str)}
                )
            )

        return result

    def _recursive_split(
        self,
        text: str,
        target_tokens: int,
        overlap_tokens: int
    ) -> List[str]:
        """Split text by paragraphs, then sentences, respecting token boundaries and overlap."""
        # Split by double newlines or single newlines
        paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
        
        # If single paragraph is still too long, split by sentences
        units = []
        for p in paragraphs:
            if self.estimate_tokens(p) > target_tokens:
                sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", p) if s.strip()]
                units.extend(sentences)
            else:
                units.append(p)

        chunks: List[str] = []
        current_chunk_units: List[str] = []
        current_token_count = 0

        for unit in units:
            unit_tokens = self.estimate_tokens(unit)
            if current_token_count + unit_tokens > target_tokens and current_chunk_units:
                chunk_str = " ".join(current_chunk_units).strip()
                chunks.append(chunk_str)

                # Overlap: retain trailing units up to overlap_tokens
                overlap_units = []
                overlap_count = 0
                for u in reversed(current_chunk_units):
                    u_tok = self.estimate_tokens(u)
                    if overlap_count + u_tok <= overlap_tokens:
                        overlap_units.insert(0, u)
                        overlap_count += u_tok
                    else:
                        break

                current_chunk_units = overlap_units + [unit]
                current_token_count = overlap_count + unit_tokens
            else:
                current_chunk_units.append(unit)
                current_token_count += unit_tokens

        if current_chunk_units:
            chunks.append(" ".join(current_chunk_units).strip())

        return chunks


def chunk_document(
    pages: List[ParsedPage],
    target_tokens: int = 400,
    overlap_percent: float = 0.15
) -> List[DocumentChunk]:
    """Convenience function to chunk parsed document pages."""
    chunker = TextChunker(target_tokens=target_tokens, overlap_percent=overlap_percent)
    return chunker.chunk_pages(pages)
