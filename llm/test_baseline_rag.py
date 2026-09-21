"""
CLI Test Script for Phase 3 (Baseline RAG).
Runs end-to-end naive RAG loop (Retrieve -> Prompt -> Ollama -> Grounded Answer + Citation).

"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from embeddings import get_vector_store
from llm import BaselineRAG, OllamaClient


def run_rag_query(rag: BaselineRAG, query: str, k: int = 3):
    """Execute RAG query and format visual answer card with citations."""
    print(f"\n========================================================")
    print(f"QUESTION: {query}")
    print(f"========================================================")

    response = rag.answer_question(query, k=k)

    print(f"\n--- ANSWER ({response.model_name} | Latency: {response.latency_seconds}s) ---")
    print(response.answer)

    print("\n--- CITATIONS (Explainable AI) ---")
    if response.citations:
        for c in response.citations:
            print(f"  • {c.source_file} -> Page {c.page_number} (Relevance Score: {c.score * 100:.1f}%)")
    else:
        print("  (No citations - No relevant context found)")

    print("\n--- RETRIEVED CONTEXT SNIPPETS ---")
    for idx, chunk in enumerate(response.retrieved_chunks, start=1):
        snippet = chunk.text[:150].replace("\n", " ")
        print(f"  [{idx}] ({chunk.source_file} p.{chunk.page_number}): {snippet}...")

    print("========================================================\n")


def main():
    parser = argparse.ArgumentParser(description="MentorOS Phase 3 Baseline RAG Test Runner")
    parser.add_argument("--query", type=str, help="Question to ask the baseline RAG system")
    parser.add_argument("-k", type=int, default=3, help="Top-k chunks to retrieve (default: 3)")
    parser.add_argument("--interactive", action="store_true", help="Run interactive Q&A session")
    args = parser.parse_args()

    print("Initializing OllamaClient and VectorStore ...")
    client = OllamaClient()
    if not client.is_available():
        print("ERROR: Could not connect to local Ollama server at http://localhost:11434.")
        print("Please start Ollama in your terminal using `ollama serve` and try again.")
        sys.exit(1)

    print(f"  Connected to Ollama! Using model: {client.model_name}")

    vector_store = get_vector_store()
    print(f"  Vector store loaded. Total chunks in index: {vector_store.count()}")

    rag = BaselineRAG(vector_store=vector_store, ollama_client=client, top_k=args.k)

    if args.query:
        run_rag_query(rag, args.query, k=args.k)
    elif args.interactive:
        print("\n--- Baseline RAG Interactive Session --- (Type 'exit' to quit)")
        while True:
            try:
                q = input("\nAsk MentorOS: ").strip()
                if not q or q.lower() in {"exit", "quit"}:
                    break
                run_rag_query(rag, q, k=args.k)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        # Run 2 default test cases: 1 in-domain question, 1 out-of-domain refusal question
        print("\n--- Running Automated Baseline RAG Verification Tests ---")

        # Test Case 1: In-domain question
        q1 = "What is engineering scientific software?"
        run_rag_query(rag, q1, k=args.k)

        # Test Case 2: Out-of-domain question (verifies refusal)
        q2 = "What is quantum teleportation algorithm in python?"
        run_rag_query(rag, q2, k=args.k)


if __name__ == "__main__":
    main()
