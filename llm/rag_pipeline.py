"""
Baseline RAG Pipeline for MentorOS (Phase 3 & 5).
Executes end-to-end RAG workflow:
  1. Retrieve top-k relevant chunks from Chroma VectorStore
  2. Format strict grounded prompt template with citation markers
  3. Query local Ollama LLM
  4. Run Evaluation Agent (Hallucination Gate) to score faithfulness & enforce 60% threshold
  5. Return grounded answer with citation metadata and confidence score for Explainable AI
"""

from dataclasses import dataclass, field
from typing import List, Optional
import time

from embeddings import VectorStore, RetrievedChunk, get_vector_store
from llm.ollama_client import OllamaClient
from agents.evaluation_agent import EvaluationAgent, EvaluationResult


BASELINE_RAG_PROMPT_TEMPLATE = """Answer the question using ONLY the context below. If the context doesn't contain the answer, say "I don't have enough information in the uploaded documents to answer this."

Context:
{context_text}

Question: {user_question}
Answer:"""

REFUSAL_RESPONSE = "I couldn't find enough evidence in the uploaded documents to answer this safely. Please upload more material on this topic."


@dataclass
class Citation:
    """Represents a source citation for Explainable AI."""
    source_file: str
    page_number: int
    chunk_id: str
    score: float

    def format_citation(self) -> str:
        return f"{self.source_file} (Page {self.page_number})"


@dataclass
class RAGResponse:
    """End-to-end RAG answer output with citations, evaluation metrics, and latency."""
    query: str
    answer: str
    raw_answer: str
    citations: List[Citation]
    retrieved_chunks: List[RetrievedChunk]
    latency_seconds: float
    model_name: str
    confidence_score: float
    passed_gate: bool
    evaluation: Optional[EvaluationResult] = None
    is_refusal: bool = False


class BaselineRAG:
    """Baseline RAG pipeline for MentorOS integrated with Evaluation Agent."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        ollama_client: Optional[OllamaClient] = None,
        evaluation_agent: Optional[EvaluationAgent] = None,
        top_k: int = 5,
        temperature: float = 0.2,
        eval_threshold: float = 0.60,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.ollama_client = ollama_client or OllamaClient()
        self.evaluation_agent = evaluation_agent or EvaluationAgent(ollama_client=self.ollama_client)
        self.top_k = top_k
        self.temperature = temperature
        self.eval_threshold = eval_threshold

    def _format_context(self, chunks: List[RetrievedChunk]) -> str:
        """Format retrieved chunks into a numbered context block with citation headers."""
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            header = f"[Document #{i} | Source: {chunk.source_file} | Page {chunk.page_number}]"
            context_parts.append(f"{header}\n{chunk.text}")
        return "\n\n".join(context_parts)

    def answer_question(
        self,
        query: str,
        k: Optional[int] = None,
        temperature: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> RAGResponse:
        """
        Execute RAG pipeline with hallucination gating.

        Flow:
          1. retrieve top-k chunks from vector store
          2. format prompt with context & citation metadata
          3. call Ollama local LLM
          4. run Evaluation Agent to score confidence & enforce threshold
          5. return RAGResponse with filtered answer and citations
        """
        start_time = time.time()
        k = k or self.top_k
        temp = temperature if temperature is not None else self.temperature
        thresh = threshold if threshold is not None else self.eval_threshold

        # Step 1: Retrieve top-k chunks
        retrieved_chunks = self.vector_store.retrieve(query, k=k)

        # Step 2: Handle empty index / no relevant chunks case
        if not retrieved_chunks:
            elapsed = time.time() - start_time
            eval_res = EvaluationResult(
                passed_gate=False,
                confidence_score=0.0,
                faithfulness_score=0.0,
                semantic_similarity=0.0,
                reasoning="No context retrieved from vector store.",
                filtered_answer=REFUSAL_RESPONSE,
                original_answer="",
                threshold_used=thresh,
            )
            return RAGResponse(
                query=query,
                answer=REFUSAL_RESPONSE,
                raw_answer="",
                citations=[],
                retrieved_chunks=[],
                latency_seconds=round(elapsed, 3),
                model_name=self.ollama_client.model_name,
                confidence_score=0.0,
                passed_gate=False,
                evaluation=eval_res,
                is_refusal=True,
            )

        # Step 3: Format context & build prompt
        context_text = self._format_context(retrieved_chunks)
        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(
            context_text=context_text,
            user_question=query.strip(),
        )

        # Step 4: Query local Ollama LLM
        raw_answer = self.ollama_client.generate(prompt=prompt, temperature=temp)

        # Step 5: Run Evaluation Agent (Hallucination Gate)
        eval_result = self.evaluation_agent.evaluate(
            query=query,
            answer=raw_answer,
            retrieved_chunks=retrieved_chunks,
            threshold=thresh,
        )

        # Step 6: Build citations
        citations = [
            Citation(
                source_file=c.source_file,
                page_number=c.page_number,
                chunk_id=c.chunk_id,
                score=c.score,
            )
            for c in retrieved_chunks
        ]

        elapsed = time.time() - start_time

        return RAGResponse(
            query=query,
            answer=eval_result.filtered_answer,
            raw_answer=raw_answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            latency_seconds=round(elapsed, 3),
            model_name=self.ollama_client.model_name,
            confidence_score=eval_result.confidence_score,
            passed_gate=eval_result.passed_gate,
            evaluation=eval_result,
            is_refusal=not eval_result.passed_gate,
        )
