# Adding OKF to the Existing MentorOS (Integration Roadmap)

You already have a complete system: ingestion, embeddings, vector store, RAG, Evaluation Agent, Planner, Memory, Podcast, API and UI. This roadmap adds OKF **without rewriting any of it**. I have not seen your code, so Step 0 is an audit you do first; where I name files or functions, they are placeholders for yours.

**OKF reminder (v0.2 spec):** a bundle is a folder of Markdown files with YAML frontmatter. Only `type` is required. Useful optional fields: `title`, `description`, `tags`, `sources` (with ids), `generated: {by, at}`, `verified: [{by, at}]`, `status` (draft / stable / deprecated), `stale_after`. Footnote labels must match `sources[].id`. `index.md` and `log.md` are reserved filenames. Trust tier is derived, never stored: no `verified` = unverified, non-human verifier = machine-confirmed, `human:<id>` verifier = human-reviewed.

---

## 1. Principles for adding it safely

1. **Additive only.** OKF is a new layer *in front of* your existing retrieval, not a replacement. Your RAG path stays untouched and remains the fallback.
2. **Feature flag.** `USE_OKF=false` must give you exactly today's behaviour. Every change below respects it.
3. **Same interfaces.** The OKF retriever returns the same result shape your pipeline already consumes, so the LLM call, Evaluation Agent, API and UI need little or no change at first.
4. **Shadow before switching.** Run OKF in the background on real questions and compare to RAG before any user sees it.
5. **Verify against raw chunks, always.** A compile mistake must never be "confirmed" by the page that contains it.
6. **Per-student data stays out of the bundle.** Memory and confidence history stay in your database. The bundle is shared course knowledge only.

---

## 2. Roadmap at a glance

| Step | What | Touches existing code? | Est. time* |
|---|---|---|---|
| 0 | Audit your current code | No | 0.5 day |
| 1 | Freeze baseline, build test set | No | 2 days |
| 2 | Stable chunk IDs and provenance | **Yes (ingestion, re-index)** | 1 to 2 days |
| 3 | Bundle skeleton and conventions | No | 1 day |
| 4 | `okf/` library: parse, write, check, index, log | No (new module) | 2 to 3 days |
| 5 | Compiler: chunks to concept pages | No (new module) | 4 to 6 days |
| 6 | Validation and trust fields | Small (Eval Agent gets a mode) | 2 days |
| 7 | OKF retriever and hybrid router | Small (one adapter) | 3 days |
| 8 | Shadow mode and comparison | Small (logging) | 2 days |
| 9 | Trust-aware Evaluation Agent | Small | 1 to 2 days |
| 10 | Planner, Memory, Podcast tweaks | Small | 2 days |
| 11 | API and UI additions | Medium | 3 to 5 days |
| 12 | A/B evaluation and decision gate | No | 3 days |
| 13 | Maintenance: new uploads, staleness, updates | Small | 2 days |

*Rough guesses for one person; I have not benchmarked anything on your hardware. Total is roughly 4 to 6 weeks. If you have plenty of time, do all of it in order.

---

## 3. Steps in detail

### Step 0: Audit your current code (before touching anything)

Answer these from your own repo and write the answers in a `INTEGRATION_NOTES.md`:

1. Does every chunk already have a stable ID, source file, and page or slide number? How is it stored (Chroma metadata, SQLite)?
2. What is the exact return shape of your `retrieve()` (fields, scores, order)?
3. What does the Evaluation Agent take as input and return (confidence, verdict, refusal)? Where does the refusal text live?
4. What routes does the Planner have, and how does it choose them?
5. How does Memory key topics today (free-text strings, chunk IDs, something else)?
6. What does the API return for an answer, and what does the UI render from it?
7. How is each course or book separated (collections, folders)?

If you paste these, or the key files, I can turn this into exact file-by-file edits.

### Step 1: Freeze the baseline and build a test set

1. `git tag baseline-pre-okf`. Record Python and library versions.
2. Write **40 to 60 test questions** per course: mostly answerable (with the page where the answer lives), about 20% not answerable from the books.
3. Run the current system on them and save: answer, retrieved chunks, confidence, refusal or not, latency. Score correctness and citation accuracy by hand for at least a sample.
4. These numbers are what OKF must beat. Keep the test set out of any compile prompts.

