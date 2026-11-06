# Reliable Maintenance: Local P0-P3 Validation

Date: 2026-11-03. Windows / Python 3.12.2 / Docker Linux engine 29.9.2.
This report covers the bounded roadmap selected in docs/AGENT_STRENGTHENING_REVIEW_20261103.md.
No paid model API, automatic commit/push, resume rewrite, new agent team or distributed index service.

## Scope Status

| Priority | Local result | Deliberate boundary |
| --- | --- | --- |
| P0 | Source notices, optional pinned dependencies, documented builds and CI definitions | Remote publication/CI pending user approval; no full provenance/license audit |
| P1 | Trusted completion checks, structured diagnostics, bounded repair and durable observations | Operator profile success is not independent task acceptance |
| P2 | Budgeted Python repository map and actual Python LSP definitions/references/diagnostics | Optional trusted host server, Python only, no dynamic-dispatch proof |
| P3 | Durable tool/time/token stops, cancellation signal and repeated-observation detection | Cooperative boundaries, not hard billing/time limits or remote rollback |

Usage: [RELIABLE_MAINTENANCE.md](../docs/RELIABLE_MAINTENANCE.md).
Roadmap synchronization: repository and global mini-coding-agent-harness Skills both updated.
The old no-vector and per-stage-stop instructions remain historical, not active workflow.

## Final Local Gates

| Check | Result |
| --- | --- |
| Full suite with actual Docker, Qdrant and installed Python LSP | 391 passed, 1 optional Windows symlink skip |
| Branch-enabled coverage | 83.77% (75% required) |
| Strict unhandled-thread-exception gate | pass |
| Ruff | pass |
| mypy | pass, 39 source files |
| compileall / pip check | pass |
| Both Skill validators | pass |
| Existing deterministic compatibility benchmark | 40/40 pass |

Raw compatibility outputs are retained in `artifacts/RELIABILITY_COMPAT_20261103.md`, `.json`,
and `artifacts/reliability-compat-20261103-runs/`. This remains the original scripted lexical
suite, not a new 40-task autonomous language-server/verification-controller model score.

The new controller/navigation/control tests add 27 passing cases to the previous 364-test baseline.
Actual language-server tests include cleanup on an initialization deadline and explicit rejection
of provider-credential forwarding. The existing test contract now counts enabled retrieval schemas,
not all possible optional schemas. Historical score artifacts are not edited or rescored.

## P0: Reproducible Starting Point

`THIRD_PARTY_NOTICES.md` identifies Learn Claude Code, preserves the upstream MIT notice and
separates project-specific extension areas. It does not authenticate leaked official source or
claim a completed line-by-line provenance audit. README links expose the attribution.

`requirements-codeintel.lock` is a separate pinned optional overlay, not a replacement for the
existing runtime/development locks. Main packages: Python LSP Server 1.15.0, Jedi 0.20.1,
Python LSP JSON-RPC 1.1.2, Pyflakes 3.4.0. The verification image adds Ruff 0.16.7 to the existing
sandbox. Local optional packages pass `pip check`; new Python 3.10/3.11/3.12 CI definitions have
not yet run remotely. Existing base lock versions were not upgraded for this scope.

## P1: Actual Docker Completion Boundary

Evidence: [RELIABILITY_SMOKE_20261103.json](RELIABILITY_SMOKE_20261103.json).

The driver is an injected deterministic model client; file tools, SQLite, workspace copying and
Docker syntax/Ruff/pytest executions are real. It is not an autonomous LLM coding benchmark.

1. Create an isolated copy of a small addition function with an existing failing implementation.
2. The driver writes another incorrect implementation and proposes a final answer.
3. Syntax and Ruff pass, but pytest exits 1. Completion is refused and actual diagnostics feed back.
4. The driver writes the correct implementation and proposes completion again.
5. All three checks pass on a stable source snapshot; the run is completed after two tool dispatches.
6. Original source bytes remain unchanged; no patch is automatically applied.

