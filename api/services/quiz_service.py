"""
Quiz service (Phase 4 QUIZ handler — real implementation).
Generates 3-5 MCQs grounded in retrieved document chunks.
Grading is deterministic: compares submitted indices to stored answer_idx.
"""

import json
import re
from typing import List, Optional

from api.services import pipeline

_SYSTEM = """You are a quiz generator for MentorOS, an AI tutor.
Create multiple-choice questions using ONLY the provided context.

Rules:
- 3 to 5 questions, ordered easy to hard.
- Each question has exactly 4 options; exactly one correct.
- "answer_idx" is the 0-based index of the correct option.
- "explanation" is 1-2 sentences citing the context idea (no page numbers needed).
- If context is irrelevant/insufficient, return {"questions": []}.

Respond with VALID JSON ONLY:
{"questions": [{"question": "...", "options": ["...","...","...","..."], "answer_idx": 0, "explanation": "..."}]}"""


def _parse_questions(raw: str) -> List[dict]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    questions = data.get("questions", [])
    clean = []
    for q in questions:
        try:
            options = [str(o) for o in q["options"]]
            if len(options) != 4:
                continue
            idx = int(q["answer_idx"])
            if idx < 0 or idx > 3:
                idx = 0
            clean.append(
                {
                    "question": str(q["question"]).strip(),
                    "options": options,
                    "answer_idx": idx,
                    "explanation": str(q.get("explanation", "")).strip(),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return clean[:5]


def generate(query: str, context_text: str) -> List[dict]:
    """Generate MCQs from retrieved context. Returns [] if impossible."""
    if not context_text.strip():
        return []
    client = pipeline.get_ollama()
    prompt = f"""Context:
{context_text}

Student asked: "{query}"

Generate the quiz JSON:"""
    raw = client.generate(prompt=prompt, system_prompt=_SYSTEM, temperature=0.3)
    return _parse_questions(raw)


def grade(quiz: List[dict], answers: List[int]) -> List[dict]:
    """Deterministic grading against stored answer_idx."""
    feedback = []
    for i, q in enumerate(quiz):
        submitted = answers[i] if i < len(answers) else -1
        correct_idx = int(q.get("answer_idx", -1))
        feedback.append(
            {
                "correct": submitted == correct_idx,
                "your_answer": submitted,
                "correct_idx": correct_idx,
                "explanation": q.get("explanation", ""),
            }
        )
    return feedback


def format_quiz_markdown(quiz: List[dict], score: Optional[int] = None) -> str:
    """Render graded results as markdown for the chat message."""
    lines = []
    if score is not None:
        total = len(quiz)
        pct = round(100 * score / total) if total else 0
        lines.append(f"## Quiz result: **{score}/{total}** ({pct}%)")
        lines.append("")
    for i, q in enumerate(quiz, start=1):
        fb = q.get("_feedback")
        if fb is not None:
            mark = "✅" if fb.get("correct") else "❌"
            lines.append(f"### {mark} Q{i}. {q['question']}")
        else:
            lines.append(f"### Q{i}. {q['question']}")
        for j, opt in enumerate(q["options"]):
            letter = "ABCD"[j] if j < 4 else "?"
            lines.append(f"- **{letter}.** {opt}")
        if fb is not None:
            if not fb.get("correct") and 0 <= fb.get("your_answer", -1) < 4:
                lines.append(f"  - Your answer: {'ABCD'[fb['your_answer']]}")
            lines.append(f"  - {fb.get('explanation', '')}")
        lines.append("")
    return "\n".join(lines).strip()
