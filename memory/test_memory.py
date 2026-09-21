"""
CLI Test Script for Phase 6 (Learning Memory + Reflection Generator).

Tests:
  1. LearningMemoryStore — CRUD, update rules (boost/penalty), weak/strong queries
  2. ReflectionGenerator  — generates and displays session reflection (calls Ollama)

Usage:
    python memory/test_memory.py                  # full suite
    python memory/test_memory.py --skip-reflection # store tests only (no Ollama needed)
    python memory/test_memory.py --session mytest  # custom session ID
"""

import argparse
import sys
import tempfile
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory.memory_store import LearningMemoryStore, TopicRecord
from memory.reflection_generator import ReflectionGenerator


# --------------------------------------------------------------------------─ #
# Helpers                                                                       #
# --------------------------------------------------------------------------─ #

def _pass(label: str) -> None:
    print(f"  [PASS] {label}")


def _fail(label: str, e: Exception) -> None:
    print(f"  [FAIL] {label}: {e}")
    traceback.print_exc()


# --------------------------------------------------------------------------─ #
# Store tests (no Ollama required)                                              #
# --------------------------------------------------------------------------─ #

def run_store_tests(session_id: str) -> None:
    print("\n==============================================")
    print("  Phase 6 — LearningMemoryStore Tests")
    print("==============================================\n")

    # Use a temp DB so tests don't pollute the real one
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        store = LearningMemoryStore(session_id=session_id, db_path=db_path)

        passed = 0
        total = 0

        # -- Test 1: New topic starts at 0.50 ------------------------------
        total += 1
        try:
            record = store.update("gradient descent")
            assert abs(record.confidence - 0.60) < 0.01, \
                   f"Expected ~0.60 on first correct answer, got {record.confidence}"
            assert record.interaction_count == 1
            _pass("New topic confidence starts at 0.50 + CORRECT_BOOST => ~0.60")
            passed += 1
        except Exception as e:
            _fail("New topic first update", e)

        # -- Test 2: Mistake applies penalty ------------------------------─
        total += 1
        try:
            record = store.update("gradient descent", made_mistake=True)
            assert record.mistake_count == 1
            assert record.confidence < 0.60
            _pass(f"Mistake penalty applied — confidence dropped to {record.confidence_pct()}")
            passed += 1
        except Exception as e:
            _fail("Mistake penalty", e)

        # -- Test 3: asked_simpler applies smaller penalty ----------------─
        total += 1
        try:
            before = store.get("gradient descent").confidence
            record = store.update("gradient descent", asked_simpler=True)
            assert record.confidence < before
            _pass(f"asked_simpler penalty applied — confidence: {before:.2f} → {record.confidence:.2f}")
            passed += 1
        except Exception as e:
            _fail("asked_simpler penalty", e)

        # -- Test 4: eval_confidence blends toward score ------------------─
        total += 1
        try:
            before = store.get("gradient descent").confidence
            record = store.update("gradient descent", eval_confidence=0.90)
            assert record.confidence > before
            _pass(f"eval_confidence blend applied — confidence: {before:.2f} → {record.confidence:.2f}")
            passed += 1
        except Exception as e:
            _fail("eval_confidence blend", e)

        # -- Test 5: Multiple topics, get_all ------------------------------
        total += 1
        try:
            topics = [
                "binary search",
                "neural networks",
                "backpropagation",
                "overfitting",
                "regularisation",
            ]
            for t in topics:
                store.update(t)
            all_records = store.get_all()
            assert len(all_records) >= len(topics) + 1  # + gradient descent
            _pass(f"get_all() returned {len(all_records)} records")
            passed += 1
        except Exception as e:
            _fail("get_all()", e)

        # -- Test 6: Weak topics query ------------------------------------─
        total += 1
        try:
            # Force a topic to be weak
            for _ in range(5):
                store.update("binary search", made_mistake=True)
            weak = store.get_weak_topics()
            assert any(r.topic == "binary search" for r in weak), \
                f"'binary search' should be weak. Got: {[r.topic for r in weak]}"
            _pass(f"get_weak_topics() returned: {[r.topic for r in weak]}")
            passed += 1
        except Exception as e:
            _fail("get_weak_topics()", e)

        # -- Test 7: Strong topics query ----------------------------------─
        total += 1
        try:
            # Force a topic to be strong
            for _ in range(8):
                store.update("neural networks")
            strong = store.get_strong_topics()
            assert any(r.topic == "neural networks" for r in strong), \
                f"'neural networks' should be strong. Got: {[r.topic for r in strong]}"
            _pass(f"get_strong_topics() returned: {[r.topic for r in strong]}")
            passed += 1
        except Exception as e:
            _fail("get_strong_topics()", e)

        # -- Test 8: export_snapshot --------------------------------------─
        total += 1
        try:
            snap = store.export_snapshot()
            assert "session_id" in snap
            assert "topics" in snap
            assert "weak_topics" in snap
            assert "strong_topics" in snap
            _pass(f"export_snapshot() keys OK ({snap['topic_count']} topics)")
            passed += 1
        except Exception as e:
            _fail("export_snapshot()", e)

        # -- Test 9: Confidence clamped to [0.05, 1.0] --------------------─
        total += 1
        try:
            store.update("brand new topic")
            for _ in range(50):
                store.update("brand new topic", made_mistake=True)
            rec = store.get("brand new topic")
            assert rec.confidence >= 0.05, f"Confidence went below min: {rec.confidence}"
            for _ in range(50):
                store.update("brand new topic")
            rec = store.get("brand new topic")
            assert rec.confidence <= 1.00, f"Confidence exceeded max: {rec.confidence}"
            _pass(f"Confidence clamped correctly (min={0.05}, max={1.00})")
            passed += 1
        except Exception as e:
            _fail("Confidence clamping", e)

        # -- Test 10: reset_session ----------------------------------------─
        total += 1
        try:
            store.reset_session()
            remaining = store.get_all()
            assert len(remaining) == 0, f"Expected 0 records after reset, got {len(remaining)}"
            _pass("reset_session() cleared all session records")
            passed += 1
        except Exception as e:
            _fail("reset_session()", e)

        store.close()

    print(f"\n== Store Tests: {passed}/{total} passed ==\n")


