"""
Reflection Generator for MentorOS (Phase 6).

At session end (or on-demand), generates a structured learning reflection
by feeding the session's topic confidence scores back into the local LLM.

Output format (ReflectionReport):
  - learned_well:      list of topics the student mastered this session
  - needs_revision:    list of weak topics that need more practice
  - recommended_session: a short paragraph the student can act on
  - full_summary:      the raw LLM reflection text
  - session_id:        the session this report covers
  - generated_at:      ISO timestamp

Public API:
  gen = ReflectionGenerator()
  report = gen.generate(memory_store)          -> ReflectionReport
  report = gen.generate(memory_store, session_id="s42")
  print(report.full_summary)
  report.to_dict()                              -> dict
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

# memory_store uses only stdlib — safe to import eagerly
from memory.memory_store import LearningMemoryStore, TopicRecord

if TYPE_CHECKING:
    from llm.ollama_client import OllamaClient

logger = logging.getLogger("MentorOS.ReflectionGenerator")


@dataclass
class ReflectionReport:
    """Structured session-end learning reflection."""
    session_id: str
    generated_at: str
    learned_well: List[str]          # Topics with high confidence
    needs_revision: List[str]        # Topics with low confidence
    recommended_session: str         # Short actionable next-steps paragraph
    full_summary: str                # Raw LLM reflection text
    topic_count: int = 0
    strong_count: int = 0
    weak_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def display(self) -> str:
        """Pretty-print the reflection for console output."""
        lines = [
            "=" * 60,
            f"📚  Session Reflection  |  {self.session_id}",
            "=" * 60,
            "",
            f"Topics covered: {self.topic_count}  |  "
            f"Strong: {self.strong_count}  |  Need revision: {self.weak_count}",
            "",
            "✅  Learned Well:",
        ]
        for t in self.learned_well:
            lines.append(f"   • {t}")
        lines += [
            "",
            "⚠️   Needs Revision:",
        ]
        for t in self.needs_revision:
            lines.append(f"   • {t}")
        lines += [
            "",
            "🎯  Recommended Next Session:",
            f"   {self.recommended_session}",
            "",
            "📝  Full Summary:",
            self.full_summary,
            "=" * 60,
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"ReflectionReport(session={self.session_id!r}, "
            f"strong={self.strong_count}, weak={self.weak_count})"
        )


class ReflectionGenerator:
    """
    Generates end-of-session learning reflections using the local LLM.

    Reads topic confidence data from a LearningMemoryStore and produces a
    structured ReflectionReport with actionable next-step recommendations.
    Falls back gracefully to a rule-based summary if Ollama is unavailable.
    """

    REFLECTION_SYSTEM_PROMPT = """You are MentorOS, an AI learning tutor generating a concise,
encouraging end-of-session reflection for a student.

You will be given a list of topics the student studied this session along with
confidence scores (0% = total beginner, 100% = fully mastered).

Your task is to produce a structured JSON response:
{
  "learned_well": ["<topic1>", "<topic2>", ...],
  "needs_revision": ["<topic1>", "<topic2>", ...],
  "recommended_session": "<one paragraph of actionable study advice>",
  "full_summary": "<2-3 sentence encouraging overall summary>"
}

