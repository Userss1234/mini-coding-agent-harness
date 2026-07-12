from __future__ import annotations

from dataclasses import dataclass
import difflib
import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import shutil
import shlex
import sys
import subprocess
import time
from typing import Any, Callable

from .retrieval import (
    build_workspace_index,
    explain_retrieval_plan,
    format_index_summary,
    format_retrieval_explanation,
    format_search_results,
    search_workspace,
    tokenize_query,
)
from .trace import TraceLogger, preview


@dataclass
class ToolResult:
    ok: bool
    output: str
    metadata: dict[str, Any] | None = None


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., ToolResult]
    risk: str = "read"


class ToolRegistry:
    def __init__(
        self,
        workspace: Path,
        trace: TraceLogger,
        allow_write: bool = False,
        max_tool_retries: int = 1,
        retry_delay: float = 0.05,
    ):
        self.workspace = workspace.resolve()
        self.trace = trace
        self.allow_write = allow_write
        self.max_tool_retries = max_tool_retries
        self.retry_delay = retry_delay
        self._tools: dict[str, Tool] = {}
        self.metrics: dict[str, int] = {
            "read_cache_hits": 0,
            "read_cache_misses": 0,
            "read_cache_invalidations": 0,
        }
        self.todos: list[dict[str, str]] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            result = ToolResult(False, f"Unknown tool: {name}")
            self.trace.log("tool_call", tool=name, args=kwargs, ok=False, output=result.output)
            return result

        permission = self._permission_decision(tool, kwargs)
        if permission != "allow":
            result = ToolResult(False, f"Blocked by permission policy: {permission}")
            self.trace.log(
                "tool_call",
                tool=name,
                args=kwargs,
                risk=tool.risk,
                permission=permission,
                ok=False,
                output=result.output,
            )
            return result

        result = self._call_handler_with_retries(tool, kwargs)

        self.trace.log(
            "tool_call",
            tool=name,
            args=kwargs,
            risk=tool.risk,
            permission=permission,
            ok=result.ok,
            output=preview(result.output),
            metadata=result.metadata or {},
        )
        return result

    def _call_handler_with_retries(self, tool: Tool, kwargs: dict[str, Any]) -> ToolResult:
        attempt = 0
        while True:
            try:
                return tool.handler(**kwargs)
            except Exception as exc:
                if not self._should_retry_tool(tool, exc, attempt):
                    return ToolResult(False, f"{type(exc).__name__}: {exc}")
                delay = self.retry_delay * (2 ** attempt)
                self.trace.log(
                    "tool_retry",
                    tool=tool.name,
                    risk=tool.risk,
                    attempt=attempt + 1,
                    max_retries=self.max_tool_retries,
                    delay_seconds=delay,
                    error=f"{type(exc).__name__}: {exc}",
                )
                time.sleep(delay)
                attempt += 1

    def _should_retry_tool(self, tool: Tool, exc: Exception, attempt: int) -> bool:
        if attempt >= self.max_tool_retries:
            return False
        if tool.risk == "write":
            return False
        return is_transient_exception(exc)

    def _permission_decision(self, tool: Tool, kwargs: dict[str, Any]) -> str:
        if tool.name in {"write_file", "edit_file", "delete_file"}:
            raw_path = kwargs.get("path")
            if raw_path is None:
                return "blocked_missing_path"
            try:
                target = safe_path(self.workspace, str(raw_path))
            except ValueError:
                return "blocked_path_escape"
            if tool.name == "delete_file" and kwargs.get("confirm") is not True:
                return "blocked_delete_requires_confirmation"
            if target.exists() and not self.allow_write:
                return "blocked_overwrite_requires_allow_write"
        if tool.name == "save_memory":
            raw_name = kwargs.get("memory_name")
            if raw_name is None:
                return "blocked_missing_name"
            slug = _memory_slug(str(raw_name))
            if slug:
                target = self.workspace / "skills" / f"{slug}.md"
                if target.exists() and not self.allow_write:
                    return "blocked_overwrite_requires_allow_write"
        if tool.name == "shell":
            return shell_permission_decision(str(kwargs.get("command", "")))
        return "allow"


SHELL_OPERATOR_MARKERS = ["&&", "||", ";", "|", ">", "<", "\n", "\r"]

ALLOWED_SHELL_COMMANDS = {
    "cat",
    "dir",
    "echo",
    "findstr",
    "get-childitem",
    "ls",
    "pwd",
    "python",
    "python.exe",
    "py",
    "py.exe",
    "pytest",
    "pytest.exe",
    "type",
    Path(sys.executable).name.lower(),
}

READ_ONLY_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "rev-parse",
    "show",
    "status",
    "ls-files",
}

CONTEXT_PACK_IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "artifacts",
    "eval_runs",
}


def safe_path(workspace: Path, path: str | Path) -> Path:
    candidate = (workspace / path).resolve()
    if not candidate.is_relative_to(workspace):
        raise ValueError(f"Path escapes workspace: {path}")
    return candidate


