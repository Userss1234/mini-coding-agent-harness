from __future__ import annotations

from pathlib import Path

from harness.mcp_smoke import run_mcp_smoke


def test_run_mcp_smoke_writes_protocol_report(tmp_path: Path) -> None:
    (tmp_path / "MCP.md").write_text("# MCP\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")

    report = run_mcp_smoke(
        tmp_path,
        tmp_path / "mcp_trace.jsonl",
        tmp_path / "MCP_SMOKE.md",
    )

    assert "# MCP Smoke Report" in report
    assert "tools" in report
    assert "resources" in report
    assert "prompts" in report
    assert "`permission_policy`" in report
    assert (tmp_path / "MCP_SMOKE.md").exists()
    assert "transport" in (tmp_path / "mcp_trace.jsonl").read_text(encoding="utf-8")
