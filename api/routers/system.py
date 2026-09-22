"""System router — GET /api/status (Phase 9.2)."""

from fastapi import APIRouter

from api.services import pipeline

router = APIRouter()


@router.get("/status")
def get_status():
    return pipeline.status_dict()
