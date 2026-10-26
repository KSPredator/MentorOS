"""
Database engine and session management for MentorOS.
Provides thread-safe SQLAlchemy sessions for repositories.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api import config
from db.schema import Base, Course, now_iso

_engine = None
_SessionFactory = None


def get_engine(db_path: Optional[Path] = None):
    global _engine
    if _engine is None or db_path is not None:
        path = db_path or config.DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite with foreign key enforcement and check_same_thread=False
        connect_args = {"check_same_thread": False} if "sqlite" in str(path) else {}
        url = f"sqlite:///{path.resolve().as_posix()}"
        engine = create_engine(url, connect_args=connect_args)
        if db_path is None:
            _engine = engine
        return engine
    return _engine


def get_session_factory(db_path: Optional[Path] = None) -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None or db_path is not None:
        engine = get_engine(db_path)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        if db_path is None:
            _SessionFactory = factory
        return factory
    return _SessionFactory


@contextmanager
def get_db_session(db_path: Optional[Path] = None) -> Generator[Session, None, None]:
    """Context manager for transactional database sessions."""
    factory = get_session_factory(db_path)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_default_course(session: Session) -> Course:
    """Ensure the standard default course exists in the database."""
    default_course = session.get(Course, "default")
    if not default_course:
        default_course = Course(
            course_id="default",
            name="Default Course",
            bundle_path="bundle/default",
            embed_model="all-MiniLM-L6-v2",
            created_at=now_iso(),
        )
        session.add(default_course)
        session.flush()
    return default_course
