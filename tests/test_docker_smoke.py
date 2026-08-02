from __future__ import annotations

from pathlib import Path

from harness.docker_smoke import run_docker_smoke
from harness.execution import ExecutionResult


class FakeDockerExecutor:
    backend = "docker"
    python_executable = "python"
    workspace_path = "/workspace"

    def __init__(self, result: ExecutionResult):
        self.result = result
        self.calls = []

    def describe(self):
        return {
            "image": "sandbox:test",
            "network": "none",
            "cpus": "1.0",
            "memory": "512m",
            "pids_limit": 256,
            "user": "10001:10001",
            "read_only_root": True,
            "fallback_to_host": False,
        }

    def run(self, argv, *, timeout, env=None):
        self.calls.append({"argv": argv, "timeout": timeout, "env": env})
        return self.result


def test_docker_smoke_writes_pass_report(tmp_path: Path) -> None:
    executor = FakeDockerExecutor(ExecutionResult(
        backend="docker",
        returncode=0,
        stdout="uid=10001 workspace=ok network=blocked",
    ))
    output_path = tmp_path / "smoke.md"

    report = run_docker_smoke(tmp_path, output_path, executor=executor)

    assert "Status: **pass**" in report
    assert "uid=10001 workspace=ok network=blocked" in report
    assert "| Network | `none` |" in report
    assert output_path.read_text(encoding="utf-8") == report
    assert executor.calls[0]["env"] == {"PYTHONPATH": "/workspace"}


def test_docker_smoke_marks_unavailable_runtime_as_blocked(tmp_path: Path) -> None:
    executor = FakeDockerExecutor(ExecutionResult(
        backend="docker",
        returncode=127,
        stderr="Docker executable not found",
        error="docker_unavailable",
    ))

    report = run_docker_smoke(tmp_path, executor=executor)

    assert "Status: **blocked**" in report
    assert "Error: **docker_unavailable**" in report
    assert "no container claim should be made" in report
