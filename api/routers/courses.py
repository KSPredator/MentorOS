"""
Courses API router for MentorOS.
Provides course listing and registration.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.models import CourseOut
from db import get_db_session, CourseRepository, ensure_default_course

router = APIRouter()


class CreateCourseRequest(BaseModel):
    course_id: str
    name: str
    bundle_path: str = "bundle/default"
    embed_model: str = "all-MiniLM-L6-v2"


@router.get("/courses", response_model=List[CourseOut])
def list_courses():
    with get_db_session() as session:
        ensure_default_course(session)
        repo = CourseRepository(session)
        courses = repo.list_all()
        return [
            CourseOut(
                course_id=c.course_id,
                name=c.name,
                bundle_path=c.bundle_path,
                embed_model=c.embed_model,
                created_at=c.created_at,
            )
            for c in courses
        ]


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(body: CreateCourseRequest):
    with get_db_session() as session:
        repo = CourseRepository(session)
        existing = repo.get(body.course_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Course '{body.course_id}' already exists.")
        c = repo.upsert(
            course_id=body.course_id,
            name=body.name,
            bundle_path=body.bundle_path or f"bundle/{body.course_id}",
            embed_model=body.embed_model,
        )
        return CourseOut(
            course_id=c.course_id,
            name=c.name,
            bundle_path=c.bundle_path,
            embed_model=c.embed_model,
            created_at=c.created_at,
        )
