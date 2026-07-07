from __future__ import annotations

from datetime import datetime
import difflib
from pathlib import Path

from .tools import ToolRegistry


def inspect_repo(registry: ToolRegistry, output_path: str = "REVIEW.md") -> str:
    """Run a small deterministic repo inspection and write REVIEW.md."""
    todos = [
        "List Python files",
        "Read key project files",
        "Run Python syntax checks",
        "Run Git diff inspection",
        "Run pytest tests",
        "List workflow memories",
        "Compact execution context",
        "Recover from failed tool calls",
        "Summarize output diff",
        "Write an evidence-backed review",
    ]
    todo_state = [{"task": item, "status": "pending"} for item in todos]
    registry.call("todo_write", todos=todo_state)

    py_files = registry.call("list_python_files")
    update_todo(todo_state, todos[0], "completed")
    registry.call("todo_write", todos=todo_state)

    candidate_files = [
        "README.md",
        "README.zh-CN.md",
        "main.py",
        "harness/tools.py",
        "harness/trace.py",
        "harness/agent.py",
        "harness/review.py",
        "harness/evaluation.py",
        "pytest.ini",
        "EVAL.md",
    ]
    evidence: list[tuple[str, str, str]] = []
    snippets: dict[str, str] = {}
    for path in candidate_files:
        target = registry.workspace / path
        if target.exists():
            result = registry.call("read_file", path=path, max_chars=3000)
            snippets[path] = result.output
            evidence.append((f"Read `{path}`", path, "verified"))
    update_todo(todo_state, todos[1], "completed")
    registry.call("todo_write", todos=todo_state)

    syntax = registry.call("run_py_compile")
    update_todo(todo_state, todos[2], "completed")
    registry.call("todo_write", todos=todo_state)

    git_diff = registry.call("git_diff")
    update_todo(todo_state, todos[3], "completed")
    registry.call("todo_write", todos=todo_state)

    tests = registry.call("run_tests")
    update_todo(todo_state, todos[4], "completed")
    registry.call("todo_write", todos=todo_state)

    cache = registry.call("cache_stats")
    memory = registry.call("list_memories")
    update_todo(todo_state, todos[5], "completed")
    registry.call("todo_write", todos=todo_state)

    context = registry.call("compact_context")
    update_todo(todo_state, todos[6], "completed")
    registry.call("todo_write", todos=todo_state)
    recovery = registry.call("recover_errors")
    update_todo(todo_state, todos[7], "completed")
    registry.call("todo_write", todos=todo_state)

    python_count = (py_files.metadata or {}).get("count", 0)
    syntax_status = "passed" if syntax.ok else "failed"
    git_diff_status = "available" if git_diff.ok else "unavailable"
    test_status = "passed" if tests.ok else "failed"
    context_status = "available" if context.ok else "failed"
    memory_count = (memory.metadata or {}).get("count", 0)
    recovery_count = (recovery.metadata or {}).get("failure_count", 0)
    cache_metrics = cache.metadata or {}
    findings = build_findings(
        python_count=python_count,
        syntax_status=syntax_status,
        git_diff_status=git_diff_status,
        test_status=test_status,
        context_status=context_status,
        memory_count=memory_count,
        recovery_count=recovery_count,
        cache_metrics=cache_metrics,
        snippets=snippets,
    )

    target = registry.workspace / output_path
    before_report = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    report = _build_report(
        workspace=registry.workspace,
        python_files=py_files.output,
        python_count=python_count,
        syntax_output=syntax.output,
        syntax_status=syntax_status,
        git_diff_output=git_diff.output,
        git_diff_status=git_diff_status,
        test_output=tests.output,
        test_status=test_status,
        context_output=context.output,
        context_status=context_status,
        memory_output=memory.output,
        memory_count=memory_count,
        recovery_output=recovery.output,
        recovery_count=recovery_count,
        cache_output=cache.output,
        cache_metrics=cache_metrics,
        evidence=evidence,
        snippets=snippets,
        findings=findings,
        write_diff_summary=None,
    )
    write_diff_summary = _summarize_text_diff(before_report, report, output_path)
    update_todo(todo_state, todos[8], "completed")
    registry.call("todo_write", todos=todo_state)

    report = _build_report(
        workspace=registry.workspace,
        python_files=py_files.output,
        python_count=python_count,
        syntax_output=syntax.output,
        syntax_status=syntax_status,
        git_diff_output=git_diff.output,
        git_diff_status=git_diff_status,
        test_output=tests.output,
        test_status=test_status,
        context_output=context.output,
        context_status=context_status,
        memory_output=memory.output,
        memory_count=memory_count,
        recovery_output=recovery.output,
        recovery_count=recovery_count,
        cache_output=cache.output,
        cache_metrics=cache_metrics,
        evidence=evidence,
        snippets=snippets,
        findings=findings,
        write_diff_summary=write_diff_summary,
    )
    write_diff_summary = _summarize_text_diff(before_report, report, output_path)
    report = _build_report(
        workspace=registry.workspace,
        python_files=py_files.output,
        python_count=python_count,
        syntax_output=syntax.output,
        syntax_status=syntax_status,
        git_diff_output=git_diff.output,
        git_diff_status=git_diff_status,
        test_output=tests.output,
        test_status=test_status,
        context_output=context.output,
        context_status=context_status,
        memory_output=memory.output,
        memory_count=memory_count,
        recovery_output=recovery.output,
        recovery_count=recovery_count,
        cache_output=cache.output,
        cache_metrics=cache_metrics,
        evidence=evidence,
        snippets=snippets,
        findings=findings,
        write_diff_summary=write_diff_summary,
    )
    write = registry.call("write_file", path=output_path, content=report)
    if write.ok:
        update_todo(todo_state, todos[9], "completed")
        registry.call("todo_write", todos=todo_state)
    return write.output


