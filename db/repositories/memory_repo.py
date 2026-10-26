"""
Memory repository for MentorOS.
Tracks per-student learning memory keyed by (session_id, course_id, concept_id) with migration resolution.
"""

from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import TopicAlias, TopicMemory, now_iso


class MemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_topic(
        self,
        session_id: str,
        course_id: str,
        concept_id: str,
    ) -> Optional[TopicMemory]:
        return self.session.get(TopicMemory, (session_id, course_id, concept_id))

    def list_topics(self, session_id: str, course_id: str = "default") -> List[TopicMemory]:
        stmt = (
            select(TopicMemory)
            .where(
                TopicMemory.session_id == session_id,
                TopicMemory.course_id == course_id,
            )
            .order_by(TopicMemory.confidence.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_weak_topics(
        self,
        session_id: str,
        course_id: str = "default",
        n: int = 5,
        threshold: float = 0.50,
    ) -> List[TopicMemory]:
        stmt = (
            select(TopicMemory)
            .where(
                TopicMemory.session_id == session_id,
                TopicMemory.course_id == course_id,
                TopicMemory.confidence < threshold,
            )
            .order_by(TopicMemory.confidence.asc())
            .limit(n)
        )
        return list(self.session.scalars(stmt).all())

    def get_strong_topics(
        self,
        session_id: str,
        course_id: str = "default",
        n: int = 5,
        threshold: float = 0.70,
    ) -> List[TopicMemory]:
        stmt = (
            select(TopicMemory)
            .where(
                TopicMemory.session_id == session_id,
                TopicMemory.course_id == course_id,
                TopicMemory.confidence >= threshold,
            )
            .order_by(TopicMemory.confidence.desc())
            .limit(n)
        )
        return list(self.session.scalars(stmt).all())

    def update_topic(
        self,
        session_id: str,
        course_id: str,
        concept_id: str,
        confidence_delta: Optional[float] = None,
        exact_confidence: Optional[float] = None,
        made_mistake: bool = False,
        asked_simpler: bool = False,
    ) -> TopicMemory:
        rec = self.get_topic(session_id, course_id, concept_id)
        now = now_iso()

        if rec is None:
            initial_conf = exact_confidence if exact_confidence is not None else 0.50
            rec = TopicMemory(
                session_id=session_id,
                course_id=course_id,
                concept_id=concept_id,
                confidence=initial_conf,
                mistake_count=1 if made_mistake else 0,
                interaction_count=1,
                last_seen=now,
            )
            self.session.add(rec)
        else:
            rec.interaction_count += 1
            rec.last_seen = now
            if made_mistake:
                rec.mistake_count += 1
                rec.confidence = max(0.05, min(1.0, rec.confidence - 0.15))
            elif asked_simpler:
                rec.confidence = max(0.05, min(1.0, rec.confidence - 0.08))
            elif exact_confidence is not None:
                # Blend 20% toward new eval score
                rec.confidence = max(0.05, min(1.0, (rec.confidence * 0.8) + (exact_confidence * 0.2)))
            elif confidence_delta is not None:
                rec.confidence = max(0.05, min(1.0, rec.confidence + confidence_delta))

        self.session.flush()
        return rec

    def resolve_topic_to_concept_id(
        self,
        topic_text: str,
        course_id: str = "default",
        embedder=None,
        concepts: Optional[List] = None,
        similarity_threshold: float = 0.80,
    ) -> Tuple[str, str]:
        """
        Resolve a topic string to a concept_id per prompt section 5:
        1. Exact match against topic_aliases.
        2. Embedding match of old topic string against concept titles.
        3. Fallback to 'topic:<free text>' retaining all history.
        Returns: (concept_id, resolution_method)
        """
        cleaned = topic_text.strip().lower()

        # Step 1: Exact alias match
        alias_stmt = select(TopicAlias.concept_id).where(
            TopicAlias.course_id == course_id,
            TopicAlias.alias == cleaned,
        )
        matched_concept = self.session.scalars(alias_stmt).first()
        if matched_concept:
            return matched_concept, "alias_match"

        # Step 2: Embedding match against concept titles
        if embedder and concepts:
            try:
                topic_emb = embedder.embed_text(cleaned)
                best_concept = None
                best_score = -1.0
                for c in concepts:
                    title_emb = embedder.embed_text(c.title.lower())
                    score = sum(a * b for a, b in zip(topic_emb, title_emb))
                    if score > best_score:
                        best_score = score
                        best_concept = c.concept_id

                if best_score >= similarity_threshold and best_concept:
                    # Register this new alias
                    new_alias = TopicAlias(
                        course_id=course_id,
                        alias=cleaned,
                        concept_id=best_concept,
                        created_at=now_iso(),
                    )
                    self.session.add(new_alias)
                    self.session.flush()
                    return best_concept, f"embedding_match_{best_score:.2f}"
            except Exception:
                pass

        # Step 3: Retain as topic:<free text>
        return f"topic:{cleaned}", "fallback_free_text"
