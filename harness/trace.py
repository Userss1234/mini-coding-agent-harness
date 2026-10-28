from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .redaction import redact


@dataclass
class TraceEvent:
    event: str
    timestamp: str
    data: dict[str, Any]


class TraceLogger:
    """Append-only JSONL trace for agent and tool activity."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **data: Any) -> None:
        item = TraceEvent(
            event=event,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=redact(data),
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(redact(asdict(item)), ensure_ascii=False,
                                default=lambda value: redact(str(value))) + "\n")


def preview(value: Any, limit: int = 1200) -> str:
    text = str(redact(value))
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text) - limit} more chars)"

