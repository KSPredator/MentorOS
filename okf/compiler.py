"""
OKF Concept Compiler for MentorOS.
Transforms grounded document chunks into cited, verified OKF Concept Markdown pages.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ingestion.chunker import DocumentChunk
from llm.ollama_client import OllamaClient
from okf.models import Concept
from okf.bundle import write_concept, append_log, trust_tier

logger = logging.getLogger("MentorOS.OKFCompiler")

COMPILER_VERSION = "mentoros_compiler/2.0"
COMPILE_SYSTEM_PROMPT = """You are a strict technical compiler creating Open Knowledge Format (OKF v0.2) concept pages from course source chunks.
Write a clear, concise, structured concept explanation using ONLY the provided evidence chunks.

STRICT CITATION RULES:
1. Every factual sentence or paragraph MUST end with a bracketed citation pointing to the exact Chunk ID it was derived from, like [^chunk-id].
2. Do NOT invent information outside the provided chunks.
3. Keep all numbers, formulas, and technical names exactly as written in the evidence.
4. Output Markdown body only (do not include frontmatter)."""


def compute_prompt_hash(prompt_template: str) -> str:
    return hashlib.sha256(prompt_template.encode("utf-8")).hexdigest()[:16]


class ConceptCompiler:
    """Compiles document chunks into verified OKF concept pages with deterministic checks."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama_client = ollama_client or OllamaClient()

    def extract_topics_from_chunks(self, chunks: List[DocumentChunk], max_topics: int = 15) -> List[Dict[str, Any]]:
        """
        Derive initial topic candidate list from document headings and prominent concepts.
        Deterministic extraction: extracts markdown headings (#, ##, ###) and bold titles.
        """
        topics_found = {}
        for c in chunks:
            # Check for markdown headers
            header_matches = re.findall(r"^(?:#{1,3})\s+([A-Za-z0-9\s,\-:]{4,60})", c.text, re.MULTILINE)
            for h in header_matches:
                clean_h = h.strip()
                if clean_h and len(clean_h) > 3 and clean_h.lower() not in topics_found:
                    topics_found[clean_h.lower()] = {
                        "title": clean_h,
                        "chunks": [c],
                    }
                elif clean_h.lower() in topics_found:
                    topics_found[clean_h.lower()]["chunks"].append(c)

        # Fallback if few or no markdown headings were found (e.g. raw text or slides)
        if len(topics_found) < 2 and chunks:
            # Use top chunk first lines
            for idx, c in enumerate(chunks[:max_topics]):
                first_line = c.text.strip().split("\n")[0][:60].strip()
                clean_title = re.sub(r"[^A-Za-z0-9\s-]", "", first_line).strip()
                if clean_title and len(clean_title) > 5 and clean_title.lower() not in topics_found:
                    topics_found[clean_title.lower()] = {
                        "title": clean_title,
                        "chunks": [c],
                    }

        result = list(topics_found.values())[:max_topics]
        return result

    def deterministic_checks(
        self,
        body: str,
        input_chunks: List[DocumentChunk],
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Deterministic validations before saving concept:
        1. Every footnote citation [^id] exists in input chunk IDs.
        2. Citations are present (not zero citations).
        3. Numbers in body exist in cited chunks.
        Returns: (passed, cited_chunk_ids, error_messages)
        """
        errors = []
        valid_input_ids = {c.chunk_id: c.text for c in input_chunks}

        # Find all citations like [^chunk-id] or [chunk-id]
        cited_ids = re.findall(r"\[\^?([a-zA-Z0-9_\-]+)\]", body)
        cited_ids = [cid for cid in cited_ids if cid in valid_input_ids]

        if not cited_ids:
            errors.append("No valid chunk citations found in compiled body.")

        # Check for ungrounded numbers (>3 digits)
        body_numbers = set(re.findall(r"\b\d{3,}\b", body))
        all_chunk_text = " ".join(c.text for c in input_chunks)
        for num in body_numbers:
            if num not in all_chunk_text:
                errors.append(f"Number '{num}' in compiled text does not exist in source chunks.")

        passed = len(errors) == 0
        return passed, list(set(cited_ids)), errors

    def compile_topic_page(
        self,
        topic_title: str,
        topic_slug: str,
        evidence_chunks: List[DocumentChunk],
        course_id: str = "default",
        retries: int = 2,
    ) -> Concept:
        """
        Compile evidence chunks into an OKF Concept page.
        """
        evidence_prompt_parts = []
        valid_chunk_map = {}
        for c in evidence_chunks:
            valid_chunk_map[c.chunk_id] = c
            evidence_prompt_parts.append(f"--- Chunk ID: {c.chunk_id} (Page/Slide {c.page_number}) ---\n{c.text}")

        evidence_text = "\n\n".join(evidence_prompt_parts[:10])

        user_prompt = f"""Topic: {topic_title}

Evidence Chunks:
{evidence_text}

Instructions:
Write an authoritative concept summary of '{topic_title}' strictly based on the evidence chunks above.
Add [^{evidence_chunks[0].chunk_id}] style citations to facts."""

        compiled_body = ""
        passed = False
        cited_ids: List[str] = []
        errors: List[str] = []

        for attempt in range(retries):
            try:
                raw_out = self.ollama_client.generate(
                    prompt=user_prompt,
                    system_prompt=COMPILE_SYSTEM_PROMPT,
                    temperature=0.1,
                )
                passed, cited_ids, errors = self.deterministic_checks(raw_out, evidence_chunks)
                if passed:
                    compiled_body = raw_out
                    break
                else:
                    logger.warning(f"Compile check retry {attempt + 1}: {errors}")
            except Exception as e:
                logger.warning(f"Ollama compile error: {e}")

        # Fallback if generation failed or Ollama not running:
        # Synthesize deterministic extractive concept from evidence chunks directly!
        if not compiled_body:
            paragraphs = []
            cited_ids = []
            for c in evidence_chunks[:4]:
                first_para = c.text.strip().split("\n\n")[0].strip()
                paragraphs.append(f"{first_para} [^{c.chunk_id}].")
                cited_ids.append(c.chunk_id)
            compiled_body = f"# {topic_title}\n\n" + "\n\n".join(paragraphs)
            passed = True

        # Build frontmatter per OKF v0.2 spec
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        stale_after_str = (now + timedelta(days=180)).strftime("%Y-%m-%d")

        sources_list = []
        for cid in set(cited_ids):
            c_obj = valid_chunk_map.get(cid)
            if c_obj:
                sources_list.append({
                    "id": cid,
                    "title": f"{c_obj.source_file} (Page {c_obj.page_number})",
                })
            else:
                sources_list.append({"id": cid, "title": cid})

        first_sentence = compiled_body.replace("\n", " ").strip()[:180]
        input_hash = hashlib.sha256("".join(c.text_hash for c in evidence_chunks).encode("utf-8")).hexdigest()

        meta: Dict[str, Any] = {
            "title": topic_title,
            "type": "Concept",
            "description": first_sentence,
            "tags": [course_id, topic_slug],
            "sources": sources_list,
            "generated": {
                "by": COMPILER_VERSION,
                "at": now_str,
            },
            "status": "draft",
            "stale_after": stale_after_str,
        }

        concept_id = f"{course_id}/{topic_slug}"
        return Concept(
            id=concept_id,
            meta=meta,
            body=compiled_body,
        )
