"""
MentorOS Database Layer.
Schema, sessions, and repository classes.
"""

from db.schema import (
    Base,
    Course,
    Document,
    Chunk,
    Concept,
    ConceptSource,
    TopicAlias,
    CompileJob,
    EvalRun,
    TopicMemory,
    Session,
    Message,
    File,
    metadata,
    now_iso,
)
from db.session import get_engine, get_session_factory, get_db_session, ensure_default_course
from db.repositories import (
    CourseRepository,
    DocumentRepository,
    ChunkRepository,
    ConceptRepository,
    CompileJobRepository,
    EvalRunRepository,
    MemoryRepository,
)

__all__ = [
    "Base",
    "Course",
    "Document",
    "Chunk",
    "Concept",
    "ConceptSource",
    "TopicAlias",
    "CompileJob",
    "EvalRun",
    "TopicMemory",
    "Session",
    "Message",
    "File",
    "metadata",
    "now_iso",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "ensure_default_course",
    "CourseRepository",
    "DocumentRepository",
    "ChunkRepository",
    "ConceptRepository",
    "CompileJobRepository",
    "EvalRunRepository",
    "MemoryRepository",
]