def _build_report(
    workspace: Path,
    python_files: str,
    python_count: int,
    syntax_output: str,
    syntax_status: str,
    git_diff_output: str,
    git_diff_status: str,
    test_output: str,
    test_status: str,
    context_output: str,
    context_status: str,
    memory_output: str,
    memory_count: int,
    recovery_output: str,
    recovery_count: int,
    cache_output: str,
    cache_metrics: dict,
    evidence: list[tuple[str, str, str]],
    snippets: dict[str, str],
    findings: list[tuple[str, str, str]],
    write_diff_summary: dict[str, int] | None,
) -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    evidence_rows = "\n".join(
        f"| {claim} | `{source}` | {status} |"
        for claim, source, status in evidence
    ) or "| No files read | N/A | missing |"

    file_rows = "\n".join(f"- `{line}`" for line in python_files.splitlines() if line.strip())
    if not file_rows:
        file_rows = "- No Python files found."

    observed_modules = "\n".join(
        f"- `{path}`: {first_nonempty_line(text)}"
        for path, text in snippets.items()
    ) or "- No key files were found."

    finding_rows = "\n".join(
        f"| {claim} | `{source}` | {reason} |"
        for claim, source, reason in findings
    ) or "| No findings generated | N/A | N/A |"
    if write_diff_summary:
        diff_summary = (
            "| File | Added Lines | Removed Lines | Hunks |\n"
            "|---|---:|---:|---:|\n"
            f"| `REVIEW.md` | {write_diff_summary.get('added_lines', 0)} | "
            f"{write_diff_summary.get('removed_lines', 0)} | {write_diff_summary.get('hunks', 0)} |"
        )
    else:
        diff_summary = "Diff summary is calculated before writing the final report."

    return f"""# Repository Review

Generated: {generated}

Workspace: `{workspace}`

## Summary

- Python files found: **{python_count}**
- Python syntax check: **{syntax_status}**
- Git diff: **{git_diff_status}**
- Pytest: **{test_status}**
- Context compaction: **{context_status}**
- Workflow memories: **{memory_count}**
- Failed tool calls analyzed: **{recovery_count}**
- Read cache hits/misses: **{cache_metrics.get("read_cache_hits", 0)} / {cache_metrics.get("read_cache_misses", 0)}**
- Trace file: `trace.jsonl`

## Evidence

| Claim | Source | Status |
|---|---|---|
{evidence_rows}

## Python Files

{file_rows}

## Key Files Observed

{observed_modules}

## Syntax Check

```text
{syntax_output}
```

## Git Diff

```text
{git_diff_output}
```

## Test Run

```text
{test_output}
```

## Cache Metrics

```text
{cache_output}
```

## Context Summary

```text
{context_output}
```

## Workflow Memories

```text
{memory_output}
```

## Error Recovery

```text
{recovery_output}
```

## Write Diff Summary

{diff_summary}

## Evidence-Backed Findings

| Finding | Source | Evidence |
|---|---|---|
{finding_rows}

## Next Improvements

- Add model-generated todos for arbitrary user issues.
- Add cache savings to benchmark summaries across multiple tasks.
- Add stricter source-to-claim validation.
"""


