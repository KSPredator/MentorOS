"""
Baseline RAG Pipeline for MentorOS (Phase 3).
Executes end-to-end RAG workflow:
  1. Retrieve top-k relevant chunks from Chroma VectorStore
  2. Format strict grounded prompt template with citation markers
  3. Query local Ollama LLM
  4. Return grounded answer with citation metadata
"""

from dataclasses import dataclass, field
from typing import List, Optional
import time

from embeddings import VectorStore, RetrievedChunk, get_vector_store
from llm.ollama_client import OllamaClient


# Strict grounding prompt template specified in Phase 3 of mentoros-build-roadmap.md
BASELINE_RAG_PROMPT_TEMPLATE = """Answer the question using ONLY the context below. If the context doesn't contain the answer, say "I don't have enough information in the uploaded documents to answer this."

Context:
{context_text}

Question: {user_question}
Answer:"""

REFUSAL_RESPONSE = "I don't have enough information in the uploaded documents to answer this."


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
    """End-to-end RAG answer output with citations and timing performance metrics."""
    query: str
    answer: str
    citations: List[Citation]
    retrieved_chunks: List[RetrievedChunk]
    latency_seconds: float
    model_name: str
    is_refusal: bool = False


class BaselineRAG:
    """Naive Baseline RAG pipeline for MentorOS."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        ollama_client: Optional[OllamaClient] = None,
        top_k: int = 5,
        temperature: float = 0.2,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.ollama_client = ollama_client or OllamaClient()
        self.top_k = top_k
        self.temperature = temperature

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
    ) -> RAGResponse:
        """
        Execute baseline RAG pipeline for a user question.

        Flow:
          1. retrieve top-k chunks from vector store
          2. format prompt with context & citation metadata
          3. call Ollama local LLM
          4. return RAGResponse with citations and latency
        """
        start_time = time.time()
        k = k or self.top_k
        temp = temperature if temperature is not None else self.temperature

        # Step 1: Retrieve top-k chunks
        retrieved_chunks = self.vector_store.retrieve(query, k=k)

        # Step 2: Handle empty index / no relevant chunks case
        if not retrieved_chunks:
            elapsed = time.time() - start_time
            return RAGResponse(
                query=query,
                answer=REFUSAL_RESPONSE,
                citations=[],
                retrieved_chunks=[],
                latency_seconds=round(elapsed, 3),
                model_name=self.ollama_client.model_name,
                is_refusal=True,
            )

        # Step 3: Format context & build prompt
        context_text = self._format_context(retrieved_chunks)
        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(
            context_text=context_text,
            user_question=query.strip(),
        )

        # Step 4: Query local Ollama LLM
        answer = self.ollama_client.generate(prompt=prompt, temperature=temp)

        # Check if the LLM outputted a refusal message
        is_refusal = (
            REFUSAL_RESPONSE.lower() in answer.lower()
            or "don't have enough information" in answer.lower()
            or "do not have enough information" in answer.lower()
        )

        # Step 5: Build citations
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
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            latency_seconds=round(elapsed, 3),
            model_name=self.ollama_client.model_name,
            is_refusal=is_refusal,
        )
