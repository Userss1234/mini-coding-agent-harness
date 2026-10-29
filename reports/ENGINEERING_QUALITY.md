# Engineering Quality Baseline

## Scope

This baseline makes future protocol, persistence, retrieval, and Docker changes pass the same
repeatable checks before they enter the integration workflow.

## Enforced Gates

- Runtime dependencies are compiled into `requirements.lock`.
- Development and test dependencies are compiled into `requirements-dev.lock`.
- Ruff enforces import order, Python modernization, and core error rules.
- mypy checks `main.py` and all `harness` modules while treating third-party packages as external.
- pytest measures branch coverage for `harness` and fails below 75%.
- GitHub Actions runs the quality gates on Python 3.10, 3.11, and 3.12 before integration jobs.
- The Docker sandbox installs the same locked runtime dependency graph as CI.

## Local Verification

Follow-up on 2026-10-28: actual local Docker/WSL, authenticated MCP/hybrid and paid agent
ABBA validation are now recorded in [LIVE_VALIDATION_20261028.md](LIVE_VALIDATION_20261028.md).
The per-priority environment limitations below describe their original stage, not the current
Docker installation. Cross-version remote CI for these local commits remains unrun.

Current local verification uses Windows and Python 3.12.2 with the development environment:

| Check | Result |
|---|---|
| Ruff | pass, 0 findings |
| mypy | pass, 33 source files |
| pytest | pass, 304 tests; 1 optional symlink skip |
| Branch coverage | 82.94% (75% required) |
| Scripted benchmark | 40/40 pass |
| Python compilation | pass |

The generated coverage database and benchmark workspaces remain local and are ignored by Git.

The 2026-10-29 [requirement/budget guidance experiment](VERIFICATION_GUIDANCE_20261029.md)
adds optional plan metadata and an off-by-default advisory mode. Its actual agent acceptance
remains 9/12, with new context/cleanup limits; this is not a correctness or success-rate gain.
GitHub Actions is the authoritative cross-version and Docker runtime check.

Priority 1 adds durable SQLite run recovery. The current stage is locally verified and not yet
pushed; the existing remote CI results predate this change. See `reports/RUN_RECOVERY.md`.

Priority 2 adds budgeted context replacement and persisted structured summaries, with local
long-task and real process-restart evidence in `reports/CONTEXT_WINDOW.md`.

Priority 3 adds isolated copies, content-bound terminal review, conflict-aware source application,
application recovery and shared trace/storage/HTML redaction. See `reports/WORKSPACE_ISOLATION.md`.
Docker is not installed locally for this stage; Docker command-policy/cleanup tests pass, but
new Docker runtime and cross-version integration validation await the user's combined push.

Priority 4 separates public behavioral challenges from compatibility regression, protects
external acceptance, adds optional AST chunking, and measures ranking, cache observations and
evidence-path follow-up. See `reports/EVALUATION_CREDIBILITY.md`. New real Docker/hybrid/agent
counterbalanced runs remain unperformed locally; reference acceptance and fixture controllers
are not model scores.

The first ownership split moved the deterministic task catalog and fixtures into
`harness/eval_tasks.py`. `harness/evaluation.py` decreased from 2,998 to 1,277 lines while retaining
the original task IDs and compatibility export used by existing callers. Post-split verification
passed 177 tests at 79.31% branch coverage and the 40/40 scripted benchmark.

The second ownership split moved workspace path checks, transient-error classification, and
Shell/Git allowlist decisions from `harness/tools.py` into `harness/permissions.py`. The registry
remains the sole enforcement point, and compatibility exports preserve the existing `harness.tools`
surface. Focused policy tests cover path escape, retry classification, shell operators, malformed
commands, and read-only Git boundaries. Post-split verification passed 187 tests at 79.43% branch
coverage and the 40/40 scripted benchmark.

## Claim Boundary

This report proves a repeatable engineering gate, not complete static typing or exhaustive test
coverage. Third-party package internals are not traversed by mypy, and the global coverage result
contains modules exercised through subprocess smoke commands that appear as uncovered in the parent
process.