### Step 2: Stable chunk IDs and provenance

OKF footnotes point at source chunks, so chunks need permanent, readable IDs.

1. ID scheme: `<doc-slug>-p<page>-c<index>` (slides: `-s<slide>`). Example: `os-unit3-p41-c2`.
2. Store ID, document, page and chunk text in your vector store metadata and in a small SQLite table (`chunks`) so you can look any chunk up by ID without a vector query.
3. If your current chunks lack these, **re-ingest** into a *new* collection, leave the old one in place, and switch the flag only when the new one passes your baseline test set unchanged. (Re-chunking can alter retrieval quality, so check it.)
4. Keep original files in the bundle later under `references/`, so footnotes can point to them.

### Step 3: Bundle skeleton and conventions

One bundle per course, in its **own git repo** (OKF recommends git for history and diffs):

```
bundle/os-course/
  index.md                 # only place frontmatter is allowed: okf_version: "0.2"
  log.md                   # dated change log, newest first
  operating-systems/
    index.md
    paging.md
    segmentation.md
  references/
    os_unit3.pdf
```

Write a one-page `BUNDLE_CONVENTIONS.md`:
- `type` values you use (free-form per spec): `Concept`, `Formula`, `Worked Example`, `Course Source`.
- Compiler output starts as `status: draft`; it becomes `stable` only after validation passes.
- File names are slugs of the title; Concept ID is the path without `.md`.
- The spec has no page-number fragment, so put the page in the source `title` and use **one source `id` per chunk** (for example `os-unit3-p41-c2`).
- Do not use `index.md` or `log.md` as concept files.

### Step 4: Build the `okf/` library (pure code, no LLM)

A small module you can unit-test completely:

| Function | Job |
|---|---|
| `load_concept(path)` | parse frontmatter (PyYAML) and body; tolerate unknown keys |
| `write_concept(concept)` | write frontmatter and body; **preserve unknown keys** (spec requires) |
| `trust_tier(concept)` | derive unverified / machine-confirmed / human-reviewed from `verified` (a bare mapping counts as a one-element list) |
| `is_stale(concept, now)` | `now >= stale_after`; absent `status` means `stable` |
| `check_bundle(root)` | conformance: parseable frontmatter and non-empty `type` in every non-reserved `.md`; tolerate broken links and missing indexes |
| `extract_links(concept)` | markdown links to other concepts (absolute `/path.md` or relative) |
| `build_graph(root)` | links to edges (networkx) |
| `regen_index(dir)` | write `index.md` entries as `* [Title](path) - description` |
| `append_log(root, kind, text)` | add dated entry (`## YYYY-MM-DD`) newest first |

All timestamps ISO 8601 with explicit UTC offset. Actors: `<producer>/<version>`, `human:<id>`, `process:<id>`.

Sketch of the shape (untested, adapt to your code):

```python
@dataclass
class Concept:
    id: str                 # path without .md
    meta: dict              # frontmatter, unknown keys preserved
    body: str
```

### Step 5: Build the compiler (chunks to concept pages)

1. **Topic list.** Derive topics from headings first (cheap, deterministic); optionally ask the LLM to merge or rename. Start with the top 30 to 50 topics of one book, not everything.
2. **Gather evidence.** For each topic, take its section's chunks (or retrieve with your existing `retrieve()`), keeping their IDs.
3. **Page body.** Prompt the model:
   > Write the page body using ONLY the chunks below. End every sentence with a footnote label equal to a chunk ID. Leave out anything the chunks don't cover. Do not add outside knowledge.
4. **Frontmatter is built by code**, not the LLM: `type`, `title`, `description` (first line of the body or a short LLM summary), `tags` (heading path), `sources` (only the chunk IDs actually cited, with document and page in the title), `generated: {by: mentoros_compiler/<model>, at: <now>}`, `status: draft`, `stale_after` (for example end of semester).
5. **Deterministic checks before saving:** every footnote label exists in `sources`; every `sources` id was in the input; every number or formula in the body also appears in the cited chunks; nothing outside the allowed structure. Reject and retry (max 2) otherwise.
6. **Links.** Generate by code: find other concept titles in the body text and link them with absolute paths. Don't ask the LLM to invent links.
7. Keep prompts short. Your 6 GB card limits context in practice even if the model advertises a long window.
8. Run it as a background job after upload; show "compiling" status in the UI. Measure compile time per page and write it down.

