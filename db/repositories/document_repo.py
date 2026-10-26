"""
Document repository for MentorOS.
Handles document identity with stable slugs, collision resolution, and content-hash versioning.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import Document, now_iso


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, doc_id: str) -> Optional[Document]:
        return self.session.get(Document, doc_id)

    def get_by_slug(self, course_id: str, slug: str) -> Optional[Document]:
        stmt = select(Document).where(
            Document.course_id == course_id,
            Document.slug == slug,
        )
        return self.session.scalars(stmt).first()

    def list_by_course(self, course_id: str) -> List[Document]:
        stmt = (
            select(Document)
            .where(Document.course_id == course_id)
            .order_by(Document.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_or_create_doc_id(self, course_id: str, base_slug: str, filename: str) -> str:
        """
        Derive doc_id from slug with collision suffix if a different file already used this slug.
        If the same filename was used, reuse the existing doc_id.
        """
        existing = self.get_by_slug(course_id, base_slug)
        if not existing or existing.filename == filename:
            return base_slug

        # Collision with a different file name: add collision suffix
        counter = 1
        while True:
            candidate = f"{base_slug}-{counter}"
            doc = self.get_by_slug(course_id, candidate)
            if not doc or doc.filename == filename:
                return candidate
            counter += 1

    def upsert(
        self,
        course_id: str,
        base_slug: str,
        filename: str,
        content_hash: str,
    ) -> Document:
        """
        Upsert a document.
        - If new: creates version 1.
        - If existing with different content_hash: bumps version and updates hash.
        - If existing with same content_hash: returns unchanged.
        """
        doc_id = self.get_or_create_doc_id(course_id, base_slug, filename)
        doc = self.get(doc_id)

        now = now_iso()
        if doc:
            if doc.content_hash != content_hash:
                doc.version += 1
                doc.content_hash = content_hash
                doc.status = "processing"
                doc.error = None
                doc.updated_at = now
            else:
                doc.updated_at = now
        else:
            doc = Document(
                doc_id=doc_id,
                course_id=course_id,
                slug=doc_id,
                filename=filename,
                content_hash=content_hash,
                version=1,
                status="processing",
                error=None,
                created_at=now,
                updated_at=now,
            )
            self.session.add(doc)

        self.session.flush()
        return doc

    def update_status(self, doc_id: str, status: str, error: Optional[str] = None):
        doc = self.get(doc_id)
        if doc:
            doc.status = status
            doc.error = error
            doc.updated_at = now_iso()
            self.session.flush()

    def delete(self, doc_id: str) -> bool:
        doc = self.get(doc_id)
        if doc:
            self.session.delete(doc)
            self.session.flush()
            return True
        return False
