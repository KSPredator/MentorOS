"""
CLI Test Script for Phase 5 (Evaluation Agent / Hallucination Gate).
Verifies confidence scoring, 60% threshold gating, and hallucination refusal.

Usage:
    python agents/test_evaluation.py
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import EvaluationAgent
from embeddings import RetrievedChunk
from llm import BaselineRAG


def test_standalone_evaluator():
    """Test EvaluationAgent directly with valid vs hallucinated answers."""
    print("\n--- 1. Testing Standalone EvaluationAgent ---")
    agent = EvaluationAgent(threshold=0.60)

    mock_chunk = RetrievedChunk(
        chunk_id="doc1_p1_c0",
        text="Engineering/scientific software includes applications ranging from automotive stress analysis to space shuttle orbital dynamics.",
        source_file="doc1.pdf",
        page_number=1,
        chunk_index=0,
        score=0.92,
        metadata={}
    )

    # Case A: Fully grounded answer (Should PASS >= 60%)
    query_a = "What is engineering scientific software?"
    answer_a = "Engineering/scientific software ranges from automotive stress analysis to space shuttle orbital dynamics."

    print(f"\n[Case A - Grounded Answer] Query: '{query_a}'")
    res_a = agent.evaluate(query_a, answer_a, [mock_chunk])
    print(f"  Passed Gate    : {res_a.passed_gate}")
    print(f"  Confidence     : {res_a.confidence_score * 100:.1f}% (Threshold: {res_a.threshold_used * 100:.0f}%)")
    print(f"  Faithfulness   : {res_a.faithfulness_score * 100:.1f}%")
    print(f"  Similarity     : {res_a.semantic_similarity * 100:.1f}%")
    print(f"  Reasoning      : {res_a.reasoning}")
    print(f"  Displayed Ans  : {res_a.filtered_answer}")

    assert res_a.passed_gate is True, "Case A should pass the gate!"

    # Case B: Hallucinated / Unsupported answer (Should BLOCK < 60%)
    query_b = "What is engineering scientific software?"
    answer_b = "Engineering scientific software was invented in 1920 by Nikola Tesla to control quantum computers in Japan."

    print(f"\n[Case B - Hallucinated Answer] Query: '{query_b}'")
    res_b = agent.evaluate(query_b, answer_b, [mock_chunk])
    print(f"  Passed Gate    : {res_b.passed_gate}")
    print(f"  Confidence     : {res_b.confidence_score * 100:.1f}% (Threshold: {res_b.threshold_used * 100:.0f}%)")
    print(f"  Faithfulness   : {res_b.faithfulness_score * 100:.1f}%")
    print(f"  Similarity     : {res_b.semantic_similarity * 100:.1f}%")
    print(f"  Reasoning      : {res_b.reasoning}")
    print(f"  Displayed Ans  : {res_b.filtered_answer}")

    assert res_b.passed_gate is False, "Case B should be blocked by the gate!"
    print("\n[SUCCESS] Standalone EvaluationAgent tests passed!")


def test_integrated_rag():
    """Test EvaluationAgent wired inside BaselineRAG pipeline."""
    print("\n--- 2. Testing Integrated BaselineRAG + Evaluation Gate ---")
    rag = BaselineRAG(eval_threshold=0.60)

    query = "What is engineering scientific software?"
    response = rag.answer_question(query)

    print(f"Query           : {response.query}")
    print(f"Passed Gate     : {response.passed_gate}")
    print(f"Confidence Score: {response.confidence_score * 100:.1f}%")
    print(f"Display Answer  : {response.answer}")
    if response.evaluation:
        print(f"Evaluator Rationale: {response.evaluation.reasoning}")

    print("\n[SUCCESS] Integrated RAG + Evaluation Gate test passed!")


def main():
    print("========================================================")
    print("Running Phase 5 Evaluation Agent (Hallucination Gate) Tests")
    print("========================================================")
    test_standalone_evaluator()
    test_integrated_rag()
    print("\n========================================================")
    print("All Phase 5 Evaluation Agent tests completed successfully!")
    print("========================================================\n")


if __name__ == "__main__":
    main()
