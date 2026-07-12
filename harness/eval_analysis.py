from __future__ import annotations

from collections.abc import Mapping, Sequence
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

FAILURE_PATTERN_DESCRIPTIONS = {
    "max_turns": "the trace ended because the agent hit the turn budget",
    "no_file_change": "no successful edit_file or write_file call was observed",
    "over_exploration": "shell/Git exploration dominated before the repair",
    "verification_failed": "the verifier reported failure or tests failed after attempted work",
    "tool_failures": "one or more tool calls failed during the task",
    "trace_unavailable": "the JSON report references a trace that was not available locally",
}


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


def build_eval_history(
    run_specs: Sequence[str],
    output_path: Path | None = None,
) -> str:
    runs = [_load_history_run(spec) for spec in run_specs]
    report = build_eval_history_report(runs)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    return report


def build_failure_dashboard(
    run_specs: Sequence[str],
    output_path: Path | None = None,
    trace_root: Path | None = None,
) -> str:
    runs = [_load_history_run(spec) for spec in run_specs]
    report = build_failure_dashboard_report(runs, trace_root=trace_root)
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


def build_eval_history_report(runs: Sequence[Mapping[str, Any]]) -> str:
    if not runs:
        raise ValueError("At least one eval run is required.")

    trend_rows = "\n".join(_history_trend_row(run) for run in runs)
    tool_rows = "\n".join(_history_tool_row(run) for run in runs)
    task_rows = _task_outcome_change_rows(runs)
    latest = runs[-1]
    first = runs[0]
    first_summary = _summary(first["report"])
    latest_summary = _summary(latest["report"])
    success_delta = _float_or_zero(latest_summary.get("success_rate")) - _float_or_zero(first_summary.get("success_rate"))
    tool_delta = _float_or_zero(latest_summary.get("average_tool_calls")) - _float_or_zero(first_summary.get("average_tool_calls"))
    cost_delta = _float_or_zero(latest_summary.get("estimated_cost_usd")) - _float_or_zero(first_summary.get("estimated_cost_usd"))

    return f"""# Eval History Report

## Summary

This report tracks evaluation runs over time so benchmark changes can be discussed as an engineering trend, not a single snapshot.

- Runs compared: **{len(runs)}**
- Success-rate change: **{success_delta:+.2%}**
- Average tool-call change: **{tool_delta:+.2f}**
- Estimated cost change: **${cost_delta:+.6f}**

## Run Trend

| Run | Source | Mode | Memory | Context | Retrieval | Passed | Success Rate | Avg Tool Calls | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failed Tasks |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
{trend_rows}

## Key Tool Calls

| Run | todo_write | run_tests | shell | git_diff | read_file | context_pack | edit/write |
|---|---:|---:|---:|---:|---:|---:|---:|
{tool_rows}

## Task Outcome Changes

{task_rows}

## Interpretation

Use this history report to explain whether a harness change improved success rate, reduced exploratory tool use, changed verification behavior, or raised model cost. Keep claims tied to the rows above.
"""


def build_failure_dashboard_report(
    runs: Sequence[Mapping[str, Any]],
    trace_root: Path | None = None,
) -> str:
    if not runs:
        raise ValueError("At least one eval run is required.")

    root = (trace_root or Path.cwd()).resolve()
    failures_by_run = [_failure_records_for_run(run, root) for run in runs]
    pattern_rows = _failure_pattern_count_rows(runs, failures_by_run)
    detail_rows = _failure_detail_rows(failures_by_run)
    resolved_rows = _failure_resolution_rows(runs)
    first_failed = len(_failed_task_names(runs[0]["report"]))
    latest_failed = len(_failed_task_names(runs[-1]["report"]))
    total_failed = sum(len(items) for items in failures_by_run)
    unique_patterns = sorted({pattern for items in failures_by_run for item in items for pattern in item["patterns"]})

    return f"""# Eval Failure Dashboard

## Summary

This report aggregates failed eval tasks by failure mode so agent behavior can be debugged across runs.

- Runs analyzed: **{len(runs)}**
- Failed tasks in first run: **{first_failed}**
- Failed tasks in latest run: **{latest_failed}**
- Failed task observations: **{total_failed}**
- Failure patterns observed: **{', '.join(f'`{item}`' for item in unique_patterns) if unique_patterns else 'none'}**

## Failure Pattern Counts

| Pattern | Meaning | {_failure_run_headers(runs)} |
|---|---|{_failure_count_alignments(runs)}|
{pattern_rows}

## Failed Task Details

{detail_rows}

## First-To-Latest Failure Movement

{resolved_rows}

## Interpretation

Use this dashboard to decide whether the next harness change should reduce exploration, force earlier file edits, improve verification, or raise the turn budget. A useful change should move tasks out of these buckets, not only improve a single aggregate score.
"""


