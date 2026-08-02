# Docker Execution Sandbox

The harness can route `shell`, `run_tests`, and `run_py_compile` through a pluggable command executor. Host execution remains the default. Docker execution is opt-in and uses the same tool permission checks before a container is started.

## Build

```powershell
docker build --file docker/sandbox/Dockerfile --tag mini-coding-agent-harness-sandbox:latest .
```

The build context excludes `.env`, Git metadata, virtual environments, reports, and generated eval workspaces through `.dockerignore`.

## Run

Global CLI options must appear before the subcommand:

```powershell
python main.py --execution-backend docker manual
python main.py --execution-backend docker eval --mode scripted --task syntax_check --task pytest_suite
python main.py docker-smoke --output artifacts/DOCKER_SANDBOX_SMOKE.md
```

`docker-smoke` verifies that the configured image runs as non-root, can read the mounted workspace, and cannot open an outbound network connection.

## Default Boundaries

| Boundary | Default |
|---|---|
| Image | `mini-coding-agent-harness-sandbox:latest` |
| Network | `none` |
| CPU | `1.0` |
| Memory | `512m` |
| PID limit | `256` |
| User | `10001:10001` |
| Root filesystem | read-only |
| Temporary storage | `/tmp` tmpfs, 64 MiB, `noexec,nosuid` |
| Linux capabilities | all dropped |
| Privilege escalation | `no-new-privileges` |
| Workspace mount | `/workspace`, read-write |

The workspace stays writable because file edits are performed by permission-checked harness tools and some test suites need temporary project output. The container root filesystem remains read-only.

Each run receives a unique container name. If the client-side timeout fires, the executor attempts `docker rm -f` so detached work is not left behind.

## Configuration

Use the `HARNESS_DOCKER_*` variables documented in `.env.example`. Only a small allowlist of execution variables is forwarded into the container; provider keys and the host environment are not copied into container arguments.

Docker selection fails closed when the CLI is missing. Set `HARNESS_DOCKER_FALLBACK=host` only when an explicit non-isolated fallback is acceptable. Fallback use is recorded in tool metadata.

## Threat Boundary

Docker adds process, filesystem, network, capability, and cgroup boundaries. It is not a VM boundary, and mounting a writable workspace still gives the container access to that workspace. Keep the harness path/write permission checks enabled and do not describe this as an absolute security sandbox.

## Validation

Unit tests validate Docker argument construction, secret-environment filtering, resource flags, fail-closed behavior, explicit fallback, tool routing, and timeout cleanup without requiring Docker locally. GitHub Actions builds the image and requires the runtime smoke report to pass.