def build_findings(
    python_count: int,
    syntax_status: str,
    git_diff_status: str,
    test_status: str,
    context_status: str,
    memory_count: int,
    recovery_count: int,
    cache_metrics: dict,
    snippets: dict[str, str],
) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = [
        (
            f"The project currently contains {python_count} Python files.",
            "list_python_files",
            "The file list was produced by the tool registry.",
        ),
        (
            f"Python syntax check {syntax_status}.",
            "run_py_compile",
            "All listed Python files were compiled with py_compile.",
        ),
        (
            f"Git diff inspection is {git_diff_status}.",
            "git_diff",
            "The tool runs git diff -- . when the workspace is inside a Git worktree.",
        ),
        (
            f"Pytest run {test_status}.",
            "run_tests",
            "The tool runs python -m pytest and records return code plus duration metadata.",
        ),
        (
            f"Context compaction is {context_status}.",
            "compact_context",
            "The tool summarizes trace events into current goal, files touched, failures, and next step.",
        ),
        (
            f"The project has {memory_count} saved workflow memories.",
            "list_memories",
            "The tool lists reusable workflows stored under skills/*.md.",
        ),
        (
            f"Error recovery analyzed {recovery_count} failed tool calls.",
            "recover_errors",
            "The tool classifies failed tool calls and suggests concrete next steps.",
        ),
        (
            "Read cache metrics are captured for each inspection run.",
            "cache_stats",
            (f"hits={cache_metrics.get('read_cache_hits', 0)}, "
             f"misses={cache_metrics.get('read_cache_misses', 0)}, "
             f"hit_rate={cache_metrics.get('read_cache_hit_rate', 0.0):.2%}."),
        ),
    ]

    if "harness/tools.py" in snippets:
        findings.append((
            "Tool calls are routed through a central ToolRegistry.",
            "harness/tools.py",
            "The file defines Tool, ToolResult, ToolRegistry, and build_registry.",
        ))
        findings.append((
            "Multi-step work can be planned and tracked with todo_write.",
            "harness/tools.py",
            "todo_write stores the current todo list and records status changes in trace metadata.",
        ))
        findings.append((
            "Todo plans are checked for basic quality before execution proceeds.",
            "harness/tools.py",
            "todo_write emits todo_quality with issues such as short lists or missing action verbs.",
        ))
        findings.append((
            "Shell execution has a basic permission gate.",
            "harness/tools.py",
            "The permission policy blocks dangerous shell patterns before execution.",
        ))
        findings.append((
            "Write operations include diff metadata for auditability.",
            "harness/tools.py",
            "write_file computes a unified diff before returning ToolResult metadata.",
        ))
        findings.append((
            "Overwriting existing files requires explicit write permission.",
            "harness/tools.py",
            "ToolRegistry blocks write_file when the target exists and allow_write is false.",
        ))
        findings.append((
            "Repeated read_file calls can reuse cached content when the file has not changed.",
            "harness/tools.py",
            "read_file caches by path, mtime, size, line limit, and max_chars, and reports cache_hit in metadata.",
        ))

    if "harness/trace.py" in snippets:
        findings.append((
            "Execution traces are persisted as append-only JSONL.",
            "harness/trace.py",
            "TraceLogger.log writes one JSON object per event.",
        ))

    if "harness/review.py" in snippets:
        findings.append((
            "The deterministic inspect workflow creates an evidence-backed REVIEW.md.",
            "harness/review.py",
            "inspect_repo reads selected files, runs syntax checks, and writes the report.",
        ))
        findings.append((
            "Final reports summarize the write diff for easier human review.",
            "harness/review.py",
            "inspect_repo computes added lines, removed lines, and hunks before writing REVIEW.md.",
        ))

    if "harness/evaluation.py" in snippets:
        findings.append((
            "A deterministic evaluation runner is available.",
            "harness/evaluation.py",
            "run_evaluation executes benchmark tasks and reports success rate, tool calls, duration, and failure categories.",
        ))

    if "EVAL.md" in snippets:
        findings.append((
            "The latest evaluation report is saved as EVAL.md.",
            "EVAL.md",
            "The report records task-level status, tool-call counts, failed tool calls, duration, and trace paths.",
        ))

    if "harness/agent.py" in snippets:
        findings.append((
            "A minimal model-driven tool loop is available through ask.",
            "harness/agent.py",
            "run_agent sends tool schemas to the model and dispatches tool_use blocks.",
        ))

    return findings


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return "(empty file)"


def update_todo(todo_state: list[dict[str, str]], task: str, status: str) -> None:
    for item in todo_state:
        if item["task"] == task:
            item["status"] = status
            return


def _summarize_text_diff(before: str, after: str, path: str) -> dict[str, int]:
    diff = "\n".join(difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"{path} (before)",
        tofile=f"{path} (after)",
        lineterm="",
    ))
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
