from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from harness.agent import run_agent
from harness.execution import DockerExecutor, ExecutionResult, HostExecutor, ReadOnlyDockerExecutor
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.verification import VerificationConfig, VerificationController
from harness.workspace import WorkspaceSession
from tests.test_agent import FakeBlock, FakeClient, FakeResponse


@pytest.fixture
def fixture_checker(monkeypatch):
    def run(self, argv, *, timeout, env=None):
        # Only the trusted syntax compiler runs on these synthetic test files.
        assert argv[4].startswith("import json,sys,tokenize")
        result = subprocess.run([sys.executable, *argv[1:]], cwd=self.workspace,
                                text=True, capture_output=True, timeout=timeout)
        return ExecutionResult("docker", result.returncode, result.stdout, result.stderr)
    monkeypatch.setattr(ReadOnlyDockerExecutor, "run", run)


def setup_registry(tmp_path, max_repairs=2):
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"),
                              executor=DockerExecutor(tmp_path), allow_write=True)
    registry.verification_controller = VerificationController(
        tmp_path, registry.executor, VerificationConfig(max_repairs=max_repairs))
    return registry


def test_model_edit_diagnosis_repair_and_verified_completion(tmp_path, fixture_checker):
    registry = setup_registry(tmp_path)
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="bad", name="write_file",
                                           input={"path": "work.py", "content": "def ("})]),
        FakeResponse("end_turn", [FakeBlock("text", text="done too early")]),
        FakeResponse("tool_use", [FakeBlock("tool_use", id="fix", name="write_file",
                                           input={"path": "work.py", "content": "value = 1\n"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="verified work.py")]),
    ])
    answer = run_agent("Fix work.py", registry, client=client, model="fixture",
                       retrieval_preflight=False, run_store=store)
    assert answer == "verified work.py"
    state = store.load(store.list_runs()[0]["id"])
    assert state["status"] == "completed"
    assert state["verification_state"]["repairs"] == 1
    assert state["verification_state"]["last_report"]["status"] == "passed"
    events = [json.loads(line) for line in registry.trace.path.read_text().splitlines()]
    reports = [e["data"] for e in events if e["event"] == "completion_verification"]
    assert [r["status"] for r in reports] == ["failed", "passed"]
    assert reports[0]["checks"][0]["diagnostics"][0]["code"] == "SyntaxError"


def test_repeated_failed_final_proposal_stops_without_blind_loop(tmp_path, fixture_checker):
    registry = setup_registry(tmp_path)
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="bad", name="write_file",
                                           input={"path": "work.py", "content": "def ("})]),
        FakeResponse("end_turn", [FakeBlock("text", text="done")]),
        FakeResponse("end_turn", [FakeBlock("text", text="still done")]),
    ])
    assert "verification_failed" in run_agent("fix", registry, client=client,
                                               retrieval_preflight=False)
    assert registry.verification_controller.state["repairs"] == 1


def test_unavailable_check_cannot_be_passed_or_repaired(tmp_path, monkeypatch):
    registry = setup_registry(tmp_path)
    controller = registry.verification_controller
    controller.start()
    (tmp_path / "work.py").write_text("value = 1\n")
    monkeypatch.setattr(ReadOnlyDockerExecutor, "run", lambda *a, **k: ExecutionResult(
        "docker", None, timed_out=True, error="timeout"))
    result = controller.check()
    assert result["status"] == "unverified"
    assert not controller.repair_allowed(result)


def test_source_mutation_during_checks_invalidates_pass(tmp_path, monkeypatch):
    controller = setup_registry(tmp_path).verification_controller
    controller.start()
    (tmp_path / "work.py").write_text("value = 1\n")

    def run(*args, **kwargs):
        (tmp_path / "work.py").write_text("value = 2\n")
        return ExecutionResult("docker", 0, stdout="[]")

    monkeypatch.setattr(ReadOnlyDockerExecutor, "run", run)
    assert controller.check()["status"] == "unverified"


@pytest.mark.parametrize("options", [{"checks": ()}, {"checks": ("shell",)},
                                      {"timeout": 0}, {"max_repairs": 4},
                                      {"test_target": "../secret"}, {"test_target": "-x"}])
def test_invalid_operator_profile_rejected(options):
    with pytest.raises(ValueError):
        VerificationConfig(**options)


