"""
Phase 8 Evaluation Metrics Module for MentorOS
=============================================
Implements standard Information Retrieval & Generation metrics:
  - Recall@K (K=1, 3, 5)
  - MRR (Mean Reciprocal Rank)
  - Semantic Similarity / BERTScore Proxy
  - Faithfulness / Hallucination Rate
  - Latency breakdown
"""

import math
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from embeddings.embedder import EmbeddingModel
from embeddings.vector_store import RetrievedChunk


def _normalize_text(text: str) -> str:
    """Lowercase and strip punctuation for token matching."""
    text = text.lower()
    return re.sub(r"[^\w\s]", " ", text)


def _extract_keywords(text: str, min_len: int = 3) -> set:
    """Extract informative keywords from text, filtering common stopwords."""
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from", "are", "what",
        "how", "why", "which", "when", "where", "does", "have", "been", "was",
        "were", "will", "can", "into", "than", "more", "such", "also", "their"
    }
    words = _normalize_text(text).split()
    return {w for w in words if len(w) >= min_len and w not in stopwords}


def is_chunk_relevant(chunk_text: str, ground_truth: str, threshold: float = 0.40) -> bool:
    """
    Determines if a retrieved chunk contains the ground truth answer.
    Checks keyword overlap and substring containment.
    """
    gt_keywords = _extract_keywords(ground_truth)
    if not gt_keywords:
        return True
        
    chunk_normalized = _normalize_text(chunk_text)
    matched = sum(1 for kw in gt_keywords if kw in chunk_normalized)
    overlap_ratio = matched / len(gt_keywords)
    
    return overlap_ratio >= threshold


def compute_recall_at_k(
    retrieved_chunks: List[RetrievedChunk],
    ground_truth: str,
    k: int = 3,
) -> float:
    """
    Recall@K: 1.0 if at least one of the top-k chunks is relevant, else 0.0.
    """
    top_k = retrieved_chunks[:k]
    for chunk in top_k:
        if is_chunk_relevant(chunk.text, ground_truth):
            return 1.0
    return 0.0


def compute_mrr(
    retrieved_chunks: List[RetrievedChunk],
    ground_truth: str,
    max_k: int = 10,
) -> float:
    """
    Mean Reciprocal Rank (MRR): 1 / (rank of first relevant chunk), or 0.0 if not found in top max_k.
    """
    for rank, chunk in enumerate(retrieved_chunks[:max_k], start=1):
        if is_chunk_relevant(chunk.text, ground_truth):
            return 1.0 / rank
    return 0.0


class SemanticScoreEvaluator:
    """Evaluates semantic similarity between generated answer and ground truth (BERTScore proxy)."""

    def __init__(self, embedder: Optional[EmbeddingModel] = None):
        self.embedder = embedder or EmbeddingModel()

    def score(self, generated_answer: str, ground_truth: str) -> float:
        """Compute cosine similarity between embeddings of generated and reference answers."""
        if not generated_answer.strip() or not ground_truth.strip():
            return 0.0
            
        gen_emb = self.embedder.embed_text(generated_answer)
        gt_emb = self.embedder.embed_text(ground_truth)
        
        sim = sum(a * b for a, b in zip(gen_emb, gt_emb))
        return max(0.0, min(1.0, float(sim)))
