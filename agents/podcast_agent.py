"""
Podcast Agent — Phase 12 Two-Voice Audio Explainer
===================================================
Converts lecture notes, textbook chapters, or Q&A context into engaging,
natural 2-person educational podcast episodes.

Speakers:
  - HOST (Tutor): Enthusiastic, explains core concepts, uses intuitive analogies (Voice: en-US-GuyNeural)
  - STUDENT (Learner): Curious, asks sharp clarifying questions and edge cases (Voice: en-US-JennyNeural)

Outputs:
  - Stitched MP3 audio with natural pauses between speaking turns
  - Timestamped dialogue transcripts for interactive UI synchronization
"""

import asyncio
import io
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MentorOS.PodcastAgent")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PODCAST_STORAGE_DIR = PROJECT_ROOT / "data" / "podcasts"
PODCAST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Default TTS Voices
HOST_VOICE = "en-US-GuyNeural"
STUDENT_VOICE = "en-US-JennyNeural"


@dataclass
class DialogueTurn:
    speaker: str  # "HOST" or "STUDENT"
    text: str
    estimated_duration_s: float = 0.0
    start_time_s: float = 0.0


@dataclass
class PodcastEpisode:
    id: str
    title: str
    topic: str
    created_at: float
    total_duration_s: float
    turns: List[Dict[str, Any]]
    audio_filename: str
    sources: List[str]


PODCAST_SCRIPT_PROMPT = """You are a scriptwriter for an educational podcast called "MentorOS Deep Dive".
Write an engaging, clear 2-person dialogue explaining the topic based ONLY on the provided context material.

Speakers:
- HOST (Alex): An expert tutor who explains complex technical concepts clearly with relatable analogies.
- STUDENT (Sam): A smart, curious learner who asks great follow-up questions, asks for clarifications, and connects the ideas.

Guidelines:
1. Ground every explanation in the provided material. Do not invent unrelated facts.
2. Keep the dialogue conversational, dynamic, and easy to listen to (natural back-and-forth).
3. Aim for {num_turns} turns total (alternating between HOST and STUDENT).
4. Strictly format every turn as:
HOST: <text>
STUDENT: <text>

Topic: {topic}

Context Material:
{context}

Begin the script directly with HOST:
"""


