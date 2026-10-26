"""
Evaluation Harness for MentorOS (Step 6 / Step 12).
Executes A/B/C configurations on versioned test sets:
  Config A: Current Baseline (raw RAG only, USE_OKF=False)
  Config B: Hybrid OKF + RAG with standard evaluation formula
  Config C: Hybrid OKF + RAG with trust-aware evaluation formula

Records results to eval_runs table in data/mentoros.db.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import uuid

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api import config
from db import get_db_session, EvalRunRepository
from embeddings.vector_store import VectorStore
from llm.hybrid_retriever import HybridRetriever
from agents.evaluation_agent import EvaluationAgent
from llm.ollama_client import OllamaClient


def load_test_set(path: Path) -> List[Dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


class EvaluationHarness:
    def __init__(self, course_id: str = "default", test_set_path: Optional[Path] = None):
        self.course_id = course_id
        self.test_set_path = test_set_path or (PROJECT_ROOT / "eval" / course_id / "v1.jsonl")
        self.ollama_client = OllamaClient()
        self.eval_agent = EvaluationAgent(ollama_client=self.ollama_client)

    def run_benchmark(self, config_choice: str = "A") -> Dict[str, Any]:
        """
        Execute benchmark for config A, B, or C.
        """
        assert config_choice in ("A", "B", "C"), f"Unknown config: {config_choice}"
        test_items = load_test_set(self.test_set_path)

        use_okf = config_choice in ("B", "C")
        use_trust_eval = (config_choice == "C")

        retriever = HybridRetriever(use_okf=use_okf)

        latencies = []
        correct_refusals = 0
        total_unanswerable = 0
        false_refusals = 0
        total_answerable = 0
        okf_hits = 0

        for item in test_items:
            q = item["question"]
            answerable = item.get("answerable", True)

            t0 = time.time()
            ret_res = retriever.retrieve(q, course_id=self.course_id)
            elapsed = time.time() - t0
            latencies.append(elapsed)

            if ret_res.path == "okf":
                okf_hits += 1

            # Simple answer synthesis simulation
            if not ret_res.chunks:
                is_refused = True
            else:
                top_text = ret_res.chunks[0].text[:300]
                eval_res = self.eval_agent.evaluate(
                    query=q,
                    answer=top_text,
                    retrieved_chunks=ret_res.chunks,
                    path="okf" if (use_trust_eval and ret_res.path == "okf") else "rag",
                    trust_tier=ret_res.trust_tier,
                )
                is_refused = not eval_res.passed_gate

            if not answerable:
                total_unanswerable += 1
                if is_refused:
                    correct_refusals += 1
            else:
                total_answerable += 1
                if is_refused:
                    false_refusals += 1

        total = len(test_items)
        latencies.sort()
        p50 = latencies[len(latencies) // 2] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        metrics = {
            "total_questions": total,
            "answerable_count": total_answerable,
            "unanswerable_count": total_unanswerable,
            "okf_path_share": round(okf_hits / total, 3) if total else 0.0,
            "refusal_accuracy": round(correct_refusals / total_unanswerable, 3) if total_unanswerable else 1.0,
            "false_refusal_rate": round(false_refusals / total_answerable, 3) if total_answerable else 0.0,
            "latency_p50_s": round(p50, 4),
            "latency_p95_s": round(p95, 4),
        }

        run_id = f"run_{config_choice}_{uuid.uuid4().hex[:8]}"
        with get_db_session() as session:
            repo = EvalRunRepository(session)
            repo.record_run(
                run_id=run_id,
                course_id=self.course_id,
                config=config_choice,
                test_set=str(self.test_set_path.relative_to(PROJECT_ROOT).as_posix()),
                metrics=metrics,
            )

        print(f"\n========================================================")
        print(f"Eval Run [{config_choice}] Completed: {run_id}")
        print(f"  OKF Path Share:    {metrics['okf_path_share'] * 100:.1f}%")
        print(f"  Refusal Accuracy:  {metrics['refusal_accuracy'] * 100:.1f}%")
        print(f"  False Refusal Rate: {metrics['false_refusal_rate'] * 100:.1f}%")
        print(f"  Latency P50:       {metrics['latency_p50_s']}s")
        print(f"========================================================\n")
        return metrics


def main():
    parser = argparse.ArgumentParser(description="MentorOS Evaluation Harness")
    parser.add_argument("--config", choices=["A", "B", "C"], default="A", help="Benchmark configuration")
    parser.add_argument("--course-id", default="default", help="Course ID")
    args = parser.parse_args()

    harness = EvaluationHarness(course_id=args.course_id)
    harness.run_benchmark(config_choice=args.config)


if __name__ == "__main__":
    main()
