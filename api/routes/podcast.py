"""
Podcast API Route — Phase 12 Two-Voice Audio Explainer
=======================================================
Endpoints:
  POST /podcast/generate  — Generate 2-person dialogue script and synthesized MP3
  GET  /podcast/audio/{filename} — Stream/download podcast MP3
  GET  /podcast/list      — List all saved podcast episodes
  GET  /podcast/{id}      — Retrieve podcast episode metadata
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents.podcast_agent import PodcastAgent, PODCAST_STORAGE_DIR

logger = logging.getLogger("MentorOS.API.Podcast")
router = APIRouter(prefix="/podcast", tags=["Podcast"])

# Singleton agent instance
_podcast_agent: Optional[PodcastAgent] = None


def get_podcast_agent() -> PodcastAgent:
    global _podcast_agent
    if _podcast_agent is None:
        _podcast_agent = PodcastAgent()
    return _podcast_agent


class PodcastGenerateRequest(BaseModel):
    topic: str
    context: Optional[str] = None
    num_turns: Optional[int] = 8


class PodcastEpisodeResponse(BaseModel):
    id: str
    title: str
    topic: str
    created_at: float
    total_duration_s: float
    turns: List[Dict[str, Any]]
    audio_filename: str
    audio_url: str
    sources: List[str]


@router.post("/generate", response_model=PodcastEpisodeResponse)
async def generate_podcast(req: PodcastGenerateRequest):
    """
    Generate an engaging 2-speaker educational podcast episode
    from topic keywords or specific text context.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    
    agent = get_podcast_agent()
    try:
        episode = agent.create_podcast_from_topic(
            topic=req.topic.strip(),
            context=req.context,
            num_turns=req.num_turns or 8,
        )
        
        return PodcastEpisodeResponse(
            id=episode.id,
            title=episode.title,
            topic=episode.topic,
            created_at=episode.created_at,
            total_duration_s=episode.total_duration_s,
            turns=episode.turns,
            audio_filename=episode.audio_filename,
            audio_url=f"/podcast/audio/{episode.audio_filename}",
            sources=episode.sources,
        )
    except Exception as e:
        logger.error(f"Error generating podcast for topic '{req.topic}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate podcast: {str(e)}")


@router.get("/audio/{filename}")
async def get_podcast_audio(filename: str):
    """Stream or download a generated podcast MP3 file."""
    # Sanitize filename
    safe_name = Path(filename).name
    file_path = PODCAST_STORAGE_DIR / safe_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
        
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=safe_name,
    )


@router.get("/list", response_model=List[PodcastEpisodeResponse])
async def list_podcasts():
    """List all previously generated podcast episodes."""
    agent = get_podcast_agent()
    episodes = agent.list_episodes()
    
    result = []
    for ep in episodes:
        audio_name = ep.get("audio_filename", f"{ep['id']}.mp3")
        result.append(
            PodcastEpisodeResponse(
                id=ep["id"],
                title=ep.get("title", f"Deep Dive: {ep.get('topic', 'Episode')}"),
                topic=ep.get("topic", "General"),
                created_at=ep.get("created_at", 0),
                total_duration_s=ep.get("total_duration_s", 0),
                turns=ep.get("turns", []),
                audio_filename=audio_name,
                audio_url=f"/podcast/audio/{audio_name}",
                sources=ep.get("sources", []),
            )
        )
    return result


@router.get("/{podcast_id}", response_model=PodcastEpisodeResponse)
async def get_podcast_details(podcast_id: str):
    """Retrieve detailed transcript and metadata for a specific podcast episode."""
    agent = get_podcast_agent()
    ep = agent.get_episode(podcast_id)
    if not ep:
        raise HTTPException(status_code=404, detail=f"Podcast episode '{podcast_id}' not found.")
        
    audio_name = ep.get("audio_filename", f"{ep['id']}.mp3")
    return PodcastEpisodeResponse(
        id=ep["id"],
        title=ep.get("title", f"Deep Dive: {ep.get('topic', 'Episode')}"),
        topic=ep.get("topic", "General"),
        created_at=ep.get("created_at", 0),
        total_duration_s=ep.get("total_duration_s", 0),
        turns=ep.get("turns", []),
        audio_filename=audio_name,
        audio_url=f"/podcast/audio/{audio_name}",
        sources=ep.get("sources", []),
    )
