"""
SQLAlchemy declarative schema for MentorOS.
Postgres-compatible, SQLite-supported source of truth for:
  courses, documents, chunks, concepts, concept_sources, topic_aliases,
  compile_jobs, eval_runs, sessions, messages, files, topic_memory.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

metadata = MetaData()
Base = declarative_base(metadata=metadata)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Course(Base):
    __tablename__ = "courses"

    course_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    bundle_path = Column(String(512), nullable=False)
    embed_model = Column(String(128), nullable=False, default="all-MiniLM-L6-v2")
    created_at = Column(String(64), nullable=False, default=now_iso)

    documents = relationship("Document", back_populates="course", cascade="all, delete-orphan")
    concepts = relationship("Concept", back_populates="course", cascade="all, delete-orphan")
    topic_aliases = relationship("TopicAlias", back_populates="course", cascade="all, delete-orphan")
    compile_jobs = relationship("CompileJob", back_populates="course", cascade="all, delete-orphan")
    eval_runs = relationship("EvalRun", back_populates="course", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    doc_id = Column(String(128), primary_key=True)  # slug with collision suffix
    course_id = Column(String(64), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(128), nullable=False)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA-256 of file bytes
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="processing")  # processing | indexed | failed
    error = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False, default=now_iso)
    updated_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        UniqueConstraint("course_id", "slug", name="uq_documents_course_slug"),
        Index("idx_documents_course_status", "course_id", "status"),
    )

    course = relationship("Course", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    compile_jobs = relationship("CompileJob", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String(128), primary_key=True)  # <doc-slug>-p<page>-c<index> or -s / -sec
    doc_id = Column(String(128), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    doc_version = Column(Integer, nullable=False, default=1)
    unit = Column(String(16), nullable=False)  # page | slide | section
    unit_no = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_hash = Column(String(64), nullable=False)  # SHA-256 of chunk text
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    source_file = Column(String(255), nullable=False)
    legacy_id = Column(String(255), nullable=True)
    created_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        Index("idx_chunks_doc_version", "doc_id", "doc_version"),
        Index("idx_chunks_text_hash", "text_hash"),
        Index("idx_chunks_legacy_id", "legacy_id"),
        Index("idx_chunks_source_file", "source_file"),
    )

    document = relationship("Document", back_populates="chunks")
    concept_sources = relationship("ConceptSource", back_populates="chunk", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    concept_id = Column(String(255), primary_key=True)  # bundle relative path without .md
    course_id = Column(String(64), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft")  # draft | stable | deprecated
    trust_tier = Column(String(32), nullable=False, default="unverified")  # unverified | machine-confirmed | human-reviewed
    bundle_commit = Column(String(64), nullable=True)
    input_hash = Column(String(64), nullable=True)  # hash of input chunk hashes
    body = Column(Text, nullable=False)
    meta_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String(64), nullable=False, default=now_iso)
    updated_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        Index("idx_concepts_course_status", "course_id", "status"),
        Index("idx_concepts_trust_tier", "trust_tier"),
    )

    course = relationship("Course", back_populates="concepts")
    sources = relationship("ConceptSource", back_populates="concept", cascade="all, delete-orphan")
    topic_aliases = relationship("TopicAlias", back_populates="concept", cascade="all, delete-orphan")


class ConceptSource(Base):
    __tablename__ = "concept_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(String(255), ForeignKey("concepts.concept_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(String(128), ForeignKey("chunks.chunk_id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("concept_id", "chunk_id", name="uq_concept_sources"),
        Index("idx_concept_sources_chunk", "chunk_id"),
    )

    concept = relationship("Concept", back_populates="sources")
    chunk = relationship("Chunk", back_populates="concept_sources")


class TopicAlias(Base):
    __tablename__ = "topic_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String(255), nullable=False)  # lowercased text
    course_id = Column(String(64), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(255), ForeignKey("concepts.concept_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        UniqueConstraint("course_id", "alias", name="uq_topic_aliases"),
        Index("idx_topic_aliases_alias", "alias"),
    )

    course = relationship("Course", back_populates="topic_aliases")
    concept = relationship("Concept", back_populates="topic_aliases")


class CompileJob(Base):
    __tablename__ = "compile_jobs"

    job_id = Column(String(64), primary_key=True)
    doc_id = Column(String(128), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    doc_version = Column(Integer, nullable=False, default=1)
    course_id = Column(String(64), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    compiler_version = Column(String(64), nullable=False)
    prompt_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="queued")  # queued | running | completed | failed
    stage = Column(String(32), nullable=False, default="init")
    error = Column(Text, nullable=True)
    timings_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String(64), nullable=False, default=now_iso)
    updated_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        UniqueConstraint("doc_id", "doc_version", "compiler_version", "prompt_hash", name="uq_compile_jobs_key"),
        Index("idx_compile_jobs_status", "status"),
    )

    course = relationship("Course", back_populates="compile_jobs")
    document = relationship("Document", back_populates="compile_jobs")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    run_id = Column(String(64), primary_key=True)
    course_id = Column(String(64), ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    config = Column(String(16), nullable=False)  # 'A' | 'B' | 'C'
    test_set = Column(String(255), nullable=False)
    git_sha = Column(String(64), nullable=True)
    metrics_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        Index("idx_eval_runs_course_config", "course_id", "config"),
    )

    course = relationship("Course", back_populates="eval_runs")


class TopicMemory(Base):
    __tablename__ = "topic_memory"

    session_id = Column(String(128), primary_key=True)
    course_id = Column(String(64), primary_key=True, default="default")
    concept_id = Column(String(255), primary_key=True)  # concept ID or topic:<free text>
    confidence = Column(Float, nullable=False, default=0.50)
    mistake_count = Column(Integer, nullable=False, default=0)
    interaction_count = Column(Integer, nullable=False, default=0)
    last_seen = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        Index("idx_topic_memory_session_course", "session_id", "course_id"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(String(64), nullable=False, default=now_iso)
    updated_at = Column(String(64), nullable=False, default=now_iso)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    meta = Column(Text, nullable=False, default="{}")
    created_at = Column(String(64), nullable=False, default=now_iso)

    __table_args__ = (
        Index("idx_messages_session_id", "session_id", "id"),
    )


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, unique=True)
    ext = Column(String(16), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="processing")
    chunk_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    uploaded_at = Column(String(64), nullable=False, default=now_iso)
