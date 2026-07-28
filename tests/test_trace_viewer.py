from __future__ import annotations

from pathlib import Path

from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.trace_viewer import (
    build_trace_report,
    load_trace_events,
    summarize_permission_events,
    summarize_trace_events,
)


def test_build_trace_report_renders_tool_statuses(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("old old\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    registry.call("read_file", path="sample.txt")
    registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")

    html = build_trace_report(trace.path, tmp_path / "TRACE.html")

    assert "Mini Coding Agent Trace" in html
    assert "Tool calls" in html
    assert "Failed tools" in html
    assert "read_file" in html
    assert "edit_file" in html
    assert "failed" in html
    assert 'id="trace-search"' in html
    assert 'id="event-filter"' in html
    assert 'id="tool-filter"' in html
    assert 'id="status-filter"' in html
    assert 'class="event-row"' in html
    assert "Tool-call mix:" in html
    assert (tmp_path / "TRACE.html").exists()


def test_build_trace_report_renders_permission_audit(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("hello\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    registry.call("read_file", path="sample.txt")
    registry.call("shell", command="git push origin main")
    registry.call("shell", command="echo hello > out.txt")

    html = build_trace_report(trace.path, tmp_path / "TRACE.html")
    events, _ = load_trace_events(trace.path)
    audit = summarize_permission_events([item for item in events if item.get("event") == "tool_call"])

    assert audit["allowed_count"] == 1
    assert audit["blocked_count"] == 2
    assert audit["decisions"]["blocked_git_not_allowlisted"] == 1
    assert audit["decisions"]["blocked_shell_operator"] == 1
    assert "Allowed calls" in html
    assert "Blocked calls" in html
    assert "Failed after allow" in html
    assert "Blocked Permission Calls" in html
    assert "blocked_git_not_allowlisted" in html
    assert "blocked_shell_operator" in html
    assert "No blocked calls recorded" not in html
    assert not (tmp_path / "out.txt").exists()


def test_load_trace_events_counts_parse_errors(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        '{"event": "session_start", "timestamp": "now", "data": {}}\n'
        'not json\n',
        encoding="utf-8",
    )

    events, parse_errors = load_trace_events(trace_path)

    assert len(events) == 1
    assert parse_errors == 1


def test_summarize_trace_events_aggregates_duration_usage_and_tools() -> None:
    events = [
        {
            "event": "session_start",
            "timestamp": "2026-07-28T10:00:00+00:00",
            "data": {},
        },
        {
            "event": "tool_call",
            "timestamp": "2026-07-28T10:00:01+00:00",
            "data": {"tool": "read_file", "ok": True},
        },
        {
            "event": "agent_response",
            "timestamp": "2026-07-28T10:00:02+00:00",
            "data": {
                "turn": 0,
                "usage": {"input_tokens": 120, "output_tokens": 30},
            },
        },
        {
            "event": "agent_response",
            "timestamp": "2026-07-28T10:00:03.500000+00:00",
            "data": {
                "turn": 1,
                "usage": {"input_tokens": 80, "output_tokens": 20},
            },
        },
    ]

    summary = summarize_trace_events(events)

    assert summary["duration_seconds"] == 3.5
    assert summary["model_turns"] == 2
    assert summary["input_tokens"] == 200
    assert summary["output_tokens"] == 50
    assert summary["tools"] == {"read_file": 1}
