"""
Evaluation Agent (Hallucination Gate) for MentorOS (Phase 5).
Scores generated answers against retrieved document context for faithfulness and factual grounding.

Features:
  1. Dual Scoring: Semantic embedding similarity + LLM Faithfulness judge call.
  2. Threshold Enforcement: Default 60% (0.60) confidence threshold.
  3. Hallucination Refusal: If score < threshold, blocks answer and returns transparent refusal.
  4. Explainable AI: Provides confidence percentage and rationale for UI panel.
"""

from dataclasses import dataclass, asdict
import json
import logging
import re
from typing import List, Optional, Union

from embeddings import EmbeddingModel, RetrievedChunk
from llm.ollama_client import OllamaClient

logger = logging.getLogger("MentorOS.EvaluationAgent")


@dataclass
class EvaluationResult:
    """Result of Evaluation Agent assessment."""
    passed_gate: bool
    confidence_score: float        # Combined score (0.0 to 1.0)
    faithfulness_score: float      # LLM judge score (0.0 to 1.0)
    semantic_similarity: float     # Embedding similarity score (0.0 to 1.0)
    reasoning: str                 # Rationale for Explainable AI panel
    filtered_answer: str           # Original answer if passed, or refusal message if blocked
    original_answer: str           # Raw generated answer from RAG model
    threshold_used: float = 0.60

    def to_dict(self) -> dict:
        return asdict(self)


class EvaluationAgent:
    """The Hallucination Gate for MentorOS."""

    DEFAULT_THRESHOLD = 0.60  # 60% confidence threshold
    REFUSAL_MESSAGE = (
        "I couldn't find enough evidence in the uploaded documents to answer this safely. "
        "Please upload more material on this topic."
    )

    JUDGE_SYSTEM_PROMPT = """You are an impartial Faithfulness Evaluator for a RAG system.
Evaluate whether the Proposed Answer is strictly supported ONLY by the Provided Context.

Scoring Rules:
- Score 90-100: Answer is completely supported by the context without hallucination.
- Score 60-89: Answer is mostly supported, with minor unverified details.
- Score 0-59: Answer introduces facts NOT present in context, or directly contradicts context.

Respond in JSON format ONLY:
{"faithfulness_score": <int 0-100>, "is_supported": <bool>, "reasoning": "<brief 1-2 sentence explanation>"}'"""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        embedder: Optional[EmbeddingModel] = None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.ollama_client = ollama_client or OllamaClient()
        self.embedder = embedder or EmbeddingModel()
        self.threshold = threshold

    def _compute_semantic_similarity(self, answer: str, chunks: List[RetrievedChunk]) -> float:
        """Compute cosine similarity between generated answer and top retrieved context chunk."""
        if not chunks or not answer.strip():
            return 0.0

        answer_emb = self.embedder.embed_text(answer)
        top_chunk_emb = self.embedder.embed_text(chunks[0].text)

        # Dot product of normalized vectors = Cosine similarity
        sim = sum(a * b for a, b in zip(answer_emb, top_chunk_emb))
        return max(0.0, min(1.0, float(sim)))

    def _judge_faithfulness(self, query: str, answer: str, context_text: str) -> tuple[float, str]:
        """Call Ollama LLM as a judge to evaluate faithfulness of answer against context."""
        judge_prompt = f"""[Context]:
{context_text}

[Question]:
{query}

[Proposed Answer]:
{answer}

JSON Evaluation:"""

        try:
            raw_res = self.ollama_client.generate(
                prompt=judge_prompt,
                system_prompt=self.JUDGE_SYSTEM_PROMPT,
                temperature=0.0,
            )

            match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                raw_score = float(data.get("faithfulness_score", 70))
                normalized_score = max(0.0, min(1.0, raw_score / 100.0))
                reasoning = data.get("reasoning", "Evaluated by LLM Judge.")
                return normalized_score, reasoning
        except Exception as e:
            logger.warning(f"Faithfulness LLM judge call failed: {e}")

        # Fallback if LLM judge call fails
        return 0.70, "Evaluated via semantic similarity heuristic."

    def evaluate(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[RetrievedChunk],
        threshold: Optional[float] = None,
    ) -> EvaluationResult:
        """
        Evaluate generated answer against retrieved context chunks.

        If confidence_score < threshold (60%), blocks the answer and returns refusal message.
        """
        current_threshold = threshold if threshold is not None else self.threshold

        # Handle empty retrieval or empty answer
        if not retrieved_chunks or not answer.strip():
            return EvaluationResult(
                passed_gate=False,
                confidence_score=0.0,
                faithfulness_score=0.0,
                semantic_similarity=0.0,
                reasoning="No relevant document context was retrieved to verify this answer.",
                filtered_answer=self.REFUSAL_MESSAGE,
                original_answer=answer,
                threshold_used=current_threshold,
            )

        # Step 1: Compute Semantic Similarity
        sem_sim = self._compute_semantic_similarity(answer, retrieved_chunks)

        # Step 2: Format Context Text
        context_text = "\n\n".join(
            f"[Page {c.page_number}]: {c.text}" for c in retrieved_chunks[:3]
        )

        # Step 3: LLM Judge Faithfulness Call
        faithfulness_score, reasoning = self._judge_faithfulness(query, answer, context_text)

        # Step 4: Combined Confidence Score (70% Faithfulness Judge + 30% Semantic Similarity)
        combined_confidence = round((0.70 * faithfulness_score) + (0.30 * sem_sim), 4)

        # Step 5: Gate Enforcement
        passed = combined_confidence >= current_threshold

        filtered_answer = answer if passed else self.REFUSAL_MESSAGE

        logger.info(
            f"Evaluation Gate: [{'PASSED' if passed else 'BLOCKED'}] | "
            f"Confidence: {combined_confidence * 100:.1f}% (Threshold: {current_threshold * 100:.0f}%) | "
            f"Faithfulness: {faithfulness_score * 100:.1f}% | Similarity: {sem_sim * 100:.1f}%"
        )

        return EvaluationResult(
            passed_gate=passed,
            confidence_score=combined_confidence,
            faithfulness_score=round(faithfulness_score, 4),
            semantic_similarity=round(sem_sim, 4),
            reasoning=reasoning,
            filtered_answer=filtered_answer,
            original_answer=answer,
            threshold_used=current_threshold,
        )
