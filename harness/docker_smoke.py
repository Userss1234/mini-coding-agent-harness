from __future__ import annotations

from pathlib import Path
from typing import Any

from .execution import CommandExecutor, DockerExecutor


SMOKE_SCRIPT = """import os
import pathlib
import socket

assert os.getuid() != 0, "container must run as non-root"
assert pathlib.Path("README.md").is_file(), "workspace bind mount is missing"
sock = socket.socket()
sock.settimeout(1.0)
try:
    sock.connect(("1.1.1.1", 53))
except OSError:
    network = "blocked"
else:
    sock.close()
    raise AssertionError("container network is not isolated")
print(f"uid={os.getuid()} workspace=ok network={network}")
"""


def run_docker_smoke(
    workspace: Path,
    output_path: Path | None = None,
    executor: CommandExecutor | None = None,
) -> str:
    workspace = workspace.resolve()
    active_executor = executor or DockerExecutor(workspace)
    result = active_executor.run(
        [active_executor.python_executable, "-c", SMOKE_SCRIPT],
        timeout=30,
        env={"PYTHONPATH": active_executor.workspace_path},
    )
    policy = active_executor.describe()
    if result.error == "docker_unavailable":
        status = "blocked"
    elif result.returncode == 0 and result.backend == "docker":
        status = "pass"
    else:
        status = "fail"
    report = _format_docker_smoke_report(status, result, policy)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    return report


def _format_docker_smoke_report(status: str, result: Any, policy: dict[str, object]) -> str:
    output = result.output or "(no output)"
    return f"""# Docker Sandbox Smoke Report

## Summary

- Status: **{status}**
- Execution backend: **{result.backend}**
- Return code: **{result.returncode if result.returncode is not None else 'none'}**
- Timed out: **{'yes' if result.timed_out else 'no'}**
- Error: **{result.error or 'none'}**

## Sandbox Policy

| Boundary | Value |
|---|---|
| Image | `{policy.get('image', 'unknown')}` |
| Network | `{policy.get('network', 'unknown')}` |
| CPU limit | `{policy.get('cpus', 'unknown')}` |
| Memory limit | `{policy.get('memory', 'unknown')}` |
| PID limit | `{policy.get('pids_limit', 'unknown')}` |
| User | `{policy.get('user', 'unknown')}` |
| Read-only root | `{policy.get('read_only_root', 'unknown')}` |
| Host fallback | `{policy.get('fallback_to_host', 'unknown')}` |

## Runtime Check

```text
{output}
```

## Interpretation

A `pass` verifies non-root execution, the workspace bind mount, and blocked outbound networking inside the configured image. `blocked` means Docker was unavailable and no container claim should be made. Unit tests still validate command construction, fail-closed behavior, environment filtering, resource flags, and timeout cleanup.
"""
