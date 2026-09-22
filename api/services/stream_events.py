"""
SSE event helpers for MentorOS streaming responses (Phase 9).
"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def event(name: str, data: Any) -> ServerSentEvent:
    """Build a named SSE event with JSON payload."""
    return ServerSentEvent(data=json.dumps(data, ensure_ascii=False, default=str), event=name)


def stage_event(stage: str) -> ServerSentEvent:
    return event("stage", {"stage": stage})
