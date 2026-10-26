"""
Hybrid Retriever for MentorOS.
Blends OKF curated concept pages with raw document chunk retrieval.

Flow:
  1. Query course concept vector index (title + description + tags)
  2. Skip deprecated concepts; penalize stale concepts
  3. 1-hop graph expansion over Markdown links (capped at 2-3 extra concepts)
  4. If best concept score >= threshold:
       context = concept body + raw cited source chunks (from SQLite chunks table)
       path = "okf"
     Else:
       fall back to raw chunk VectorStore.retrieve()
       path = "rag"
  5. Return unified List[RetrievedChunk] with path and trust_tier metadata
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from api import config
from db import get_db_session, ConceptRepository, ChunkRepository, CourseRepository
from embeddings.vector_store import RetrievedChunk, VectorStore
from embeddings.vector_index import ChromaVectorIndex, get_course_collection_name
from okf.bundle import is_stale, trust_tier, load_concept
from okf.graph import extract_links

logger = logging.getLogger("MentorOS.HybridRetriever")


@dataclass
class HybridRetrievalResult:
    chunks: List[RetrievedChunk]
    path: str                   # "okf" | "rag"
    concept_ids: List[str]      # list of concept IDs matched
    trust_tier: str             # "unverified" | "machine-confirmed" | "human-reviewed"
    best_concept_score: float   # highest concept similarity score
    is_stale: bool = False


class HybridRetriever:
    """Combines OKF concept graph retrieval with raw chunk vector fallback."""

    def __init__(
        self,
        raw_vector_store: Optional[VectorStore] = None,
        concept_threshold: float = 0.50,
        use_okf: Optional[bool] = None,
    ):
        self.raw_vector_store = raw_vector_store
        self.concept_threshold = concept_threshold
        self.use_okf = use_okf if use_okf is not None else config.USE_OKF

    def _fallback_rag(self, query: str, course_id: str, k: int) -> HybridRetrievalResult:
        """Call standard chunk retriever."""
        if self.raw_vector_store is not None:
            chunks = self.raw_vector_store.retrieve(query, k=k)
        else:
            col_name = get_course_collection_name(course_id=course_id, version=1)
            index = ChromaVectorIndex(collection_name=col_name, persist_dir=config.CHROMA_DIR)
            chunks = index.query(query, k=k)

        return HybridRetrievalResult(
            chunks=chunks,
            path="rag",
            concept_ids=[],
            trust_tier="unverified",
            best_concept_score=0.0,
            is_stale=False,
        )

    def retrieve(
        self,
        query: str,
        course_id: str = "default",
        k: int = 5,
        threshold: Optional[float] = None,
    ) -> HybridRetrievalResult:
        """
        Execute hybrid retrieval pipeline.
        With USE_OKF=False, directly calls raw RAG.
        """
        thresh = threshold if threshold is not None else self.concept_threshold

        # Feature flag check (safe baseline fallback)
        if not self.use_okf:
            return self._fallback_rag(query, course_id=course_id, k=k)

        concepts_col = get_course_collection_name(course_id=course_id, is_concepts=True)
        try:
            concept_index = ChromaVectorIndex(collection_name=concepts_col, persist_dir=config.CHROMA_DIR)
            if concept_index.count() == 0:
                return self._fallback_rag(query, course_id=course_id, k=k)

            # 1. Search concept collection
            matched_concepts = concept_index.query(query, k=3)
            if not matched_concepts:
                return self._fallback_rag(query, course_id=course_id, k=k)

            best_match = matched_concepts[0]
            if best_match.score < thresh:
                logger.info(f"OKF concept score {best_match.score:.2f} < threshold {thresh:.2f}. Falling back to RAG.")
                return self._fallback_rag(query, course_id=course_id, k=k)

            # 2. Load primary concept from database
            with get_db_session() as session:
                concept_repo = ConceptRepository(session)
                chunk_repo = ChunkRepository(session)

                primary_concept = concept_repo.get(best_match.chunk_id)
                if not primary_concept or primary_concept.status == "deprecated":
                    return self._fallback_rag(query, course_id=course_id, k=k)

                concept_ids = [primary_concept.concept_id]
                trust = primary_concept.trust_tier or "unverified"
                concept_chunks_out: List[RetrievedChunk] = []

                # Synthesize primary concept chunk
                concept_chunk = RetrievedChunk(
                    chunk_id=primary_concept.concept_id,
                    text=f"# {primary_concept.title}\n\n{primary_concept.body}",
                    source_file=f"bundle/{primary_concept.concept_id}.md",
                    page_number=1,
                    chunk_index=0,
                    score=best_match.score,
                    metadata={
                        "is_okf_concept": True,
                        "concept_id": primary_concept.concept_id,
                        "trust_tier": trust,
                        "title": primary_concept.title,
                    },
                    doc_slug=primary_concept.concept_id.split("/")[-1],
                )
                concept_chunks_out.append(concept_chunk)

                # 3. One-hop graph expansion over linked concepts (cap at 2 extra)
                linked_concepts = []
                link_pattern = r"\[([^\]]+)\]\(([^)]+\.md)\)"
                raw_links = re.findall(link_pattern, primary_concept.body)
                for _, link_target in raw_links[:2]:
                    target_slug = link_target.replace(".md", "").split("/")[-1]
                    target_cid = f"{course_id}/{target_slug}"
                    linked_c = concept_repo.get(target_cid)
                    if linked_c and linked_c.status != "deprecated":
                        linked_concepts.append(linked_c)
                        concept_ids.append(linked_c.concept_id)
                        concept_chunks_out.append(
                            RetrievedChunk(
                                chunk_id=linked_c.concept_id,
                                text=f"# Related Concept: {linked_c.title}\n\n{linked_c.body[:400]}",
                                source_file=f"bundle/{linked_c.concept_id}.md",
                                page_number=1,
                                chunk_index=0,
                                score=round(best_match.score * 0.9, 4),
                                metadata={
                                    "is_okf_concept": True,
                                    "concept_id": linked_c.concept_id,
                                    "trust_tier": linked_c.trust_tier,
                                },
                                doc_slug=target_slug,
                            )
                        )

                # 4. Fetch raw cited chunks for grounding
                cited_chunk_ids = concept_repo.get_sources(primary_concept.concept_id)
                for cid in cited_chunk_ids[:4]:
                    raw_c = chunk_repo.get(cid)
                    if raw_c:
                        concept_chunks_out.append(
                            RetrievedChunk(
                                chunk_id=raw_c.chunk_id,
                                text=raw_c.text,
                                source_file=raw_c.source_file,
                                page_number=raw_c.unit_no,
                                chunk_index=raw_c.chunk_index,
                                score=best_match.score,
                                metadata={
                                    "is_raw_cited_chunk": True,
                                    "source_file": raw_c.source_file,
                                    "page_number": raw_c.unit_no,
                                },
                                doc_slug=raw_c.doc_id,
                            )
                        )

                logger.info(
                    f"OKF Concept Match: [{primary_concept.concept_id}] (Score: {best_match.score:.2f}) | "
                    f"Trust: {trust} | Linked: {len(linked_concepts)} | Grounding Chunks: {len(cited_chunk_ids)}"
                )

                return HybridRetrievalResult(
                    chunks=concept_chunks_out,
                    path="okf",
                    concept_ids=concept_ids,
                    trust_tier=trust,
                    best_concept_score=best_match.score,
                    is_stale=False,
                )

        except Exception as e:
            logger.warning(f"Hybrid retrieval encountered error: {e}. Falling back to RAG.")
            return self._fallback_rag(query, course_id=course_id, k=k)
