from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from harness.execution import (
    DockerExecutionConfig,
    DockerExecutor,
    ExecutionResult,
    HostExecutor,
    build_executor,
)
from harness.tools import build_registry
from harness.trace import TraceLogger


def test_host_executor_records_backend_and_output(tmp_path: Path, monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="host-ok\n", stderr="")

    monkeypatch.setattr("harness.execution.subprocess.run", fake_run)
    executor = HostExecutor(tmp_path)

    result = executor.run(["python", "--version"], timeout=5, env={"PYTHONPATH": str(tmp_path)})

    assert result.returncode == 0
    assert result.output == "host-ok"
    assert result.backend == "host"
    assert result.metadata["containerized"] is False
    assert captured["command"] == ["python", "--version"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"]["PYTHONPATH"] == str(tmp_path)


def test_docker_executor_builds_isolated_command_and_filters_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="container-ok\n", stderr="")

    monkeypatch.setattr("harness.execution.shutil.which", lambda _: "C:/docker.exe")
    monkeypatch.setattr("harness.execution.subprocess.run", fake_run)
    executor = DockerExecutor(tmp_path)

    result = executor.run(
        ["python", "-m", "pytest", "tests"],
        timeout=30,
        env={"PYTHONPATH": "/workspace", "DEEPSEEK_API_KEY": "must-not-pass"},
    )

    command = captured["command"]
    assert result.returncode == 0
    assert result.backend == "docker"
    assert result.metadata["network_isolated"] is True
    assert result.metadata["forwarded_env_keys"] == ["PYTHONPATH"]
    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == command[command.index("--network"):command.index("--network") + 2]
    assert ["--cap-drop", "ALL"] == command[command.index("--cap-drop"):command.index("--cap-drop") + 2]
    assert ["--security-opt", "no-new-privileges"] == command[command.index("--security-opt"):command.index("--security-opt") + 2]
    assert "--read-only" in command
    assert "DEEPSEEK_API_KEY" not in " ".join(command)
    assert command[-5:] == [
        "mini-coding-agent-harness-sandbox:latest",
        "python",
        "-m",
        "pytest",
        "tests",
    ]
    assert captured["kwargs"]["shell"] is False


def test_docker_executor_fails_closed_when_docker_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("harness.execution.shutil.which", lambda _: None)
    executor = DockerExecutor(tmp_path)

    result = executor.run(["python", "--version"], timeout=5)

    assert result.returncode == 127
    assert result.backend == "docker"
    assert result.error == "docker_unavailable"
    assert result.metadata["docker_available"] is False
    assert "install Docker" in result.output


def test_docker_executor_removes_container_after_timeout(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(command, 1, output="partial output")
        return SimpleNamespace(returncode=0, stdout="removed", stderr="")

    monkeypatch.setattr("harness.execution.shutil.which", lambda _: "C:/docker.exe")
    monkeypatch.setattr("harness.execution.subprocess.run", fake_run)
    executor = DockerExecutor(tmp_path)

    result = executor.run(["python", "slow.py"], timeout=1)

    assert result.timed_out is True
    assert result.output == "partial output"
    assert result.metadata["timeout_cleanup_attempted"] is True
    assert result.metadata["timeout_cleanup_succeeded"] is True
    container_name = result.metadata["container_name"]
    assert calls[1] == ["docker", "rm", "-f", container_name]


def test_docker_executor_supports_explicit_host_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("harness.execution.shutil.which", lambda _: None)
    monkeypatch.setattr(
        "harness.execution.subprocess.run",
        lambda command, **kwargs: SimpleNamespace(returncode=0, stdout="fallback-ok", stderr=""),
    )
    executor = DockerExecutor(
        tmp_path,
        DockerExecutionConfig(fallback_to_host=True),
    )

    result = executor.run(["python", "--version"], timeout=5)

    assert result.returncode == 0
    assert result.backend == "host"
    assert result.metadata["requested_backend"] == "docker"
    assert result.metadata["fallback_reason"] == "docker_unavailable"


def test_docker_config_rejects_unsafe_resource_values() -> None:
    with pytest.raises(ValueError, match="CPU"):
        DockerExecutionConfig(cpus="0").validate()
    with pytest.raises(ValueError, match="memory"):
        DockerExecutionConfig(memory="unlimited").validate()
    with pytest.raises(ValueError, match="user"):
        DockerExecutionConfig(user="root").validate()


def test_build_executor_rejects_unknown_backend(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported execution backend"):
        build_executor(tmp_path, "vm")


class RecordingDockerExecutor:
    backend = "docker"
    python_executable = "python"
    workspace_path = "/workspace"

    def __init__(self):
        self.calls = []

    def describe(self):
        return {
            "backend": "docker",
            "containerized": True,
            "network_isolated": True,
            "resource_limited": True,
        }

    def run(self, argv, *, timeout, env=None):
        self.calls.append({"argv": list(argv), "timeout": timeout, "env": dict(env or {})})
        output = "1 passed" if "pytest" in argv else ""
        return ExecutionResult(
            backend="docker",
            returncode=0,
            stdout=output,
            metadata=self.describe(),
        )


def test_tool_registry_routes_compile_tests_and_shell_through_executor(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    executor = RecordingDockerExecutor()
    registry = build_registry(
        tmp_path,
        TraceLogger(tmp_path / "trace.jsonl"),
        executor=executor,
    )

    compiled = registry.call("run_py_compile")
    tested = registry.call("run_tests", timeout=30)
    shelled = registry.call("shell", command="python --version")
    policy = registry.call("permission_policy")

    assert compiled.ok
    assert tested.ok
    assert shelled.ok
    assert executor.calls[0]["argv"][1] == "-c"
    assert "sample.py" in executor.calls[0]["argv"]
    assert executor.calls[1]["argv"][1:3] == ["-m", "pytest"]
    assert executor.calls[2]["argv"] == ["python", "--version"]
    assert all(result.metadata["execution_backend"] == "docker" for result in [compiled, tested, shelled])
    assert policy.metadata["execution_backend"] == "docker"
    assert policy.metadata["container_isolation"] is True
    assert policy.metadata["os_sandbox"] is False
