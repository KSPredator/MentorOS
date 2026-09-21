"""
Learning Memory Store for MentorOS (Phase 6).

Persists per-topic learning state across sessions using SQLite.
Each topic entry tracks:
  - confidence:        float 0.0–1.0  (how well the student knows this topic)
  - mistake_count:     int            (cumulative errors on this topic)
  - last_seen:         ISO timestamp  (when the topic was last interacted with)
  - interaction_count: int            (total interactions for this topic)

Public API:
  store = LearningMemoryStore(session_id)
  store.update(topic, eval_confidence=0.8)      -> TopicRecord
  store.update(topic, made_mistake=True)        -> TopicRecord
  store.update(topic, asked_simpler=True)       -> TopicRecord
  store.get(topic)                              -> TopicRecord | None
  store.get_all()                               -> list[TopicRecord]
  store.get_weak_topics(n)                      -> list[TopicRecord]
  store.get_strong_topics(n)                    -> list[TopicRecord]
  store.reset_session()                         -> None
  store.export_snapshot()                       -> dict
"""

import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("MentorOS.LearningMemoryStore")

# Default DB path — stored in the data/ directory at project root
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "learning_memory.db"


@dataclass
class TopicRecord:
    """Represents the stored learning state for a single topic."""
    topic: str
    session_id: str
    confidence: float           # 0.0 = no knowledge → 1.0 = mastered
    mistake_count: int
    interaction_count: int
    last_seen: str              # ISO 8601 UTC timestamp

    def confidence_pct(self) -> str:
        return f"{self.confidence * 100:.0f}%"

    def is_weak(self, threshold: float = 0.50) -> bool:
        return self.confidence < threshold

    def to_dict(self) -> dict:
        return asdict(self)

    def __repr__(self) -> str:
        return (
            f"TopicRecord(topic={self.topic!r}, confidence={self.confidence_pct()}, "
            f"mistakes={self.mistake_count}, interactions={self.interaction_count})"
        )


