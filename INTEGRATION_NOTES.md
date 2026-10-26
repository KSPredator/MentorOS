# MentorOS — OKF Integration Audit (Step 0)

Audit conducted against the existing MentorOS repository codebase in accordance with Step 0 of `mentoros-okf-integration-roadmap.md`.

---

### 1. Does every chunk already have a stable ID, source file, and page or slide number? How is it stored (Chroma metadata, SQLite)?

* **Current ID Scheme:**
  Chunks are created in `ingestion/chunker.py` using the pattern:
  `{source_file}_p{page_number}_c{chunk_index}`
  where `source_file` is the raw filename (e.g., `OS_unit3.pdf`).
* **Page vs Slide:**
  `ingestion/parser.py` extracts `page_number` (1-indexed) for PDF, DOCX (400-word estimated pages), TXT/MD, and slide index for PPTX. However, `chunker.py` currently prefixes all with `_p` regardless of whether the document is a presentation.
* **Storage Location:**
  Chunks are stored **only in ChromaDB** (`embeddings/vector_store.py`) under the collection `mentoros_collection`. Chroma metadata stores:
  `{"source_file": str, "page_number": int, "chunk_index": int, "token_count": int}`.
  There is currently **no SQLite table** for raw chunks. Chunks can currently only be retrieved via Chroma query or Chroma ID get.

---

### 2. What is the exact return shape of your `retrieve()` (fields, scores, order)?

* **Function Signature:** `VectorStore.retrieve(query: str, k: int = 5) -> List[RetrievedChunk]` in `embeddings/vector_store.py`.
* **Return Type:** `RetrievedChunk` dataclass with fields:
  * `chunk_id: str`
  * `text: str`
  * `source_file: str`
  * `page_number: int`
  * `chunk_index: int`
  * `score: float` — Cosine similarity converted from Chroma cosine distance (`round(max(0.0, min(1.0, 1.0 - dist)), 4)`).
  * `metadata: dict` (contains `source_file`, `page_number`, `chunk_index`, `token_count`).
* **Ordering:** Sorted strictly descending by similarity `score` (`retrieved.sort(key=lambda x: x.score, reverse=True)`).

---

### 3. What does the Evaluation Agent take as input and return (confidence, verdict, refusal)? Where does the refusal text live?

* **Inputs:** `EvaluationAgent.evaluate(query: str, answer: str, retrieved_chunks: List[RetrievedChunk], threshold: Optional[float] = None) -> EvaluationResult` in `agents/evaluation_agent.py`.
* **Output:** `EvaluationResult` dataclass with fields:
  * `passed_gate: bool` (whether `confidence_score >= threshold_used`)
  * `confidence_score: float` (blended: `round(0.70 * faithfulness_score + 0.30 * semantic_similarity, 4)`)
  * `faithfulness_score: float` (Ollama LLM judge score normalized 0.0–1.0)
  * `semantic_similarity: float` (cosine similarity between answer embedding and top chunk embedding)
  * `reasoning: str` (judge explanation for Explainable AI)
  * `filtered_answer: str` (the original answer if passed, or `REFUSAL_MESSAGE` if blocked)
  * `original_answer: str` (raw unblocked LLM response)
  * `threshold_used: float` (default `0.60`)
* **Refusal Text Location:**
  Class constant `EvaluationAgent.REFUSAL_MESSAGE`:
  `"I couldn't find enough evidence in the uploaded documents to answer this safely. Please upload more material on this topic."`

---

### 4. What routes does the Planner have, and how does it choose them?

* **Routes:** Enum `PlannerAction` in `agents/planner_agent.py`:
  * `RETRIEVE` — Content / concept questions needing RAG vector retrieval.
  * `MEMORY` — Student mastery, weak topics, or learning history questions.
  * `QUIZ` — Practice quiz / self-assessment requests.
  * `PODCAST` — Audio / podcast script explainer requests.
  * `GENERAL` — Greetings or conversational queries.
* **Routing Mechanism:**
  1. **Rule-based fast-path (0ms):** Regex matching over `MEMORY_PATTERNS`, `QUIZ_PATTERNS`, `PODCAST_PATTERNS`, and `GENERAL_PATTERNS`.
  2. **LLM classifier fallback:** Ollama prompt with `SYSTEM_PROMPT` returning JSON `{"action": ..., "confidence": ..., "reasoning": ...}` with `temperature=0.0`.
  3. **Default fallback:** Routes to `RETRIEVE` with confidence `0.70` if ambiguous or on error.

---

### 5. How does Memory key topics today (free-text strings, chunk IDs, something else)?

* **Keying Strategy:** Free-text strings (lowercased) representing concept/topic names (e.g. `"virtual memory"`, `"paging"`).
* **Storage Location:** SQLite database at `data/learning_memory.db` (`memory/memory_store.py`) in table:
  `topic_memory(topic TEXT, session_id TEXT, confidence REAL, mistake_count INTEGER, interaction_count INTEGER, last_seen TEXT, PRIMARY KEY (topic, session_id))`.

---

### 6. What does the API return for an answer, and what does the UI render from it?

* **API Response Model:** `AskResponse` in `api/models.py`:
  * `session_id: str`
  * `user_message_id: int`
  * `assistant_message_id: int`
  * `action: str`
  * `route_method: str`
  * `route_confidence: float`
  * `type: str` (`"answer"` | `"refusal"` | `"quiz"` | `"memory"` | `"podcast"` | `"general"`)
  * `content: str`
  * `citations: List[CitationOut]` (`source_file`, `page_number`, `chunk_id`, `score`)
  * `retrieved: List[RetrievedOut]` (`chunk_id`, `source_file`, `page_number`, `score`, `text_preview`)
  * `evaluation: Optional[EvaluationOut]` (`passed_gate`, `confidence_score`, `faithfulness_score`, `semantic_similarity`, `reasoning`, `threshold_used`)
  * `latency_seconds: float`
  * `model_name: str`
  * `memory_updates: List[MemoryUpdateOut]`
  * `quiz: Optional[List[QuizQuestionOut]]`
  * `podcast_script: Optional[List[PodcastLineOut]]`
  * `podcast_audio_url: Optional[str]`
  * `is_refusal: bool`
* **UI Rendering (`frontend/src/components/chat/`):**
  * `AssistantMessage.jsx`: Markdown response body, action route badge, confidence badge.
  * `CitationList.jsx`: Interactive citation badges with source filename, page/slide number, and similarity score.
  * `EvaluationBadge.jsx`: Color-coded confidence gate pill with expandable drawer showing LLM judge faithfulness score, semantic similarity, and reason.
  * `RefusalCard.jsx`: Warning banner for hallucination refusal.
  * `QuizCard.jsx`, `MemoryCard.jsx`, `PodcastCard.jsx`: Specialized interactive widgets based on message `type`.

---

### 7. How is each course or book separated (collections, folders)?

* Currently, **all uploaded documents reside in a single flat directory** (`data/uploads/`) and **single ChromaDB collection** (`mentoros_collection`).
* Metadata field `source_file` in ChromaDB and the SQLite `files` table in `data/mentoros.db` identify distinct documents.
* There is currently no multi-collection or per-course isolation in the storage layer.
