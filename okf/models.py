"""
OKF Data Models conforming to OKF v0.2 specification.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Concept:
    """Represents an OKF Concept file."""
    id: str                 # path relative to bundle root without .md (e.g. 'operating-systems/paging')
    meta: Dict[str, Any]    # YAML frontmatter; unknown keys must be preserved
    body: str               # Markdown content body
    file_path: Optional[str] = None

    @property
    def title(self) -> str:
        return self.meta.get("title", self.id.split("/")[-1].replace("-", " ").title())

    @property
    def description(self) -> str:
        return self.meta.get("description", "")

    @property
    def concept_type(self) -> str:
        return self.meta.get("type", "Concept")

    @property
    def status(self) -> str:
        # Per spec: absent status defaults to 'stable'
        return self.meta.get("status", "stable")

    @property
    def stale_after(self) -> Optional[str]:
        return self.meta.get("stale_after")

    @property
    def sources(self) -> List[Dict[str, Any]]:
        srcs = self.meta.get("sources", [])
        if isinstance(srcs, list):
            return srcs
        return []

    @property
    def verified(self) -> List[Dict[str, Any]]:
        v = self.meta.get("verified", [])
        if isinstance(v, dict):
            return [v]
        elif isinstance(v, list):
            return v
        return []