A workspace `pytest.ini` deliberately tries to ignore the selected test. The fixed invocation
ignores that config, and the first failure proves the test still ran. Ruff similarly uses isolated
fixed rules. An operator-owned external JSON policy determines checks/target/timeout/repair limit;
there is no model tool that changes that policy. Failed, unavailable and passing checks have
distinct states. Repair allowance and source baseline persist, with repeated identical failures
stopping early. Source mutations during checks invalidate an otherwise passing result.

Only safe bounded source snapshots are fingerprinted. Private/generated exclusions remain; tests
and model-authored assertions do not become an independent acceptance oracle.

## P2: Actual Python Navigation

Evidence: [PYTHON_LSP_LIVE_20261103.json](PYTHON_LSP_LIVE_20261103.json).

The unchanged public `reservation_atomicity` fixture is queried with the installed language server:

- A `valid_quantity` call in `service.py` resolves to `catalog.py`.
- Reference navigation returns three source locations, including the cross-file caller.
- Diagnostics for `catalog.py` return no findings; repository map includes both files/signatures.
- Before/after source hashes are identical. No paid model API or fake embedder is involved.

Additional actual-server unit fixtures resolve an import alias, exclude an unrelated same-name
definition and report an undefined name through Pyflakes. The transport uses the server's own
JSON-RPC stream library, a fixed isolated module command, temporary cwd/config/cache paths and
filtered environment. Request-scoped processes are shut down; timeout cleanup leaves no reader
thread. Returned URIs must correspond to current safe local Python sources.

`repo_map` is syntax-based and bounded by characters. `python_navigate` is operator-enabled and
its package versions/deadline enter resume policy. The server is trusted host-side software,
not a hostile-code sandbox. No repository-wide navigation latency or multi-language claim.

## P3: Durable Control Semantics

Focused tests verify that a two-call batch under a one-dispatch budget executes only the first:
its ledger entry completes, the second remains pending (not started), and resume neither repeats
the completed call nor resets the allowance. Control-state signatures and elapsed counters also
survive restoration. Operator cancellation is represented by a file outside the workspace.

Token-limited runs preserve reported input/output usage and stop on missing/invalid/unknown usage.
They disable automatic provider retries to avoid silently ignoring failed-request billing. Counts
are stop thresholds, not exact billing caps: one request can overshoot before usage is available.
Wall-clock accounting is cooperative/checkpoint-based and can miss the last interval of a hard
process termination. In-flight synchronous operations are not forcibly cancelled.

Controller gates can reject dispatch/completion but cannot bypass existing tool permissions.
Controlled dispatch is serial; default safe-read concurrency remains available without controls.
Repeated exact observations are an opt-in heuristic, not proof that the model is stuck.
Remote write uncertainty still blocks for explicit reconciliation; cancellation is not rollback.

## Persistence/Redaction Corrections Found During Integration

The preexisting Qdrant policy used `credential_sha256`, whose key caused the generic sanitizer to
redact even the digest and reject an unchanged resume policy. It now uses an authentication
fingerprint field, and actual-service tests check unchanged-policy round trips as well as changes.
Old redacted/mismatched checkpoints are not silently trusted or migrated.

New numeric `max_tokens` limits are explicitly retained as metrics, while strings under secret
keys remain redacted. Verification baselines use path/hash records instead of filename dictionary
keys so a name such as `tokenizer.py` does not accidentally destroy its source hash on checkpoint.

Evidence: [RELIABILITY_CLI_20261103.json](RELIABILITY_CLI_20261103.json) verifies actual CLI parsing,
external-policy loading and SQLite policy round trip with token limit intact and omitted resume
limits restored. It sends zero model requests.

## Claims and Remaining Decisions

No new real-model success-rate, cost-reduction or latency-improvement claim follows from these
tests. Raw challenge 9/12 results, the exception-contract ambiguity and existing retrieval-quality
reports remain unchanged. A new versioned real-model comparison requires explicit approval.
Remote GitHub publication/CI are still pending; local implementation is not published evidence.
P4 read-only delegation and P5 vector-index scale work remain optional, not unfinished requirements
of this local P0-P3 scope. Resume wording remains deferred as requested.
