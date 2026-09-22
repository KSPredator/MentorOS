"""
Phase 8 Baseline Pipelines for Benchmark Comparison
===================================================
Defines 3 comparative RAG architectures:
  1. Full MentorOS: Planner + ChromaDB Dense Retrieval + LLM + Evaluation Agent Gate
  2. Naive RAG: Dense Retrieval + LLM (no gate, unverified)
  3. BM25 Sparse RAG: BM25 Keyword Search + LLM (no embeddings, no gate)
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rank_bm25 import BM25Okapi
from agents.evaluation_agent import EvaluationAgent, EvaluationResult
from agents.planner_agent import PlannerAgent, PlannerAction
from embeddings import get_vector_store, VectorStore, RetrievedChunk
from llm.ollama_client import OllamaClient
from llm.rag_pipeline import BaselineRAG, BASELINE_RAG_PROMPT_TEMPLATE, REFUSAL_RESPONSE


@dataclass
class PipelineResult:
    query: str
    answer: str
    raw_answer: str
    retrieved_chunks: List[RetrievedChunk]
    passed_gate: bool
    confidence_score: float
    is_refusal: bool
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    eval_latency_ms: float
    pipeline_name: str


class BM25Retriever:
    """In-memory BM25 sparse keyword retriever using rank_bm25."""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vs = vector_store or get_vector_store()
        self._build_index()

    def _build_index(self):
        # Fetch all records from Chroma collection
        results = self.vs.collection.get(include=["documents", "metadatas"])
        self.doc_ids = results.get("ids", [])
        self.documents = results.get("documents", [])
        self.metadatas = results.get("metadatas", [])

        # Tokenize corpus for BM25
        self.tokenized_corpus = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    def retrieve(self, query: str, k: int = 5) -> List[RetrievedChunk]:
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sort indices by descending score
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        retrieved = []
        for idx in top_indices:
            meta = self.metadatas[idx] if idx < len(self.metadatas) else {}
            score = float(scores[idx])
            retrieved.append(
                RetrievedChunk(
                    chunk_id=self.doc_ids[idx],
                    text=self.documents[idx],
                    source_file=meta.get("source_file", "unknown"),
                    page_number=meta.get("page_number", 1),
                    chunk_index=meta.get("chunk_index", 0),
                    score=score,
                    metadata=meta,
                )
            )
        return retrieved


class FullMentorOSPipeline:
    """Full MentorOS system with Planner and Evaluation Agent Hallucination Gate."""

    def __init__(self, ollama: Optional[OllamaClient] = None, vs: Optional[VectorStore] = None):
        self.ollama = ollama or OllamaClient()
        self.vs = vs or get_vector_store()
        self.planner = PlannerAgent(ollama_client=self.ollama)
        self.eval_agent = EvaluationAgent(ollama_client=self.ollama, threshold=0.60)
        self.rag = BaselineRAG(
            vector_store=self.vs,
            ollama_client=self.ollama,
            evaluation_agent=self.eval_agent,
        )

    def run(self, query: str, k: int = 3) -> PipelineResult:
        t0 = time.perf_counter()
        
        # 1. Planner routing
        decision = self.planner.route(query)
        
        # 2. Retrieval
        t_ret_start = time.perf_counter()
        chunks = self.vs.retrieve(query, k=k)
        t_ret = (time.perf_counter() - t_ret_start) * 1000
        
        # 3. Generation
        t_gen_start = time.perf_counter()
        context_text = "\n\n".join(f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}" for c in chunks)
        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(context_text=context_text, user_question=query)
        raw_answer = self.ollama.generate(prompt=prompt, temperature=0.2)
        t_gen = (time.perf_counter() - t_gen_start) * 1000
        
        # 4. Evaluation Gate
        t_eval_start = time.perf_counter()
        eval_res = self.eval_agent.evaluate(query=query, answer=raw_answer, retrieved_chunks=chunks)
        t_eval = (time.perf_counter() - t_eval_start) * 1000
        
        total_time = (time.perf_counter() - t0) * 1000
        
        return PipelineResult(
            query=query,
            answer=eval_res.filtered_answer,
            raw_answer=raw_answer,
            retrieved_chunks=chunks,
            passed_gate=eval_res.passed_gate,
            confidence_score=eval_res.confidence_score,
            is_refusal=not eval_res.passed_gate,
            latency_ms=total_time,
            retrieval_latency_ms=t_ret,
            generation_latency_ms=t_gen,
            eval_latency_ms=t_eval,
            pipeline_name="Full MentorOS (Dense + Gate)",
        )


class NaiveRAGPipeline:
    """Naive baseline RAG without Planner routing or Hallucination Gating."""

    def __init__(self, ollama: Optional[OllamaClient] = None, vs: Optional[VectorStore] = None):
        self.ollama = ollama or OllamaClient()
        self.vs = vs or get_vector_store()

    def run(self, query: str, k: int = 3) -> PipelineResult:
        t0 = time.perf_counter()
        
        t_ret_start = time.perf_counter()
        chunks = self.vs.retrieve(query, k=k)
        t_ret = (time.perf_counter() - t_ret_start) * 1000
        
        t_gen_start = time.perf_counter()
        context_text = "\n\n".join(f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}" for c in chunks)
        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(context_text=context_text, user_question=query)
        raw_answer = self.ollama.generate(prompt=prompt, temperature=0.2)
        t_gen = (time.perf_counter() - t_gen_start) * 1000
        
        total_time = (time.perf_counter() - t0) * 1000
        
        return PipelineResult(
            query=query,
            answer=raw_answer,
            raw_answer=raw_answer,
            retrieved_chunks=chunks,
            passed_gate=True,
            confidence_score=1.0,
            is_refusal=False,
            latency_ms=total_time,
            retrieval_latency_ms=t_ret,
            generation_latency_ms=t_gen,
            eval_latency_ms=0.0,
            pipeline_name="Naive RAG (Dense, No Gate)",
        )


class BM25RAGPipeline:
    """Sparse keyword retrieval baseline using BM25 with no hallucination gate."""

    def __init__(self, ollama: Optional[OllamaClient] = None, vs: Optional[VectorStore] = None):
        self.ollama = ollama or OllamaClient()
        self.retriever = BM25Retriever(vector_store=vs)

    def run(self, query: str, k: int = 3) -> PipelineResult:
        t0 = time.perf_counter()
        
        t_ret_start = time.perf_counter()
        chunks = self.retriever.retrieve(query, k=k)
        t_ret = (time.perf_counter() - t_ret_start) * 1000
        
        t_gen_start = time.perf_counter()
        context_text = "\n\n".join(f"[Source: {c.source_file} | Page {c.page_number}]\n{c.text}" for c in chunks)
        prompt = BASELINE_RAG_PROMPT_TEMPLATE.format(context_text=context_text, user_question=query)
        raw_answer = self.ollama.generate(prompt=prompt, temperature=0.2)
        t_gen = (time.perf_counter() - t_gen_start) * 1000
        
        total_time = (time.perf_counter() - t0) * 1000
        
        return PipelineResult(
            query=query,
            answer=raw_answer,
            raw_answer=raw_answer,
            retrieved_chunks=chunks,
            passed_gate=True,
            confidence_score=1.0,
            is_refusal=False,
            latency_ms=total_time,
            retrieval_latency_ms=t_ret,
            generation_latency_ms=t_gen,
            eval_latency_ms=0.0,
            pipeline_name="BM25 RAG (Sparse, No Gate)",
        )
