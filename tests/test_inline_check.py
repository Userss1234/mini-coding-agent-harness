from pathlib import Path
from unittest.mock import patch

import pytest

from harness.execution import (
    DockerExecutionConfig,
    DockerExecutor,
    ExecutionResult,
    ReadOnlyDockerExecutor,
)
from harness.tools import build_registry
from harness.trace import TraceLogger


def registry_at(path, config=None):
    return build_registry(path, TraceLogger(path / "trace.jsonl"),
                          executor=DockerExecutor(path, config or DockerExecutionConfig()))


def test_inline_check_uses_read_only_mount_and_direct_python_argv(tmp_path: Path):
    captured = []

    def execute(self, argv, *, timeout, env=None):
        captured.append((self, argv, timeout, env))
        return ExecutionResult("docker", 0, stdout="checks passed", metadata=self.describe())

    code = "from source import value\nassert value > 0; print('checks passed')"
    with patch.object(ReadOnlyDockerExecutor, "run", execute):
        result = registry_at(tmp_path).call("run_python_check", code=code, timeout=12)
    assert result.ok
    checker, argv, timeout, env = captured[0]
    assert argv[:4] == ["python", "-I", "-B", "-c"] and argv[-1] == code
    assert timeout == 12 and env["PYTHONDONTWRITEBYTECODE"] == "1"
    command = checker.docker_argv(argv)
    mount = command[command.index("--mount") + 1]
    assert mount.endswith(",readonly") and "target=/workspace" in mount
    assert result.metadata["execution"]["workspace_read_only"]
    assert "run_python_check" not in build_registry(
        tmp_path, TraceLogger(tmp_path / "host.jsonl"), execution_backend="host").names()


@pytest.mark.parametrize("config", [
    DockerExecutionConfig(network="bridge"), DockerExecutionConfig(user="0:0"),
    DockerExecutionConfig(read_only_root=False), DockerExecutionConfig(fallback_to_host=True),
])
def test_inline_checks_reject_unsafe_profiles_without_execution(tmp_path: Path, config):
    with patch.object(ReadOnlyDockerExecutor, "run") as run:
        result = registry_at(tmp_path, config).call("run_python_check", code="assert True")
    assert not result.ok
    run.assert_not_called()


@pytest.mark.parametrize("args", [
    {"code": ""}, {"code": "x" * 12001}, {"code": "\u4e2d" * 5000},
    {"code": "assert True", "timeout": True}, {"code": "assert True", "timeout": 61},
])
def test_inline_check_validates_limits_before_execution(tmp_path: Path, args):
    with patch.object(ReadOnlyDockerExecutor, "run") as run:
        result = registry_at(tmp_path).call("run_python_check", **args)
    assert not result.ok
    run.assert_not_called()


def test_inline_check_does_not_retry_unknown_execution_outcomes(tmp_path: Path):
    with patch.object(ReadOnlyDockerExecutor, "run", side_effect=ConnectionError("interrupted")) as run:
        result = registry_at(tmp_path).call("run_python_check", code="assert True")
    assert not result.ok and run.call_count == 1


def test_inline_check_preserves_failure_timeout_and_output_truncation(tmp_path: Path):
    with patch.object(ReadOnlyDockerExecutor, "run", return_value=ExecutionResult(
            "docker", None, stdout="x" * 9000, timed_out=True, error="timeout")):
        result = registry_at(tmp_path).call("run_python_check", code="assert False")
    assert not result.ok and len(result.output) == 8000
    assert result.metadata["timed_out"] and result.metadata["output_truncated"]
