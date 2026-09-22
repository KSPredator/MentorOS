"""
Test Suite for Phase 12 Podcast Mode (Two-Voice Audio Explainer)
================================================================
Verifies:
  1. Script generation with HOST & STUDENT dialogue parsing
  2. Dual-voice TTS synthesis (edge-tts / pyttsx3 fallback)
  3. Audio file integrity and duration calculation
  4. FastAPI endpoints: /podcast/generate, /podcast/audio/{filename}, /podcast/list
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.podcast_agent import PodcastAgent, DialogueTurn, PODCAST_STORAGE_DIR
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_dialogue_parser():
    """Verify regex parsing of raw LLM dialogue scripts."""
    agent = PodcastAgent()
    sample_script = """
    HOST: Welcome to today's deep dive on Foundation Models!
    STUDENT: Thanks Alex, I've heard a lot about how they differ from traditional ML. What's the main shift?
    HOST: Traditional ML focused on bespoke architectures trained from scratch on task-specific labels.
    STUDENT: And foundation models are trained on massive unlabelled corpora instead, right?
    HOST: Exactly! You pre-train once at scale, and then adapt downstream.
    """
    turns = agent._parse_dialogue(sample_script)
    assert len(turns) == 5
    assert turns[0].speaker == "HOST"
    assert "Welcome to today's deep dive" in turns[0].text
    assert turns[1].speaker == "STUDENT"
    assert "differ from traditional ML" in turns[1].text
    assert turns[4].speaker == "HOST"


def test_tts_synthesis_and_episode_creation():
    """Verify dual-voice synthesis creates a valid playable MP3 file with metadata."""
    agent = PodcastAgent()
    turns = [
        DialogueTurn(speaker="HOST", text="Welcome back! Today we are discussing Retrieval Augmented Generation."),
        DialogueTurn(speaker="STUDENT", text="Is RAG used to prevent hallucinations in large language models?"),
        DialogueTurn(speaker="HOST", text="Yes, by grounding answers directly in retrieved document chunks!"),
    ]
    
    episode = agent.synthesize_podcast(
        topic="RAG Architecture Quick Explainer",
        turns=turns,
        sources=["test_lecture.pdf (p.1)"],
    )
    
    assert episode.id.startswith("podcast_")
    assert episode.audio_filename.endswith(".mp3")
    
    audio_path = PODCAST_STORAGE_DIR / episode.audio_filename
    assert audio_path.exists(), "Synthesized audio file must exist"
    assert audio_path.stat().st_size > 500, "Audio file should contain binary MP3 data"
    assert episode.total_duration_s > 0, "Total duration should be positive"
    
    # Metadata JSON check
    meta_path = PODCAST_STORAGE_DIR / f"{episode.id}.json"
    assert meta_path.exists(), "Podcast metadata JSON must exist"


def test_api_generate_podcast_endpoint():
    """Verify POST /podcast/generate returns full episode response."""
    response = client.post(
        "/podcast/generate",
        json={
            "topic": "Chapter 4: Vector Databases and Similarity Search",
            "context": "Vector databases store dense embeddings and use cosine similarity or HNSW indexing to retrieve relevant context fast.",
            "num_turns": 4,
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "id" in data
    assert "audio_url" in data
    assert len(data["turns"]) >= 2
    assert data["topic"] == "Chapter 4: Vector Databases and Similarity Search"
    
    # Check streaming audio endpoint
    audio_url = data["audio_url"]
    audio_resp = client.get(audio_url)
    assert audio_resp.status_code == 200
    assert audio_resp.headers.get("content-type") == "audio/mpeg"
    assert len(audio_resp.content) > 500


def test_api_list_podcasts():
    """Verify GET /podcast/list returns the library of episodes."""
    response = client.get("/podcast/list")
    assert response.status_code == 200
    episodes = response.json()
    assert isinstance(episodes, list)
    assert len(episodes) >= 1
    assert "turns" in episodes[0]


if __name__ == "__main__":
    print("=" * 60)
    print("Running Phase 12 Podcast Mode Tests...")
    print("=" * 60)
    
    print("\n1. Testing Dialogue Parser...")
    test_dialogue_parser()
    print("   PASSED: Dialogue Parser verified.")
    
    print("\n2. Testing Dual-Voice TTS Synthesis & Episode Creation...")
    test_tts_synthesis_and_episode_creation()
    print("   PASSED: Audio generated and verified.")
    
    print("\n3. Testing POST /podcast/generate API endpoint...")
    test_api_generate_podcast_endpoint()
    print("   PASSED: /podcast/generate and audio stream verified.")
    
    print("\n4. Testing GET /podcast/list API endpoint...")
    test_api_list_podcasts()
    print("   PASSED: /podcast/list verified.")
    
    print("\n" + "=" * 60)
    print("ALL PHASE 12 PODCAST MODE TESTS PASSED!")
    print("=" * 60)