def is_transient_exception(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    transient_markers = [
        "timeout",
        "temporarily",
        "connection",
        "rate limit",
        "ratelimit",
        "overloaded",
        "service unavailable",
        "502",
        "503",
        "504",
    ]
    return any(marker in name or marker in text for marker in transient_markers)


def shell_permission_decision(command: str) -> str:
    tokens = parse_shell_tokens(command)
    if not tokens:
        return "blocked_empty_shell"
    lowered = command.lower()
    if any(marker in lowered for marker in SHELL_OPERATOR_MARKERS):
        return "blocked_shell_operator"
    if any(token.lower() in {"--force", "-f", "/f"} for token in tokens):
        return "blocked_force_flag"

    executable = Path(tokens[0]).name.lower()
    if executable == "git":
        return git_shell_permission_decision(tokens)

    if executable not in ALLOWED_SHELL_COMMANDS:
        return "blocked_shell_not_allowlisted"
    return "allow"


def parse_shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


def git_shell_permission_decision(tokens: list[str]) -> str:
    if len(tokens) < 2:
        return "blocked_git_missing_subcommand"
    if any(token.lower().startswith("--force") for token in tokens):
        return "blocked_force_flag"

    subcommand = tokens[1].lower()
    if subcommand not in READ_ONLY_GIT_SUBCOMMANDS:
        return "blocked_git_not_allowlisted"
    if subcommand == "branch" and any(token.startswith("-") for token in tokens[2:]):
        return "blocked_git_branch_mutation"
    return "allow"


def _resolve_pytest_target(workspace: Path, target: str | None) -> str:
    if target is None or target == "auto":
        tests_dir = workspace / "tests"
        if tests_dir.exists() and _has_pytest_files(tests_dir):
            return "tests"
        return ""
    return str(target)


def _has_pytest_files(path: Path) -> bool:
    return any(path.rglob("test_*.py")) or any(path.rglob("*_test.py"))


def _clear_pycache_dirs(workspace: Path) -> int:
    removed = 0
    for path in workspace.rglob("__pycache__"):
        if path.is_dir() and path.resolve().is_relative_to(workspace):
            shutil.rmtree(path)
            removed += 1
    return removed


def _shell_list_directory(workspace: Path, tokens: list[str]) -> ToolResult:
    path_arg = "."
    for token in tokens[1:]:
        if token.startswith("-") or token.startswith("/"):
            continue
        path_arg = token
        break
    try:
        target = safe_path(workspace, path_arg)
    except ValueError as exc:
        return ToolResult(False, str(exc), {"argv": tokens, "shell": False, "builtin": "list_directory"})
    if not target.exists():
        return ToolResult(False, f"Path not found: {path_arg}", {"argv": tokens, "shell": False, "builtin": "list_directory"})
    if target.is_file():
        return ToolResult(True, target.name, {"argv": tokens, "shell": False, "builtin": "list_directory", "count": 1})

    entries = []
    for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        name = child.name + ("/" if child.is_dir() else "")
        entries.append(name)
    return ToolResult(
        True,
        "\n".join(entries) or "(empty directory)",
        {"argv": tokens, "shell": False, "builtin": "list_directory", "count": len(entries)},
    )


def build_registry(
    workspace: Path,
    trace: TraceLogger,
    allow_write: bool = False,
    max_tool_retries: int = 1,
    retry_delay: float = 0.05,
    enable_context_pack: bool = True,
) -> ToolRegistry:
    registry = ToolRegistry(
        workspace,
        trace,
        allow_write=allow_write,
        max_tool_retries=max_tool_retries,
        retry_delay=retry_delay,
    )
    read_cache: dict[tuple[Any, ...], str] = {}

    def list_python_files(include_venv: bool = False) -> ToolResult:
        ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache", "eval_runs"}
        files: list[str] = []
        for path in workspace.rglob("*.py"):
            rel = path.relative_to(workspace)
            if not include_venv and any(part in ignored_parts for part in rel.parts):
                continue
            files.append(str(rel))
        files.sort()
        return ToolResult(True, "\n".join(files), {"count": len(files)})

    def read_file(
        path: str,
        limit: int | None = None,
        max_chars: int = 12000,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        target = safe_path(workspace, path)
        stat = target.stat()
        line_limit = int(limit) if limit is not None else None
        char_limit = int(max_chars)
        start = int(start_line) if start_line is not None else None
        end = int(end_line) if end_line is not None else None
        if start is not None and start < 1:
            return ToolResult(False, "start_line must be >= 1")
        if end is not None and end < 1:
            return ToolResult(False, "end_line must be >= 1")
        if start is not None and end is not None and end < start:
            return ToolResult(False, "end_line must be >= start_line")
        cache_key = (
            str(target),
            stat.st_mtime_ns,
            stat.st_size,
            line_limit or -1,
            char_limit,
            start or -1,
            end or -1,
        )
        if cache_key in read_cache:
            text = read_cache[cache_key]
            registry.metrics["read_cache_hits"] += 1
            return ToolResult(
                True,
                text,
                {
                    "path": str(target),
                    "chars": len(text),
                    "line_limit": line_limit,
                    "max_chars": char_limit,
                    "start_line": start,
                    "end_line": end,
                    "cache_hit": True,
                },
            )

        text = target.read_text(encoding="utf-8", errors="replace")
        original_lines = text.splitlines()
        original_line_count = len(original_lines)
        selected_lines = original_lines
        if start is not None or end is not None:
            start_index = (start or 1) - 1
            end_index = end if end is not None else len(original_lines)
            selected_lines = original_lines[start_index:end_index]
            text = "\n".join(selected_lines)
        if line_limit is not None and len(selected_lines) > line_limit:
            omitted = len(selected_lines) - line_limit
            text = "\n".join(selected_lines[:line_limit])
            text += f"\n... ({omitted} more lines)"
        if len(text) > char_limit:
            text = text[:char_limit] + f"\n... ({len(text) - char_limit} more chars)"
        read_cache[cache_key] = text
        registry.metrics["read_cache_misses"] += 1
        return ToolResult(
            True,
            text,
            {
                "path": str(target),
                "chars": len(text),
                "lines": original_line_count,
                "returned_lines": len(selected_lines),
                "line_limit": line_limit,
                "max_chars": char_limit,
                "start_line": start,
                "end_line": end,
                "cache_hit": False,
            },
        )

    def write_text_with_diff(path: str, content: str) -> ToolResult:
        target = safe_path(workspace, path)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        invalidated = 0
        for key in list(read_cache):
            if key[0] == str(target):
                del read_cache[key]
                invalidated += 1
        registry.metrics["read_cache_invalidations"] += invalidated
        diff = "\n".join(difflib.unified_diff(
            before.splitlines(),
            content.splitlines(),
            fromfile=f"{path} (before)",
            tofile=f"{path} (after)",
            lineterm="",
        ))
        diff_summary = _summarize_diff(diff)
        return ToolResult(
            True,
            f"Wrote {len(content)} chars to {path}",
            {
                "path": str(target),
                "before_chars": len(before),
                "after_chars": len(content),
                "cache_invalidations": invalidated,
                "diff_summary": diff_summary,
                "diff": preview(diff, 4000),
            },
        )

    def write_file(path: str, content: str) -> ToolResult:
        return write_text_with_diff(path, content)

    def edit_file(path: str, old_text: str, new_text: str) -> ToolResult:
        if not old_text:
            return ToolResult(False, "old_text must be non-empty")
        target = safe_path(workspace, path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        before = target.read_text(encoding="utf-8", errors="replace")
        matches = before.count(old_text)
        if matches != 1:
            return ToolResult(
                False,
                f"Expected old_text to appear exactly once in {path}, found {matches}",
                {"path": str(target), "matches": matches},
            )
        after = before.replace(old_text, new_text, 1)
        result = write_text_with_diff(path, after)
        metadata = result.metadata or {}
        metadata["edit"] = {
            "old_chars": len(old_text),
            "new_chars": len(new_text),
            "replacements": 1,
        }
        return ToolResult(result.ok, f"Edited {path}: replaced 1 occurrence", metadata)

    def delete_file(path: str, confirm: bool = False) -> ToolResult:
        target = safe_path(workspace, path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if target.is_dir():
            return ToolResult(False, f"Refusing to delete directory: {path}")
        before = target.read_text(encoding="utf-8", errors="replace")
        target.unlink()
        invalidated = 0
        for key in list(read_cache):
            if key[0] == str(target):
                del read_cache[key]
                invalidated += 1
        registry.metrics["read_cache_invalidations"] += invalidated
        return ToolResult(
            True,
            f"Deleted {path}",
            {
                "path": str(target),
                "before_chars": len(before),
                "confirm": confirm,
                "cache_invalidations": invalidated,
                "deleted_preview": preview(before, 1200),
            },
        )

    def cache_stats() -> ToolResult:
        hits = registry.metrics["read_cache_hits"]
        misses = registry.metrics["read_cache_misses"]
        invalidations = registry.metrics["read_cache_invalidations"]
        total = hits + misses
        hit_rate = (hits / total) if total else 0.0
        output = (
            f"read_cache_hits={hits}\n"
            f"read_cache_misses={misses}\n"
            f"read_cache_hit_rate={hit_rate:.2%}\n"
            f"read_cache_invalidations={invalidations}"
        )
        return ToolResult(
            True,
            output,
            {
                "read_cache_hits": hits,
                "read_cache_misses": misses,
                "read_cache_hit_rate": hit_rate,
                "read_cache_invalidations": invalidations,
            },
        )

    def context_pack(
        query: str,
        glob: str = "*.py",
        limit: int = 5,
        max_chars_per_file: int = 1200,
        window: int = 2,
    ) -> ToolResult:
        query_text = str(query).strip()
        if not query_text:
            return ToolResult(False, "query must be non-empty")
        tokens = tokenize_query(query_text)
        if not tokens:
            return ToolResult(False, "query must contain at least one searchable token")

        result = search_workspace(
            workspace=workspace,
            query=query_text,
            glob_pattern=str(glob or "*"),
            limit=max(int(limit), 0),
            chunk_lines=max((max(int(window), 0) * 2) + 1, 1),
            overlap=0,
            max_chars_per_chunk=max(int(max_chars_per_file), 120),
        )
        matches = result["matches"]
        output = _format_context_pack(query_text, matches)
        return ToolResult(
            True,
            output,
            {
                "query": query_text,
                "tokens": tokens,
                "glob": str(glob or "*"),
                "count": len(matches),
                "matches": matches,
                "index": result["index"],
                "retrieval": "local_chunk_lexical_scoring",
            },
        )

    def index_workspace(glob: str = "*", chunk_lines: int = 80, overlap: int = 10) -> ToolResult:
        index = build_workspace_index(
            workspace,
            glob_pattern=str(glob or "*"),
            chunk_lines=max(int(chunk_lines), 1),
            overlap=max(int(overlap), 0),
        )
        metadata = index.metadata()
        metadata["glob"] = str(glob or "*")
        metadata["retrieval"] = "local_chunk_lexical_scoring"
        return ToolResult(True, format_index_summary(index), metadata)

    def rag_search(
        query: str,
        glob: str = "*",
        limit: int = 5,
        chunk_lines: int = 80,
        overlap: int = 10,
        max_chars_per_chunk: int = 1200,
    ) -> ToolResult:
        query_text = str(query).strip()
        if not query_text:
            return ToolResult(False, "query must be non-empty")
        tokens = tokenize_query(query_text)
        if not tokens:
            return ToolResult(False, "query must contain at least one searchable token")
        result = search_workspace(
            workspace,
            query_text,
            glob_pattern=str(glob or "*"),
            limit=max(int(limit), 0),
            chunk_lines=max(int(chunk_lines), 1),
            overlap=max(int(overlap), 0),
            max_chars_per_chunk=max(int(max_chars_per_chunk), 120),
        )
        return ToolResult(
            True,
            format_search_results(result),
            {
                "query": query_text,
                "tokens": tokens,
                "glob": str(glob or "*"),
                "count": len(result["matches"]),
                "matches": result["matches"],
                "index": result["index"],
                "retrieval": result["retrieval"],
            },
        )

    def rag_explain(
        query: str,
        glob: str = "*",
        limit: int = 5,
        chunk_lines: int = 80,
        overlap: int = 10,
        read_window: int = 20,
        max_chars_per_chunk: int = 1200,
    ) -> ToolResult:
        query_text = str(query).strip()
        if not query_text:
            return ToolResult(False, "query must be non-empty")
        tokens = tokenize_query(query_text)
        if not tokens:
            return ToolResult(False, "query must contain at least one searchable token")
        result = explain_retrieval_plan(
            workspace,
            query_text,
            glob_pattern=str(glob or "*"),
            limit=max(int(limit), 0),
            chunk_lines=max(int(chunk_lines), 1),
            overlap=max(int(overlap), 0),
            read_window=max(int(read_window), 0),
            max_chars_per_chunk=max(int(max_chars_per_chunk), 120),
        )
        return ToolResult(
            True,
            format_retrieval_explanation(result),
            {
                "query": query_text,
                "tokens": tokens,
                "glob": str(glob or "*"),
                "count": len(result["matches"]),
                "matches": result["matches"],
                "read_plan": result["read_plan"],
                "index": result["index"],
                "retrieval": result["retrieval"],
            },
        )

    def compact_context(max_items: int = 20) -> ToolResult:
        trace_path = registry.trace.path
        if not trace_path.exists():
            return ToolResult(False, f"Trace file not found: {trace_path}")

        events: list[dict[str, Any]] = []
        parse_errors = 0
        for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                parse_errors += 1

        tool_counts: dict[str, int] = {}
        files_read: list[str] = []
        files_changed: list[str] = []
        failures: list[str] = []
        latest_todos: list[dict[str, str]] = []

        for event in events:
            if event.get("event") != "tool_call":
                continue
            data = event.get("data", {})
            tool_name = str(data.get("tool", "unknown"))
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            metadata = data.get("metadata") or {}
            args = data.get("args") or {}
            if tool_name == "todo_write":
                todos = metadata.get("todos")
                if isinstance(todos, list):
                    latest_todos = [
                        {
                            "task": str(item.get("task", "")),
                            "status": str(item.get("status", "pending")),
                        }
                        for item in todos
                        if isinstance(item, dict)
                    ]
            elif tool_name == "read_file":
                path = metadata.get("path") or args.get("path")
                _append_unique(files_read, _format_trace_path(registry.workspace, path))
            elif tool_name in {"write_file", "edit_file", "delete_file"}:
                path = metadata.get("path") or args.get("path")
                _append_unique(files_changed, _format_trace_path(registry.workspace, path))

            if not data.get("ok", False):
                first_line = str(data.get("output", "")).splitlines()[0] if data.get("output") else ""
                failures.append(f"{tool_name}: {first_line}")

        pending = [item for item in latest_todos if item.get("status") in {"pending", "in_progress"}]
        in_progress = [item for item in latest_todos if item.get("status") == "in_progress"]
        if in_progress:
            current_goal = in_progress[0]["task"]
        elif pending:
            current_goal = pending[0]["task"]
        elif latest_todos:
            current_goal = "All tracked todos completed."
        else:
            current_goal = "No todo plan recorded."

        next_step = pending[0]["task"] if pending else "No pending todos; review the result and choose the next task."
        output = _format_context_summary(
            event_count=len(events),
            tool_counts=tool_counts,
            current_goal=current_goal,
            next_step=next_step,
            files_read=files_read[:max_items],
            files_changed=files_changed[:max_items],
            failures=failures[:max_items],
            latest_todos=latest_todos[:max_items],
            parse_errors=parse_errors,
        )
        return ToolResult(
            True,
            output,
            {
                "event_count": len(events),
                "tool_call_count": sum(tool_counts.values()),
                "tool_counts": tool_counts,
                "files_read": files_read,
                "files_changed": files_changed,
                "failure_count": len(failures),
                "parse_errors": parse_errors,
                "current_goal": current_goal,
                "next_step": next_step,
            },
        )

    def collect_recovery_items(max_items: int = 20) -> tuple[list[dict[str, str]], int, int]:
        trace_path = registry.trace.path
        if not trace_path.exists():
            raise FileNotFoundError(f"Trace file not found: {trace_path}")

        failures: list[dict[str, Any]] = []
        parse_errors = 0
        for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            if event.get("event") != "tool_call":
                continue
            data = event.get("data", {})
            if data.get("ok", True):
                continue
            failures.append({
                "tool": str(data.get("tool", "unknown")),
                "output": str(data.get("output", "")),
                "metadata": data.get("metadata") or {},
                "permission": str(data.get("permission", "")),
            })

        recovery_items = [
            _build_recovery_item(item["tool"], item["output"], item["metadata"], item["permission"])
            for item in failures[:max_items]
        ]
        return recovery_items, len(failures), parse_errors

    def recover_errors(max_items: int = 20) -> ToolResult:
        try:
            recovery_items, failure_count, parse_errors = collect_recovery_items(max_items)
        except FileNotFoundError as exc:
            return ToolResult(False, str(exc))

        output = _format_recovery_report(recovery_items, failure_count=failure_count, parse_errors=parse_errors)
        return ToolResult(
            True,
            output,
            {
                "failure_count": failure_count,
                "parse_errors": parse_errors,
                "recoveries": recovery_items,
            },
        )

    def retry_plan(max_items: int = 20) -> ToolResult:
        try:
            recovery_items, failure_count, parse_errors = collect_recovery_items(max_items)
        except FileNotFoundError as exc:
            return ToolResult(False, str(exc))

        steps = [
            _build_retry_step(index, item)
            for index, item in enumerate(recovery_items, start=1)
        ]
        output = _format_retry_plan(steps, failure_count=failure_count, parse_errors=parse_errors)
        return ToolResult(
            True,
            output,
            {
                "failure_count": failure_count,
                "parse_errors": parse_errors,
                "steps": steps,
            },
        )

    def save_memory(memory_name: str, summary: str, trigger: str = "", steps: list[str] | str = "") -> ToolResult:
        slug = _memory_slug(memory_name)
        if not slug:
            return ToolResult(False, "Memory name must contain at least one letter or number")

        normalized_steps = _normalize_memory_steps(steps)
        content = _format_memory_markdown(
            name=memory_name,
            summary=summary,
            trigger=trigger,
            steps=normalized_steps,
        )
        result = write_text_with_diff(f"skills/{slug}.md", content)
        metadata = result.metadata or {}
        metadata["memory"] = {
            "name": memory_name,
            "slug": slug,
            "step_count": len(normalized_steps),
        }
        return ToolResult(result.ok, f"Saved memory skills/{slug}.md", metadata)

    def list_memories(query: str = "", limit: int = 20) -> ToolResult:
        memory_dir = workspace / "skills"
        if not memory_dir.exists():
            return ToolResult(True, "(no memories)", {"count": 0, "memories": []})

        query_text = str(query).strip()
        query_tokens = _memory_query_tokens(query_text)
        memories: list[dict[str, str | int]] = []
        for path in sorted(memory_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            title = first_markdown_heading(text) or path.stem
            score = _memory_relevance_score(query_tokens, path.stem, title, text)
            if query_tokens and score == 0:
                continue
            memories.append({
                "name": title,
                "path": str(path.relative_to(workspace)),
                "score": score,
            })

        if query_tokens:
            memories.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
        else:
            memories.sort(key=lambda item: str(item["path"]))
        limited = memories[:max(int(limit), 0)]
        if query_tokens:
            output = "\n".join(
                f"- `{item['path']}` (score {item['score']}): {item['name']}"
                for item in limited
            )
            empty_text = "(no matching memories)"
        else:
            output = "\n".join(f"- `{item['path']}`: {item['name']}" for item in limited)
            empty_text = "(no memories)"
        return ToolResult(
            True,
            output or empty_text,
            {
                "count": len(limited),
                "total_matches": len(memories),
                "query": query_text,
                "memories": limited,
            },
        )

    def read_memory(memory_name: str, max_chars: int = 12000) -> ToolResult:
        slugs = _memory_reference_slugs(memory_name)
        if not slugs:
            return ToolResult(False, "Memory name must contain at least one letter or number")

        target = None
        slug = slugs[0]
        for candidate_slug in slugs:
            candidate = workspace / "skills" / f"{candidate_slug}.md"
            if candidate.exists():
                slug = candidate_slug
                target = candidate
                break
        if target is None:
            return ToolResult(False, f"Memory not found: skills/{slug}.md", {"slug": slug})

        text = target.read_text(encoding="utf-8", errors="replace")
        char_limit = int(max_chars)
        if len(text) > char_limit:
            text = text[:char_limit] + f"\n... ({len(text) - char_limit} more chars)"
        return ToolResult(
            True,
            text,
            {
                "path": str(target.relative_to(workspace)),
                "slug": slug,
                "chars": len(text),
                "max_chars": char_limit,
            },
        )

    def todo_write(todos: list[dict[str, str]] | str) -> ToolResult:
        if isinstance(todos, str):
            normalized = [{"task": todos, "status": "pending"}]
        else:
            normalized = []
            for item in todos:
                task = str(item.get("task", "")).strip()
                if not task:
                    continue
                status = str(item.get("status", "pending")).strip().lower()
                if status not in {"pending", "in_progress", "completed"}:
                    status = "pending"
                normalized.append({"task": task, "status": status})
        is_initial_plan = not registry.todos
        quality = _check_todo_quality(normalized, is_initial_plan=is_initial_plan)
        registry.todos = normalized
        registry.trace.log("todo_quality", **quality)
        return ToolResult(
            True,
            f"Updated {len(normalized)} todo(s)",
            {"todos": normalized, "quality": quality},
        )

    def grep(pattern: str, glob: str = "*.py", limit: int = 80) -> ToolResult:
        matches: list[str] = []
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(workspace)
            if any(part in {".git", ".venv", "__pycache__", "eval_runs"} for part in rel.parts):
                continue
            if not fnmatch.fnmatch(str(rel), glob):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern.lower() in line.lower():
                    matches.append(f"{rel}:{lineno}: {line.strip()}")
                    if len(matches) >= limit:
                        return ToolResult(True, "\n".join(matches), {"truncated": True})
        return ToolResult(True, "\n".join(matches) if matches else "(no matches)")

    def permission_policy() -> ToolResult:
        metadata = {
            "workspace": str(workspace),
            "allow_write": registry.allow_write,
            "write_tools": ["write_file", "edit_file", "delete_file", "save_memory"],
            "delete_requires_confirmation": True,
            "path_scope": "workspace_only",
            "shell_false": True,
            "shell_operator_markers": SHELL_OPERATOR_MARKERS,
            "allowed_shell_commands": sorted(ALLOWED_SHELL_COMMANDS),
            "read_only_git_subcommands": sorted(READ_ONLY_GIT_SUBCOMMANDS),
            "os_sandbox": False,
        }
        lines = [
            "# Permission Policy",
            "",
            f"- Workspace root: {workspace}",
            f"- Write access: {'enabled' if registry.allow_write else 'existing files require allow_write'}",
            "- File paths are resolved inside the workspace; path escape attempts are blocked.",
            "- `delete_file` requires `confirm=true` and refuses directories.",
            "- Shell commands are tokenized with `shlex`, executed with `shell=False`, and shell operators are blocked.",
            f"- Allowed shell executables: {', '.join(metadata['allowed_shell_commands'])}",
            f"- Read-only Git subcommands: {', '.join(metadata['read_only_git_subcommands'])}",
            "- Force flags and mutating Git subcommands are blocked.",
            "- This is a harness permission policy, not an OS-level sandbox.",
        ]
        return ToolResult(True, "\n".join(lines), metadata)

    def shell(command: str, timeout: int = 60) -> ToolResult:
        tokens = parse_shell_tokens(command)
        if not tokens:
            return ToolResult(False, "Could not parse shell command", {"argv": [], "shell": False})
        executable = Path(tokens[0]).name.lower()
        if executable in {"ls", "dir"}:
            return _shell_list_directory(workspace, tokens)
        try:
            completed = subprocess.run(
                tokens,
                cwd=workspace,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            return ToolResult(False, f"Executable not found: {tokens[0]}", {"argv": tokens, "shell": False, "error": str(exc)})
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        return ToolResult(
            completed.returncode == 0,
            output or "(no output)",
            {"returncode": completed.returncode, "argv": tokens, "shell": False},
        )

    def run_py_compile() -> ToolResult:
        files = [Path(line) for line in list_python_files().output.splitlines() if line.strip()]
        errors: list[str] = []
        for rel in files:
            try:
                py_compile.compile(str(workspace / rel), doraise=True)
            except Exception as exc:
                errors.append(f"{rel}: {type(exc).__name__}: {exc}")
        if errors:
            return ToolResult(False, "\n".join(errors), {"checked": len(files), "errors": len(errors)})
        return ToolResult(True, f"Parsed OK: {len(files)} Python files", {"checked": len(files), "errors": 0})

    def git_diff() -> ToolResult:
        started = time.perf_counter()
        repo_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if repo_check.returncode != 0:
            duration = time.perf_counter() - started
            return ToolResult(
                False,
                "Not a Git repository; git_diff is available only inside a Git worktree.",
                {"returncode": repo_check.returncode, "duration_seconds": round(duration, 3)},
            )

        completed = subprocess.run(
            ["git", "diff", "--", "."],
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.perf_counter() - started
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        return ToolResult(
            completed.returncode == 0,
            output or "(no git diff)",
            {
                "returncode": completed.returncode,
                "duration_seconds": round(duration, 3),
                "chars": len(output),
                "command": "git diff -- .",
            },
        )

    def run_tests(timeout: int = 120, target: str = "auto") -> ToolResult:
        if importlib.util.find_spec("pytest") is None:
            return ToolResult(
                False,
                "pytest is not installed; install pytest or add it to requirements.txt to run tests.",
                {"pytest_available": False},
            )

        started = time.perf_counter()
        command = [sys.executable, "-m", "pytest", "--rootdir=."]
        resolved_target = _resolve_pytest_target(workspace, target)
        if resolved_target:
            command.append(resolved_target)
        cleared_pycache_dirs = _clear_pycache_dirs(workspace)
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(workspace) if not existing_pythonpath else os.pathsep.join([str(workspace), existing_pythonpath])
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            output = ((exc.stdout or "") + (exc.stderr or "")).strip()
            return ToolResult(
                False,
                output or f"pytest timed out after {timeout} seconds",
                {
                    "returncode": None,
                    "duration_seconds": round(duration, 3),
                    "pytest_available": True,
                    "timed_out": True,
                    "command": " ".join(command),
                    "target": resolved_target,
                    "cleared_pycache_dirs": cleared_pycache_dirs,
                },
            )
        duration = time.perf_counter() - started
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        return ToolResult(
            completed.returncode == 0,
            output or "(no test output)",
            {
                "returncode": completed.returncode,
                "duration_seconds": round(duration, 3),
                "pytest_available": True,
                "timed_out": False,
                "command": " ".join(command),
                "target": resolved_target,
                "cleared_pycache_dirs": cleared_pycache_dirs,
            },
        )

    registry.register(Tool(
        "list_python_files",
        "List Python files under the workspace, excluding virtualenv/cache directories by default.",
        {"type": "object", "properties": {"include_venv": {"type": "boolean"}}},
        list_python_files,
    ))
    registry.register(Tool(
        "read_file",
        "Read a UTF-8 text file inside the workspace. Supports optional start_line/end_line, line limit, and max_chars.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"},
                "max_chars": {"type": "integer"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["path"],
        },
        read_file,
    ))
    registry.register(Tool(
        "todo_write",
        "Create or replace the current task todo list. Use this before multi-step repository work.",
        {
            "type": "object",
            "properties": {
                "todos": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"],
                                    },
                                },
                                "required": ["task"],
                            },
                        },
                    ]
                }
            },
            "required": ["todos"],
        },
        todo_write,
    ))
    registry.register(Tool(
        "write_file",
        "Write a UTF-8 text file inside the workspace.",
        {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        write_file,
        risk="write",
    ))
    registry.register(Tool(
        "edit_file",
        "Replace one exact text block inside a UTF-8 file. old_text must appear exactly once.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
        edit_file,
        risk="write",
    ))
    registry.register(Tool(
        "delete_file",
        "Delete one workspace file only when confirm is true. Directories are refused.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "confirm": {"type": "boolean"},
            },
            "required": ["path", "confirm"],
        },
        delete_file,
        risk="write",
    ))
    registry.register(Tool(
        "grep",
        "Search files by substring.",
        {"type": "object", "properties": {"pattern": {"type": "string"}, "glob": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["pattern"]},
        grep,
    ))
    registry.register(Tool(
        "permission_policy",
        "Explain the current workspace, write, shell, and Git permission boundaries.",
        {"type": "object", "properties": {}},
        permission_policy,
    ))
    registry.register(Tool(
        "shell",
        "Run a simple allowlisted shell command in the workspace. Shell operators, force flags, and mutating Git commands are blocked.",
        {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["command"]},
        shell,
        risk="shell",
    ))
    registry.register(Tool(
        "run_py_compile",
        "Compile all Python files to check syntax.",
        {"type": "object", "properties": {}},
        run_py_compile,
    ))
    registry.register(Tool(
        "git_diff",
        "Show repository changes with git diff -- . when the workspace is a Git worktree.",
        {"type": "object", "properties": {}},
        git_diff,
    ))
    registry.register(Tool(
        "run_tests",
        "Run the pytest test suite with python -m pytest. By default, use tests/ when it contains pytest files, otherwise run pytest from the workspace root.",
        {
            "type": "object",
            "properties": {
                "timeout": {"type": "integer"},
                "target": {"type": "string"},
            },
        },
        run_tests,
        risk="shell",
    ))
    registry.register(Tool(
        "cache_stats",
        "Report read_file cache hits, misses, hit rate, and invalidations.",
        {"type": "object", "properties": {}},
        cache_stats,
    ))
    if enable_context_pack:
        registry.register(Tool(
            "index_workspace",
            "Build a safe local retrieval index summary for workspace text chunks.",
            {
                "type": "object",
                "properties": {
                    "glob": {"type": "string"},
                    "chunk_lines": {"type": "integer"},
                    "overlap": {"type": "integer"},
                },
            },
            index_workspace,
        ))
        registry.register(Tool(
            "rag_search",
            "Search workspace code and docs using local chunked lexical retrieval with path and line metadata.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "glob": {"type": "string"},
                    "limit": {"type": "integer"},
                    "chunk_lines": {"type": "integer"},
                    "overlap": {"type": "integer"},
                    "max_chars_per_chunk": {"type": "integer"},
                },
                "required": ["query"],
            },
            rag_search,
        ))
        registry.register(Tool(
            "rag_explain",
            "Turn local RAG matches into a concrete read_file plan with path and line-range arguments.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "glob": {"type": "string"},
                    "limit": {"type": "integer"},
                    "chunk_lines": {"type": "integer"},
                    "overlap": {"type": "integer"},
                    "read_window": {"type": "integer"},
                    "max_chars_per_chunk": {"type": "integer"},
                },
                "required": ["query"],
            },
            rag_explain,
        ))
        registry.register(Tool(
            "context_pack",
            "Retrieve the most relevant workspace file snippets for a task query using local chunked lexical retrieval.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "glob": {"type": "string"},
                    "limit": {"type": "integer"},
                    "max_chars_per_file": {"type": "integer"},
                    "window": {"type": "integer"},
                },
                "required": ["query"],
            },
            context_pack,
        ))
    registry.register(Tool(
        "compact_context",
        "Summarize trace.jsonl into current goal, files read, files changed, failures, and next step.",
        {"type": "object", "properties": {"max_items": {"type": "integer"}}},
        compact_context,
    ))
    registry.register(Tool(
        "recover_errors",
        "Analyze failed tool calls in trace.jsonl and suggest concrete recovery steps.",
        {"type": "object", "properties": {"max_items": {"type": "integer"}}},
        recover_errors,
    ))
    registry.register(Tool(
        "retry_plan",
        "Turn failed trace events into an ordered next-step retry plan with suggested tools.",
        {"type": "object", "properties": {"max_items": {"type": "integer"}}},
        retry_plan,
    ))
    registry.register(Tool(
        "save_memory",
        "Save a reusable successful workflow into skills/<slug>.md.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "memory_name": {"type": "string"},
                "summary": {"type": "string"},
                "trigger": {"type": "string"},
                "steps": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
            },
            "required": ["memory_name", "summary"],
        },
        save_memory,
        risk="write",
    ))
    registry.register(Tool(
        "list_memories",
        "List reusable workflow memories saved under skills/*.md, optionally ranked by a query.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        list_memories,
    ))
    registry.register(Tool(
        "read_memory",
        "Read a reusable workflow memory from skills/<slug>.md.",
        {
            "type": "object",
            "properties": {
                "memory_name": {"type": "string"},
                "max_chars": {"type": "integer"},
            },
            "required": ["memory_name"],
        },
        read_memory,
    ))
    return registry


