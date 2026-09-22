"""
MentorOS Phase 11 -- End-to-End Integration Test Suite & Latency Profiling
========================================================================
Runs comprehensive integration tests across all system components:
  1. Document Ingestion & ChromaDB Vector Store Indexing
  2. Planner Agent Routing across all 5 actions (RETRIEVE, MEMORY, QUIZ, PODCAST, GENERAL)
  3. Grounded RAG Pipeline & Explainable AI Citations
  4. Deliberate Failure Path & Hallucination Gate Refusal
  5. Learning Memory Store Dynamic Updates & Weak Topic Tracking
  6. Reflection Generator Session Summary
  7. FastAPI REST & SSE Streaming Endpoints
  8. End-to-End Latency Benchmarking (Retrieval, LLM Generation, Evaluation Gate, Total)
"""

import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Force UTF-8 on Windows stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from agents.planner_agent import PlannerAgent, PlannerAction
from agents.evaluation_agent import EvaluationAgent
from api.main import app
from api.database import get_db
from embeddings import get_vector_store
from ingestion.parser import DocumentParser
from ingestion.chunker import chunk_document
from llm.ollama_client import OllamaClient
from llm.rag_pipeline import BaselineRAG
from memory.memory_store import LearningMemoryStore
from memory.reflection_generator import ReflectionGenerator


# -----------------------------------------------------------------------------
# Sample Test Document Content
# -----------------------------------------------------------------------------
SAMPLE_DOC_TEXT = """
# Computer Networks: Routing Protocols and Architectures

Page 1:
Routing algorithms are fundamental to packet-switched networks.
Dijkstra's Algorithm is a link-state algorithm that computes the least-cost path from one node to all other nodes in the network.
It maintains a set of nodes whose least cost path is definitively known, iteratively adding the node with the minimum distance.
Link-state routing protocols such as OSPF (Open Shortest Path First) broadcast link state advertisements to all routers in the autonomous system.

Page 2:
The Bellman-Ford algorithm is a distance-vector algorithm where each router maintains a table of distances to all destinations.
Routers periodically exchange their distance vectors with directly connected neighbors.
BGP (Border Gateway Protocol) is the standard Exterior Gateway Protocol used for inter-domain routing across the global Internet.
BGP uses path attributes such as AS-PATH to prevent routing loops and enforce policy routing.
"""


def log_test(step_num: int, title: str):
    print(f"\n{'='*70}")
    print(f" [TEST {step_num}] {title}")
    print(f"{'='*70}")


def test_1_document_ingestion_and_indexing():
    log_test(1, "Document Ingestion & ChromaDB Vector Store Indexing")
    
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_DOC_TEXT)
        tmp_path = Path(f.name)
    
    try:
        parser = DocumentParser()
        pages = parser.parse(tmp_path)
        assert len(pages) > 0, "Parser failed to parse text document"
        
        for p in pages:
            p.source_file = "computer_networks_lecture.txt"
        
        chunks = chunk_document(pages)
        assert len(chunks) > 0, "Chunker produced 0 chunks"
        
        vs = get_vector_store()
        indexed = vs.add_chunks(chunks)
        
        print(f"  [+] Parsed {len(pages)} page(s)")
        print(f"  [+] Generated {len(chunks)} chunk(s)")
        print(f"  [+] Indexed {indexed} chunk(s) in ChromaDB (Total in DB: {vs.count()})")
        assert indexed == len(chunks), f"Expected {len(chunks)} indexed, got {indexed}"
        assert vs.count() > 0, "VectorStore count must be greater than 0"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_2_planner_agent_routing():
    log_test(2, "Planner Agent Routing Across All Actions")
    
    ollama = OllamaClient()
    planner = PlannerAgent(ollama_client=ollama)
    
    test_cases = [
        ("Explain how Dijkstra algorithm works in OSPF", PlannerAction.RETRIEVE),
        ("Quiz me on distance vector routing and Bellman-Ford", PlannerAction.QUIZ),
        ("What are my weak topics from this study session?", PlannerAction.MEMORY),
        ("Make a podcast explainer about BGP and AS-PATH", PlannerAction.PODCAST),
        ("Hello! Who are you and how can you help me?", PlannerAction.GENERAL),
    ]
    
    for query, expected_action in test_cases:
        t0 = time.time()
        decision = planner.route(query)
        dt = time.time() - t0
        print(f"  Query: '{query}'")
        print(f"    -> Routed to: {decision.action.value} (method: {decision.route_method}, confidence: {decision.confidence:.2f}, time: {dt:.3f}s)")
        print(f"    -> Reasoning: {decision.reasoning}")
        assert decision.action == expected_action, f"Expected {expected_action.value}, got {decision.action.value}"


