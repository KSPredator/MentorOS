"""
CLI Test Script for Phase 4 (Planner Agent).
Verifies intent routing across RETRIEVE, MEMORY, QUIZ, PODCAST, and GENERAL queries.

Usage:
    python agents/test_planner.py
    python agents/test_planner.py --query "quiz me on machine learning"
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import PlannerAgent, PlannerAction


def main():
    parser = argparse.ArgumentParser(description="MentorOS Phase 4 Planner Agent Test Runner")
    parser.add_argument("--query", type=str, help="Specific query to test routing on")
    args = parser.parse_args()

    print("Initializing PlannerAgent ...")
    planner = PlannerAgent()

    if args.query:
        print(f"\nTesting Query: '{args.query}'")
        decision = planner.route(args.query)
        print(f"Result: [{decision.action.value}] (Method: {decision.route_method}, Confidence: {decision.confidence * 100:.0f}%)")
        print(f"Reasoning: {decision.reasoning}\n")
        return

    # Comprehensive test set covering all 5 intents
    test_cases = [
        # RETRIEVE (Content / Concept questions)
        ("What is engineering scientific software?", PlannerAction.RETRIEVE),
        ("Explain supervised learning vs unsupervised learning", PlannerAction.RETRIEVE),
        ("How does gradient descent work?", PlannerAction.RETRIEVE),

        # MEMORY (Learning memory / weakness tracking)
        ("What topics am I weak at?", PlannerAction.MEMORY),
        ("Show me my mistake history and progress", PlannerAction.MEMORY),
        ("What do I need to review for my exam?", PlannerAction.MEMORY),

        # QUIZ (Practice / self-assessment)
        ("Quiz me on chapter 1", PlannerAction.QUIZ),
        ("Give me 3 practice questions about neural networks", PlannerAction.QUIZ),
        ("Test my knowledge on Python data structures", PlannerAction.QUIZ),

        # PODCAST (Audio explainer format)
        ("Explain this topic as a podcast script", PlannerAction.PODCAST),
        ("Can I get an audio version with host and student?", PlannerAction.PODCAST),

        # GENERAL (Greetings / General dialogue)
        ("Hello, who are you?", PlannerAction.GENERAL),
        ("Thank you so much!", PlannerAction.GENERAL),
    ]

    print("\n========================================================")
    print("Running Automated Planner Routing Test Suite")
    print("========================================================\n")

    passed = 0
    total = len(test_cases)

    for query, expected_action in test_cases:
        decision = planner.route(query)
        is_match = decision.action == expected_action
        status = "PASSED" if is_match else "FAILED"
        if is_match:
            passed += 1

        print(f"[{status}] Query: \"{query}\"")
        print(f"         Expected: [{expected_action.value}] | Got: [{decision.action.value}] ({decision.route_method})")
        print(f"         Reason  : {decision.reasoning}\n")

    print("========================================================")
    print(f"Test Summary: {passed}/{total} routing test cases passed ({passed/total * 100:.0f}%)")
    print("========================================================\n")


if __name__ == "__main__":
    main()
