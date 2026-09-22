"""
Topic extractor (Phase 6 wiring helper).
Maps a user question to a short <=3-word topic label for LearningMemoryStore.

Strategy:
  1. LLM call (temperature 0) when Ollama is available — best quality.
  2. Rule-based fallback: strip question stopwords, keep first meaningful words.
"""

import re
from typing import Optional

_STOPWORDS = {
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "can", "could", "should", "would", "will", "shall",
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "that", "this",
    "these", "those", "it", "its", "of", "in", "on", "at", "to", "for", "from",
    "with", "about", "into", "over", "after", "before", "between",
    "please", "explain", "tell", "give", "show", "me", "my", "i", "you",
    "your", "we", "our", "us", "there", "here", "so", "as", "by", "up", "down",
    "define", "definition", "meaning", "describe", "summarize", "summary",
    "concept", "idea", "works", "work", "working", "help", "need", "want",
    "chapter", "page", "notes", "document", "documents", "file", "files",
    "upload", "uploaded", "read", "reading", "based",
}

_SYSTEM = (
    "You extract a short topic label from a student question. "
    "Reply with EXACTLY 2-4 lowercase words, no punctuation, no quotes. "
    "Example: 'How does memory paging work?' -> 'memory paging'"
)


def _rule_based(query: str) -> str:
    words = re.findall(r"[a-z0-9]+", query.lower())
    kept = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    if not kept:
        kept = words[:3] or ["general"]
    label = " ".join(kept[:3])
    return label.strip() or "general"


def extract(query: str, ollama_client=None) -> str:
    """Return a short topic label for memory tracking."""
    if ollama_client is not None:
        try:
            raw = ollama_client.generate(
                prompt=f'Question: "{query.strip()}"\nTopic label:',
                system_prompt=_SYSTEM,
                temperature=0.0,
                max_tokens=16,
            )
            label = raw.strip().strip('"\'`.').lower()
            label = re.sub(r"\s+", " ", label)
            if label and len(label) <= 60 and "\n" not in label:
                return label
        except Exception:
            pass
    return _rule_based(query)


def extract_optional(query: str) -> Optional[str]:
    """Convenience: always returns a non-empty label."""
    return extract(query) or "general"