def test_3_grounded_rag_and_citations():
    log_test(3, "Grounded RAG Pipeline & Explainable Citations")
    
    rag = BaselineRAG()
    query = "What algorithm computes the least-cost path in link-state routing?"
    
    t0 = time.time()
    response = rag.answer_question(query=query, k=3)
    dt = time.time() - t0
    
    print(f"  Query: '{query}'")
    print(f"  Answer: {response.answer}")
    print(f"  Passed Gate: {response.passed_gate} | Confidence: {response.confidence_score:.2%}")
    print(f"  Latency: {response.latency_seconds:.3f}s (Total pipeline: {dt:.3f}s)")
    print(f"  Citations ({len(response.citations)}):")
    for c in response.citations:
        print(f"    - {c.source_file} (Page {c.page_number}) [score: {c.score:.3f}]")
    
    assert response.passed_gate is True, "Grounded answer should pass evaluation gate"
    assert response.is_refusal is False, "Grounded answer should not be refused"
    assert len(response.citations) > 0, "Response must include citations"
    assert "dijkstra" in response.answer.lower() or "least-cost" in response.answer.lower(), "Answer should mention Dijkstra or least-cost"


def test_4_deliberate_failure_path_hallucination_refusal():
    log_test(4, "Deliberate Failure Path & Hallucination Gate Refusal")
    
    eval_agent = EvaluationAgent()
    out_of_domain_query = "What are the exact ingredients and oven temperature for baking French macarons?"
    
    vs = get_vector_store()
    retrieved_chunks = vs.retrieve(out_of_domain_query, k=3)
    
    fake_hallucinated_answer = "To bake French macarons, you need 100g almond flour, 100g powdered sugar, egg whites, and bake at 300F for 15 minutes."
    
    t0 = time.time()
    eval_result = eval_agent.evaluate(
        query=out_of_domain_query,
        answer=fake_hallucinated_answer,
        retrieved_chunks=retrieved_chunks,
    )
    dt = time.time() - t0
    
    print(f"  Query: '{out_of_domain_query}'")
    print(f"  Hallucinated answer: '{fake_hallucinated_answer}'")
    print(f"  Gate Decision:")
    print(f"    - Passed Gate: {eval_result.passed_gate}")
    print(f"    - Combined Confidence: {eval_result.confidence_score:.2%}")
    print(f"    - Faithfulness Score: {eval_result.faithfulness_score:.2%}")
    print(f"    - Semantic Similarity: {eval_result.semantic_similarity:.2%}")
    print(f"    - Evaluation Reasoning: {eval_result.reasoning}")
    print(f"    - Filtered Output: '{eval_result.filtered_answer}'")
    print(f"    - Evaluation Time: {dt:.3f}s")
    
    assert eval_result.passed_gate is False, "Hallucinated answer must fail the evaluation gate"
    assert eval_result.filtered_answer == eval_agent.REFUSAL_MESSAGE, "Filtered answer must return safe refusal"