class LearningMemoryStore:
    """
    Persistent SQLite-backed store for student topic-level learning memory.

    One store instance is normally created per session (keyed by session_id),
    but the backing DB accumulates data across all sessions so the Reflection
    Generator can query long-term trends.
    """

    # Confidence adjustment constants
    _CORRECT_BOOST = 0.10       # Confidence nudge up on correct answer
    _MISTAKE_PENALTY = 0.15     # Confidence nudge down on blocked/wrong answer
    _FOLLOWUP_PENALTY = 0.08    # Confidence nudge down when student asks for simpler explanation
    _CONFIDENCE_MIN = 0.05
    _CONFIDENCE_MAX = 1.00
    _INITIAL_CONFIDENCE = 0.50  # Starting confidence when topic is first seen

    _CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS topic_memory (
        topic             TEXT    NOT NULL,
        session_id        TEXT    NOT NULL,
        confidence        REAL    NOT NULL DEFAULT 0.5,
        mistake_count     INTEGER NOT NULL DEFAULT 0,
        interaction_count INTEGER NOT NULL DEFAULT 0,
        last_seen         TEXT    NOT NULL,
        PRIMARY KEY (topic, session_id)
    );
    """

    def __init__(
        self,
        session_id: str = "default",
        db_path: Optional[Path] = None,
    ):
        self.session_id = session_id
        self.db_path = db_path or _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _init_db(self) -> None:
        """Create table if it doesn't exist."""
        with self._conn:
            self._conn.execute(self._CREATE_TABLE_SQL)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _clamp(self, value: float) -> float:
        return max(self._CONFIDENCE_MIN, min(self._CONFIDENCE_MAX, value))

    def _row_to_record(self, row: sqlite3.Row) -> TopicRecord:
        return TopicRecord(
            topic=row["topic"],
            session_id=row["session_id"],
            confidence=row["confidence"],
            mistake_count=row["mistake_count"],
            interaction_count=row["interaction_count"],
            last_seen=row["last_seen"],
        )

    # ------------------------------------------------------------------ #
    # Core write API                                                       #
    # ------------------------------------------------------------------ #

    def update(
        self,
        topic: str,
        *,
        eval_confidence: Optional[float] = None,
        made_mistake: bool = False,
        asked_simpler: bool = False,
    ) -> TopicRecord:
        """
        Record an interaction with a topic and adjust its stored confidence.

        Args:
            topic:           Topic label (normalised to lowercase).
            eval_confidence: Confidence score from EvaluationAgent (0.0–1.0).
                             If provided, the stored confidence blends 20% toward
                             this value each interaction.
            made_mistake:    True when EvaluationAgent blocked the answer (low
                             confidence / hallucination detected). Applies a penalty.
            asked_simpler:   True when the student asked for a simpler explanation,
                             signalling they didn't fully understand. Applies a
                             smaller penalty.

        Returns:
            Updated TopicRecord.
        """
        topic = topic.strip().lower()
        existing = self.get(topic)

        if existing:
            current_conf = existing.confidence
            mistakes = existing.mistake_count
            interactions = existing.interaction_count
        else:
            current_conf = self._INITIAL_CONFIDENCE
            mistakes = 0
            interactions = 0

        # Compute updated confidence
        if eval_confidence is not None:
            # Blend: move 20% of the gap toward the evaluation score
            delta = 0.20 * (eval_confidence - current_conf)
            new_conf = self._clamp(current_conf + delta)
        elif made_mistake or asked_simpler:
            penalty = self._MISTAKE_PENALTY if made_mistake else self._FOLLOWUP_PENALTY
            new_conf = self._clamp(current_conf - penalty)
        else:
            new_conf = self._clamp(current_conf + self._CORRECT_BOOST)

        if made_mistake:
            mistakes += 1
        interactions += 1

        now = self._now_iso()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO topic_memory
                    (topic, session_id, confidence, mistake_count, interaction_count, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic, session_id) DO UPDATE SET
                    confidence        = excluded.confidence,
                    mistake_count     = excluded.mistake_count,
                    interaction_count = excluded.interaction_count,
                    last_seen         = excluded.last_seen
                """,
                (topic, self.session_id, round(new_conf, 4), mistakes, interactions, now),
            )

        record = TopicRecord(
            topic=topic,
            session_id=self.session_id,
            confidence=round(new_conf, 4),
            mistake_count=mistakes,
            interaction_count=interactions,
            last_seen=now,
        )
        logger.info(
            f"Memory updated | Topic: '{topic}' | Confidence: {record.confidence_pct()} | "
            f"Mistakes: {mistakes} | Interactions: {interactions}"
        )
        return record

    # ------------------------------------------------------------------ #
    # Read API                                                             #
    # ------------------------------------------------------------------ #

    def get(self, topic: str) -> Optional[TopicRecord]:
        """Retrieve the record for a single topic in the current session."""
        topic = topic.strip().lower()
        row = self._conn.execute(
            "SELECT * FROM topic_memory WHERE topic=? AND session_id=?",
            (topic, self.session_id),
        ).fetchone()
        return self._row_to_record(row) if row else None

    def get_all(self) -> List[TopicRecord]:
        """Return all topic records for the current session, sorted by last_seen desc."""
        rows = self._conn.execute(
            "SELECT * FROM topic_memory WHERE session_id=? ORDER BY last_seen DESC",
            (self.session_id,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_weak_topics(self, n: int = 5, threshold: float = 0.60) -> List[TopicRecord]:
        """Return the n weakest topics (confidence < threshold), sorted ascending."""
        rows = self._conn.execute(
            """
            SELECT * FROM topic_memory
            WHERE session_id=? AND confidence < ?
            ORDER BY confidence ASC
            LIMIT ?
            """,
            (self.session_id, threshold, n),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_strong_topics(self, n: int = 5, threshold: float = 0.70) -> List[TopicRecord]:
        """Return the n strongest topics (confidence >= threshold), sorted descending."""
        rows = self._conn.execute(
            """
            SELECT * FROM topic_memory
            WHERE session_id=? AND confidence >= ?
            ORDER BY confidence DESC
            LIMIT ?
            """,
            (self.session_id, threshold, n),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_all_sessions(self) -> List[str]:
        """Return list of all unique session IDs stored in the DB."""
        rows = self._conn.execute(
            "SELECT DISTINCT session_id FROM topic_memory ORDER BY session_id"
        ).fetchall()
        return [r["session_id"] for r in rows]

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    def reset_session(self) -> None:
        """Delete all records for the current session."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM topic_memory WHERE session_id=?",
                (self.session_id,),
            )
        logger.info(f"Session memory cleared for session_id='{self.session_id}'")

    def export_snapshot(self) -> dict:
        """Return a JSON-serialisable snapshot of the current session's memory."""
        records = self.get_all()
        return {
            "session_id": self.session_id,
            "exported_at": self._now_iso(),
            "topic_count": len(records),
            "topics": [r.to_dict() for r in records],
            "weak_topics": [r.topic for r in self.get_weak_topics()],
            "strong_topics": [r.topic for r in self.get_strong_topics()],
        }

    def close(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()

    def __repr__(self) -> str:
        return f"LearningMemoryStore(session_id={self.session_id!r}, db={self.db_path})"
