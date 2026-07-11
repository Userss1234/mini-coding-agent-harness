from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any


KEY_TOOL_COUNTS = [
    "todo_write",
    "run_tests",
    "shell",
    "git_diff",
    "read_file",
    "context_pack",
    "edit_file",
    "write_file",
]


def analyze_eval_reports(
    before_path: Path,
    after_path: Path,
    output_path: Path | None = None,
    trace_root: Path | None = None,
) -> str:
    before = _load_eval_json(before_path)
    after = _load_eval_json(after_path)
    root = (trace_root or Path.cwd()).resolve()
    report = build_eval_analysis_report(before, after, trace_root=root)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    return report


def build_eval_analysis_report(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    trace_root: Path | None = None,
) -> str:
    before_summary = _summary(before)
    after_summary = _summary(after)
    before_tasks = list(before.get("tasks", []))
    after_tasks = list(after.get("tasks", []))
    trace_root = (trace_root or Path.cwd()).resolve()

    metric_rows = "\n".join(
        _metric_row(label, before_value, after_value)
        for label, before_value, after_value in [
            ("Passed", _passed_text(before_summary), _passed_text(after_summary)),
            ("Success rate", _percent(before_summary.get("success_rate")), _percent(after_summary.get("success_rate"))),
            ("Average tool calls", _number(before_summary.get("average_tool_calls")), _number(after_summary.get("average_tool_calls"))),
            ("Average duration", _seconds(before_summary.get("average_duration")), _seconds(after_summary.get("average_duration"))),
            ("Input tokens", _integer(before_summary.get("total_input_tokens")), _integer(after_summary.get("total_input_tokens"))),
            ("Output tokens", _integer(before_summary.get("total_output_tokens")), _integer(after_summary.get("total_output_tokens"))),
            ("Estimated cost", _money(before_summary.get("estimated_cost_usd")), _money(after_summary.get("estimated_cost_usd"))),
            ("todo_write calls", _tool_count(before_summary, "todo_write"), _tool_count(after_summary, "todo_write")),
            ("run_tests calls", _tool_count(before_summary, "run_tests"), _tool_count(after_summary, "run_tests")),
            ("shell calls", _tool_count(before_summary, "shell"), _tool_count(after_summary, "shell")),
            ("git_diff calls", _tool_count(before_summary, "git_diff"), _tool_count(after_summary, "git_diff")),
            (
                "edit_file/write_file calls",
                str(_tool_count_int(before_summary, "edit_file") + _tool_count_int(before_summary, "write_file")),
                str(_tool_count_int(after_summary, "edit_file") + _tool_count_int(after_summary, "write_file")),
            ),
        ]
    )

    before_failures = [task for task in before_tasks if not task.get("success")]
    after_failures = [task for task in after_tasks if not task.get("success")]
    before_failure_rows = _failure_rows(before_failures, trace_root)
    after_failure_rows = _failure_rows(after_failures, trace_root)
    tool_delta_rows = _tool_delta_rows(before_summary, after_summary)

    return f"""# Eval Analysis Report

## Summary

This report compares two machine-readable evaluation reports and highlights behavior changes in the agent run.

| Metric | Before | After |
|---|---:|---:|
{metric_rows}

## Tool-Call Delta

| Tool | Before | After | Delta |
|---|---:|---:|---:|
{tool_delta_rows}

## Failed Tasks Before

{before_failure_rows}

## Failed Tasks After

{after_failure_rows}

## Failure Pattern Legend

- `max_turns`: the trace ended because the agent hit the turn budget.
- `no_file_change`: no successful `edit_file` or `write_file` call was observed.
- `over_exploration`: shell/Git exploration dominated before the repair.
- `verification_failed`: the task verifier reported failure or tests failed after attempted work.
- `tool_failures`: one or more tool calls failed during the task.
- `trace_unavailable`: the JSON report references a trace that was not available locally.

## Interpretation

Use this report to connect benchmark movement to agent behavior, not only pass rate. A useful improvement should explain which tool patterns changed and which failure modes disappeared.
"""


def _load_eval_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summary(report: Mapping[str, Any]) -> Mapping[str, Any]:
    return report.get("summary", {})


def _passed_text(summary: Mapping[str, Any]) -> str:
    return f"{int(summary.get('passed', 0))}/{int(summary.get('task_count', 0))}"


