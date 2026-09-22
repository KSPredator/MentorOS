"""
Podcast service (Phase 12 — Two-Voice Audio Explainer).
Produces an interactive two-person HOST/STUDENT educational dialogue from retrieved chunks,
synthesizes dual-voice neural TTS audio, and provides audio stream URLs.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from agents.podcast_agent import DialogueTurn, PodcastAgent, PODCAST_STORAGE_DIR
from api.services import pipeline

logger = logging.getLogger("MentorOS.PodcastService")

_SYSTEM = """You are writing a 2-person educational podcast script explaining
material to a curious student.

Speakers:
- HOST: an enthusiastic tutor who explains clearly, uses analogies
- STUDENT: a curious learner who asks follow-up questions

Use ONLY the material provided as your source of truth. Do not introduce
facts not present in it.

Write a natural back-and-forth dialogue of 6-10 exchanges. Format each line EXACTLY as:
HOST: ...
STUDENT: ...
No stage directions, no markdown, no scene headers."""


def _parse_script(raw: str) -> List[dict]:
    lines: List[dict] = []
    for line in raw.splitlines():
        m = re.match(r"^\s*(HOST|Alex|Host)\s*:\s*(.+)$", line.strip(), re.IGNORECASE)
        s = re.match(r"^\s*(STUDENT|Sam|Student|Learner)\s*:\s*(.+)$", line.strip(), re.IGNORECASE)
        if m:
            lines.append({"speaker": "HOST", "line": m.group(2).strip()})
        elif s:
            lines.append({"speaker": "STUDENT", "line": s.group(2).strip()})
    return lines


def generate_with_audio(query: str, context_text: str, sources: List[str] = None) -> Tuple[List[dict], Optional[str], Optional[str]]:
    """
    Generate HOST/STUDENT script lines from context AND synthesize dual-voice MP3.
    Returns: (script_lines, audio_url, audio_filename)
    """
    if not context_text.strip():
        return [], None, None
    
    agent = PodcastAgent()
    turns, auto_sources = agent.generate_script(topic=query, context=context_text, num_turns=6)
    
    # Synthesize audio
    try:
        episode = agent.synthesize_podcast(topic=query, turns=turns, sources=sources or auto_sources)
        audio_url = f"/api/podcast/audio/{episode.audio_filename}"
        audio_filename = episode.audio_filename
        script_dicts = [{"speaker": t.speaker, "line": t.text, "start_time_s": t.start_time_s, "estimated_duration_s": t.estimated_duration_s} for t in turns]
        return script_dicts, audio_url, audio_filename
    except Exception as e:
        logger.warning(f"Audio synthesis failed in podcast service ({e}), returning script only: {e}")
        script_dicts = [{"speaker": t.speaker, "line": t.text, "start_time_s": t.start_time_s, "estimated_duration_s": t.estimated_duration_s} for t in turns]
        return script_dicts, None, None


def generate(query: str, context_text: str) -> List[dict]:
    """Generate HOST/STUDENT script lines from context."""
    script_lines, _, _ = generate_with_audio(query, context_text)
    return script_lines


def script_to_markdown(script: List[dict], audio_url: Optional[str] = None) -> str:
    lines = ["## 🎧 Two-Voice Podcast Explainer", ""]
    if audio_url:
        lines.append(f"🎙️ **Dual-Voice Audio Generated:** [Listen / Download MP3]({audio_url})")
        lines.append("")

    for item in script:
        speaker = item.get("speaker", "?")
        text = item.get("line", "")
        if speaker == "HOST":
            lines.append(f"**🎙 HOST (Alex)** — {text}")
        else:
            lines.append(f"**🎓 STUDENT (Sam)** — {text}")
        lines.append("")
    return "\n".join(lines).strip()
