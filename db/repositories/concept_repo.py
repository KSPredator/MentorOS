"""
Concept repository for MentorOS.
Manages concept pages, source chunk mappings, and topic aliases.
"""

import json
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import Concept, ConceptSource, TopicAlias, now_iso


class ConceptRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, concept_id: str) -> Optional[Concept]:
        return self.session.get(Concept, concept_id)

    def list_by_course(self, course_id: str, status: Optional[str] = None) -> List[Concept]:
        stmt = select(Concept).where(Concept.course_id == course_id)
        if status:
            stmt = stmt.where(Concept.status == status)
        stmt = stmt.order_by(Concept.title.asc())
        return list(self.session.scalars(stmt).all())

    def upsert(
        self,
        concept_id: str,
        course_id: str,
        title: str,
        body: str,
        meta: Optional[Dict] = None,
        status: str = "draft",
        trust_tier: str = "unverified",
        description: Optional[str] = None,
        bundle_commit: Optional[str] = None,
        input_hash: Optional[str] = None,
    ) -> Concept:
        concept = self.get(concept_id)
        now = now_iso()
        meta_str = json.dumps(meta or {}, ensure_ascii=False)

        if concept:
            concept.course_id = course_id
            concept.title = title
            concept.body = body
            concept.description = description
            concept.status = status
            concept.trust_tier = trust_tier
            concept.meta_json = meta_str
            concept.updated_at = now
            if bundle_commit:
                concept.bundle_commit = bundle_commit
            if input_hash:
                concept.input_hash = input_hash
        else:
            concept = Concept(
                concept_id=concept_id,
                course_id=course_id,
                title=title,
                description=description,
                status=status,
                trust_tier=trust_tier,
                bundle_commit=bundle_commit,
                input_hash=input_hash,
                body=body,
                meta_json=meta_str,
                created_at=now,
                updated_at=now,
            )
            self.session.add(concept)

        self.session.flush()
        return concept

    def link_sources(self, concept_id: str, chunk_ids: List[str]) -> None:
        """Replace source chunk references for this concept."""
        # Delete existing links
        existing_stmt = select(ConceptSource).where(ConceptSource.concept_id == concept_id)
        for s in self.session.scalars(existing_stmt).all():
            self.session.delete(s)
        self.session.flush()

        # Add new links
        for cid in set(chunk_ids):
            cs = ConceptSource(concept_id=concept_id, chunk_id=cid)
            self.session.add(cs)
        self.session.flush()

    def get_sources(self, concept_id: str) -> List[str]:
        stmt = select(ConceptSource.chunk_id).where(ConceptSource.concept_id == concept_id)
        return list(self.session.scalars(stmt).all())

    def add_alias(self, course_id: str, alias: str, concept_id: str) -> TopicAlias:
        alias_clean = alias.strip().lower()
        stmt = select(TopicAlias).where(
            TopicAlias.course_id == course_id,
            TopicAlias.alias == alias_clean,
        )
        existing = self.session.scalars(stmt).first()
        if existing:
            existing.concept_id = concept_id
            self.session.flush()
            return existing

        alias_obj = TopicAlias(
            course_id=course_id,
            alias=alias_clean,
            concept_id=concept_id,
            created_at=now_iso(),
        )
        self.session.add(alias_obj)
        self.session.flush()
        return alias_obj

    def resolve_alias(self, course_id: str, alias: str) -> Optional[str]:
        alias_clean = alias.strip().lower()
        stmt = select(TopicAlias.concept_id).where(
            TopicAlias.course_id == course_id,
            TopicAlias.alias == alias_clean,
        )
        return self.session.scalars(stmt).first()

    def delete(self, concept_id: str) -> bool:
        concept = self.get(concept_id)
        if concept:
            self.session.delete(concept)
            self.session.flush()
            return True
        return False
