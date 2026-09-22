"""
Podcast service (Phase 12 — script generation, no TTS).
Produces a two-person HOST/STUDENT educational dialogue from retrieved chunks,
exactly per the original roadmap prompt. TTS is intentionally out of scope
for the website MVP (Phase 12b later).
"""

import re
from typing import List

from api.services import pipeline

_SYSTEM = """You are writing a 2-person educational podcast script explaining
material to a curious student.

Speakers:
- HOST: an enthusiastic tutor who explains clearly, uses analogies
- STUDENT: a curious learner who asks follow-up questions

Use ONLY the material provided as your source of truth. Do not introduce
facts not present in it.

Write a natural back-and-forth dialogue of 8-14 exchanges. Format each line EXACTLY as:
HOST: ...
STUDENT: ...
No stage directions, no markdown, no scene headers."""


def _parse_script(raw: str) -> List[dict]:
    lines: List[dict] = []
    for line in raw.splitlines():
        m = re.match(r"^\s*(HOST|STUDENT)\s*:\s*(.+)$", line.strip(), re.IGNORECASE)
        if m:
            lines.append({"speaker": m.group(1).upper(), "line": m.group(2).strip()})
    return lines


def generate(query: str, context_text: str) -> List[dict]:
    """Generate HOST/STUDENT script lines from context. [] on failure/empty."""
    if not context_text.strip():
        return []
    client = pipeline.get_ollama()
    prompt = f"""Material:
{context_text}

Topic request: "{query}"

Write the podcast dialogue now (HOST:/STUDENT: lines only):"""
    raw = client.generate(prompt=prompt, system_prompt=_SYSTEM, temperature=0.5)
    return _parse_script(raw)


def script_to_markdown(script: List[dict]) -> str:
    lines = ["## 🎧 Podcast script", ""]
    for item in script:
        speaker = item.get("speaker", "?")
        text = item.get("line", "")
        if speaker == "HOST":
            lines.append(f"**🎙 HOST** — {text}")
        else:
            lines.append(f"**🎓 STUDENT** — {text}")
        lines.append("")
    lines.append("> Audio (TTS) coming in Phase 12b — script above is the full dialogue.")
    return "\n".join(lines).strip()
