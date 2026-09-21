"""
MentorOS - Memory Module (Phase 6)
Handles student learning memory store and session reflection generation.

Exports:
  LearningMemoryStore  — persistent SQLite-backed per-topic confidence tracker
  TopicRecord          — dataclass representing one topic's learning state
  ReflectionGenerator  — LLM-powered session reflection generator
  ReflectionReport     — structured output of a reflection (learned_well, needs_revision, etc.)

Note: imports are lazy to avoid pulling in torch/embeddings at module load time.
Import directly from submodules when instantiating:
  from memory.memory_store import LearningMemoryStore, TopicRecord
  from memory.reflection_generator import ReflectionGenerator, ReflectionReport
"""


def __getattr__(name):
    """Lazy-load heavy submodules only when actually accessed."""
    if name in ("LearningMemoryStore", "TopicRecord"):
        from memory.memory_store import LearningMemoryStore, TopicRecord
        globals()["LearningMemoryStore"] = LearningMemoryStore
        globals()["TopicRecord"] = TopicRecord
        return globals()[name]
    if name in ("ReflectionGenerator", "ReflectionReport"):
        from memory.reflection_generator import ReflectionGenerator, ReflectionReport
        globals()["ReflectionGenerator"] = ReflectionGenerator
        globals()["ReflectionReport"] = ReflectionReport
        return globals()[name]
    raise AttributeError(f"module 'memory' has no attribute {name!r}")


__all__ = [
    "LearningMemoryStore",
    "TopicRecord",
    "ReflectionGenerator",
    "ReflectionReport",
]
