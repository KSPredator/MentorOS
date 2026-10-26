# MentorOS Knowledge Bundle Conventions (OKF v0.2)

This document establishes the bundle structure, naming schemes, trust lifecycle, and schema conventions for Open Knowledge Format (OKF v0.2) knowledge bundles in MentorOS.

---

## 1. Directory Structure

Each course manages its own isolated Git bundle repository under `bundle/<course_id>/`:

```text
bundle/<course_id>/
  index.md                 # Root catalog index (only file with frontmatter: okf_version: "0.2")
  log.md                   # Dated change log (newest entry first: ## YYYY-MM-DD)
  <topic_slug>.md          # Individual concept markdown pages
  references/              # Original raw course materials (PDF, PPTX, DOCX)
```

- **Reserved Filenames**: `index.md` and `log.md` are reserved files and must **never** be used as concept filenames.
- **Root `index.md`**: Only the root index contains YAML frontmatter (`okf_version: "0.2"`). Section or subfolder indexes are simple lists of Markdown links.

---

## 2. Frontmatter Schema & Concept Identity

Concept pages are Markdown files with valid YAML frontmatter.

### Concept ID & Filenames
- **File Name**: Slugs derived from the concept title (e.g. `operating-systems.md`).
- **Concept ID**: The bundle path without `.md` (e.g. `default/operating-systems`).

### Allowed Types
Per OKF v0.2, `type` is required and free-form. MentorOS uses:
- `Concept`: Curated pedagogical concept explanation.
- `Formula`: Mathematical or algorithmic formula with definitions.
- `Worked Example`: Step-by-step problem walkthrough.
- `Course Source`: Overview of source lectures or textbook chapters.

### Frontmatter Fields
```yaml
---
title: Operating Systems
type: Concept
description: Core principles of operating systems, kernel abstractions, and resource management.
tags:
  - os
  - kernel
  - concurrency
sources:
  - id: os-unit3-p41-c2
    title: OS Unit 3 (Page 41)
generated:
  by: mentoros_compiler/0.2.0
  at: "2026-10-16T12:00:00Z"
status: stable
stale_after: "2027-04-14"
verified:
  - by: process:mentoros-eval-agent
    at: "2026-10-16T12:05:00Z"
---
```

---

## 3. Footnote Citation Scheme
- Every claim or sentence grounded in course material ends with a footnote matching a chunk ID:
  ```markdown
  Virtual memory translates virtual addresses to physical frames [^os-unit3-p41-c2].
  ```
- **One source `id` per chunk**: Chunk IDs follow the scheme `<doc-slug>-p<page>-c<index>` (slides: `-s`, sections: `-sec`).
- The page number is placed in the source `title` because the OKF spec does not define page fragments in `id`.

---

## 4. Trust Lifecycle & Status

Trust tier is **derived**, never manually assigned or stored as a static field:
1. **`unverified`**:
   - `verified` field is absent or empty.
   - Status starts as `status: draft`.
2. **`machine-confirmed`**:
   - `verified` contains a non-human verifier (e.g. `process:mentoros-eval-agent`).
   - Automatically promoted to `status: stable` once deterministic sentence-level chunk evidence passes.
3. **`human-reviewed`**:
   - `verified` contains an actor prefixed with `human:` (e.g. `human:prof_smith`).
   - Highest confidence tier.

---

## 5. Maintenance & Staleness
- **Staleness**: If `now >= stale_after`, the hybrid retriever lowers the concept's weight.
- **Deprecation**: When a syllabus drops a topic, mark `status: deprecated` rather than deleting the file, preserving hyperlink integrity.
- **Git Commits**: Every compile run or verification creates a distinct Git commit in the bundle repository.