# --------------------------------------------------------------------------─ #
# Reflection tests (Ollama required)                                            #
# --------------------------------------------------------------------------─ #

def run_reflection_test(session_id: str) -> None:
    print("\n==============================================")
    print("  Phase 6 — ReflectionGenerator Test")
    print("==============================================\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_reflection.db"
        store = LearningMemoryStore(session_id=session_id, db_path=db_path)

        # Populate realistic session data
        weak_topics = [("binary search", 4), ("dynamic programming", 6), ("graph traversal", 3)]
        strong_topics = [("neural networks", 8), ("backpropagation", 7), ("gradient descent", 6)]

        for topic, mistake_hits in weak_topics:
            store.update(topic)
            for _ in range(mistake_hits):
                store.update(topic, made_mistake=True)

        for topic, correct_hits in strong_topics:
            for _ in range(correct_hits):
                store.update(topic, eval_confidence=0.85)

        print("Generating session reflection (calling Ollama)...\n")

        try:
            gen = ReflectionGenerator()
            report = gen.generate(store, session_id=session_id)
            print(report.display())
            print(f"\n[PASS] ReflectionReport generated — {report.topic_count} topics, "
                  f"{report.weak_count} weak, {report.strong_count} strong\n")
        except Exception as e:
            print(f"[FAIL] Reflection generation failed: {e}\n")
            traceback.print_exc()

        store.close()


# --------------------------------------------------------------------------─ #
# Entry point                                                                   #
# --------------------------------------------------------------------------─ #

def main():
    parser = argparse.ArgumentParser(description="MentorOS Phase 6 Memory Test Runner")
    parser.add_argument("--skip-reflection", action="store_true",
                        help="Skip the Ollama-dependent reflection test")
    parser.add_argument("--session", type=str, default="test_session_phase6",
                        help="Session ID to use for tests")
    args = parser.parse_args()

    run_store_tests(args.session)

    if not args.skip_reflection:
        run_reflection_test(args.session)
    else:
        print("Skipping ReflectionGenerator test (--skip-reflection flag set).\n")


if __name__ == "__main__":
    main()
