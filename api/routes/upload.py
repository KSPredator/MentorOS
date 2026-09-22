"""
POST /upload — Document ingestion endpoint.
Accepts a multipart file upload (PDF, DOCX, PPTX, TXT, MD),
runs the parser + chunker + vector store indexing pipeline,
and returns the number of chunks embedded.
"""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.models import UploadResponse
from embeddings import get_vector_store
from ingestion.parser import DocumentParser
from ingestion.chunker import chunk_document

logger = logging.getLogger("MentorOS.API.Upload")

router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


@router.post("/upload", response_model=UploadResponse, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(..., description="Document to ingest (PDF, DOCX, PPTX, TXT, MD)"),
    session_id: str = Form(default="default", description="Session identifier"),
) -> UploadResponse:
    """
    Upload and index a document into the vector store.

    Pipeline:
      1. Save upload to a temp file.
      2. Parse text + page numbers (DocumentParser).
      3. Chunk into 300–500-token chunks with 15% overlap (TextChunker).
      4. Embed and upsert chunks into ChromaDB (VectorStore).
      5. Return indexing statistics.
    """
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            ),
        )

    # Write upload to a temp file so parsers can open it by path
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        parser = DocumentParser()
        pages = parser.parse(tmp_path)

        if not pages:
            raise HTTPException(
                status_code=422,
                detail=f"No text could be extracted from '{file.filename}'. "
                       "The file may be empty, image-only (scanned PDF), or corrupt.",
            )

        # Patch source_file to use the original filename, not the tmp path
        original_name = file.filename or tmp_path.name
        for page in pages:
            page.source_file = original_name

        chunks = chunk_document(pages)
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="Chunking produced no output. File may contain only whitespace.",
            )

        vs = get_vector_store()
        indexed = vs.add_chunks(chunks)
        sources = vs.get_sources()

        logger.info(
            f"Uploaded '{original_name}' | pages={len(pages)} | chunks={indexed} | "
            f"session={session_id}"
        )

        return UploadResponse(
            filename=original_name,
            chunks_indexed=indexed,
            sources=sources,
            message=f"Successfully indexed {indexed} chunks from '{original_name}'.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Upload failed for '{file.filename}': {exc}")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
