# Docker Sandbox Smoke Report

## Summary

- Status: **pass**
- Execution backend: **docker**
- Return code: **0**
- Timed out: **no**
- Error: **none**

## Sandbox Policy

| Boundary | Value |
|---|---|
| Image | `mini-coding-agent-harness-sandbox:latest` |
| Network | `none` |
| CPU limit | `1.0` |
| Memory limit | `512m` |
| PID limit | `256` |
| User | `10001:10001` |
| Read-only root | `True` |
| Host fallback | `False` |

## Runtime Check

```text
uid=10001 workspace=ok network=blocked
```

## Interpretation

A `pass` verifies non-root execution, the workspace bind mount, and blocked outbound networking inside the configured image. `blocked` means Docker was unavailable and no container claim should be made. Unit tests still validate command construction, fail-closed behavior, environment filtering, resource flags, and timeout cleanup.
