"""
Phase 8 Comprehensive Benchmark Evaluation Runner
=================================================
Runs the 126 QA benchmark dataset across 3 comparative architectures:
  1. Full MentorOS (Dense Retrieval + Planner + Hallucination Gate)
  2. Naive RAG (Dense Retrieval + Direct LLM)
  3. BM25 RAG (BM25 Sparse Keyword Retrieval + Direct LLM)

Outputs:
  - data/eval_results.json (Full evaluation traces and metrics)
  - Formatted comparison tables for report inclusion
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.baselines import FullMentorOSPipeline, NaiveRAGPipeline, BM25RAGPipeline
from eval.metrics import compute_recall_at_k, compute_mrr, SemanticScoreEvaluator
from embeddings import get_vector_store
from llm.ollama_client import OllamaClient

EVAL_DATASET_PATH = PROJECT_ROOT / "data" / "eval_qa.json"
EVAL_RESULTS_PATH = PROJECT_ROOT / "data" / "eval_results.json"


def evaluate_pipeline(
    pipeline,
    dataset: List[Dict[str, Any]],
    semantic_eval: SemanticScoreEvaluator,
    k: int = 3,
) -> Dict[str, Any]:
    """Evaluate a pipeline across the entire benchmark dataset."""
    name = pipeline.__class__.__name__
    print(f"\nEvaluating: {name} (Total QA samples: {len(dataset)})...")
    
    sample_results = []
    
    recalls_1 = []
    recalls_3 = []
    recalls_5 = []
    mrrs = []
    semantic_scores = []
    latencies = []
    
    distractor_count = 0
    distractor_blocked = 0
    
    for i, item in enumerate(dataset, start=1):
        q = item["question"]
        gt = item["ground_truth"]
        is_ans = item.get("is_answerable", True)
        
        t0 = time.perf_counter()
        res = pipeline.run(query=q, k=k)
        dt = (time.perf_counter() - t0) * 1000
        
        # Retrieval metrics
        r1 = compute_recall_at_k(res.retrieved_chunks, gt, k=1) if is_ans else 0.0
        r3 = compute_recall_at_k(res.retrieved_chunks, gt, k=3) if is_ans else 0.0
        r5 = compute_recall_at_k(res.retrieved_chunks, gt, k=5) if is_ans else 0.0
        mrr = compute_mrr(res.retrieved_chunks, gt, max_k=5) if is_ans else 0.0
        
        # Generation metrics
        if is_ans:
            sem_sim = semantic_eval.score(res.answer, gt)
            recalls_1.append(r1)
            recalls_3.append(r3)
            recalls_5.append(r5)
            mrrs.append(mrr)
            semantic_scores.append(sem_sim)
        else:
            distractor_count += 1
            if res.is_refusal or "don't have enough information" in res.answer.lower() or not res.passed_gate:
                distractor_blocked += 1
            sem_sim = 1.0 if res.is_refusal else 0.0
            
        latencies.append(res.latency_ms)
        
        sample_record = {
            "id": item["id"],
            "chapter": item.get("chapter", "General"),
            "question": q,
            "ground_truth": gt,
            "is_answerable": is_ans,
            "generated_answer": res.answer,
            "passed_gate": res.passed_gate,
            "confidence_score": res.confidence_score,
            "is_refusal": res.is_refusal,
            "recall_at_1": r1,
            "recall_at_3": r3,
            "recall_at_5": r5,
            "mrr": mrr,
            "semantic_similarity": sem_sim,
            "latency_ms": res.latency_ms,
        }
        sample_results.append(sample_record)
        
        if i % 15 == 0 or i == len(dataset):
            print(f"  Processed {i}/{len(dataset)} items...")
            
    avg_r1 = (sum(recalls_1) / len(recalls_1)) if recalls_1 else 0.0
    avg_r3 = (sum(recalls_3) / len(recalls_3)) if recalls_3 else 0.0
    avg_r5 = (sum(recalls_5) / len(recalls_5)) if recalls_5 else 0.0
    avg_mrr = (sum(mrrs) / len(mrrs)) if mrrs else 0.0
    avg_sem = (sum(semantic_scores) / len(semantic_scores)) if semantic_scores else 0.0
    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    
    # Hallucination rate on unanswerable/distractor queries (lower is better)
    distractor_hallucination_rate = ((distractor_count - distractor_blocked) / distractor_count) if distractor_count > 0 else 0.0
    refusal_accuracy = (distractor_blocked / distractor_count) if distractor_count > 0 else 1.0
    
    summary = {
        "pipeline_name": getattr(pipeline, "name", name),
        "total_samples": len(dataset),
        "answerable_samples": len(recalls_1),
        "distractor_samples": distractor_count,
        "recall_at_1": round(avg_r1, 4),
        "recall_at_3": round(avg_r3, 4),
        "recall_at_5": round(avg_r5, 4),
        "mrr": round(avg_mrr, 4),
        "bertscore_similarity": round(avg_sem, 4),
        "hallucination_rate": round(distractor_hallucination_rate, 4),
        "refusal_accuracy": round(refusal_accuracy, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "samples": sample_results,
    }
    
    return summary


def get_stratified_dataset(dataset: List[Dict[str, Any]], samples_per_chapter: int = 2) -> List[Dict[str, Any]]:
    """Select a balanced subset of questions covering every chapter plus distractors."""
    chapters: Dict[str, List[Dict[str, Any]]] = {}
    distractors = []
    for item in dataset:
        if not item.get("is_answerable", True):
            distractors.append(item)
        else:
            ch = item.get("chapter", "General")
            chapters.setdefault(ch, []).append(item)
            
    stratified = []
    for ch, items in chapters.items():
        stratified.extend(items[:samples_per_chapter])
    stratified.extend(distractors[:3])
    return stratified


def run_full_evaluation(limit: int = None, stratified: bool = False, samples_per_chapter: int = 2):
    print("=" * 75)
    print("       MentorOS Phase 8 -- Full Benchmark Evaluation Suite")
    print("=" * 75)
    
    if not EVAL_DATASET_PATH.exists():
        print(f"Error: {EVAL_DATASET_PATH} not found. Running dataset builder...")
        from eval.dataset_builder import build_and_index_dataset
        build_and_index_dataset()
        
    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    if stratified:
        dataset = get_stratified_dataset(dataset, samples_per_chapter=samples_per_chapter)
        print(f"Running stratified benchmark: {len(dataset)} samples across all chapters + distractors.")
    elif limit and limit < len(dataset):
        dataset = dataset[:limit]
        print(f"Running on subset of {len(dataset)} samples for testing...")
    else:
        print(f"Loaded {len(dataset)} benchmark QA pairs.")
        
    ollama = OllamaClient()
    vs = get_vector_store()
    semantic_eval = SemanticScoreEvaluator()
    
    # Initialize pipelines
    p_full = FullMentorOSPipeline(ollama=ollama, vs=vs)
    p_full.name = "Full MentorOS (Dense + Gate)"
    
    p_naive = NaiveRAGPipeline(ollama=ollama, vs=vs)
    p_naive.name = "Naive RAG (Dense, No Gate)"
    
    p_bm25 = BM25RAGPipeline(ollama=ollama, vs=vs)
    p_bm25.name = "BM25 RAG (Sparse, No Gate)"
    
    # Execute evaluations
    results = {}
    
    results["full_mentoros"] = evaluate_pipeline(p_full, dataset, semantic_eval)
    results["naive_rag"] = evaluate_pipeline(p_naive, dataset, semantic_eval)
    results["bm25_rag"] = evaluate_pipeline(p_bm25, dataset, semantic_eval)
    
    # Save full JSON output
    with open(EVAL_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\nSaved detailed evaluation results to {EVAL_RESULTS_PATH}")
    
    # Print formatted markdown comparison table
    print("\n" + "=" * 75)
    print("           BENCHMARK RESULTS SUMMARY TABLE (Phase 8)")
    print("=" * 75)
    
    header = f"| {'Metric':<25} | {'Full MentorOS':<16} | {'Naive RAG':<16} | {'BM25 RAG':<16} |"
    divider = f"|{'-'*27}|{'-'*18}|{'-'*18}|{'-'*18}|"
    print(header)
    print(divider)
    
    metrics_to_show = [
        ("Recall@1", "recall_at_1", "{:.2%}"),
        ("Recall@3", "recall_at_3", "{:.2%}"),
        ("Recall@5", "recall_at_5", "{:.2%}"),
        ("MRR (Mean Reciprocal Rank)", "mrr", "{:.4f}"),
        ("BERTScore / Similarity", "bertscore_similarity", "{:.2%}"),
        ("Hallucination Rate (↓)", "hallucination_rate", "{:.2%}"),
        ("Refusal Accuracy (↑)", "refusal_accuracy", "{:.2%}"),
        ("Avg Latency (ms)", "avg_latency_ms", "{:.1f} ms"),
    ]
    
    for label, key, fmt in metrics_to_show:
        v_full = fmt.format(results["full_mentoros"][key])
        v_naive = fmt.format(results["naive_rag"][key])
        v_bm25 = fmt.format(results["bm25_rag"][key])
        print(f"| {label:<25} | {v_full:<16} | {v_naive:<16} | {v_bm25:<16} |")
        
    print(divider + "\n")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 8 Benchmark Evaluation Runner")
    parser.add_argument("--stratified", "-s", action="store_true", help="Run stratified benchmark across all chapters (recommended for quick run)")
    parser.add_argument("--samples-per-chapter", type=int, default=2, help="Number of samples per chapter when using --stratified (default: 2)")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Limit total number of questions to evaluate")
    args = parser.parse_args()
    
    run_full_evaluation(stratified=args.stratified, samples_per_chapter=args.samples_per_chapter, limit=args.limit)


if __name__ == "__main__":
    main()
