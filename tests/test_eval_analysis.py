from __future__ import annotations

import json
from pathlib import Path

from harness.eval_analysis import analyze_eval_reports, classify_failure


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
