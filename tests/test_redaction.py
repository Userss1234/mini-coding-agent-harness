from __future__ import annotations

import json

from harness.redaction import REDACTED, redact
from harness.tools import Tool, ToolResult, build_registry
from harness.trace import TraceLogger, preview
from harness.trace_viewer import build_trace_report


def test_nested_redaction_preserves_numeric_usage_and_live_values(monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "opaque-sensitive-value")
    original = {"password": "short", "nested": [{"message": "opaque-sensitive-value"}],
                "input_tokens": 123, "output_tokens": 45, "token": 123, "total_tokens": "secret"}
    cleaned = redact(original)
    assert original["password"] == "short"
    assert cleaned == {"password": REDACTED, "nested": [{"message": REDACTED}],
                       "input_tokens": 123, "output_tokens": 45, "token": REDACTED, "total_tokens": REDACTED}


def test_free_text_known_tokens_quoted_json_bearer_and_private_keys():
    values = ["ghp_" + "a" * 36, "github_pat_" + "b" * 50, "sk-" + "c" * 30,
              "Bearer abcdefghijklmnop", '{"api_key": "quoted-value"}',
              "-----BEGIN PRIVATE KEY-----\nmaterial\n-----END PRIVATE KEY-----"]
    for value in values:
        cleaned = redact(value)
        assert REDACTED in cleaned and cleaned != value
        assert redact(cleaned) == cleaned


def test_trace_and_html_redact_args_outputs_errors_without_changing_tool_result(tmp_path, monkeypatch):
    secret = "long-sensitive-fixture-value"
    monkeypatch.setenv("TRACE_TEST_SECRET", secret)
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace)
    registry.register(Tool("echo_private", "fixture", {}, lambda: ToolResult(True, secret)))
    result = registry.call("echo_private")
    assert result.output == secret
    trace.log("error", exception=f"Bearer {secret}", nested={"api_key": "other"})
    raw = trace.path.read_text()
    assert secret not in raw and REDACTED in raw and '"other"' not in raw
    # Old, unsanitized traces are also redacted before HTML export.
    trace.path.write_text(json.dumps({"event": "old", "data": {"output": secret}}) + "\n")
    html = build_trace_report(trace.path, tmp_path / "trace.html")
    assert secret not in html and REDACTED in html


def test_preview_redacts_before_truncation(monkeypatch):
    secret = "sensitive-value-" * 200
    monkeypatch.setenv("PREVIEW_API_KEY", secret)
    assert preview(secret, limit=20) == REDACTED