class PodcastAgent:
    """Agent that creates 2-voice audio explainer episodes from retrieved documents."""

    def __init__(self, ollama_client=None, vector_store=None):
        if ollama_client is None:
            from llm.ollama_client import OllamaClient
            self.ollama = OllamaClient()
        else:
            self.ollama = ollama_client
            
        if vector_store is None:
            from embeddings import get_vector_store
            self.vs = get_vector_store()
        else:
            self.vs = vector_store

    def retrieve_context(self, topic: str, k: int = 4) -> Tuple[str, List[str]]:
        """Retrieve relevant context chunks from ChromaDB vector store."""
        try:
            chunks = self.vs.retrieve(topic, k=k)
            if not chunks:
                return f"Topic overview and principles of: {topic}", []
            
            combined_text = "\n\n".join([f"[Source: {c.source_file}, Page {c.page_number}]\n{c.text}" for c in chunks])
            sources = list(set([f"{c.source_file} (p.{c.page_number})" for c in chunks]))
            return combined_text, sources
        except Exception as e:
            logger.warning(f"Vector store retrieval error in podcast agent: {e}")
            return f"Topic: {topic}", []

    def generate_script(self, topic: str, context: Optional[str] = None, num_turns: int = 8) -> Tuple[List[DialogueTurn], List[str]]:
        """Generate structured dialogue turns between HOST and STUDENT."""
        sources = []
        if not context:
            retrieved_context, sources = self.retrieve_context(topic, k=4)
            context = retrieved_context

        prompt = PODCAST_SCRIPT_PROMPT.format(
            topic=topic,
            context=context[:3000],  # stay safely within context limits
            num_turns=num_turns,
        )

        logger.info(f"Generating podcast script for topic: '{topic}' ({num_turns} turns requested)")
        raw_output = self.ollama.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1500,
        )

        turns = self._parse_dialogue(raw_output)
        if not turns:
            # Fallback dialogue if generation output didn't parse
            turns = [
                DialogueTurn(speaker="HOST", text=f"Welcome to MentorOS Deep Dive. Today we're exploring {topic}."),
                DialogueTurn(speaker="STUDENT", text="I'm excited to dive in! What's the main idea behind this topic?"),
                DialogueTurn(speaker="HOST", text=f"At its core, {context[:250]}."),
                DialogueTurn(speaker="STUDENT", text="That makes a lot of sense. How does this apply in practice?"),
                DialogueTurn(speaker="HOST", text="It allows us to build reliable, modular systems that scale gracefully."),
            ]

        # Calculate estimated durations and cumulative timestamps
        current_time = 0.0
        for turn in turns:
            word_count = len(turn.text.split())
            # ~140 words per minute ≈ 2.33 words/sec
            est_duration = max(1.5, word_count / 2.3)
            turn.estimated_duration_s = round(est_duration, 2)
            turn.start_time_s = round(current_time, 2)
            current_time += est_duration + 0.35  # add 350ms pause between turns

        return turns, sources

    def _parse_dialogue(self, raw_text: str) -> List[DialogueTurn]:
        """Parse raw LLM output into structured DialogueTurn objects."""
        turns: List[DialogueTurn] = []
        lines = raw_text.strip().split("\n")
        
        current_speaker = None
        current_text_parts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            host_match = re.match(r"^(?:HOST|Alex|Host)\s*:\s*(.*)$", line, re.IGNORECASE)
            student_match = re.match(r"^(?:STUDENT|Sam|Student|Learner)\s*:\s*(.*)$", line, re.IGNORECASE)

            if host_match:
                if current_speaker and current_text_parts:
                    turns.append(DialogueTurn(speaker=current_speaker, text=" ".join(current_text_parts)))
                    current_text_parts = []
                current_speaker = "HOST"
                current_text_parts.append(host_match.group(1).strip())
            elif student_match:
                if current_speaker and current_text_parts:
                    turns.append(DialogueTurn(speaker=current_speaker, text=" ".join(current_text_parts)))
                    current_text_parts = []
                current_speaker = "STUDENT"
                current_text_parts.append(student_match.group(1).strip())
            else:
                if current_speaker:
                    current_text_parts.append(line)

        if current_speaker and current_text_parts:
            turns.append(DialogueTurn(speaker=current_speaker, text=" ".join(current_text_parts)))

        # Clean turns (remove stray asterisks / quotes)
        cleaned_turns = []
        for t in turns:
            clean_text = t.text.replace("*", "").replace('"', '').strip()
            if clean_text:
                cleaned_turns.append(DialogueTurn(speaker=t.speaker, text=clean_text))

        return cleaned_turns

    async def _synthesize_edge_tts(self, turns: List[DialogueTurn], output_path: Path) -> float:
        """Synthesize dual voices using edge-tts and concatenate into an MP3 file."""
        import edge_tts

        combined_audio = bytearray()
        
        # 300ms of silence byte padding between MP3 segments
        silence_bytes = b"\x00" * 256

        for i, turn in enumerate(turns):
            voice = HOST_VOICE if turn.speaker == "HOST" else STUDENT_VOICE
            communicate = edge_tts.Communicate(turn.text, voice, rate="+5%")
            turn_audio = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    turn_audio.extend(chunk["data"])
            
            combined_audio.extend(turn_audio)
            if i < len(turns) - 1:
                combined_audio.extend(silence_bytes)

        with open(output_path, "wb") as f:
            f.write(combined_audio)

        total_words = sum(len(t.text.split()) for t in turns)
        est_duration = max(5.0, (total_words / 2.3) + (len(turns) * 0.35))
        return est_duration

    def _synthesize_pyttsx3_fallback(self, turns: List[DialogueTurn], output_path: Path) -> float:
        """Offline fallback synthesis using Windows SAPI5 pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            full_text = " ... ".join([f"{t.speaker} says: {t.text}" for t in turns])
            engine.save_to_file(full_text, str(output_path))
            engine.runAndWait()
            
            total_words = sum(len(t.text.split()) for t in turns)
            return (total_words / 2.3) + (len(turns) * 0.35)
        except Exception as e:
            logger.error(f"pyttsx3 fallback synthesis failed: {e}")
            with open(output_path, "wb") as f:
                f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
            return 5.0

    def synthesize_podcast(self, topic: str, turns: List[DialogueTurn], sources: List[str] = None) -> PodcastEpisode:
        """Synthesize the complete podcast audio and save episode metadata."""
        podcast_id = f"podcast_{uuid.uuid4().hex[:10]}"
        audio_filename = f"{podcast_id}.mp3"
        audio_path = PODCAST_STORAGE_DIR / audio_filename

        logger.info(f"Synthesizing dual-voice audio for podcast '{topic}' ({len(turns)} turns) -> {audio_filename}")
        
        try:
            # Check if event loop is already active
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    total_duration = pool.submit(lambda: asyncio.run(self._synthesize_edge_tts(turns, audio_path))).result()
            else:
                total_duration = asyncio.run(self._synthesize_edge_tts(turns, audio_path))
        except Exception as e:
            logger.warning(f"edge-tts failed ({e}), falling back to pyttsx3 SAPI5...")
            total_duration = self._synthesize_pyttsx3_fallback(turns, audio_path)

        episode = PodcastEpisode(
            id=podcast_id,
            title=f"Deep Dive: {topic}",
            topic=topic,
            created_at=time.time(),
            total_duration_s=round(total_duration, 2),
            turns=[asdict(t) for t in turns],
            audio_filename=audio_filename,
            sources=sources or [],
        )

        meta_path = PODCAST_STORAGE_DIR / f"{podcast_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(asdict(episode), f, indent=2, ensure_ascii=False)

        logger.info(f"Podcast generated successfully: {podcast_id} (~{episode.total_duration_s}s)")
        return episode

    def create_podcast_from_topic(self, topic: str, context: Optional[str] = None, num_turns: int = 8) -> PodcastEpisode:
        """End-to-end pipeline: retrieve -> generate dialogue -> synthesize dual-voice audio."""
        turns, sources = self.generate_script(topic=topic, context=context, num_turns=num_turns)
        return self.synthesize_podcast(topic=topic, turns=turns, sources=sources)

    def list_episodes(self) -> List[Dict[str, Any]]:
        """List all available podcast episodes sorted by creation date."""
        episodes = []
        for file in PODCAST_STORAGE_DIR.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    episodes.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to read podcast metadata {file}: {e}")
                
        episodes.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return episodes

    def get_episode(self, podcast_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve podcast metadata by ID."""
        meta_path = PODCAST_STORAGE_DIR / f"{podcast_id}.json"
        if not meta_path.exists():
            return None
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
