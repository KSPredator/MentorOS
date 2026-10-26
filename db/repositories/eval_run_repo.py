"""
Evaluation run repository for MentorOS.
Stores structured metrics from A/B/C evaluation harness benchmarks.
"""

import json
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.schema import EvalRun, now_iso


class EvalRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, run_id: str) -> Optional[EvalRun]:
        return self.session.get(EvalRun, run_id)

    def record_run(
        self,
        run_id: str,
        course_id: str,
        config: str,
        test_set: str,
        metrics: Dict,
        git_sha: Optional[str] = None,
    ) -> EvalRun:
        run = EvalRun(
            run_id=run_id,
            course_id=course_id,
            config=config,
            test_set=test_set,
            git_sha=git_sha,
            metrics_json=json.dumps(metrics, ensure_ascii=False),
            created_at=now_iso(),
        )
        self.session.add(run)
        self.session.flush()
        return run

    def list_runs(self, course_id: Optional[str] = None, config: Optional[str] = None) -> List[EvalRun]:
        stmt = select(EvalRun).order_by(EvalRun.created_at.desc())
        if course_id:
            stmt = stmt.where(EvalRun.course_id == course_id)
        if config:
            stmt = stmt.where(EvalRun.config == config)
        return list(self.session.scalars(stmt).all())
