from __future__ import annotations

from pathlib import Path

from harness.demo import run_demo


def test_run_demo_creates_bugfix_report_trace_and_workspace(tmp_path: Path) -> None:
    result = run_demo("python_bugfix", tmp_path / "demo")

    assert result.success
    assert result.report_path.exists()
    assert result.trace_path.exists()
    assert result.html_path.exists()
    assert "run_tests" in result.report
    assert "edit_file" in result.report
    assert "return a + b" in (result.workspace / "calculator.py").read_text(encoding="utf-8")
    assert "tool_call" in result.trace_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in result.html_path.read_text(encoding="utf-8").lower()