Rules:
- learned_well:       topics with confidence >= 70%
- needs_revision:     topics with confidence < 60%
- recommended_session: specific, actionable. Mention the top 1-2 weak topics by name.
- full_summary:       warm, encouraging tone. Acknowledge progress and areas to improve.
- Respond with VALID JSON ONLY. No markdown fences. No extra keys."""

    def __init__(self, ollama_client: Optional["OllamaClient"] = None):
        if ollama_client is None:
            from llm.ollama_client import OllamaClient
            ollama_client = OllamaClient()
        self.ollama_client = ollama_client

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_topic_table(self, records: List[TopicRecord]) -> str:
        """Format topic records as a plain-text table for the LLM prompt."""
        if not records:
            return "No topics recorded this session."
        rows = ["Topic | Confidence | Mistakes | Interactions"]
        rows.append("-" * 50)
        for r in records:
            rows.append(
                f"{r.topic} | {r.confidence_pct()} | {r.mistake_count} | {r.interaction_count}"
            )
        return "\n".join(rows)

    def _fallback_report(
        self,
        session_id: str,
        records: List[TopicRecord],
        weak: List[TopicRecord],
        strong: List[TopicRecord],
    ) -> ReflectionReport:
        """Rule-based fallback if LLM call fails."""
        learned_well = [r.topic for r in strong]
        needs_revision = [r.topic for r in weak]

        if needs_revision:
            recommendation = (
                f"Focus your next session on: {', '.join(needs_revision[:3])}. "
                "Try re-reading the relevant document sections and then test yourself with a quiz."
            )
        elif learned_well:
            recommendation = (
                f"Great job mastering {', '.join(learned_well[:3])}! "
                "Try advancing to more complex questions on these topics."
            )
        else:
            recommendation = (
                "Continue exploring the uploaded material and try asking more specific questions."
            )

        summary = (
            f"You covered {len(records)} topic(s) this session. "
            f"{len(strong)} topic(s) are well understood and {len(weak)} need more practice. "
            "Keep it up!"
        )

        return ReflectionReport(
            session_id=session_id,
            generated_at=self._now_iso(),
            learned_well=learned_well,
            needs_revision=needs_revision,
            recommended_session=recommendation,
            full_summary=summary,
            topic_count=len(records),
            strong_count=len(strong),
            weak_count=len(weak),
        )

    def generate(
        self,
        memory_store: LearningMemoryStore,
        session_id: Optional[str] = None,
        temperature: float = 0.3,
    ) -> ReflectionReport:
        """
        Generate a ReflectionReport from the given LearningMemoryStore.

        Args:
            memory_store: The LearningMemoryStore to read topics from.
            session_id:   Override session label in the report (defaults to store's session_id).
            temperature:  LLM sampling temperature (slightly warmer for narrative text).

        Returns:
            ReflectionReport with learned_well, needs_revision, and recommendations.
        """
        sid = session_id or memory_store.session_id
        records = memory_store.get_all()
        weak = memory_store.get_weak_topics()
        strong = memory_store.get_strong_topics()

        if not records:
            logger.warning("No topics found in memory store — returning empty reflection.")
            return ReflectionReport(
                session_id=sid,
                generated_at=self._now_iso(),
                learned_well=[],
                needs_revision=[],
                recommended_session="No topics were studied this session. Try uploading some documents and asking questions!",
                full_summary="No study activity was recorded for this session.",
                topic_count=0,
                strong_count=0,
                weak_count=0,
            )

        topic_table = self._build_topic_table(records)
        prompt = f"""Session ID: {sid}
Topics studied this session:

{topic_table}

Generate the JSON reflection report for this student."""

        try:
            raw_response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=self.REFLECTION_SYSTEM_PROMPT,
                temperature=temperature,
            )

            # Extract JSON object from response
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))

                learned_well = data.get("learned_well", [t.topic for t in strong])
                needs_revision = data.get("needs_revision", [t.topic for t in weak])
                recommended_session = data.get(
                    "recommended_session",
                    "Review your weak topics and practice with quiz questions.",
                )
                full_summary = data.get("full_summary", raw_response[:500])

                report = ReflectionReport(
                    session_id=sid,
                    generated_at=self._now_iso(),
                    learned_well=learned_well,
                    needs_revision=needs_revision,
                    recommended_session=recommended_session,
                    full_summary=full_summary,
                    topic_count=len(records),
                    strong_count=len(strong),
                    weak_count=len(weak),
                )
                logger.info(
                    f"Reflection generated | Session: {sid} | "
                    f"Topics: {len(records)} | Strong: {len(strong)} | Weak: {len(weak)}"
                )
                return report

        except Exception as e:
            logger.warning(f"LLM reflection call failed: {e}. Using rule-based fallback.")

        return self._fallback_report(sid, records, weak, strong)
