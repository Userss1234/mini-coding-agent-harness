from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Callable, Mapping, Protocol, Sequence
from uuid import uuid4


DOCKER_ENV_KEYS = {
    "HOME",
    "PYTHONPATH",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONUNBUFFERED",
    "PYTEST_ADDOPTS",
}


@dataclass
class ExecutionResult:
    backend: str
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False
    error: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def output(self) -> str:
        return (self.stdout + self.stderr).strip()


class CommandExecutor(Protocol):
    backend: str
    python_executable: str
    workspace_path: str

    def describe(self) -> dict[str, object]: ...

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: int,
        env: Mapping[str, str] | None = None,
    ) -> ExecutionResult: ...


@dataclass(frozen=True)
class DockerExecutionConfig:
    image: str = "mini-coding-agent-harness-sandbox:latest"
    network: str = "none"
    cpus: str = "1.0"
    memory: str = "512m"
    pids_limit: int = 256
    user: str = "10001:10001"
    tmpfs_size: str = "64m"
    read_only_root: bool = True
    fallback_to_host: bool = False

    @classmethod
    def from_env(cls) -> DockerExecutionConfig:
        return cls(
            image=os.getenv("HARNESS_DOCKER_IMAGE", cls.image),
            network=os.getenv("HARNESS_DOCKER_NETWORK", cls.network),
            cpus=os.getenv("HARNESS_DOCKER_CPUS", cls.cpus),
            memory=os.getenv("HARNESS_DOCKER_MEMORY", cls.memory),
            pids_limit=int(os.getenv("HARNESS_DOCKER_PIDS_LIMIT", str(cls.pids_limit))),
            user=os.getenv("HARNESS_DOCKER_USER", cls.user),
            tmpfs_size=os.getenv("HARNESS_DOCKER_TMPFS_SIZE", cls.tmpfs_size),
            read_only_root=_env_bool("HARNESS_DOCKER_READ_ONLY_ROOT", cls.read_only_root),
            fallback_to_host=(os.getenv("HARNESS_DOCKER_FALLBACK", "").strip().lower() == "host"),
        )

    def validate(self) -> None:
        if not self.image.strip():
            raise ValueError("Docker image must be non-empty.")
        if not self.network.strip():
            raise ValueError("Docker network must be non-empty.")
        try:
            if float(self.cpus) <= 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Docker CPU limit must be a positive number.") from exc
        if not re.fullmatch(r"[1-9][0-9]*[bkmgBKMG]?", self.memory):
            raise ValueError("Docker memory limit must look like 512m or 1g.")
        if self.pids_limit <= 0:
            raise ValueError("Docker PID limit must be positive.")
        if not re.fullmatch(r"[0-9]+(?::[0-9]+)?", self.user):
            raise ValueError("Docker user must be a numeric UID or UID:GID.")
        if not re.fullmatch(r"[1-9][0-9]*[bkmgBKMG]?", self.tmpfs_size):
            raise ValueError("Docker tmpfs size must look like 64m or 1g.")


class HostExecutor:
    backend = "host"
    python_executable = sys.executable

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.workspace_path = str(self.workspace)

    def describe(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "workspace": self.workspace_path,
            "containerized": False,
            "network_isolated": False,
            "resource_limited": False,
        }

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: int,
        env: Mapping[str, str] | None = None,
    ) -> ExecutionResult:
        merged_env = os.environ.copy()
        if env:
            merged_env.update({str(key): str(value) for key, value in env.items()})
        return _run_subprocess(
            argv,
            cwd=self.workspace,
            timeout=timeout,
            env=merged_env,
            backend=self.backend,
            metadata=self.describe(),
        )


