"""
Files router (Phase 9.3): upload, list, delete, bulk delete, chunk preview.
"""

import urllib.parse
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from api import config, db
from api.models import ChunkOut, FileOut
from api.services import file_service

router = APIRouter()


@router.post("/files/upload", response_model=FileOut, status_code=201)
def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    try:
        data = file.file.read()
        result = file_service.ingest_upload(file.filename, data)
        return _file_out(result)
    except file_service.FileValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=List[FileOut])
def list_files():
    return [_file_out(r) for r in file_service.list_files_out()]


@router.delete("/files", status_code=200)
def delete_all_files():
    removed = file_service.delete_all_files()
    return {"deleted": removed}


@router.delete("/files/{filename}", status_code=200)
def delete_file(filename: str):
    # Support URL-encoded names (spaces etc.)
    name = urllib.parse.unquote(filename)
    if not file_service.delete_file(name):
        raise HTTPException(status_code=404, detail=f"File '{name}' not found.")
    return {"deleted": name}


@router.get("/chunks/{chunk_id}", response_model=ChunkOut)
def get_chunk(chunk_id: str):
    try:
        chunk = file_service.get_chunk(chunk_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found.")
    return chunk


def _file_out(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "filename": row.get("filename", ""),
        "ext": (row.get("ext") or "").lstrip(".").upper(),
        "size_bytes": int(row.get("size_bytes") or 0),
        "status": row.get("status", "processing"),
        "chunk_count": int(row.get("chunk_count") or 0),
        "error": row.get("error"),
        "uploaded_at": row.get("uploaded_at"),
    }


# Silence unused import warning for config (kept for future validators)
_ = config
