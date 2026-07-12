from __future__ import annotations

import json
from pathlib import Path

from harness.eval_analysis import (
    analyze_eval_reports,
    build_eval_history,
    build_eval_history_report,
    build_eval_stability_report,
    build_failure_dashboard,
    build_failure_dashboard_report,
    build_stability_report,
    classify_failure,
)


def test_analyze_eval_reports_compares_metrics_and_failure_patterns(tmp_path: Path) -> None:
    before_trace = tmp_path / "traces" / "agent" / "python_add_tests.jsonl"
    before_trace.parent.mkdir(parents=True)
    before_trace.write_text(
        json.dumps({
            "event": "tool_call",
            "data": {"tool": "read_file", "ok": True, "args": {"path": "string_utils.py"}},
        }) + "\n"
        + json.dumps({
            "event": "agent_end",
            "data": {"stopped": "max_turns"},
        }) + "\n"
        + json.dumps({
            "event": "eval_agent_verifier_end",
            "data": {"success": False},
        }) + "\n",
        encoding="utf-8",
    )
    before = {
        "summary": {
            "task_count": 20,
            "passed": 18,
            "success_rate": 0.9,
            "average_tool_calls": 14.05,
            "average_duration": 107.85,
            "total_input_tokens": 578171,
            "total_output_tokens": 23038,
            "estimated_cost_usd": 2.080083,
            "tool_counts": {
                "todo_write": 71,
                "run_tests": 20,
                "shell": 20,
                "git_diff": 6,
                "edit_file": 18,
                "write_file": 1,
            },
        },
        "tasks": [{
            "task_id": "python_add_tests",
            "category": "code_maintenance",
            "success": False,
            "tool_calls": 15,
            "failed_tool_calls": 1,
            "tool_counts": {"read_file": 1, "shell": 4, "edit_file": 0, "write_file": 0},
            "trace_path": "traces/agent/python_add_tests.jsonl",
        }],
    }
    after = {
        "summary": {
            "task_count": 20,
            "passed": 20,
            "success_rate": 1.0,
            "average_tool_calls": 15.3,
            "average_duration": 111.63,
            "total_input_tokens": 655774,
            "total_output_tokens": 25649,
            "estimated_cost_usd": 2.352057,
            "tool_counts": {
                "todo_write": 92,
                "run_tests": 31,
                "shell": 11,
                "git_diff": 2,
                "edit_file": 21,
                "write_file": 2,
            },
        },
        "tasks": [{
            "task_id": "python_add_tests",
            "category": "code_maintenance",
            "success": True,
            "tool_calls": 15,
            "failed_tool_calls": 0,
            "tool_counts": {"write_file": 1, "run_tests": 1},
            "trace_path": "traces/agent/python_add_tests.jsonl",
        }],
    }
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    output_path = tmp_path / "analysis.md"
    before_path.write_text(json.dumps(before), encoding="utf-8")
    after_path.write_text(json.dumps(after), encoding="utf-8")

    report = analyze_eval_reports(before_path, after_path, output_path, trace_root=tmp_path)

    assert "18/20" in report
    assert "20/20" in report
    assert "| `shell` | 20 | 11 | -9 |" in report
    assert "`max_turns`" in report
    assert "`no_file_change`" in report
    assert "`over_exploration`" in report
    assert "No failed tasks." in report
    assert output_path.read_text(encoding="utf-8") == report


def test_classify_failure_uses_json_when_trace_is_missing(tmp_path: Path) -> None:
    task = {
        "success": False,
        "failed_tool_calls": 1,
        "tool_counts": {"shell": 5, "edit_file": 0, "write_file": 0, "run_tests": 0},
        "trace_path": "missing.jsonl",
    }

    patterns = classify_failure(task, trace_root=tmp_path)

    assert patterns == ["trace_unavailable", "no_file_change", "over_exploration", "tool_failures"]


def test_build_eval_history_report_shows_trends_and_task_changes() -> None:
    before = _history_report(
        passed=18,
        task_count=20,
        average_tool_calls=14.05,
        cost=2.080083,
        shell_calls=20,
        run_tests_calls=20,
        failed_tasks=["python_add_tests", "readme_update"],
    )
    after = _history_report(
        passed=20,
        task_count=20,
        average_tool_calls=15.3,
        cost=2.352057,
        shell_calls=11,
        run_tests_calls=31,
        failed_tasks=[],
    )

    report = build_eval_history_report([
        {"label": "baseline", "path": "before.json", "report": before},
        {"label": "prompt-contract", "path": "after.json", "report": after},
    ])

    assert "# Eval History Report" in report
    assert "Success-rate change: **+10.00%**" in report
    assert "| baseline | `before.json` | agent | on | on | on | 18/20 | 90.00% |" in report
    assert "| prompt-contract | 92 | 31 | 11 | 2 | 49 | 10 | 23 |" in report
    assert "| `python_add_tests` | fail -> pass |" in report
    assert "| `readme_update` | fail -> pass |" in report


