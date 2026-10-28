from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from .run_store import SQLiteRunStore

_GENERATED = {
    ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", "artifacts", "eval_runs", "dist", "build",
}
_PRIVATE = {
    ".git", ".ssh", ".aws", ".codex", ".agents", "credentials", "credentials.json",
    ".npmrc", ".pypirc", ".netrc", ".git-credentials", "id_rsa", "id_ed25519",
    "secrets.json", "secrets.yaml", "secrets.yml",
}
MAX_FILES = 10000
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()


def _linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)
    )


def _path(root: Path, name: str) -> Path:
    if not root.is_dir() or _linked(root):
        raise ValueError("Workspace root must be an ordinary directory")
    rel = PurePosixPath(name)
    if not name or rel.is_absolute() or str(rel) != name or any(
        part in {".", ".."} or ":" in part or "\\" in part
        or any(ord(char) < 32 for char in part) for part in rel.parts
    ):
        raise ValueError("Unsafe workspace path")
    path = root
    for index, part in enumerate(rel.parts):
        path = path / part
        if path.exists() or path.is_symlink():
            if _linked(path):
                raise ValueError(f"Links/reparse points are not supported: {name}")
            if index < len(rel.parts) - 1 and not path.is_dir():
                raise ValueError(f"Parent path is not a directory: {name}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes workspace")
    return path


def _private(name: str) -> bool:
    lower = name.lower()
    return lower in _PRIVATE or (lower.startswith(".env") and lower != ".env.example") or lower.endswith(
        (".pem", ".key", ".p12", ".pfx")
    )


def _scan(root: Path, *, source: bool = False) -> dict[str, dict[str, Any]]:
    if not root.is_dir() or _linked(root):
        raise ValueError("Workspace root must be an ordinary directory")
    result: dict[str, dict[str, Any]] = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        for name in list(dirs):
            if name in _GENERATED or (source and _private(name)):
                dirs.remove(name)
            elif _private(name) or _linked(parent / name):
                raise ValueError(f"Protected directory or link: {name}")
        for name in sorted(files):
            if name.endswith((".pyc", ".jsonl")) or name.startswith((".coverage",)) or ".sqlite3" in name:
                continue
            if _private(name):
                if source:
                    continue
                raise ValueError(f"Protected file: {name}")
            path = parent / name
            rel = path.relative_to(root).as_posix()
            _path(root, rel)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise ValueError(f"Unsupported or oversized file: {rel}")
            content = path.read_bytes()
            total += len(content)
            if len(result) >= MAX_FILES or total > MAX_TOTAL_BYTES or len(content) > MAX_FILE_BYTES:
                raise ValueError("Workspace copy limit exceeded")
            result[rel] = {"sha256": _digest(content), "mode": stat.S_IMODE(info.st_mode)}
    return result


