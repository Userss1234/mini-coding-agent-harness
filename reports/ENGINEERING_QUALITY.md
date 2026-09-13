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

Validated on Python 3.10 with the committed development lock:

| Check | Result |
|---|---|
| Ruff | pass, 0 findings |
| mypy | pass, 21 source files |
| pytest | pass, 177 tests |
| Branch coverage | 79.28% (75% required) |
| Scripted benchmark | 40/40 pass |
| Python compilation | pass |

The generated coverage database and benchmark workspaces remain local and are ignored by Git.
GitHub Actions is the authoritative cross-version and Docker runtime check.

## Claim Boundary

This report proves a repeatable engineering gate, not complete static typing or exhaustive test
coverage. Third-party package internals are not traversed by mypy, and the global coverage result
contains modules exercised through subprocess smoke commands that appear as uncovered in the parent
process.