def test_5_learning_memory_dynamics():
    log_test(5, "Learning Memory Store Dynamic Updates")
    
    session_id = f"test_session_{int(time.time())}"
    store = LearningMemoryStore(session_id=session_id)
    
    try:
        # 1. Multiple positive interactions push confidence into strong range (>=70%)
        for _ in range(3):
            store.update(topic="Dijkstra Algorithm", eval_confidence=0.95, made_mistake=False)
            
        # 2. Low confidence topic with mistakes stays in weak range (<60%)
        store.update(topic="BGP Policy Routing", eval_confidence=0.20, made_mistake=True)
        store.update(topic="BGP Policy Routing", eval_confidence=0.20, made_mistake=True)
        
        snapshot = store.export_snapshot()
        print(f"  Session ID: {session_id}")
        print(f"  Total Topics Tracked: {snapshot['topic_count']}")
        print(f"  Strong Topics (>=70%): {snapshot['strong_topics']}")
        print(f"  Weak Topics (<60%): {snapshot['weak_topics']}")
        
        assert "dijkstra algorithm" in [t.lower() for t in snapshot['strong_topics']]
        assert "bgp policy routing" in [t.lower() for t in snapshot['weak_topics']]
        
        weak_records = store.get_weak_topics(n=5)
        assert len(weak_records) >= 1
        print(f"  Weak topic record: topic='{weak_records[0].topic}', confidence={weak_records[0].confidence:.2f}, mistakes={weak_records[0].mistake_count}")
    finally:
        store.reset_session()
        store.close()


def test_6_reflection_generator():
    log_test(6, "Reflection Generator Session Summary")
    
    session_id = f"test_session_refl_{int(time.time())}"
    store = LearningMemoryStore(session_id=session_id)
    
    try:
        for _ in range(3):
            store.update("Link State Routing", eval_confidence=0.95, made_mistake=False)
        store.update("Distance Vector Routing", eval_confidence=0.30, made_mistake=True)
        
        gen = ReflectionGenerator()
        t0 = time.time()
        report = gen.generate(memory_store=store, session_id=session_id)
        dt = time.time() - t0
        
        print(f"  Reflection Generated in {dt:.3f}s:")
        print(f"  Learned Well: {report.learned_well}")
        print(f"  Needs Revision: {report.needs_revision}")
        print(f"  Recommended Session: {report.recommended_session}")
        print(f"  Full Summary: {report.full_summary}")
        
        assert len(report.learned_well) > 0, "Learned well should have topics"
        assert len(report.needs_revision) > 0, "Needs revision should have topics"
        assert len(report.recommended_session) > 10, "Recommended session must not be empty"
    finally:
        store.reset_session()
        store.close()


def test_7_fastapi_rest_and_streaming_api():
    log_test(7, "FastAPI Endpoints Integration (REST & SSE Stream)")
    
    client = TestClient(app)
    
    # 1. GET /status
    res = client.get("/status")
    assert res.status_code == 200, f"/status failed: {res.text}"
    status_data = res.json()
    print(f"  [+] /status: status={status_data['status']}, indexed_chunks={status_data['indexed_chunks']}")
    
    # 2. POST /upload
    test_file_content = b"# Phase 11 Test Doc\n\nFastAPI and ChromaDB integration test."
    res = client.post(
        "/upload",
        files={"file": ("test_integration.txt", test_file_content, "text/plain")},
        data={"session_id": "api_test_session"},
    )
    assert res.status_code == 200, f"/upload failed: {res.text}"
    upload_data = res.json()
    print(f"  [+] /upload: indexed={upload_data['chunks_indexed']} chunks from {upload_data['filename']}")
    
    # 3. POST /ask (JSON)
    res = client.post(
        "/ask",
        json={
            "question": "What is Dijkstra algorithm used for?",
            "session_id": "api_test_session",
            "top_k": 3,
        }
    )
    assert res.status_code == 200, f"/ask failed: {res.text}"
    ask_data = res.json()
    print(f"  [+] /ask: planner={ask_data['planner']['action']}, confidence={ask_data['confidence_score']:.2f}, citations={len(ask_data['citations'])}")
    
    # 4. POST /ask/stream (SSE)
    res = client.post(
        "/ask/stream",
        json={
            "question": "Explain OSPF in one sentence",
            "session_id": "api_test_session",
            "top_k": 3,
        }
    )
    assert res.status_code == 200, f"/ask/stream failed: {res.text}"
    assert "text/event-stream" in res.headers["content-type"]
    
    events = []
    for line in res.text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except Exception:
                pass
    
    event_types = [e.get("type") for e in events]
    print(f"  [+] /ask/stream SSE: Received {len(events)} events, types={set(event_types)}")
    assert "planner" in event_types, "Stream missing planner event"
    assert "token" in event_types, "Stream missing token event"
    assert "done" in event_types, "Stream missing done event"
    
    done_evt = next(e for e in events if e.get("type") == "done")
    print(f"    -> Done event metadata: confidence={done_evt.get('confidence')}, citations={len(done_evt.get('citations', []))}, passed_gate={done_evt.get('passed_gate')}")
    
    # 5. GET /history
    res = client.get("/history?session_id=api_test_session")
    assert res.status_code == 200
    hist_data = res.json()
    print(f"  [+] /history: count={hist_data['count']} messages recorded in DB")
    assert hist_data['count'] >= 2
    
    # 6. GET /memory
    res = client.get("/memory?session_id=api_test_session")
    assert res.status_code == 200
    mem_data = res.json()
    print(f"  [+] /memory: topic_count={mem_data['topic_count']}")
    
    # 7. DELETE /history
    res = client.delete("/history?session_id=api_test_session")
    assert res.status_code == 200
    print(f"  [+] DELETE /history: cleared messages")