def _percent(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "n/a"


def _number(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _seconds(value: Any) -> str:
    return f"{_number(value)}s" if value is not None else "n/a"


def _integer(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "0"


def _money(value: Any) -> str:
    try:
        return f"${float(value):.6f}"
    except (TypeError, ValueError):
        return "$0.000000"


def _tool_count(summary: Mapping[str, Any], tool: str) -> str:
    return str(_tool_count_int(summary, tool))


def _tool_count_int(summary: Mapping[str, Any], tool: str) -> int:
    return int((summary.get("tool_counts") or {}).get(tool, 0))


def _metric_row(label: str, before: str, after: str) -> str:
    return f"| {label} | {before} | {after} |"


def _tool_delta_rows(before_summary: Mapping[str, Any], after_summary: Mapping[str, Any]) -> str:
    tools = sorted(set(KEY_TOOL_COUNTS) | set((before_summary.get("tool_counts") or {})) | set((after_summary.get("tool_counts") or {})))
    rows = []
    for tool in tools:
        before = _tool_count_int(before_summary, tool)
        after = _tool_count_int(after_summary, tool)
        delta = after - before
        rows.append(f"| `{tool}` | {before} | {after} | {delta:+d} |")
    return "\n".join(rows)


def _failure_rows(tasks: list[Mapping[str, Any]], trace_root: Path) -> str:
    if not tasks:
        return "No failed tasks."
    rows = [
        "| Task | Category | Tool Calls | Failed Tool Calls | Patterns | Trace |",
        "|---|---|---:|---:|---|---|",
    ]
    for task in tasks:
        patterns = ", ".join(f"`{item}`" for item in classify_failure(task, trace_root))
        rows.append(
            "| `{task_id}` | {category} | {tool_calls} | {failed_tool_calls} | {patterns} | `{trace}` |".format(
                task_id=task.get("task_id", "unknown"),
                category=task.get("category", "unknown"),
                tool_calls=int(task.get("tool_calls", 0) or 0),
                failed_tool_calls=int(task.get("failed_tool_calls", 0) or 0),
                patterns=patterns or "`unknown`",
                trace=task.get("trace_path", ""),
            )
        )
    return "\n".join(rows)


def classify_failure(task: Mapping[str, Any], trace_root: Path | None = None) -> list[str]:
    patterns: list[str] = []
    tool_counts = task.get("tool_counts") or {}
    shell_like = int(tool_counts.get("shell", 0) or 0) + int(tool_counts.get("git_diff", 0) or 0)
    edit_like = int(tool_counts.get("edit_file", 0) or 0) + int(tool_counts.get("write_file", 0) or 0)
    test_calls = int(tool_counts.get("run_tests", 0) or 0)

    trace_path = _resolve_trace_path(str(task.get("trace_path") or ""), trace_root)
    trace_events, trace_available = _load_trace_events(trace_path)
    if trace_available:
        if any(event.get("event") == "agent_end" and (event.get("data") or {}).get("stopped") == "max_turns" for event in trace_events):
            patterns.append("max_turns")
        if not _trace_has_successful_file_change(trace_events):
            patterns.append("no_file_change")
        if any(event.get("event") == "eval_agent_verifier_end" and not (event.get("data") or {}).get("success") for event in trace_events):
            patterns.append("verification_failed")
    else:
        patterns.append("trace_unavailable")
        if edit_like == 0:
            patterns.append("no_file_change")

    if shell_like >= 3 and shell_like >= edit_like + test_calls:
        patterns.append("over_exploration")
    if int(task.get("failed_tool_calls", 0) or 0) > 0:
        patterns.append("tool_failures")
    if not task.get("success") and test_calls > 0 and "verification_failed" not in patterns:
        patterns.append("verification_failed")

    return _dedupe(patterns)


def _resolve_trace_path(trace_path: str, trace_root: Path | None) -> Path | None:
    if not trace_path:
        return None
    path = Path(trace_path)
    if path.is_absolute():
        return path
    if trace_root:
        return trace_root / path
    return Path.cwd() / path


def _load_trace_events(path: Path | None) -> tuple[list[dict[str, Any]], bool]:
    if path is None or not path.exists():
        return [], False
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, True


def _trace_has_successful_file_change(events: list[Mapping[str, Any]]) -> bool:
    for event in events:
        if event.get("event") != "tool_call":
            continue
        data = event.get("data") or {}
        if data.get("tool") in {"edit_file", "write_file"} and data.get("ok"):
            return True
    return False


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
