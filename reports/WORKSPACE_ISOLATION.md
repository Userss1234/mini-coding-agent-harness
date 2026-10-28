# Priority 3: Isolated Workspaces and Reviewed Changes

Status: **complete; final local acceptance passed**

## Scope

Opt-in isolated CLI runs now use a bounded, credential-filtered copy with an external baseline,
run database and trace. Review binds exact file payloads and source hashes to a SHA-256 ID.
Application is a separate interactive-terminal command, not a model tool or startup approval
flag. Revalidation blocks stale patches, host conflicts and path/link changes. Application
journals, atomic per-file replacement and operator-approved recovery handle partial execution.

One shared redactor now covers durable state/export, JSONL traces and HTML reports, without
mutating live tool results. Numeric token usage and context-budget metrics remain observable.

## Local Verification

Windows / Python 3.12.2. No model API calls, push or remote CI for this stage.

| Gate | Result |
|---|---|
| Focused workspace/redaction tests | 39 passed, 1 optional symlink skip |
| Full pytest suite and branch coverage | 276 passed, 1 skip; 82.38% (75% required) |
| Workspace module coverage | 94% |
| Ruff / mypy / compilation | pass; mypy 30 source files |
| 40-task scripted regression | 40/40 passed on frozen source |
| Deterministic copy/test/review/apply workflow | see WORKSPACE_ISOLATION_SMOKE.json |

Tests include changed/deleted/new source conflicts, stale and tampered reviews, decline and
edits during approval, exact CRLF application, real process exit between file replacements,
rollback without overwriting newer user work, concurrent operation exclusion, copy limits,
credential exclusions, Docker mount/constraint policy, CLI persistence/resume and Windows
junction rejection. Optional symlink creation may skip when Windows lacks that privilege;
junction tests do not rely on symlink privilege.

Text review also rejects invalid UTF-8, binary data and terminal control characters. A copy
of the actual repository selected 172 files under the explicit snapshot policy and generated
an empty review without changing the source. The isolated smoke separately checks exact
reviewed bytes after applying a real tested repair.

The fixture smoke uses real tools and subprocess pytest. Its application approval is a
deterministic callback, not a human interaction claim. The committed JSON contains portable
behavioral results, not host-specific absolute paths or transient review IDs.

The final scripted report and per-task traces are retained locally as
`artifacts/priority3-verified-EVAL.md`, `.json` and `priority3-verified-eval-runs/`.
Reproduce the final regression with:

```powershell
python main.py eval --mode scripted --output artifacts/priority3-verified-EVAL.md --json-output artifacts/priority3-verified-EVAL.json --trace-dir artifacts/priority3-verified-eval-runs
```

## Docker and Security Boundary

No Docker CLI/runtime is available on this machine for this stage. Existing Docker runtime
evidence is historical; this change does not claim a new container execution result. Local
tests check that only the copy is mounted, insecure isolated policies are refused, and the
existing executor's network/user/resource/timeout cleanup behavior is preserved. Remote
integration remains to be rerun after the user's combined push.

This is a local single-user workflow, not a hardened multi-tenant service. Copying is not an
OS sandbox; use Docker for untrusted code. Interactive approval is not identity authentication.
External editors are not locked. Multi-file application uses a journal and recoverable per-file
operations, not an atomic filesystem transaction. Sensitive code may remain in exact review/
baseline artifacts; centralized redaction is best effort and is not encryption or DLP.

Usage and detailed limitations: `docs/WORKSPACE_ISOLATION.md`. Resume editing remains deferred;
Priority 4 must wait for user authorization after this stage is reported.
