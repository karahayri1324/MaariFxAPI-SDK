"""SSE (Server-Sent Events) parser for streaming responses."""

from __future__ import annotations

import json
from typing import AsyncIterator, Iterator

import httpx

from .models import StreamEvent, Usage


def _parse_event(event_type: str, data: str) -> StreamEvent | None:
    """Parse raw SSE fields into a StreamEvent."""
    if not data:
        return None

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        # Plain-text data -- treat as token content.
        return StreamEvent(type=event_type or "token", token=data)

    usage_raw = payload.get("usage")
    usage = Usage(**usage_raw) if isinstance(usage_raw, dict) else None

    return StreamEvent(
        type=event_type or payload.get("type", "unknown"),
        token=payload.get("token"),
        text=payload.get("text"),
        view_url=payload.get("view_url"),
        request_id=payload.get("requestId"),
        message=payload.get("message"),
        usage=usage,
    )


def iter_sse(response: httpx.Response) -> Iterator[StreamEvent]:
    """Iterate over SSE events from a synchronous httpx streaming response.

    Yields ``StreamEvent`` objects as they arrive.
    """
    event_type = ""
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        line = raw_line.rstrip("\n").rstrip("\r")

        if not line:
            # Blank line signals end of an event block.
            if data_lines:
                data = "\n".join(data_lines)
                event = _parse_event(event_type, data)
                if event is not None:
                    yield event
            event_type = ""
            data_lines = []
            continue

        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
        # Ignore comments (lines starting with ':') and other fields.


async def aiter_sse(response: httpx.Response) -> AsyncIterator[StreamEvent]:
    """Iterate over SSE events from an asynchronous httpx streaming response.

    Yields ``StreamEvent`` objects as they arrive.
    """
    event_type = ""
    data_lines: list[str] = []

    async for raw_line in response.aiter_lines():
        line = raw_line.rstrip("\n").rstrip("\r")

        if not line:
            if data_lines:
                data = "\n".join(data_lines)
                event = _parse_event(event_type, data)
                if event is not None:
                    yield event
            event_type = ""
            data_lines = []
            continue

        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())
