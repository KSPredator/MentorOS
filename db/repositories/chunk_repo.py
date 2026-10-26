"""
Chunk repository for MentorOS.
Stores fine-grained chunk metadata with text hashing, provenance units (page/slide/section), and legacy ID mapping.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from db.schema import Chunk, now_iso


class ChunkRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, chunk_id: str) -> Optional[Chunk]:
        return self.session.get(Chunk, chunk_id)

    def get_by_legacy_id(self, legacy_id: str) -> Optional[Chunk]:
        stmt = select(Chunk).where(Chunk.legacy_id == legacy_id)
        return self.session.scalars(stmt).first()

    def list_by_doc(self, doc_id: str, doc_version: Optional[int] = None) -> List[Chunk]:
        stmt = select(Chunk).where(Chunk.doc_id == doc_id)
        if doc_version is not None:
            stmt = stmt.where(Chunk.doc_version == doc_version)
        stmt = stmt.order_by(Chunk.unit_no.asc(), Chunk.chunk_index.asc())
        return list(self.session.scalars(stmt).all())

    def list_by_source_file(self, source_file: str) -> List[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.source_file == source_file)
            .order_by(Chunk.unit_no.asc(), Chunk.chunk_index.asc())
        )
        return list(self.session.scalars(stmt).all())

    def upsert_chunks(self, chunks: List[Any]) -> int:
        """
        Upsert a list of chunks (DocumentChunk dataclass or dict).
        Preserves unchanged chunks by comparing text_hash.
        """
        if not chunks:
            return 0

        now = now_iso()
        count = 0
        for c in chunks:
            if hasattr(c, "chunk_id"):
                cid = c.chunk_id
                doc_id = getattr(c, "doc_slug", "") or getattr(c, "doc_id", "")
                doc_version = getattr(c, "doc_version", 1)
                unit = getattr(c, "unit", "page")
                unit_no = getattr(c, "page_number", 1)
                cidx = getattr(c, "chunk_index", 0)
                thash = getattr(c, "text_hash", "")
                text = c.text
                toks = getattr(c, "token_count", 0)
                sfile = getattr(c, "source_file", "")
                legacy_id = getattr(c, "legacy_id", None)
            elif isinstance(c, dict):
                cid = c.get("chunk_id", "")
                doc_id = c.get("doc_id", "") or c.get("doc_slug", "")
                doc_version = c.get("doc_version", 1)
                unit = c.get("unit", "page")
                unit_no = c.get("page_number", c.get("unit_no", 1))
                cidx = c.get("chunk_index", 0)
                thash = c.get("text_hash", "")
                text = c.get("text", "")
                toks = c.get("token_count", 0)
                sfile = c.get("source_file", "")
                legacy_id = c.get("legacy_id")
            else:
                continue

            existing = self.get(cid)
            if existing:
                if existing.text_hash != thash or existing.doc_version != doc_version:
                    existing.text = text
                    existing.text_hash = thash
                    existing.doc_version = doc_version
                    existing.unit = unit
                    existing.unit_no = unit_no
                    existing.chunk_index = cidx
                    existing.token_count = toks
                    existing.source_file = sfile
                    if legacy_id:
                        existing.legacy_id = legacy_id
            else:
                chunk_obj = Chunk(
                    chunk_id=cid,
                    doc_id=doc_id,
                    doc_version=doc_version,
                    unit=unit,
                    unit_no=unit_no,
                    chunk_index=cidx,
                    text_hash=thash,
                    text=text,
                    token_count=toks,
                    source_file=sfile,
                    legacy_id=legacy_id,
                    created_at=now,
                )
                self.session.add(chunk_obj)
            count += 1

        self.session.flush()
        return count

    def delete_by_doc(self, doc_id: str) -> int:
        chunks = self.list_by_doc(doc_id)
        for c in chunks:
            self.session.delete(c)
        self.session.flush()
        return len(chunks)

    def delete_by_source(self, source_file: str) -> int:
        chunks = self.list_by_source_file(source_file)
        for c in chunks:
            self.session.delete(c)
        self.session.flush()
        return len(chunks)

    def count(self) -> int:
        return self.session.scalar(select(func.count(Chunk.chunk_id))) or 0
