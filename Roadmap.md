MentorOS — Full Build Roadmap (RTX 4050 / 6GB VRAM)
A practical, ordered path from empty repo to a working demo. Each phase builds on the last — don't skip ahead to the frontend before the RAG core actually answers questions correctly.

## Status (last updated: 2026-09-22)
- Phase 0–6: complete (environment, ingestion, embeddings, RAG baseline, planner, evaluation agent, learning memory + reflection).
- Phase 9–10: complete — FastAPI backend (`api/`) + React frontend (`frontend/`) fully wired (SSE streaming, quiz, memory, dashboard, file upload).
- Phase 7: not in scope — LoRA fine-tuning left as optional follow-up (no artifacts built).
- Phase 8: not in scope — evaluation framework left as optional follow-up (`eval/` reserved).
- Phase 11–12: not started yet — integration test + demo prep; podcast script generation only (no TTS).

---
Phase 0 — Environment Setup
Install Ollama (handles running the local LLM, no manual CUDA wrangling needed): download from ollama.com, then pull a quantized Gemma model:
```
   ollama pull gemma3:4b
   ```
This is Google's Gemma 3 4B, Q4_K_M quantized (~3.3GB) — comfortably fits your 6GB VRAM alongside the embedding model. Test it responds: `ollama run gemma3:4b "Explain binary search in one sentence"`
If you have headroom left after loading the embedding model and want stronger answer quality, `gemma3:12b` is worth trying too — it's a heavier pull and will use most of your VRAM on its own, so benchmark latency before committing to it for the full pipeline.
Python environment: Python 3.10+, create a venv, and install the core stack:
```
   pip install langchain langchain-community chromadb sentence-transformers pypdf python-docx python-pptx fastapi uvicorn
   ```
