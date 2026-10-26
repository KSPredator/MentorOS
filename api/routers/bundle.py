"""
OKF Knowledge Bundle API router for MentorOS.
Endpoints for bundle tree, concept viewer, human verification, and knowledge graph.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from api import config
from api.models import ConceptOut, VerifyConceptRequest, KnowledgeGraphOut, GraphNodeOut, GraphEdgeOut
from db import get_db_session, ConceptRepository, CourseRepository
from okf.bundle import load_concept, write_concept, is_stale, trust_tier, append_log
from okf.graph import build_graph
from okf.worker import git_commit_bundle

router = APIRouter()


@router.get("/bundle")
def get_bundle_overview(course_id: str = Query("default")):
    """Get bundle root index and list of concepts for a course."""
    bundle_dir = config.BASE_DIR / "bundle" / course_id
    index_file = bundle_dir / "index.md"

    index_text = index_file.read_text(encoding="utf-8") if index_file.exists() else "# Course Bundle"

    with get_db_session() as session:
        repo = ConceptRepository(session)
        concepts = repo.list_by_course(course_id)
        concept_list = [
            {
                "concept_id": c.concept_id,
                "title": c.title,
                "description": c.description,
                "status": c.status,
                "trust_tier": c.trust_tier,
                "updated_at": c.updated_at,
            }
            for c in concepts
        ]

    return {
        "course_id": course_id,
        "bundle_dir": str(bundle_dir),
        "index_content": index_text,
        "concepts": concept_list,
    }


@router.get("/concept/{concept_id:path}", response_model=ConceptOut)
def get_concept(concept_id: str, course_id: str = Query("default")):
    """Fetch concept markdown page, metadata, trust tier, and sources."""
    with get_db_session() as session:
        repo = ConceptRepository(session)
        concept = repo.get(concept_id)
        if not concept:
            # Try looking up with course_id prefix if omitted
            if not concept_id.startswith(f"{course_id}/"):
                concept = repo.get(f"{course_id}/{concept_id}")

        if not concept:
            raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found.")

        meta = json.loads(concept.meta_json or "{}")
        sources = repo.get_sources(concept.concept_id)

        # Check staleness
        stale_date = meta.get("stale_after")
        is_stale_flag = False
        if stale_date:
            try:
                clean_s = stale_date.replace("Z", "+00:00")
                stale_dt = datetime.fromisoformat(clean_s).replace(tzinfo=timezone.utc) if "T" not in clean_s else datetime.fromisoformat(clean_s)
                is_stale_flag = datetime.now(timezone.utc) >= stale_dt
            except Exception:
                pass

        return ConceptOut(
            concept_id=concept.concept_id,
            course_id=concept.course_id,
            title=concept.title,
            description=concept.description,
            status=concept.status,
            trust_tier=concept.trust_tier,
            body=concept.body,
            meta=meta,
            sources=sources,
            stale_after=stale_date,
            is_stale=is_stale_flag,
        )


@router.post("/concept/{concept_id:path}/verify", response_model=ConceptOut)
def verify_concept(concept_id: str, body: VerifyConceptRequest, course_id: str = Query("default")):
    """
    Apply human verification to concept page per OKF v0.2 spec.
    Adds verified entry {by: human:<id>, at: <now_iso>}, updates trust_tier to 'human-reviewed',
    writes back to file, and creates a git commit.
    """
    with get_db_session() as session:
        repo = ConceptRepository(session)
        concept = repo.get(concept_id)
        if not concept and not concept_id.startswith(f"{course_id}/"):
            concept = repo.get(f"{course_id}/{concept_id}")

        if not concept:
            raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found.")

        meta = json.loads(concept.meta_json or "{}")
        verified_list = meta.get("verified", [])
        if isinstance(verified_list, dict):
            verified_list = [verified_list]
        elif not isinstance(verified_list, list):
            verified_list = []

        now_str = datetime.now(timezone.utc).isoformat()
        verifier_tag = body.verifier_id if body.verifier_id.startswith("human:") else f"human:{body.verifier_id}"

        verified_list.append({"by": verifier_tag, "at": now_str})
        meta["verified"] = verified_list
        meta["status"] = "stable"

        # Update DB
        concept.meta_json = json.dumps(meta, ensure_ascii=False)
        concept.trust_tier = "human-reviewed"
        concept.status = "stable"
        concept.updated_at = now_str
        session.flush()

        # Update Markdown file on disk & git commit
        bundle_dir = config.BASE_DIR / "bundle" / concept.course_id
        concept_slug = concept.concept_id.split("/")[-1]
        dest_file = bundle_dir / f"{concept_slug}.md"

        from okf.models import Concept as OKFConcept
        okf_c = OKFConcept(id=concept.concept_id, meta=meta, body=concept.body, file_path=str(dest_file))
        write_concept(okf_c, dest_path=dest_file)

        append_log(bundle_dir, "VERIFIED", f"Concept '{concept.title}' verified by {verifier_tag}.")
        git_sha = git_commit_bundle(bundle_dir, f"Human verification by {verifier_tag} on {concept.title}")
        if git_sha:
            concept.bundle_commit = git_sha
            session.flush()

        sources = repo.get_sources(concept.concept_id)
        return ConceptOut(
            concept_id=concept.concept_id,
            course_id=concept.course_id,
            title=concept.title,
            description=concept.description,
            status=concept.status,
            trust_tier="human-reviewed",
            body=concept.body,
            meta=meta,
            sources=sources,
            stale_after=meta.get("stale_after"),
            is_stale=False,
        )


@router.get("/graph", response_model=KnowledgeGraphOut)
def get_knowledge_graph(course_id: str = Query("default")):
    """Build and return Knowledge Graph (nodes and edges) for Knowledge Map visualization."""
    bundle_dir = config.BASE_DIR / "bundle" / course_id
    if not bundle_dir.exists():
        return KnowledgeGraphOut(nodes=[], edges=[])

    G = build_graph(bundle_dir)
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append(
            GraphNodeOut(
                id=str(node_id),
                title=data.get("title", str(node_id)),
                type=data.get("type", "Concept"),
                status=data.get("status", "stable"),
                trust_tier=data.get("trust_tier", "unverified"),
            )
        )

    edges = []
    for u, v in G.edges():
        edges.append(GraphEdgeOut(source=str(u), target=str(v)))

    return KnowledgeGraphOut(nodes=nodes, edges=edges)
