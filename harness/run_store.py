from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

SCHEMA_VERSION = 1
REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization|credential)")
_INLINE_SECRET = re.compile(
    r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;\"'}]+"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_TOKEN_METRICS = {
    "max_input_tokens", "summary_tokens", "before_estimated_tokens", "after_estimated_tokens",
}


def redact(value: Any) -> Any:
    """Sanitize durable state; intentionally independent from live model messages."""
    if isinstance(value, dict):
        return {
            str(key): REDACTED if (
                _SECRET_KEY.search(str(key))
                and not (key in _TOKEN_METRICS and isinstance(item, int) and not isinstance(item, bool))
            ) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        for key, secret in os.environ.items():
            if _SECRET_KEY.search(key) and len(secret) >= 8:
                value = value.replace(secret, REDACTED)
        value = _BEARER.sub("Bearer " + REDACTED, value)
        return _INLINE_SECRET.sub(lambda match: match[1] + REDACTED, value)
    return value


class RunStore(Protocol):
    def lock(self, run_id: str) -> AbstractContextManager[None]: ...
    def create(self, run_id: str, state: dict[str, Any]) -> None: ...
    def load(self, run_id: str) -> dict[str, Any]: ...
    def save(self, run_id: str, state: dict[str, Any]) -> None: ...
    def plan(self, run_id: str, state: dict[str, Any], calls: list[dict[str, Any]]) -> None: ...
    def calls(self, run_id: str) -> list[dict[str, Any]]: ...
    def start_call(self, run_id: str, call_id: str) -> None: ...
    def complete_call(
        self, run_id: str, call_id: str, result: dict[str, Any], state: dict[str, Any]
    ) -> None: ...


def new_run_id() -> str:
    return uuid4().hex


class SQLiteRunStore:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, SCHEMA_VERSION}:
                raise ValueError(f"Unsupported run database schema: {version}")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    state TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    state TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tool_calls (
                    run_id TEXT NOT NULL REFERENCES runs(id), call_id TEXT NOT NULL,
                    name TEXT NOT NULL, arguments TEXT NOT NULL,
                    status TEXT NOT NULL, result TEXT,
                    PRIMARY KEY (run_id, call_id)
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, path TEXT NOT NULL,
                    PRIMARY KEY (run_id, kind, path)
                );
            """)
            db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA synchronous = FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def lock(self, run_id: str) -> Iterator[None]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
            raise ValueError("Invalid run ID")
        lock_dir = self.path.parent / (self.path.name + ".locks")
        lock_dir.mkdir(exist_ok=True)
        db = sqlite3.connect(lock_dir / (run_id + ".sqlite3"), timeout=0.1)
        try:
            # A separate database holds an OS-released process lock across checkpoints.
            db.execute("CREATE TABLE IF NOT EXISTS owner (id INTEGER)")
            db.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as exc:
            db.close()
            raise RuntimeError(f"Run {run_id} is already active") from exc
        try:
            yield
        finally:
            db.rollback()
            db.close()

    def create(self, run_id: str, state: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?)",
                (run_id, state["status"], self._json(state), self._now()),
            )
            self._checkpoint(db, run_id, state)
            for kind, path in state.get("artifacts", {}).items():
                db.execute(
                    "INSERT INTO artifacts VALUES (?, ?, ?)",
                    (run_id, kind, str(redact(str(path)))),
                )

    def load(self, run_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown run: {run_id}")
        return json.loads(row[0])

    def save(self, run_id: str, state: dict[str, Any]) -> None:
        with self._connect() as db:
            self._checkpoint(db, run_id, state)

    def _checkpoint(
        self, db: sqlite3.Connection, run_id: str, state: dict[str, Any]
    ) -> None:
        payload = self._json(state)
        now = self._now()
        changed = db.execute(
            "UPDATE runs SET state = ?, status = ?, updated_at = ? WHERE id = ?",
            (payload, state["status"], now, run_id),
        ).rowcount
        if changed != 1:
            raise ValueError(f"Unknown run: {run_id}")
        db.execute(
            "INSERT INTO checkpoints(run_id, state, created_at) VALUES (?, ?, ?)",
            (run_id, payload, now),
        )

    def plan(
        self, run_id: str, state: dict[str, Any], calls: list[dict[str, Any]]
    ) -> None:
        with self._connect() as db:
            for call in calls:
                if any(redact(call[key]) != call[key] for key in ("id", "name")):
                    raise ValueError("Tool identifiers cannot contain credentials")
                db.execute(
                    "INSERT INTO tool_calls VALUES (?, ?, ?, ?, 'pending', NULL)",
                    (run_id, call["id"], call["name"], self._json(call["input"])),
                )
            self._checkpoint(db, run_id, state)

    def calls(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT call_id, name, arguments, status, result FROM tool_calls "
                "WHERE run_id = ? ORDER BY rowid", (run_id,),
            ).fetchall()
        return [
            {"id": row[0], "name": row[1], "input": json.loads(row[2]),
             "status": row[3], "result": json.loads(row[4]) if row[4] else None}
            for row in rows
        ]

    def start_call(self, run_id: str, call_id: str) -> None:
        with self._connect() as db:
            changed = db.execute(
                "UPDATE tool_calls SET status = 'started' "
                "WHERE run_id = ? AND call_id = ? AND status = 'pending'",
                (run_id, call_id),
            ).rowcount
            if changed != 1:
                raise RuntimeError("Tool call is not pending; refusing duplicate execution")

    def complete_call(
        self, run_id: str, call_id: str, result: dict[str, Any], state: dict[str, Any]
    ) -> None:
        with self._connect() as db:
            changed = db.execute(
                "UPDATE tool_calls SET status = 'completed', result = ? "
                "WHERE run_id = ? AND call_id = ? AND status = 'started'",
                (self._json(result), run_id, call_id),
            ).rowcount
            if changed != 1:
                raise RuntimeError("Tool call is not started")
            self._checkpoint(db, run_id, state)

    def reconcile(self, run_id: str, call_id: str, content: str, *, is_error: bool) -> None:
        with self.lock(run_id):
            state = self.load(run_id)
            state["status"] = "paused"
            state["reconciliation"] = {"call_id": call_id, "source": "operator"}
            self.complete_call(
                run_id, call_id,
                {"type": "tool_result", "tool_use_id": call_id,
                 "content": content, "is_error": is_error},
                state,
            )

    def list_runs(self) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, status, updated_at FROM runs ORDER BY updated_at DESC"
            ).fetchall()
        return [{"id": row[0], "status": row[1], "updated_at": row[2]} for row in rows]

    def export(self, run_id: str, output: Path) -> None:
        with self.lock(run_id):
            self._export(run_id, output)

    def _export(self, run_id: str, output: Path) -> None:
        if output.resolve() == self.path:
            raise ValueError("Export cannot overwrite the database")
        with self._connect() as db:
            state = self.load(run_id)
            rows = db.execute(
                "SELECT sequence, state, created_at FROM checkpoints "
                "WHERE run_id = ? ORDER BY sequence", (run_id,),
            ).fetchall()
            artifacts = db.execute(
                "SELECT kind, path FROM artifacts WHERE run_id = ?", (run_id,),
            ).fetchall()
        events = [{"event": "run", "run_id": run_id, "state": state}]
        events.extend({"event": "checkpoint", "sequence": row[0],
                       "state": json.loads(row[1]), "timestamp": row[2]} for row in rows)
        events.extend({"event": "tool_call", **call} for call in self.calls(run_id))
        events.extend({"event": "artifact", "kind": kind, "path": path}
                      for kind, path in artifacts)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(self._json(event) for event in events) + "\n", encoding="utf-8")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(redact(value), ensure_ascii=False, allow_nan=False)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
