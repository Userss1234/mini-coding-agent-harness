from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


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
            data=data,
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(item), ensure_ascii=False, default=str) + "\n")


def preview(value: Any, limit: int = 1200) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text) - limit} more chars)"