### Step 6: Validation and trust fields

1. Add a **"verify page" mode** to your existing Evaluation Agent: for each sentence, check it against the chunk its footnote cites.
2. All sentences pass: set `verified: {by: process:mentoros-eval-agent, at: <now>}` and `status: stable`. Any fail: stay `draft`, append the reason to `log.md`.
3. Prefer a judge different from the generator where you can (a stricter prompt, a cross-encoder or NLI check, or a bigger model), so the same blind spot doesn't approve its own mistakes.
4. Read 20+ pages by hand yourself. Compile quality on your real books is the thing most likely to disappoint, so look early.
5. `git commit` the bundle after every compile run.

### Step 7: OKF retriever and hybrid router (the integration point)

Create one new function that returns **exactly the same shape as your current `retrieve()`**, plus a few optional fields:

```text
retrieve_hybrid(query):
  1. OKF lookup: search concept title + description + tags (BM25 and/or embeddings); small index, fast
  2. skip status=deprecated; mark stale (now >= stale_after) and prefer fresher / higher trust
  3. one-hop graph expansion over links (cap at 2 to 3 extra concepts)
  4. if best OKF score >= threshold: context = concept body + the raw chunks named in its sources
     else: fall back to your existing retrieve()
  5. return same result schema, plus: path ("okf"|"rag"), concept_ids, trust_tier
```

- Start the threshold around 0.5 and tune it on your test set. That number is a guess, not a recommendation.
- Log `path` for every question. You need it for the comparison.
- Behind `USE_OKF`. With the flag off, call your existing function directly.
- Include the raw cited chunks in the context, not just the concept page, so the Evaluation Agent can verify against them.

### Step 8: Shadow mode

For one to two weeks of your own use (or a replayed question set), run **both** paths on every question. Show the user only the RAG answer. Log both answers, which path OKF would take, scores, latency and confidence. Then compare offline. This tells you whether OKF helps before anyone depends on it.

### Step 9: Trust-aware Evaluation Agent

Keep the faithfulness check against raw chunks. Add trust to the confidence signal. A starting formula (hypothesis to tune, not a result):

`confidence = 0.5 × faithfulness + 0.3 × retrieval_score + 0.2 × trust_weight`

`trust_weight`: 0.3 unverified, 0.6 machine-confirmed, 1.0 human-reviewed. If you set a stale page's weight lower, record that choice in your docs. Keep your existing refusal path and threshold, and compare behaviour with the flag on and off.

### Step 10: Planner, Memory, Podcast (small changes)

- **Planner:** content questions default to the hybrid retriever; other routes unchanged.
- **Memory:** change the topic key to the **concept ID**. Migrate existing rows by matching old topic strings to concept titles (exact match first, then manual review of leftovers). Leave unmatched topics as free-text keys.
- **Podcast:** build the script from a concept page plus its linked pages when one exists, otherwise from chunks as today.
- **Reflection:** list concept titles with links in the summary.

### Step 11: API and UI additions

| Addition | Detail |
|---|---|
| Answer payload | add `path` (curated concept vs raw notes), `trust_tier`, `concept_ids`, and footnote-to-chunk mapping |
| `GET /bundle` | tree and index |
| `GET /concept/{id}` | page, trust tier, staleness |
| `POST /concept/{id}/verify` | adds `verified: {by: human:<id>, at}` and commits to git |
| `GET /graph` | nodes and edges for the Knowledge Map |
| UI | trust badge on answers; "curated" vs "raw notes" label; concept viewer with clickable footnotes (opens the source page); "Mark as correct" button; Knowledge Map coloured by the student's confidence from Memory |
| Timeline | add an "OKF lookup" stage to the thinking timeline |

Keep the old fields in the payload so the current UI keeps working during the rollout.

### Step 12: A/B evaluation and decision gate

Compare on the same held-out set:

| System | Description |
|---|---|
| A | Your current system (`baseline-pre-okf`) |
| B | Hybrid OKF + RAG, Evaluation Agent unchanged |
| C | Hybrid OKF + RAG with trust-aware Evaluation Agent |