def test_configuration_outside_workspace_and_no_host_fallback(tmp_path):
    workspace = tmp_path / "source"
    workspace.mkdir()
    config = workspace / "checks.json"
    config.write_text('{"version":1,"checks":["syntax"]}')
    with pytest.raises(ValueError, match="outside"):
        VerificationConfig.load(config, workspace)
    with pytest.raises(ValueError, match="Docker"):
        VerificationController(workspace, HostExecutor(workspace), VerificationConfig())


def test_verification_baseline_retains_token_named_paths_after_redaction(tmp_path):
    from harness.redaction import redact

    (tmp_path / "tokenizer.py").write_text("value=1\n")
    controller = setup_registry(tmp_path).verification_controller
    controller.start()
    baseline = redact(controller.state)["baseline"]
    assert baseline[0]["path"] == "tokenizer.py"
    assert len(baseline[0]["sha256"]) == 64


def test_ruff_and_missing_pytest_target_are_honest(tmp_path, monkeypatch):
    config = VerificationConfig(checks=("ruff", "pytest"))
    controller = VerificationController(tmp_path, DockerExecutor(tmp_path), config)
    controller.start()
    (tmp_path / "work.py").write_text("value = 1\n")
    monkeypatch.setattr(ReadOnlyDockerExecutor, "run", lambda *a, **k: ExecutionResult(
        "docker", 1, stderr="No module named ruff"))
    result = controller.check()
    assert result["status"] == "unverified"
    assert [c["status"] for c in result["checks"]] == ["unverified", "unverified"]


@pytest.mark.skipif(os.getenv("HARNESS_LIVE_DOCKER") != "1", reason="Opt-in actual Docker verification")
def test_actual_docker_verification_repairs_before_completion_and_preserves_source(tmp_path):
    from harness.execution import DockerExecutionConfig
    from harness.run_controls import RunControlConfig, RunControls

    source = tmp_path / "source"
    source.mkdir()
    (source / "mathlib.py").write_text("def add(a, b):\n    return a-b\n")
    (source / "tests").mkdir()
    (source / "tests/test_mathlib.py").write_text("from mathlib import add\ndef test_add(): assert add(2, 3) == 5\n")
    (source / "pytest.ini").write_text("[pytest]\naddopts=--ignore=tests/test_mathlib.py\n")
    original = (source / "mathlib.py").read_bytes()
    session = WorkspaceSession.create(source, tmp_path / "isolated")
    executor = DockerExecutor(session.workspace, DockerExecutionConfig(
        image="mini-coding-agent-harness-verification:latest"))
    registry = build_registry(session.workspace, TraceLogger(session.path / "trace.jsonl"),
                              executor=executor, allow_write=True)
    registry.verification_controller = VerificationController(
        session.workspace, executor, VerificationConfig(checks=("syntax", "ruff", "pytest")))
    registry.run_controls = RunControls(RunControlConfig(max_tools=4, max_seconds=120), session.workspace)
    store = SQLiteRunStore(session.path / "runs.sqlite3")
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="wrong", name="write_file",
            input={"path": "mathlib.py", "content": "def add(a, b):\n    return a*b\n"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="premature completion")]),
        FakeResponse("tool_use", [FakeBlock("tool_use", id="right", name="write_file",
            input={"path": "mathlib.py", "content": "def add(a, b):\n    return a+b\n"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="checks passed for mathlib.py")]),
    ])
    assert run_agent("repair addition", registry, client=client, model="deterministic-driver",
                      run_store=store, retrieval_preflight=False) == "checks passed for mathlib.py"
    assert (source / "mathlib.py").read_bytes() == original
    events = [json.loads(line) for line in registry.trace.path.read_text().splitlines()]
    reports = [e["data"] for e in events if e["event"] == "completion_verification"]
    assert [report["status"] for report in reports] == ["failed", "passed"]
    assert reports[0]["checks"][-1]["status"] == "failed"
    assert all(check["status"] == "passed" for check in reports[1]["checks"])
    state = store.load(store.list_runs()[0]["id"])
    assert state["control_state"]["tools"] == 2
    report_path = os.getenv("HARNESS_VERIFICATION_REPORT")
    if report_path:
        from pathlib import Path
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "driver": "injected deterministic client",
            "execution": "actual restricted read-only Docker checks", "source_unchanged": True,
            "observed_checks": reports, "run_status": state["status"],
            "control_state": state["control_state"]}, indent=2) + "\n", encoding="utf-8")