def _check_todo_quality(todos: list[dict[str, str]], is_initial_plan: bool) -> dict[str, Any]:
    issues: list[str] = []
    if len(todos) < 2:
        issues.append("todo_list_too_short")
    if is_initial_plan and todos and all(item.get("status") == "completed" for item in todos):
        issues.append("all_todos_completed_immediately")

    allowed_starts = {
        "add",
        "check",
        "compact",
        "create",
        "diagnose",
        "fix",
        "inspect",
        "list",
        "read",
        "recover",
        "run",
        "search",
        "summarize",
        "update",
        "verify",
        "write",
    }
    for index, item in enumerate(todos):
        task = item.get("task", "").strip()
        if not task:
            issues.append(f"todo_{index}_empty_task")
            continue
        first_word = task.split()[0].lower().strip(":,.;")
        if first_word not in allowed_starts:
            issues.append(f"todo_{index}_missing_action_verb")

    return {
        "ok": not issues,
        "issues": issues,
        "count": len(todos),
        "initial_plan": is_initial_plan,
    }


def _summarize_diff(diff: str) -> dict[str, int]:
    added = 0
    removed = 0
    hunks = 0
    for line in diff.splitlines():
        if line.startswith("@@"):
            hunks += 1
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"added_lines": added, "removed_lines": removed, "hunks": hunks}


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _format_trace_path(workspace: Path, value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    try:
        path = Path(text)
        if path.is_absolute():
            return str(path.resolve().relative_to(workspace))
    except ValueError:
        return text
    return text


def _format_context_summary(
    event_count: int,
    tool_counts: dict[str, int],
    current_goal: str,
    next_step: str,
    files_read: list[str],
    files_changed: list[str],
    failures: list[str],
    latest_todos: list[dict[str, str]],
    parse_errors: int,
) -> str:
    tool_rows = "\n".join(f"- `{name}`: {count}" for name, count in sorted(tool_counts.items()))
    files_read_rows = "\n".join(f"- `{path}`" for path in files_read) or "- None recorded."
    files_changed_rows = "\n".join(f"- `{path}`" for path in files_changed) or "- None recorded."
    failure_rows = "\n".join(f"- {item}" for item in failures) or "- None recorded."
    todo_rows = "\n".join(
        f"- [{_todo_checkbox(item.get('status', 'pending'))}] {item.get('task', '')}"
        for item in latest_todos
    ) or "- No todo plan recorded."

    return f"""# Context Summary

- Trace events: {event_count}
- Tool calls: {sum(tool_counts.values())}
- Current goal: {current_goal}
- Next step: {next_step}
- Trace parse errors: {parse_errors}

## Tool Calls

{tool_rows or "- None recorded."}

## Files Read

{files_read_rows}

## Files Changed

{files_changed_rows}

## Key Errors

{failure_rows}

## Latest Todos

{todo_rows}
"""


def _build_context_matches(
    workspace: Path,
    query_tokens: list[str],
    glob_pattern: str,
    limit: int,
    max_chars_per_file: int,
    window: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    matches: list[dict[str, Any]] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        if _context_path_is_ignored(rel):
            continue
        rel_text = str(rel).replace("\\", "/")
        if not _matches_context_glob(rel_text, glob_pattern):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "\x00" in text:
            continue

        lines = text.splitlines()
        scored_line = _best_context_line(query_tokens, lines)
        path_score = _path_context_score(query_tokens, rel_text)
        total_score = int(scored_line["score"]) + path_score
        if total_score <= 0:
            continue
        start_line = max(1, int(scored_line["line"]) - window)
        end_line = min(len(lines), int(scored_line["line"]) + window)
        snippet = "\n".join(lines[start_line - 1:end_line])
        if len(snippet) > max_chars_per_file:
            snippet = snippet[:max_chars_per_file] + f"\n... ({len(snippet) - max_chars_per_file} more chars)"

        matches.append({
            "path": rel_text,
            "score": total_score,
            "line_score": int(scored_line["score"]),
            "path_score": path_score,
            "start_line": start_line,
            "end_line": end_line,
            "snippet": snippet,
        })

    matches.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return matches[:limit]


def _context_path_is_ignored(rel: Path) -> bool:
    return any(part in CONTEXT_PACK_IGNORED_PARTS or part.startswith(".") and part != "." for part in rel.parts)


def _matches_context_glob(path: str, glob_pattern: str) -> bool:
    patterns = [
        item.strip()
        for item in glob_pattern.split(",")
        if item.strip()
    ] or ["*"]
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern) for pattern in patterns)