Metrics: hallucination rate (manual check on a sample), citation precision, refusal accuracy on unanswerable questions (and false-refusal rate), latency, share of questions answered via OKF, validator pass rate, compile time per page.

Write your pass criteria **before** you look at results (for example: hallucination and citation precision clearly better, latency within about 20% of A, false refusals not up). With a small test set, small differences can be noise, so report the test-set size next to every number.

**If OKF doesn't win:** keep it flagged off, report the result honestly, and look at where it fails (bad pages, low coverage, wrong threshold). A measured negative result is still a valid outcome.

### Step 13: Maintenance

- **New upload:** ingest, then compile only the new or changed documents, validate, commit, `append_log`.
- **Changed book:** recompile affected pages, bump `generated.at`, clear old `verified` entries (the content changed), log it.
- **Staleness:** a nightly or on-start check flags pages past `stale_after`; the retriever deprioritises them and the UI shows a "re-check" hint.
- **Deprecation:** set `status: deprecated` instead of deleting, so links still resolve.
- **Conformance in CI:** run `check_bundle` as a test.
- **Git hygiene:** one commit per compile run or per human verification.

---

## 4. What changes in your existing code

| Component | Change | Size |
|---|---|---|
| Ingestion / chunking | stable chunk IDs, page metadata, `chunks` table | Medium (one-time re-index) |
| Vector store | none beyond metadata | Tiny |
| `retrieve()` | untouched; wrapped by `retrieve_hybrid()` | None |
| LLM call | none | None |
| Evaluation Agent | new "verify page" mode; trust-aware score | Small |
| Planner | default content route calls the hybrid retriever | Tiny |
| Memory | topic key becomes concept ID, plus migration | Small |
| Podcast | read concept pages first | Small |
| API | new endpoints and payload fields (old ones kept) | Medium |
| UI | badge, viewer, map, verify button | Medium |
| New | `okf/` library, compiler, bundle repo, shadow logging | Large (but isolated) |

---

## 5. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Compiler writes a wrong page and it gets trusted | footnote-per-sentence rule, deterministic checks, judge pass, manual review, `draft` until validated, raw-chunk verification at answer time |
| Re-chunking changes retrieval quality | new collection, compare on the baseline set before switching |
| Slower upload (compile step) | background job, only new or changed documents, top topics first; measure it |
| Low coverage (only compiled topics have pages) | RAG fallback always on |
| Spec is young; many blog posts still describe v0.1 | follow `okf/SPEC.md` itself (v0.2): `generated.at` replaces `timestamp`; `sources` replaces the body `# Citations` list |
| Exact details lost in compilation (numbers, formulas) | include raw cited chunks in answer context; deterministic number check at compile time |
| More moving parts | feature flag, shadow mode, versioned bundle in git, rollback below |

**Rollback:** set `USE_OKF=false`. Nothing else needs to change, because RAG, the old collection and the old API fields all still work.

---

## 6. If you want to ship a smaller version first (OKF-lite)

Do Steps 0 to 4, a heading-level compiler (no LLM topic extraction), Step 6 (validation), Step 7 (hybrid retriever), and Step 12. Skip the link graph, Knowledge Map, staleness and the verify button for now. You still get curated, cited, trust-labelled pages with a RAG fallback, and you can add the rest later because the bundle format doesn't change.

**Cut order** if time gets tight: Knowledge Map, verify button, staleness, graph expansion, Podcast tweak.

---

## 7. First-week checklist

- [ ] Tag `baseline-pre-okf` and save current results
- [ ] Write the test set (40 to 60 questions per course, about 20% unanswerable)
- [x] Fill in `INTEGRATION_NOTES.md` from the Step 0 questions
- [x] Add stable chunk IDs and the `chunks` table
- [ ] Create the bundle repo with `index.md` (`okf_version: "0.2"`) and `log.md`
- [ ] Build `okf/` parse, write and `check_bundle`, with tests
- [ ] Hand-write 3 concept pages from one real chapter, to confirm the format feels right before automating

---

## Sources

- OKF v0.2 specification: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
- OKF vs RAG explainer: https://geotoolbox.ai/blog/okf-vs-rag
