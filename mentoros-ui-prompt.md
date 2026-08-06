# MentorOS — Frontend UI/UX Prompt

Use this prompt with a frontend generation tool (v0, Cursor, Bolt, Claude Code, etc.) or hand it to a designer/developer to build the MentorOS web interface.

---

## Prompt

Build a responsive, premium-feeling web app called **MentorOS** — an AI learning companion with a RAG pipeline (PDF upload + Q&A) running on a local Ollama LLM. The UI should resemble a Claude/ChatGPT-style layout, with three main regions: a **left history sidebar**, a **central chat area**, and a **right file panel**.

### 1. Overall Layout

Three-column layout:

```
[ Left Sidebar ]   [ Center: Chat Area ]   [ Right Panel: Uploaded Files ]
   ~260px               flexible                   ~300px
```

- Both side panels should be collapsible (hamburger/chevron toggle) for mobile and smaller screens.
- On load (default/home state), the center panel shows a **"New Chat"** empty state — not an existing conversation.
- Dark theme by default, premium SaaS aesthetic (see Section 5).

---

### 2. Left Sidebar — Chat History

- Fixed vertical panel on the left.
- Top: a **"+ New Chat"** button, prominent, pinned above the history list.
- Below it: a scrollable list of **past chat sessions**, each rendered as a **rounded rectangle card**, stacked vertically.

Each history card should show, **row-wise inside the card**:

| Element | Description |
|---|---|
| **Title** | Auto-generated chat/session title (e.g. "Operating Systems – Memory Mgmt") truncated with ellipsis if long |
| **Timestamp** | Small, muted text — "2h ago", "Yesterday", or date |
| **Confidence badge** | A pill/badge showing the student's confidence level for that session (e.g. "Confidence: 74%") with a color scale — red (low, <40%), amber (40–70%), green (>70%) |
| **Optional mini progress bar** | Thin horizontal bar under the title reflecting confidence % visually |

Card behavior:
- Hover: subtle highlight/glow, slight scale-up (magnetic hover effect).
- Active/selected chat: distinct highlighted background + left accent border.
- Right-click or hover-reveal: options (rename, delete, pin).
- Cards grouped by date sections ("Today", "Yesterday", "Previous 7 Days") like ChatGPT/Claude history.

---

### 3. Center — Chat / New Chat Area

**Default state (on page load):**
- Centered "New Chat" hero: MentorOS logo/wordmark, a short tagline (e.g. *"Upload your notes. Ask anything. Learn with evidence."*), and a large input box with a prompt placeholder like *"Ask a question about your uploaded documents..."*
- Below input: quick-suggestion chips (e.g. "Summarize this PDF", "Quiz me on Chapter 3", "Explain simply").

**Active chat state:**
- Standard chat thread: user messages right-aligned (or minimal bubble), AI responses left-aligned with the MentorOS avatar.
- Each AI response includes, stacked below the answer text:
  - **Confidence score** (numeric/pill)
  - **Evidence / retrieved chunks** (collapsible accordion showing source snippets with page/section references)
  - **AI Thinking Timeline** (collapsible step tracker: Planning → Searching → Ranking Evidence → Generating → Verifying → Ready)
  - **Quick action buttons**: "Explain Simpler," "Give Example," "Generate Quiz," "Ask Follow-up"
- Sticky input bar at the bottom of the chat with attach/upload icon, send button, and a small model/status indicator (e.g. "Ollama · Qwen2.5").

---

### 4. Right Panel — Uploaded Files

- Vertical panel on the right, visible by default alongside a new or active chat.
- Header: "Documents" with an **upload button** (drag-and-drop zone + file picker).
- List of uploaded files, each as a compact card showing:
  - File type icon (PDF/DOCX/PPT)
  - File name (truncated)
  - Upload date / size
  - Status indicator: "Indexed ✓", "Processing...", or "Failed"
  - Overflow menu: remove, re-index, view chunks
- Empty state when no files uploaded: icon + "No documents yet — upload a PDF to get started" + upload CTA.
- Optional: a small "X sections indexed" counter per file for transparency.

---

### 5. Visual & Interaction Style

- **Theme:** Premium dark mode — deep charcoal/near-black background (`#0B0B0F`–`#111114`), soft off-white text, one accent color (e.g. electric indigo or teal) used sparingly for CTAs, active states, and confidence-high badges.
- **Typography:** Large, confident headings for empty states; clean sans-serif (Inter/Geist) for body text.
- **Motion:** Smooth page/panel transitions, magnetic button hover, card hover elevation, skeleton loaders while retrieving/generating, subtle cursor-spotlight effect on the landing/new-chat state.
- **Glass accents:** Use sparingly — e.g. a subtle frosted-glass effect on the sticky input bar or modals, not overused across the whole UI.
- **Empty states:** Thoughtful illustrations/icons + one-line guidance text (for New Chat, no documents, no history yet).
- **Responsiveness:** On mobile, sidebar and file panel collapse into slide-over drawers accessible via icons in a top bar; chat becomes full-width.

---

### 6. Component List to Generate

1. `Sidebar` (New Chat button + grouped history list + ChatHistoryCard)
2. `ChatHistoryCard` (title, timestamp, confidence badge, mini progress bar)
3. `NewChatHero` (logo, tagline, input, suggestion chips)
4. `ChatThread` + `MessageBubble` (user/AI variants)
5. `AnswerPanel` (confidence, evidence accordion, thinking timeline, quick actions)
6. `FilePanel` (upload zone, file list, `FileCard`)
7. `TopBar` (mobile menu toggles, model status)
8. `InputBar` (sticky, attach icon, send button)

---

### 7. Tech Notes (optional, include if generating code)

- Framework: React + Tailwind CSS, Framer Motion for animations.
- State: chat history, active chat, uploaded files, and confidence scores should be modeled as separate stores/contexts so the sidebar and dashboard can reuse them later.
- Keep components modular so the Evaluation Agent's confidence score and the Learning Memory's weak-topic data can plug into `ChatHistoryCard` and `AnswerPanel` without UI rewrites.