class DockerExecutor:
    backend = "docker"
    python_executable = "python"
    workspace_path = "/workspace"

    def __init__(
        self,
        workspace: Path,
        config: DockerExecutionConfig | None = None,
        docker_executable: str = "docker",
    ):
        self.workspace = workspace.resolve()
        self.config = config or DockerExecutionConfig.from_env()
        self.config.validate()
        self.docker_executable = docker_executable
        self._fallback = HostExecutor(self.workspace) if self.config.fallback_to_host else None

    def describe(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "workspace": str(self.workspace),
            "container_workspace": self.workspace_path,
            "containerized": True,
            "image": self.config.image,
            "network": self.config.network,
            "network_isolated": self.config.network == "none",
            "cpus": self.config.cpus,
            "memory": self.config.memory,
            "pids_limit": self.config.pids_limit,
            "user": self.config.user,
            "read_only_root": self.config.read_only_root,
            "resource_limited": True,
            "fallback_to_host": self.config.fallback_to_host,
        }

    def docker_argv(
        self,
        argv: Sequence[str],
        env: Mapping[str, str] | None = None,
        container_name: str | None = None,
    ) -> list[str]:
        workspace_text = str(self.workspace)
        if "," in workspace_text:
            raise ValueError("Docker bind-mount source cannot contain a comma.")
        command = [
            self.docker_executable,
            "run",
            "--rm",
        ]
        if container_name:
            command.extend(["--name", container_name])
        command.extend([
            "--stop-timeout",
            "1",
            "--network",
            self.config.network,
            "--cpus",
            self.config.cpus,
            "--memory",
            self.config.memory,
            "--pids-limit",
            str(self.config.pids_limit),
            "--user",
            self.config.user,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--workdir",
            self.workspace_path,
            "--mount",
            f"type=bind,source={workspace_text},target={self.workspace_path}",
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,size={self.config.tmpfs_size}",
        ])
        if self.config.read_only_root:
            command.append("--read-only")
        container_env = {
            "HOME": "/tmp",
            "PYTHONUNBUFFERED": "1",
        }
        if env:
            container_env.update({
                str(key): str(value)
                for key, value in env.items()
                if str(key) in DOCKER_ENV_KEYS
            })
        for key in sorted(container_env):
            command.extend(["--env", f"{key}={container_env[key]}"])
        command.append(self.config.image)
        command.extend(str(item) for item in argv)
        return command

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: int,
        env: Mapping[str, str] | None = None,
    ) -> ExecutionResult:
        if shutil.which(self.docker_executable) is None:
            return self._docker_unavailable(argv, timeout=timeout, env=env)
        container_name = f"mini-agent-{uuid4().hex[:12]}"
        docker_argv = self.docker_argv(argv, env, container_name=container_name)
        metadata = self.describe()
        metadata["container_name"] = container_name
        metadata["container_command"] = [str(item) for item in argv]
        metadata["forwarded_env_keys"] = sorted(
            str(key) for key in (env or {}) if str(key) in DOCKER_ENV_KEYS
        )
        return _run_subprocess(
            docker_argv,
            cwd=self.workspace,
            timeout=timeout,
            env=os.environ.copy(),
            backend=self.backend,
            metadata=metadata,
            timeout_cleanup=lambda: self._cleanup_container(container_name),
        )

    def _cleanup_container(self, container_name: str) -> bool:
        try:
            completed = subprocess.run(
                [self.docker_executable, "rm", "-f", container_name],
                cwd=self.workspace,
                env=os.environ.copy(),
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return completed.returncode == 0

    def _docker_unavailable(
        self,
        argv: Sequence[str],
        *,
        timeout: int,
        env: Mapping[str, str] | None,
    ) -> ExecutionResult:
        message = "Docker executable not found; install Docker or select the host execution backend."
        if self._fallback is None:
            metadata = self.describe()
            metadata["docker_available"] = False
            return ExecutionResult(
                backend=self.backend,
                returncode=127,
                stderr=message,
                error="docker_unavailable",
                metadata=metadata,
            )
        result = self._fallback.run(argv, timeout=timeout, env=env)
        result.metadata.update({
            "requested_backend": self.backend,
            "fallback_reason": "docker_unavailable",
            "docker_available": False,
        })
        return result


def build_executor(
    workspace: Path,
    backend: str | None = None,
) -> CommandExecutor:
    selected = (backend or os.getenv("HARNESS_EXECUTION_BACKEND", "host")).strip().lower()
    if selected == "host":
        return HostExecutor(workspace)
    if selected == "docker":
        return DockerExecutor(workspace)
    raise ValueError(f"Unsupported execution backend: {selected}")


def _run_subprocess(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    env: Mapping[str, str],
    backend: str,
    metadata: dict[str, object],
    timeout_cleanup: Callable[[], bool] | None = None,
) -> ExecutionResult:
    command = [str(item) for item in argv]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=dict(env),
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        if timeout_cleanup is not None:
            metadata["timeout_cleanup_attempted"] = True
            metadata["timeout_cleanup_succeeded"] = bool(timeout_cleanup())
        return ExecutionResult(
            backend=backend,
            returncode=None,
            stdout=_stream_text(exc.stdout),
            stderr=_stream_text(exc.stderr),
            duration_seconds=round(time.perf_counter() - started, 3),
            timed_out=True,
            error="timeout",
            metadata=metadata,
        )
    except FileNotFoundError as exc:
        return ExecutionResult(
            backend=backend,
            returncode=127,
            stderr=str(exc),
            duration_seconds=round(time.perf_counter() - started, 3),
            error="executable_not_found",
            metadata=metadata,
        )
    return ExecutionResult(
        backend=backend,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_seconds=round(time.perf_counter() - started, 3),
        metadata=metadata,
    )


def _stream_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
