"""
Durable Compile Job Worker for MentorOS.
Processes jobs from compile_jobs table:
  parse -> chunk -> embed -> topics -> compile -> verify -> commit to bundle.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import subprocess
import time
from typing import Optional

from api import config
from db import (
    get_db_session,
    CourseRepository,
    DocumentRepository,
    ChunkRepository,
    ConceptRepository,
    CompileJobRepository,
)
from ingestion import ingest_file, slugify
from ingestion.chunker import DocumentChunk
from embeddings import ChromaVectorIndex, get_course_collection_name
from okf.compiler import ConceptCompiler, COMPILER_VERSION, COMPILE_SYSTEM_PROMPT, compute_prompt_hash
from okf.bundle import init_bundle, write_concept, append_log, regen_index

logger = logging.getLogger("MentorOS.OKFWorker")


def git_commit_bundle(bundle_dir: Path, commit_message: str) -> Optional[str]:
    """Attempt git commit in the bundle directory. If not a git repo, initializes or ignores."""
    try:
        git_dir = bundle_dir / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=str(bundle_dir), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "MentorOS Bot"], cwd=str(bundle_dir), capture_output=True)
            subprocess.run(["git", "config", "user.email", "bot@mentoros.ai"], cwd=str(bundle_dir), capture_output=True)

        subprocess.run(["git", "add", "."], cwd=str(bundle_dir), capture_output=True, check=True)
        res = subprocess.run(["git", "commit", "-m", commit_message], cwd=str(bundle_dir), capture_output=True, text=True)
        # Get head sha
        sha_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(bundle_dir), capture_output=True, text=True)
        return sha_res.stdout.strip() if sha_res.returncode == 0 else None
    except Exception as e:
        logger.warning(f"Git commit failed on bundle: {e}")
        return None


class CompileWorker:
    """Executes compile jobs from the database queue."""

    def __init__(self, bundle_base_dir: Optional[Path] = None):
        self.bundle_base_dir = bundle_base_dir or (config.BASE_DIR / "bundle")
        self.compiler = ConceptCompiler()

    def process_job(self, job_id: str) -> bool:
        """Run a single compile job through all pipeline stages."""
        timings = {}
        start_all = time.time()

        with get_db_session() as session:
            job_repo = CompileJobRepository(session)
            doc_repo = DocumentRepository(session)
            chunk_repo = ChunkRepository(session)
            concept_repo = ConceptRepository(session)
            course_repo = CourseRepository(session)

            job = job_repo.get(job_id)
            if not job or job.status not in ("queued", "running"):
                return False

            doc = doc_repo.get(job.doc_id)
            if not doc:
                job_repo.mark_failed(job_id, f"Document '{job.doc_id}' not found.")
                return False

            course = course_repo.get(job.course_id)
            if not course:
                job_repo.mark_failed(job_id, f"Course '{job.course_id}' not found.")
                return False

            course_bundle_dir = self.bundle_base_dir / course.course_id
            init_bundle(course_bundle_dir, course_name=course.name)

            file_path = config.UPLOAD_DIR / doc.filename
            if not file_path.exists():
                job_repo.mark_failed(job_id, f"File on disk '{file_path}' not found.")
                return False

            try:
                # Stage 1: Parse & Chunk
                t0 = time.time()
                job_repo.update_stage(job_id, stage="chunk", status="running")
                chunks = ingest_file(file_path)
                for c in chunks:
                    c.metadata["doc_id"] = doc.doc_id
                    c.doc_slug = doc.doc_id
                    c.doc_version = doc.version
                chunk_repo.upsert_chunks(chunks)
                timings["chunk_s"] = round(time.time() - t0, 3)

                # Stage 2: Embed into per-course collection
                t0 = time.time()
                job_repo.update_stage(job_id, stage="embed", status="running")
                col_name = get_course_collection_name(course_id=course.course_id, embed_model=course.embed_model, version=1)
                vector_index = ChromaVectorIndex(collection_name=col_name, persist_dir=config.CHROMA_DIR)
                vector_index.upsert(chunks)
                timings["embed_s"] = round(time.time() - t0, 3)

                # Stage 3: Topic Extraction
                t0 = time.time()
                job_repo.update_stage(job_id, stage="topics", status="running")
                topics = self.compiler.extract_topics_from_chunks(chunks)
                timings["topics_count"] = len(topics)
                timings["topics_s"] = round(time.time() - t0, 3)

                # Stage 4: Compile Concept Pages
                t0 = time.time()
                job_repo.update_stage(job_id, stage="compile", status="running")
                compiled_concepts = []

                # Also prepare concepts vector index
                concepts_col_name = get_course_collection_name(course_id=course.course_id, is_concepts=True)
                concepts_vector_index = ChromaVectorIndex(collection_name=concepts_col_name, persist_dir=config.CHROMA_DIR)

                for t_item in topics:
                    t_title = t_item["title"]
                    t_slug = slugify(t_title)
                    ev_chunks = t_item["chunks"]

                    concept = self.compiler.compile_topic_page(
                        topic_title=t_title,
                        topic_slug=t_slug,
                        evidence_chunks=ev_chunks,
                        course_id=course.course_id,
                    )

                    # Stage 5: Verification
                    # If passed deterministic checks: mark machine-confirmed and stable
                    passed = len(concept.sources) > 0
                    if passed:
                        concept.meta["status"] = "stable"
                        concept.meta["verified"] = [
                            {"by": "process:mentoros-eval-agent", "at": datetime.now(timezone.utc).isoformat()}
                        ]
                    else:
                        concept.meta["status"] = "draft"
                        append_log(course_bundle_dir, "REJECT", f"Concept '{t_title}' remained draft: insufficient evidence.")

                    # Write to file
                    dest_path = course_bundle_dir / f"{t_slug}.md"
                    write_concept(concept, dest_path=dest_path)

                    # Register in DB
                    c_obj = concept_repo.upsert(
                        concept_id=concept.id,
                        course_id=course.course_id,
                        title=concept.title,
                        body=concept.body,
                        meta=concept.meta,
                        status=concept.status,
                        trust_tier=concept.meta.get("trust_tier", "machine-confirmed" if passed else "unverified"),
                        description=concept.description,
                    )
                    cited_chunk_ids = [s["id"] for s in concept.sources]
                    concept_repo.link_sources(concept.id, cited_chunk_ids)

                    # Register topic alias
                    concept_repo.add_alias(course.course_id, t_title, concept.id)

                    # Embed concept description & title into concept vector index
                    concept_chunk = DocumentChunk(
                        chunk_id=concept.id,
                        text=f"{concept.title}: {concept.description}\n{concept.body[:300]}",
                        source_file=f"{t_slug}.md",
                        page_number=1,
                        chunk_index=0,
                        token_count=100,
                        metadata={"title": concept.title, "concept_id": concept.id, "course_id": course.course_id},
                        doc_slug=t_slug,
                    )
                    concepts_vector_index.upsert([concept_chunk])

                    compiled_concepts.append(concept)

                timings["compile_s"] = round(time.time() - t0, 3)

                # Stage 6: Regenerate bundle index & Commit
                regen_index(course_bundle_dir)
                append_log(course_bundle_dir, "COMPILED", f"Compiled {len(compiled_concepts)} concepts from '{doc.filename}'.")

                commit_sha = git_commit_bundle(course_bundle_dir, f"Compile {len(compiled_concepts)} concepts from {doc.filename}")
                if commit_sha:
                    for c in compiled_concepts:
                        concept_repo.upsert(
                            concept_id=c.id,
                            course_id=course.course_id,
                            title=c.title,
                            body=c.body,
                            meta=c.meta,
                            status=c.status,
                            trust_tier="machine-confirmed",
                            bundle_commit=commit_sha,
                        )

                timings["total_s"] = round(time.time() - start_all, 3)
                job_repo.mark_completed(job_id, timings=timings)
                doc_repo.update_status(doc.doc_id, "indexed")
                return True

            except Exception as e:
                logger.exception(f"Compile job {job_id} failed: {e}")
                timings["total_s"] = round(time.time() - start_all, 3)
                job_repo.mark_failed(job_id, error=str(e), timings=timings)
                doc_repo.update_status(doc.doc_id, "failed", error=str(e))
                return False

    def poll_and_run(self, limit: int = 5) -> int:
        """Poll queued jobs and process them sequentially."""
        with get_db_session() as session:
            job_repo = CompileJobRepository(session)
            pending = job_repo.list_pending(limit=limit)

        processed = 0
        for job in pending:
            if self.process_job(job.job_id):
                processed += 1
        return processed
