"""
Course repository for MentorOS.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import Course, now_iso


class CourseRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, course_id: str) -> Optional[Course]:
        return self.session.get(Course, course_id)

    def list_all(self) -> List[Course]:
        stmt = select(Course).order_by(Course.course_id.asc())
        return list(self.session.scalars(stmt).all())

    def upsert(
        self,
        course_id: str,
        name: str,
        bundle_path: str,
        embed_model: str = "all-MiniLM-L6-v2",
    ) -> Course:
        course = self.get(course_id)
        if course:
            course.name = name
            course.bundle_path = bundle_path
            course.embed_model = embed_model
        else:
            course = Course(
                course_id=course_id,
                name=name,
                bundle_path=bundle_path,
                embed_model=embed_model,
                created_at=now_iso(),
            )
            self.session.add(course)
        self.session.flush()
        return course

    def delete(self, course_id: str) -> bool:
        course = self.get(course_id)
        if course:
            self.session.delete(course)
            self.session.flush()
            return True
        return False