(You can swap LangChain for raw code later if you want more control — fine to use it for v1.)
Project structure (keep it modular from day one, since the report's architecture depends on this):
```
   mentoros/
     ingestion/       # PDF/DOCX/PPT parsing + chunking
     embeddings/      # embedding model wrapper + vector store
     agents/          # planner_agent.py, evaluation_agent.py
     memory/          # learning memory store + reflection generator
     llm/             # Ollama client wrapper
     eval/            # Recall@K, MRR, BERTScore, latency harness
     api/             # FastAPI backend
     frontend/        # React app (from the earlier UI prompt)
     data/uploads/     # user-uploaded docs
     data/eval_qa.json # your 150-200 held-out QA pairs
   ```
---
Phase 1 — Document Ingestion
Write parsers for PDF (`pypdf` or `pdfplumber`), DOCX (`python-docx`), PPTX (`python-pptx`) that extract raw text + page/slide numbers (you need these for citations later).
Chunk the text: 300–500 tokens per chunk with ~15% overlap is a reasonable default. Store chunk metadata (source file, page number, chunk index) alongside the text — this is what your Explainable AI panel will cite.
Test on 3–4 of your own real lecture PDFs before moving on. If parsing garbles tables or equations, note that as a known limitation now rather than discovering it during your demo.
---
Phase 2 — Embeddings + Vector Store
Use a small, fast sentence-transformer for embeddings — `all-MiniLM-L6-v2` (384-dim, matches the diagram in your report) is a good default and runs comfortably on CPU or your 4050.
Set up Chroma (simplest to run locally, no separate server needed) as your vector DB. Store: chunk text, embedding, source file, page number.
Write a `retrieve(query, k=5)` function: embed the query, cosine-similarity search, return top-k chunks with metadata.
Sanity check: manually ask a question you know the answer to from your test PDF, confirm the retrieved chunks are actually the relevant ones before building anything on top.
---
Phase 3 — Baseline RAG (get this working before anything fancy)
Write the simplest possible pipeline: `retrieve() → build prompt with context → call Ollama → return answer`.
Prompt template should force the model to answer only from the provided context and say so explicitly if it can't:
```
   Answer the question using ONLY the context below. If the context doesn't
   contain the answer, say "I don't have enough information in the uploaded
   documents to answer this."

   Context:
   {retrieved_chunks}

   Question: {user_question}
   ```
Get this loop working end-to-end (upload → ask → get grounded answer) before adding the planner or evaluation agent. This is your naive-RAG baseline for later comparison in your evaluation framework.
---
Phase 4 — Planner Agent
Start simple: a rule-based or lightweight-LLM-call router that decides, per incoming message, whether to:
retrieve from documents (default for content questions)
pull from Learning Memory (for "what am I weak at?" type questions)
trigger a quiz (for "quiz me" style requests)
You don't need a separate fine-tuned classifier for v1 — a short structured prompt to the same Ollama model asking it to output one of `{RETRIEVE, MEMORY, QUIZ}` works fine and is fast at this size.
Log the planner's routing decision somewhere visible (console or a debug panel) so you can verify it's actually routing correctly during testing.
---
Phase 5 — Evaluation Agent (the hallucination gate)
After the LLM generates an answer, score it against the retrieved chunks:
Cheap approach: compute embedding similarity between the generated answer and the retrieved context.
Better approach: a second LLM call asking Ollama to rate faithfulness ("Does this answer follow only from this context? Score 0-100 and explain") — slower but more accurate, and this is your reported "confidence score."
Set a threshold (start with 60%): below it, don't show the answer — show "I couldn't find enough evidence, please upload more material" as per your architecture diagram.
This is the component your report calls out as novel — make sure it's actually wired in before display, not computed after the fact for logging only.
---
Phase 6 — Learning Memory + Reflection
Simple schema per user/session: `{topic: str, confidence: float, last_seen: timestamp, mistake_count: int}`.
Update this after each Q&A: if the Evaluation Agent's confidence was low, or the user asked a follow-up "explain simpler," nudge that topic's confidence down.
At session end (or on request), generate a reflection summary: feed the session's topic list + confidence scores back into the LLM with a prompt like "Summarize what the student learned well and what needs revision, in this format: ..."
This is the piece that powers your dashboard's "weak topics" and "recommended session" — build it as a standalone module so the frontend can query it independently.
---
Phase 7 — LoRA Fine-Tuning (optional for v1, do this once the base pipeline works)
Where to run it: if you want to fine-tune `gemma3:12b`, use a free Google Colab T4 (16GB) session — locally on your 4050, stick to fine-tuning `gemma3:4b` (or even `gemma3:1b`) instead to stay safe on VRAM.
Prepare instruction data: pairs like `{"instruction": "Explain X simply", "input": "<retrieved context>", "output": "<ideal tutor-style answer>"}` — a few hundred to a couple thousand examples is enough for a LoRA adapter, not full fine-tuning scale.
Use `peft` + `bitsandbytes` for QLoRA:
```
   pip install peft bitsandbytes transformers accelerate
   ```
Export the LoRA adapter, merge it (or keep separate), convert to GGUF if needed, and load it into Ollama via a custom `Modelfile`.
Treat this as an enhancement, not a blocker — your baseline (non-fine-tuned) RAG pipeline should already work well before you invest time here.
---
Phase 8 — Evaluation Framework
Build your held-out set: 150–200 manually written QA pairs from your own uploaded documents (this satisfies the evaluation section of your report).
Implement the metrics your report promises:
Recall@k / MRR — did the retriever find the right chunk in the top-k?
BERTScore — semantic similarity between generated and reference answers.
Faithfulness/hallucination rate — % of "high confidence" answers actually supported by evidence (spot-check manually on a sample).
Latency — time from query to final answer.
Run this against: (a) your full pipeline, (b) naive RAG without planner/evaluation agent, (c) BM25 instead of dense retrieval — these are the baselines your report commits to.
---
Phase 9 — Backend API
Wrap everything in FastAPI: endpoints for `/upload`, `/ask`, `/history`, `/memory`, `/reflection`.
Keep the API stateless per-request where possible; store session/chat history and memory in a lightweight local DB (SQLite is plenty for a capstone project — no need for Postgres).
Stream responses if you want the "AI Thinking Timeline" UI effect to feel real — FastAPI supports server-sent events or WebSocket streaming from Ollama's streaming API.
---
Phase 10 — Frontend
Use the UI prompt from earlier in this conversation — feed it into your React setup (or a tool like Claude Code / v0 / Cursor) to scaffold the sidebar/chat/file-panel layout.
Wire it to your FastAPI backend: new chat → POST `/ask`, sidebar history → GET `/history`, file panel → POST `/upload` and GET status.
Build this last. A polished frontend on top of a broken RAG pipeline demos worse than a plain pipeline that actually answers correctly.
---
Phase 11 — Integration Testing & Demo Prep
Run your full evaluation suite (Phase 8) and record the numbers — you'll want these for your report and demo.
Test the failure paths deliberately: ask something not in the uploaded docs and confirm the Evaluation Agent correctly refuses instead of hallucinating. This is the single most convincing thing to show in a demo.
Time a few end-to-end queries on your actual 4050 to get real latency numbers for your report rather than estimates.
---
Phase 12 — Podcast Mode (Two-Voice Audio Explainer)
This is two separate building blocks: turning content into a two-person dialogue script, then turning that script into audio.
1. Script generation
   The Planner Agent detects podcast-mode intent ("explain this like a podcast," "walk me through chapter 3 in audio") and routes here instead of the normal answer path.
   Retrieve the same document chunks you'd use for a normal answer, then send them to Ollama with a prompt like:
```
  You are writing a 2-person educational podcast script explaining the
  following material to a curious student.

  Speakers:
  - HOST: an enthusiastic tutor who explains clearly, uses analogies
  - STUDENT: a curious learner who asks follow-up questions

  Use ONLY the material below as your source of truth. Do not introduce
  facts not present in it.

  Material:
  {retrieved_chunks}

  Write a natural back-and-forth dialogue, 8-14 exchanges. Format each
  line as:
  HOST: ...
  STUDENT: ...
  ```
Output is a plain HOST/STUDENT-tagged script — this becomes both the audio source and the synced transcript shown in the UI.
2. Two-voice text-to-speech (stay local, no paid API)
   Piper TTS — lightweight, fast on CPU, decent voice variety, easiest MVP option.
   Coqui XTTS-v2 — noticeably better quality, supports voice cloning from a short reference clip, needs ~3-4GB VRAM (fine on the 4050 since this runs after the LLM call finishes, not simultaneously with it).
   Start with Piper to get the feature working end-to-end, upgrade to XTTS-v2 later if you want it to sound more natural.
   Pipeline: assign HOST lines to Voice A and STUDENT lines to Voice B, generate each line as a separate clip, insert a 200–400ms silence between speaker turns, then stitch everything into one MP3/WAV with `pydub` or `ffmpeg`.
3. Frontend: podcast player
   Add a "🎧 Listen" action next to any answer or topic page.
   A simple audio player (HTML5 `<audio>` or a lightweight waveform component) with play/pause/seek.
   Show the transcript underneath; for the MVP just display the full script, and only add line-by-line highlighting later if you have time and the TTS engine exposes timing data.
4. How it fits your existing architecture
   New module: Podcast Agent, reusing your existing Retrieval step — no duplicate RAG logic. Flow becomes: retrieve → (new) generate dialogue script → (new) TTS → return audio + transcript, as an alternate branch alongside your normal retrieve → generate → evaluate path.
   Feasibility: an 8-14 exchange script (~400-600 words) takes a few seconds with Piper or up to ~30-60 seconds with XTTS-v2 on your hardware — show a loading state ("Recording your podcast...") rather than expecting instant playback.
---
Suggested Order of Priority (if time is short)
Phases 0–3 (ingestion → baseline RAG) — this must work.
Phase 5 (evaluation agent) — this is your core differentiator, don't cut it.
Phase 4 (planner) and Phase 6 (memory) — next priority.
Phase 9–10 (API + frontend) — needed for a demo, but simple versions are fine.
Phase 7 (LoRA fine-tuning) and Phase 8 (full evaluation framework) — do these if time allows; they strengthen the report but a working non-fine-tuned system with basic metrics is still a complete project.