def test_8_latency_benchmarking():
    log_test(8, "System Latency Profiling on Local Hardware")
    
    ollama = OllamaClient()
    vs = get_vector_store()
    eval_agent = EvaluationAgent(ollama_client=ollama)
    rag = BaselineRAG(vector_store=vs, ollama_client=ollama, evaluation_agent=eval_agent)
    
    query = "Explain Dijkstra's algorithm and link-state routing"
    
    # 1. Retrieval Latency
    t0 = time.perf_counter()
    chunks = vs.retrieve(query, k=3)
    t_retrieve = (time.perf_counter() - t0) * 1000
    
    # 2. LLM Generation Latency
    context_text = "\n".join(c.text for c in chunks)
    prompt = f"Answer using context:\n{context_text}\n\nQuestion: {query}\nAnswer:"
    t0 = time.perf_counter()
    raw_answer = ollama.generate(prompt=prompt, temperature=0.2)
    t_llm = (time.perf_counter() - t0) * 1000
    
    # 3. Evaluation Gate Latency
    t0 = time.perf_counter()
    eval_result = eval_agent.evaluate(query=query, answer=raw_answer, retrieved_chunks=chunks)
    t_eval = (time.perf_counter() - t0) * 1000
    
    # 4. End-to-End Pipeline Latency
    t0 = time.perf_counter()
    rag_res = rag.answer_question(query=query, k=3)
    t_e2e = (time.perf_counter() - t0) * 1000
    
    print("\n  +-------------------------------------------------------------+")
    print("  |            MentorOS Latency Benchmark Summary               |")
    print("  +----------------------------------------+--------------------+")
    print(f"  | ChromaDB Dense Retrieval (top-3)       | {t_retrieve:8.2f} ms        |")
    print(f"  | Ollama Local LLM Generation            | {t_llm:8.2f} ms        |")
    print(f"  | Evaluation Agent (Hallucination Gate)  | {t_eval:8.2f} ms        |")
    print(f"  | Full End-to-End RAG Pipeline           | {t_e2e:8.2f} ms        |")
    print("  +----------------------------------------+--------------------+\n")
    print(f"  Evaluation Score: {eval_result.confidence_score:.2%} | Gate: {'PASSED' if eval_result.passed_gate else 'BLOCKED'}")


if __name__ == "__main__":
    print("=" * 70)
    print("       MentorOS Phase 11 -- Comprehensive Integration Test Suite")
    print("=" * 70)
    
    start_all = time.time()
    
    test_1_document_ingestion_and_indexing()
    test_2_planner_agent_routing()
    test_3_grounded_rag_and_citations()
    test_4_deliberate_failure_path_hallucination_refusal()
    test_5_learning_memory_dynamics()
    test_6_reflection_generator()
    test_7_fastapi_rest_and_streaming_api()
    test_8_latency_benchmarking()
    
    total_time = time.time() - start_all
    print("\n" + "=" * 70)
    print(f"  ALL PHASE 11 INTEGRATION TESTS PASSED SUCCESSFULLY! ({total_time:.2f}s)")
    print("=" * 70)