def _atomic(path: Path, content: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _text(content: bytes) -> str:
    if b"\x00" in content:
        raise ValueError("Binary changes are not supported by text review")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Only UTF-8 text changes can be reviewed") from exc
    if any((ord(char) < 32 and char not in "\t\n\r") or 127 <= ord(char) <= 159 for char in text):
        raise ValueError("Terminal control characters are not supported by text review")
    return text


class WorkspaceSession:
    """Local copy/review/apply lifecycle, not an OS security sandbox."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.metadata = json.loads((self.path / "session.json").read_text(encoding="utf-8"))
        if self.metadata.get("version") != 1:
            raise ValueError("Unsupported workspace session version")
        self.source = Path(self.metadata["source"])
        if not self.source.is_absolute() or self.path.is_relative_to(self.source) or self.source.is_relative_to(self.path):
            raise ValueError("Session must be outside its source workspace")
        self.workspace = self.path / "workspace"
        self.baseline = self.path / "baseline"
        self.operations = SQLiteRunStore(self.path / "operations.sqlite3")
        self.source_operations = SQLiteRunStore(
            Path(tempfile.gettempdir()) / "mini-agent-workspace-locks" /
            (_digest(str(self.source).casefold().encode()) + ".sqlite3")
        )

    @classmethod
    def create(cls, source: Path, path: Path) -> WorkspaceSession:
        source, path = source.resolve(), path.resolve()
        if path.is_relative_to(source) or source.is_relative_to(path):
            raise ValueError("Session and source must be separate, non-nested directories")
        files = _scan(source, source=True)
        path.mkdir(parents=True, exist_ok=False)
        for folder in ("workspace", "baseline"):
            (path / folder).mkdir()
            for name, info in files.items():
                content = _path(source, name).read_bytes()
                if _digest(content) != info["sha256"]:
                    raise ValueError("Source changed during workspace creation; use a new session")
                _atomic(_path(path / folder, name), content, info["mode"])
        _atomic(path / "session.json", _json({"version": 1, "source": str(source), "files": files}))
        return cls(path)

    def _check_baseline(self) -> None:
        if _scan(self.baseline) != self.metadata["files"]:
            raise ValueError("Baseline changed; session cannot be trusted")
        if _linked(self.source):
            raise ValueError("Source root became a link")

    def changes(self) -> dict[str, Any]:
        self._check_baseline()
        current = _scan(self.workspace)
        entries = []
        diff = []
        for name in sorted(self.metadata["files"].keys() | current.keys()):
            before = self.metadata["files"].get(name)
            after = current.get(name)
            if before == after:
                continue
            if before and after and before["mode"] != after["mode"]:
                raise ValueError("File permission changes are not supported")
            old = _path(self.baseline, name).read_bytes() if before else b""
            new = _path(self.workspace, name).read_bytes() if after else b""
            if (before and _digest(old) != before["sha256"]) or (
                after and _digest(new) != after["sha256"]
            ):
                raise ValueError("Files changed during review")
            old_text, new_text = _text(old), _text(new)
            entries.append({
                "path": name, "before": before, "after": after,
                "content": base64.b64encode(new).decode() if after else None,
            })
            diff.append(f"# {json.dumps(name)}: {before and before['sha256']} -> {after and after['sha256']}\n")
            for line in difflib.unified_diff(
                old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                fromfile=json.dumps("a/" + name) if before else "/dev/null",
                tofile=json.dumps("b/" + name) if after else "/dev/null",
            ):
                diff.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
        payload = {"version": 1, "source": str(self.source), "entries": entries, "patch": "".join(diff)}
        return {**payload, "id": _digest(_json(payload))}

    def review(self) -> dict[str, Any]:
        with self.operations.lock("workspace"):
            self.ensure_available()
            review = self.changes()
            _atomic(self.path / "review.json", _json(review))
            _atomic(self.path / "review.patch", review["patch"].encode("utf-8"))
            return review

    def ensure_available(self) -> None:
        journal = self.path / "application.json"
        if journal.exists():
            state = json.loads(journal.read_text(encoding="utf-8"))
            if state["status"] != "rolled_back":
                raise ValueError("Session already applied or interrupted; inspect application.json/recover")

    def _matches(self, name: str, expected: dict[str, Any] | None) -> bool:
        path = _path(self.source, name)
        if not expected:
            return not path.exists()
        return path.is_file() and _digest(path.read_bytes()) == expected["sha256"] and (
            stat.S_IMODE(path.stat().st_mode) == expected["mode"]
        )

    def _write_entry(self, entry: dict[str, Any], *, restore: bool = False) -> None:
        target = _path(self.source, entry["path"])
        info = entry["before"] if restore else entry["after"]
        if info is None:
            target.unlink(missing_ok=True)
        else:
            content = (_path(self.baseline, entry["path"]).read_bytes() if restore
                       else base64.b64decode(entry["content"], validate=True))
            _atomic(target, content, info["mode"])

    def apply(self, review_id: str, approve: Callable[[str], bool]) -> None:
        with self.operations.lock("workspace"), self.source_operations.lock("apply"):
            self.ensure_available()
            review = json.loads((self.path / "review.json").read_text(encoding="utf-8"))
            if review != self.changes() or review["id"] != review_id or (
                (self.path / "review.patch").read_bytes() != review["patch"].encode("utf-8")
            ):
                raise ValueError("Review changed or stale; generate and inspect a new review")
            if not review["entries"]:
                raise ValueError("No changes to apply")
            for entry in review["entries"]:
                if not self._matches(entry["path"], entry["before"]):
                    raise ValueError(f"Host conflict: {entry['path']}")
            if approve(review_id) is not True:
                raise ValueError("Human approval declined")
            # Recheck after human review; do not hold stale pre-approval assumptions.
            if review != self.changes():
                raise ValueError("Workspace changed during approval")
            for entry in review["entries"]:
                if not self._matches(entry["path"], entry["before"]):
                    raise ValueError(f"Host conflict: {entry['path']}")
            journal = {"status": "applying", "review": review}
            _atomic(self.path / "application.json", _json(journal))
            try:
                for entry in review["entries"]:
                    if not self._matches(entry["path"], entry["before"]):
                        raise ValueError(f"Host conflict: {entry['path']}")
                    self._write_entry(entry)
            except Exception:
                self._rollback(journal)
                raise
            journal["status"] = "applied"
            _atomic(self.path / "application.json", _json(journal))

    def _rollback(self, journal: dict[str, Any]) -> None:
        entries = journal["review"]["entries"]
        for entry in entries:
            if not self._matches(entry["path"], entry["before"]) and not self._matches(
                entry["path"], entry["after"]
            ):
                raise ValueError(f"Rollback conflict; inspect manually: {entry['path']}")
        for entry in reversed(entries):
            if not self._matches(entry["path"], entry["before"]):
                self._write_entry(entry, restore=True)
        journal["status"] = "rolled_back"
        _atomic(self.path / "application.json", _json(journal))

    def recover(self, approve: Callable[[str], bool]) -> None:
        with self.operations.lock("workspace"), self.source_operations.lock("apply"):
            self._check_baseline()
            journal = json.loads((self.path / "application.json").read_text(encoding="utf-8"))
            payload = journal["review"].copy()
            review_id = payload.pop("id")
            if _digest(_json(payload)) != review_id or payload["source"] != str(self.source):
                raise ValueError("Invalid recovery journal")
            if journal["status"] != "applying":
                raise ValueError("Only interrupted applications can be recovered")
            if approve(review_id) is not True:
                raise ValueError("Human approval declined")
            self._rollback(journal)