def _failure_records_for_run(run: Mapping[str, Any], trace_root: Path) -> list[dict[str, Any]]:
    records = []
    for task in run["report"].get("tasks", []):
        if task.get("success"):
            continue
        records.append({
            "run": run["label"],
            "task_id": str(task.get("task_id", "unknown")),
            "category": str(task.get("category", "unknown")),
            "tool_calls": int(task.get("tool_calls", 0) or 0),
            "failed_tool_calls": int(task.get("failed_tool_calls", 0) or 0),
            "patterns": classify_failure(task, trace_root),
            "trace": _display_path(Path(str(task.get("trace_path", "")))) if task.get("trace_path") else "",
        })
    return records


def _failure_run_headers(runs: Sequence[Mapping[str, Any]]) -> str:
    return " | ".join(str(run["label"]) for run in runs)


def _failure_count_alignments(runs: Sequence[Mapping[str, Any]]) -> str:
    return "|".join("---:" for _ in runs)


def _failure_pattern_count_rows(
    runs: Sequence[Mapping[str, Any]],
    failures_by_run: Sequence[Sequence[Mapping[str, Any]]],
) -> str:
    patterns = sorted(set(FAILURE_PATTERN_DESCRIPTIONS) | {pattern for failures in failures_by_run for item in failures for pattern in item["patterns"]})
    rows = []
    for pattern in patterns:
        counts = []
        for failures in failures_by_run:
            count = sum(1 for item in failures if pattern in item["patterns"])
            counts.append(str(count))
        rows.append(f"| `{pattern}` | {FAILURE_PATTERN_DESCRIPTIONS.get(pattern, 'unclassified failure pattern')} | {' | '.join(counts)} |")
    return "\n".join(rows)


