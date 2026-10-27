# Priority 1: Durable Run State and Recovery

Status: **local verification passed**

## Implemented Surface

- Standard-library SQLite `RunStore` with version-1 schema, transactional checkpoints,
  normalized model messages, tool-call ledger, todos and trace artifact references.
- Default CLI persistence for `ask`, explicit opt-out, checkpoint resume, run inspection,
  redacted JSONL export and operator reconciliation of interrupted tool calls.
- One shared Agent Loop for durable and in-memory execution; existing eval callers retain
  the in-memory default.
- Resume checks workspace, permissions, execution policy, retrieval backend, registered tool
  schemas and provider/endpoint identity before continuing.
- Local per-run process exclusion whose lock is released by operating-system process exit.

## Local Verification

Environment: Windows, Python 3.12.2. No model API calls or remote CI runs were used for this stage.

| Gate | Result |
|---|---|
| Full pytest suite | 214 passed |
| Total branch-enabled coverage | 81.18% (75% required) |
| SQLite store coverage | 98% |
| Recovery session coverage | 92% |
| Ruff | pass |
| mypy | pass, 27 source files |
| Python compilation and CLI help | pass |
| 40-task scripted regression | 40/40 pass |

## Recovery Evidence

The fixture client emits two tool calls that append distinguishable effects to a temporary
file. A real child process is terminated after it signals one of these boundaries. A new
registry and SQLite connection then restore the run.

| Interruption boundary | Verified behavior |
|---|---|
| Planned response committed, no dispatch | Pending calls execute once, in order |
| First tool result committed, batch incomplete | First result reused, only second call executes |
| Tool side effect performed, result uncommitted | Resume blocks; neither automatic repetition nor later calls occur |
| Operator verifies the unknown effect | Result is recorded, remaining pending call continues once |
| Waiting for the next model response | Previously completed effects are not repeated |
| Another process still owns the run | Concurrent resume/reconciliation/export lock is rejected |

Additional tests verify budget pauses with restored messages/todos, cached completion without
provider credentials, transient checkpoint retention after a provider error, duplicate-call-ID
rejection, redacted pending-argument blocking, provider/policy mismatch rejection, schema
reopening and future-version refusal, and credential absence from stored/exported test payloads.

Tests: `tests/test_run_recovery.py`, `tests/test_run_cli.py` and the real child-process fixture
`tests/fixtures/run_crash_worker.py`. The pre-existing agent and model-adapter suites also pass.

## Claim Boundaries

This is local crash recovery, not distributed execution or an exactly-once transaction spanning
SQLite and external commands/files. A started call with no committed result remains unknown
until an operator verifies it. A killed process may leave a run status of `running`; the ledger
and lock, rather than that status label alone, determine whether resume is possible.

Credential redaction covers durable records and exports using recognized fields/patterns and
environment values. It is not encryption or complete secret discovery. Central execution-trace
redaction, context-window replacement and host patch approval remain later priorities.

No new real-agent success-rate, token-efficiency, retrieval-quality or Docker-isolation claim
is made by this stage. Remote verification waits for the user's combined push.