def _best_context_line(query_tokens: list[str], lines: list[str]) -> dict[str, int]:
    best = {"line": 1, "score": 0}
    for lineno, line in enumerate(lines, start=1):
        lower = line.lower()
        score = 0
        for token in query_tokens:
            if token in lower:
                score += 4 + min(lower.count(token), 3)
        if score > 0 and any(marker in lower for marker in {"def ", "class ", "function ", "describe(", "it("}):
            score += 1
        if score > best["score"]:
            best = {"line": lineno, "score": score}
    return best


def _path_context_score(query_tokens: list[str], path: str) -> int:
    lower = path.lower().replace("_", " ").replace("-", " ").replace("/", " ")
    score = 0
    for token in query_tokens:
        if token in lower:
            score += 3
    return score


def _format_context_pack(query: str, matches: list[dict[str, Any]]) -> str:
    if not matches:
        return f"# Context Pack\n\n- Query: {query}\n- Matches: 0\n\n(no matching context)"

    sections = []
    for item in matches:
        sections.append(
            "## `{path}` (score {score}, lines {start_line}-{end_line})\n\n"
            "```text\n{snippet}\n```".format(
                path=item["path"],
                score=item["score"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                snippet=item["snippet"],
            )
        )
    return "# Context Pack\n\n- Query: {query}\n- Matches: {count}\n- Retrieval: lexical path and line scoring\n\n{sections}\n".format(
        query=query,
        count=len(matches),
        sections="\n\n".join(sections),
    )


def _todo_checkbox(status: str) -> str:
    if status == "completed":
        return "x"
    if status == "in_progress":
        return "-"
    return " "


def _memory_slug(name: str) -> str:
    chars: list[str] = []
    last_was_dash = False
    for char in name.lower():
        if char.isalnum():
            chars.append(char)
            last_was_dash = False
        elif not last_was_dash:
            chars.append("-")
            last_was_dash = True
    return "".join(chars).strip("-")


def _memory_reference_slugs(name: str) -> list[str]:
    raw = str(name).strip()
    normalized = raw.replace("\\", "/").strip("/")
    stem = normalized.rsplit("/", 1)[-1]
    if stem.lower().endswith(".md"):
        stem = stem[:-3]
    candidates = [_memory_slug(stem), _memory_slug(raw)]
    seen: set[str] = set()
    unique: list[str] = []
    for slug in candidates:
        if slug and slug not in seen:
            seen.add(slug)
            unique.append(slug)
    return unique


def _normalize_memory_steps(steps: list[str] | str) -> list[str]:
    if isinstance(steps, str):
        return [line.strip("- ").strip() for line in steps.splitlines() if line.strip("- ").strip()]
    return [str(item).strip() for item in steps if str(item).strip()]


def _memory_query_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in query.lower():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return [token for token in tokens if len(token) >= 2]


def _memory_relevance_score(tokens: list[str], stem: str, title: str, text: str) -> int:
    if not tokens:
        return 0
    stem_text = stem.lower().replace("-", " ")
    title_text = title.lower()
    body_text = text.lower()
    score = 0
    for token in tokens:
        if token in title_text:
            score += 5
        if token in stem_text:
            score += 3
        if token in body_text:
            score += min(body_text.count(token), 3)
    return score


def _format_memory_markdown(name: str, summary: str, trigger: str, steps: list[str]) -> str:
    step_rows = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    if not step_rows:
        step_rows = "No steps recorded yet."
    trigger_text = trigger.strip() or "Use when a similar repository-maintenance task appears."
    return f"""# {name.strip()}

## Summary

{summary.strip()}

## Trigger

{trigger_text}

## Steps

{step_rows}
"""


def first_markdown_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _build_recovery_item(
    tool_name: str,
    output: str,
    metadata: dict[str, Any],
    permission: str,
) -> dict[str, str]:
    text = output.lower()
    category = "unknown_failure"
    action = "Read the failed tool output, inspect the relevant file or command, then retry with a smaller step."

    if permission and permission != "allow":
        category = "permission_block"
        if "overwrite" in permission:
            action = "Rerun with explicit write permission only if the overwrite is intended, or choose a new output path."
        elif "delete_requires_confirmation" in permission:
            action = "Rerun delete_file with explicit confirmation (confirm=true) only after verifying the target file is safe to delete."
        elif "path_escape" in permission:
            action = "Use a path inside the workspace and avoid absolute or parent-directory paths."
        elif "dangerous_shell" in permission:
            action = "Replace the shell command with a safer whitelisted command or a dedicated tool."
        elif "shell_operator" in permission:
            action = "Remove shell operators such as pipes or redirection, then use one simple allowlisted command."
        elif "shell_not_allowlisted" in permission:
            action = "Use a dedicated tool or a simple allowlisted read/verification command instead of this shell command."
        elif "git_not_allowlisted" in permission:
            action = "Use read-only Git commands such as git status, git diff, git log, or the dedicated git_diff tool."
        elif "force_flag" in permission:
            action = "Remove force flags and choose a safer read-only command or a dedicated tool."
    elif tool_name == "git_diff" or "not a git repository" in text:
        category = "git_repo_missing"
        action = "Run inside a Git worktree, initialize a repo for the project, or skip repo-level diff when Git is unavailable."
    elif tool_name == "run_tests" and ("no tests ran" in text or metadata.get("returncode") == 5):
        category = "no_tests_collected"
        action = "Add pytest files under tests/ or the workspace root so run_tests can validate behavior."
    elif "pytest is not installed" in text:
        category = "missing_dependency"
        action = "Install pytest or add it to requirements.txt before running run_tests."
    elif metadata.get("timed_out") or "timed out" in text or "timeoutexpired" in text:
        category = "timeout"
        action = "Increase the timeout, narrow the command, or split the task into smaller checks."
    elif "file not found" in text:
        category = "missing_file"
        action = "List files or grep first, then retry with an existing workspace-relative path."
    elif "appear exactly once" in text or "old_text must be non-empty" in text:
        category = "edit_match_failed"
        action = "Read the latest file content and choose a non-empty old_text snippet that appears exactly once."

    first_line = output.splitlines()[0] if output else "(no output)"
    return {
        "tool": tool_name,
        "category": category,
        "error": first_line,
        "action": action,
    }


def _format_recovery_report(
    recovery_items: list[dict[str, str]],
    failure_count: int,
    parse_errors: int,
) -> str:
    if not recovery_items:
        rows = "- No failed tool calls found."
    else:
        rows = "\n".join(
            f"- `{item['tool']}` ({item['category']}): {item['action']}"
            for item in recovery_items
        )
    return f"""# Error Recovery

- Failed tool calls: {failure_count}
- Trace parse errors: {parse_errors}

## Recovery Steps

{rows}
"""


def _build_retry_step(index: int, recovery: dict[str, str]) -> dict[str, str | int]:
    category = recovery["category"]
    suggested_tool = "read_file"
    detail = recovery["action"]

    if category == "edit_match_failed":
        suggested_tool = "read_file -> edit_file"
        detail = "Read the current file content, choose an exact old_text snippet that appears once, then retry edit_file."
    elif category == "missing_file":
        suggested_tool = "list_python_files or grep"
        detail = "Discover the correct workspace-relative path before retrying the failed file operation."
    elif category == "permission_block":
        suggested_tool = recovery["tool"]
        detail = recovery["action"]
    elif category == "no_tests_collected":
        suggested_tool = "write_file -> run_tests"
        detail = "Add or fix pytest files under tests/ or the workspace root, then run tests again."
    elif category == "timeout":
        suggested_tool = "run_tests or shell"
        detail = "Narrow the target or increase timeout before rerunning the command."
    elif category == "git_repo_missing":
        suggested_tool = "git_diff"
        detail = "Run git_diff only inside a Git worktree, or skip diff validation for this workspace."
    elif category == "missing_dependency":
        suggested_tool = "read_file -> edit_file"
        detail = "Inspect dependency files and add the missing dependency before rerunning verification."

    return {
        "index": index,
        "source_tool": recovery["tool"],
        "category": category,
        "suggested_tool": suggested_tool,
        "detail": detail,
    }


def _format_retry_plan(
    steps: list[dict[str, str | int]],
    failure_count: int,
    parse_errors: int,
) -> str:
    if not steps:
        rows = "- No failed tool calls found."
    else:
        rows = "\n".join(
            "{index}. `{source_tool}` failed as `{category}`. Next use `{suggested_tool}`: {detail}".format(
                index=item["index"],
                source_tool=item["source_tool"],
                category=item["category"],
                suggested_tool=item["suggested_tool"],
                detail=item["detail"],
            )
            for item in steps
        )
    return f"""# Retry Plan

- Failed tool calls: {failure_count}
- Trace parse errors: {parse_errors}
- Planned steps: {len(steps)}

## Ordered Steps

{rows}
"""