def _failure_detail_rows(failures_by_run: Sequence[Sequence[Mapping[str, Any]]]) -> str:
    records = [item for failures in failures_by_run for item in failures]
    if not records:
        return "No failed tasks in the selected runs."
    rows = [
        "| Run | Task | Category | Tool Calls | Failed Tool Calls | Patterns | Trace |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for item in records:
        patterns = ", ".join(f"`{pattern}`" for pattern in item["patterns"]) or "`unknown`"
        rows.append(
            "| {run} | `{task}` | {category} | {tool_calls} | {failed_tool_calls} | {patterns} | `{trace}` |".format(
                run=item["run"],
                task=item["task_id"],
                category=item["category"],
                tool_calls=item["tool_calls"],
                failed_tool_calls=item["failed_tool_calls"],
                patterns=patterns,
                trace=item["trace"],
            )
        )
    return "\n".join(rows)


def _failure_resolution_rows(runs: Sequence[Mapping[str, Any]]) -> str:
    first_failed = set(_failed_task_names(runs[0]["report"]))
    latest_failed = set(_failed_task_names(runs[-1]["report"]))
    resolved = sorted(first_failed - latest_failed)
    introduced = sorted(latest_failed - first_failed)
    persistent = sorted(first_failed & latest_failed)
    return "\n".join([
        f"- Resolved failures: **{_task_list_text(resolved)}**",
        f"- Introduced failures: **{_task_list_text(introduced)}**",
        f"- Persistent failures: **{_task_list_text(persistent)}**",
    ])


def _task_list_text(items: Sequence[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "none"


def _load_history_run(spec: str) -> dict[str, Any]:
    label, path = _parse_history_spec(spec)
    report = _load_eval_json(path)
    summary = _summary(report)
    return {
        "label": label or str(summary.get("label") or path.stem),
        "path": _display_path(path),
        "report": report,
    }


def _parse_history_spec(spec: str) -> tuple[str | None, Path]:
    if "=" not in spec:
        return None, Path(spec)
    label, path = spec.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label:
        raise ValueError(f"Missing history run label in: {spec}")
    if not path:
        raise ValueError(f"Missing history run path in: {spec}")
    return label, Path(path)


def _display_path(path: Path) -> str:
    return path.as_posix()


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


def _history_trend_row(run: Mapping[str, Any]) -> str:
    report = run["report"]
    summary = _summary(report)
    failed_tasks = _failed_task_names(report)
    return (
        "| {label} | `{source}` | {mode} | {memory} | {context} | {retrieval} | {passed} | {success_rate} | "
        "{avg_tools} | {duration} | {input_tokens} | {output_tokens} | {cost} | {failed_tasks} |"
    ).format(
        label=run["label"],
        source=run["path"],
        mode=summary.get("mode", "unknown"),
        memory=_enabled_text(summary.get("memory_enabled")),
        context=_enabled_text(summary.get("context_enabled")),
        retrieval=_enabled_text(summary.get("retrieval_enabled")),
        passed=_passed_text(summary),
        success_rate=_percent(summary.get("success_rate")),
        avg_tools=_number(summary.get("average_tool_calls")),
        duration=_seconds(summary.get("average_duration")),
        input_tokens=_integer(summary.get("total_input_tokens")),
        output_tokens=_integer(summary.get("total_output_tokens")),
        cost=_money(summary.get("estimated_cost_usd")),
        failed_tasks=", ".join(f"`{task}`" for task in failed_tasks) if failed_tasks else "none",
    )


def _history_tool_row(run: Mapping[str, Any]) -> str:
    summary = _summary(run["report"])
    edit_write = _tool_count_int(summary, "edit_file") + _tool_count_int(summary, "write_file")
    return (
        "| {label} | {todo} | {tests} | {shell} | {git_diff} | {read_file} | {context_pack} | {edit_write} |"
    ).format(
        label=run["label"],
        todo=_tool_count(summary, "todo_write"),
        tests=_tool_count(summary, "run_tests"),
        shell=_tool_count(summary, "shell"),
        git_diff=_tool_count(summary, "git_diff"),
        read_file=_tool_count(summary, "read_file"),
        context_pack=_tool_count(summary, "context_pack"),
        edit_write=edit_write,
    )


def _task_outcome_change_rows(runs: Sequence[Mapping[str, Any]]) -> str:
    task_ids = sorted({
        str(task.get("task_id"))
        for run in runs
        for task in run["report"].get("tasks", [])
        if task.get("task_id")
    })
    changed_rows = []
    for task_id in task_ids:
        statuses = [_task_status(run["report"], task_id) for run in runs]
        known_statuses = [status for status in statuses if status != "missing"]
        if len(set(known_statuses)) <= 1:
            continue
        status_text = " -> ".join(statuses)
        changed_rows.append(f"| `{task_id}` | {status_text} |")
    if not changed_rows:
        return "No task outcome changes across the selected runs."
    return "\n".join(["| Task | Outcome Trend |", "|---|---|", *changed_rows])


def _task_status(report: Mapping[str, Any], task_id: str) -> str:
    for task in report.get("tasks", []):
        if task.get("task_id") == task_id:
            return "pass" if task.get("success") else "fail"
    return "missing"


def _failed_task_names(report: Mapping[str, Any]) -> list[str]:
    return [str(task.get("task_id")) for task in report.get("tasks", []) if task.get("task_id") and not task.get("success")]


def _enabled_text(value: Any) -> str:
    if value is True:
        return "on"
    if value is False:
        return "off"
    return "unknown"


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