def test_build_eval_history_loads_labeled_paths_and_writes_output(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    output_path = tmp_path / "history.md"
    first_path.write_text(json.dumps(_history_report(passed=1, task_count=2, failed_tasks=["readme_update"])), encoding="utf-8")
    second_path.write_text(json.dumps(_history_report(passed=2, task_count=2, failed_tasks=[])), encoding="utf-8")

    report = build_eval_history([
        f"before={first_path}",
        f"after={second_path}",
    ], output_path=output_path)

    assert "before" in report
    assert "after" in report
    assert "1/2" in report
    assert "2/2" in report
    assert output_path.read_text(encoding="utf-8") == report


def test_build_failure_dashboard_report_aggregates_patterns(tmp_path: Path) -> None:
    trace_path = tmp_path / "traces" / "readme_update.jsonl"
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text(
        json.dumps({
            "event": "agent_end",
            "data": {"stopped": "max_turns"},
        }) + "\n"
        + json.dumps({
            "event": "eval_agent_verifier_end",
            "data": {"success": False},
        }) + "\n",
        encoding="utf-8",
    )
    before = _history_report(
        passed=1,
        task_count=2,
        shell_calls=5,
        failed_tasks=["readme_update"],
    )
    before["tasks"][1].update({
        "category": "documentation",
        "tool_calls": 7,
        "failed_tool_calls": 1,
        "tool_counts": {"shell": 5, "edit_file": 0, "write_file": 0, "run_tests": 0},
        "trace_path": "traces/readme_update.jsonl",
    })
    after = _history_report(passed=2, task_count=2, failed_tasks=[])

    report = build_failure_dashboard_report([
        {"label": "baseline", "path": "before.json", "report": before},
        {"label": "current", "path": "after.json", "report": after},
    ], trace_root=tmp_path)

    assert "# Eval Failure Dashboard" in report
    assert "| `max_turns` | the trace ended because the agent hit the turn budget | 1 | 0 |" in report
    assert "| `no_file_change` | no successful edit_file or write_file call was observed | 1 | 0 |" in report
    assert "| baseline | `readme_update` | documentation | 7 | 1 |" in report
    assert "Resolved failures: **`readme_update`**" in report
    assert "Introduced failures: **none**" in report


def test_build_failure_dashboard_loads_labeled_paths_and_writes_output(tmp_path: Path) -> None:
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    output_path = tmp_path / "failures.md"
    before_path.write_text(json.dumps(_history_report(passed=1, task_count=2, failed_tasks=["python_add_tests"])), encoding="utf-8")
    after_path.write_text(json.dumps(_history_report(passed=2, task_count=2, failed_tasks=[])), encoding="utf-8")

    report = build_failure_dashboard([
        f"before={before_path}",
        f"after={after_path}",
    ], output_path=output_path, trace_root=tmp_path)

    assert "before" in report
    assert "after" in report
    assert "`trace_unavailable`" in report
    assert output_path.read_text(encoding="utf-8") == report


def test_build_eval_stability_report_marks_single_run_baseline() -> None:
    run = _history_report(passed=36, task_count=36, failed_tasks=[])

    report = build_eval_stability_report([
        {"label": "full-36-v1", "path": "run1.json", "report": run},
    ])

    assert "# Eval Stability Report" in report
    assert "single-run baseline only" in report
    assert "Common tasks across all runs: **2**" in report
    assert "Unstable tasks: **none**" in report
    assert "| `python_add_tests` | pass | 1 | 0 | 0 | `stable_pass` |" in report


def test_build_eval_stability_report_marks_unstable_and_missing_tasks() -> None:
    first = _history_report(passed=2, task_count=2, failed_tasks=[])
    second = _history_report(passed=1, task_count=2, failed_tasks=["readme_update"])
    second["tasks"].append({"task_id": "new_task", "success": True})

    report = build_eval_stability_report([
        {"label": "run1", "path": "run1.json", "report": first},
        {"label": "run2", "path": "run2.json", "report": second},
    ])

    assert "repeated-run variance measured" in report
    assert "Unstable tasks: **`new_task`, `readme_update`**" in report
    assert "| `readme_update` | pass -> fail | 1 | 1 | 0 | `unstable` |" in report
    assert "| `new_task` | missing -> pass | 1 | 0 | 1 | `incomplete` |" in report


def test_build_stability_report_loads_labeled_paths_and_writes_output(tmp_path: Path) -> None:
    run_path = tmp_path / "run.json"
    output_path = tmp_path / "stability.md"
    run_path.write_text(json.dumps(_history_report(passed=2, task_count=2, failed_tasks=[])), encoding="utf-8")

    report = build_stability_report([f"full-36-v1={run_path}"], output_path=output_path)

    assert "full-36-v1" in report
    assert "2/2" in report
    assert output_path.read_text(encoding="utf-8") == report


def _history_report(
    passed: int,
    task_count: int,
    average_tool_calls: float = 1.0,
    cost: float = 0.0,
    shell_calls: int = 0,
    run_tests_calls: int = 0,
    failed_tasks: list[str] | None = None,
) -> dict:
    failed_task_ids = failed_tasks or []
    tasks = []
    for task_id in ["python_add_tests", "readme_update"]:
        tasks.append({
            "task_id": task_id,
            "success": task_id not in failed_task_ids,
        })
    return {
        "summary": {
            "label": "selected",
            "mode": "agent",
            "memory_enabled": True,
            "context_enabled": True,
            "retrieval_enabled": True,
            "task_count": task_count,
            "passed": passed,
            "success_rate": passed / task_count,
            "average_tool_calls": average_tool_calls,
            "average_duration": 12.5,
            "total_input_tokens": 100,
            "total_output_tokens": 20,
            "estimated_cost_usd": cost,
            "tool_counts": {
                "todo_write": 92,
                "run_tests": run_tests_calls,
                "shell": shell_calls,
                "git_diff": 2,
                "read_file": 49,
                "context_pack": 10,
                "edit_file": 21,
                "write_file": 2,
            },
        },
        "tasks": tasks,
    }
