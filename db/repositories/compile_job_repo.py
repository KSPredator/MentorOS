"""
Compile job repository for MentorOS.
Durable job tracking with idempotency over (doc_id, version, compiler_version, prompt_hash).
"""

import json
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import CompileJob, now_iso


class CompileJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, job_id: str) -> Optional[CompileJob]:
        return self.session.get(CompileJob, job_id)

    def find_idempotent_job(
        self,
        doc_id: str,
        doc_version: int,
        compiler_version: str,
        prompt_hash: str,
    ) -> Optional[CompileJob]:
        stmt = select(CompileJob).where(
            CompileJob.doc_id == doc_id,
            CompileJob.doc_version == doc_version,
            CompileJob.compiler_version == compiler_version,
            CompileJob.prompt_hash == prompt_hash,
        )
        return self.session.scalars(stmt).first()

    def enqueue_job(
        self,
        course_id: str,
        doc_id: str,
        doc_version: int,
        compiler_version: str = "0.2.0",
        prompt_hash: str = "default",
    ) -> CompileJob:
        import uuid
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        return self.create_or_reuse_job(
            job_id=job_id,
            doc_id=doc_id,
            doc_version=doc_version,
            course_id=course_id,
            compiler_version=compiler_version,
            prompt_hash=prompt_hash,
        )

    def create_or_reuse_job(
        self,
        job_id: str,
        doc_id: str,
        doc_version: int,
        course_id: str,
        compiler_version: str,
        prompt_hash: str,
    ) -> CompileJob:
        existing = self.find_idempotent_job(
            doc_id=doc_id,
            doc_version=doc_version,
            compiler_version=compiler_version,
            prompt_hash=prompt_hash,
        )
        if existing:
            return existing

        now = now_iso()
        job = CompileJob(
            job_id=job_id,
            doc_id=doc_id,
            doc_version=doc_version,
            course_id=course_id,
            compiler_version=compiler_version,
            prompt_hash=prompt_hash,
            status="queued",
            stage="init",
            error=None,
            timings_json="{}",
            created_at=now,
            updated_at=now,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def list_pending(self, limit: int = 10) -> List[CompileJob]:
        stmt = (
            select(CompileJob)
            .where(CompileJob.status.in_(["queued", "running"]))
            .order_by(CompileJob.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def update_stage(
        self,
        job_id: str,
        stage: str,
        status: str = "running",
        error: Optional[str] = None,
        timings: Optional[Dict] = None,
    ):
        job = self.get(job_id)
        if job:
            job.stage = stage
            job.status = status
            job.updated_at = now_iso()
            if error is not None:
                job.error = error
            if timings:
                current_timings = json.loads(job.timings_json or "{}")
                current_timings.update(timings)
                job.timings_json = json.dumps(current_timings)
            self.session.flush()

    def mark_completed(self, job_id: str, timings: Optional[Dict] = None):
        self.update_stage(job_id=job_id, stage="completed", status="completed", timings=timings)

    def mark_failed(self, job_id: str, error: str, timings: Optional[Dict] = None):
        self.update_stage(job_id=job_id, stage="failed", status="failed", error=error, timings=timings)
