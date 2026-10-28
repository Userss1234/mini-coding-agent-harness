# Isolated Workspaces and Reviewed Application

## Workflow

`ask --isolate SESSION` copies the selected source into a new, persistent session directory.
The source and session must be separate, non-nested directories. File tools, retrieval and
execution target `SESSION/workspace`; baseline files, SQLite run state, trace and review
artifacts stay outside the copy. Original uncommitted source changes are included in the
snapshot, so no commit, checkout or clean worktree is required.

From the source repository:

```powershell
python main.py --workspace . --allow-write --execution-backend docker ask "Fix the requested bug and run tests" --isolate ..\agent-workspaces\repair-001
python main.py --allow-write resume RUN_ID --isolate ..\agent-workspaces\repair-001
python main.py workspace-review ..\agent-workspaces\repair-001
python main.py workspace-apply ..\agent-workspaces\repair-001 --review FULL_REVIEW_ID
```

The first command needs configured model credentials, Docker and the existing sandbox image.
The session directory must not already exist. Isolated runs require persistence; custom
`--trace` and `--run-db` paths are replaced by the session's fixed external artifact paths.
Resume inherits the execution policy and requires the original `--allow-write` setting.

For a snapshot without any model call:

```powershell
python main.py --workspace . workspace-create ..\agent-workspaces\inspection-001
```

The original non-isolated CLI and library modes remain supported. A plain `ask` still uses
the selected workspace directly; isolation is opt-in, not an implicit change to existing runs.

## Review Boundary

`workspace-review` writes `review.patch` and `review.json`, with a full SHA-256 review ID.
The ID binds the source path, change list, before/after hashes, modes, exact new file bytes
and rendered diff. Additions, deletions, empty files, Unicode text and missing final newlines
are represented. Existing CRLF bytes are preserved when applying the reviewed payload.
Binary/non-UTF-8 changes, terminal control characters and permission changes are refused, rather than represented
by a misleading text diff. `git_diff` in isolated agent runs compares the copy with its baseline.

Read the complete patch. The apply command displays it again and requires an interactive
terminal response exactly matching `APPLY FULL_REVIEW_ID`. There is no `--yes` or piped-input
approval. Neither apply nor recovery is registered as a model-facing tool. `--allow-write`
allows edits inside the copy; a model's `delete_file(confirm=true)` is only a tool argument,
not human approval to change the source.

Before approval and again afterward, the harness checks every affected source file against
its original content and mode, verifies the baseline, and rejects stale or changed reviews.
A changed, removed or newly occupied source path, non-directory parent, link or Windows
junction blocks application. Unrelated source files are not overwritten. The same session
cannot be applied twice. Applied/interrupted sessions cannot resume agent edits.

## Application and Recovery

SQLite locks exclude concurrent CLI agent/review/apply operations on a session and serialize
harness applications targeting the same source. These locks do not lock unrelated editors.
Pause external edits while applying; path checks are not protection against a malicious
same-user process racing filesystem operations.

Before any source mutation, `application.json` records the exact review and `applying` state.
Each individual file replacement uses a staged file, fsync and atomic rename. This is not a
filesystem-wide transaction or a power-loss durability guarantee. Ordinary failures attempt
rollback. A process termination leaves an explicit interrupted state, never a silent success.

Inspect the journal and source, then restore the pre-application state with:

```powershell
python main.py workspace-recover ..\agent-workspaces\repair-001
```

Recovery also requires terminal approval of the recorded review ID. It restores only files
that still match either their original or reviewed state. Any newer conflicting content
blocks rollback rather than overwriting it. Recovery is idempotent after another interruption;
empty directories or staged temporary files created during an abrupt exit may remain. A rolled-back session can be reviewed
again. A completed application is retained for audit; ordinary recovery does not undo an
already completed application. Retain session artifacts until changes are accepted, then remove
the explicitly selected session directory using normal filesystem tools.

## Copy and Execution Limits

The selected snapshot is limited to 10000 files, 10 MiB per file and 100 MiB total. Generated
directories such as virtual environments, node_modules, build/dist, artifacts, eval_runs and
test/type/lint caches are omitted, as are JSONL, bytecode, coverage and SQLite files. Git
metadata and common credential files/directories are not copied. `.env.example` is retained.
This is an explicit copy policy, not a full `.gitignore` implementation. Ordinary eligible
symlinks, Windows junctions and other reparse points are refused rather than followed.

Generated files stay outside the review. Creating credential/Git files inside the copy is
refused at review time. Unchanged binary assets may be copied but binary edits cannot be
applied by this text-review workflow. Projects needing excluded runtime data must arrange
that separately; do not copy credentials into the session to work around the policy.

Isolated `ask` defaults to Docker when no execution backend is configured. Docker mounts only
the working copy, retains CPU/memory/PID limits and timeout cleanup, and requires network=none,
a non-root UID, read-only root and no host fallback. Host mode is available for trusted local
fixtures, with an explicit warning. A copied directory alone does not sandbox arbitrary Python,
tests or subprocesses; host execution can still access the host with the user's privileges.

## Central Redaction

`harness.redaction.redact` is shared by SQLite storage/export, JSONL trace writing and HTML
rendering (including legacy traces). It redacts nested credential keys, recognized tokens,
Bearer headers, inline assignments, PEM private keys and sufficiently long values of secret-
named environment variables. Numeric usage/budget metrics are explicitly preserved. Preview
strings are sanitized before truncation; original live tool/model values are not mutated.

Redaction is best-effort pattern matching, not a data-loss-prevention guarantee. Unknown secrets,
encoded forms or fragments may remain. Existing JSONL files are not rewritten. Baseline copies,
review payloads and patches intentionally retain exact code bytes and are not redacted; keep
sessions private, inspect before sharing, and do not assume every credential uses a known name.
Interactive confirmation is a workflow boundary, not identity authentication or tamper-proof
protection against a process already running under the same account.

## Local Evidence

```powershell
python -m pytest tests/test_workspace.py tests/test_redaction.py -q
python -m tests.fixtures.workspace_workflow --output artifacts/workspace-smoke.json
```

The workflow runs real local file tools and pytest, records a failing test followed by a passing
test in the copy, verifies the source stays unchanged before approval, rejects a decline and
applies exact reviewed bytes. Its approval is a deterministic test callback, not a claimed human
session. See `reports/WORKSPACE_ISOLATION.md` for stage gates and Docker verification boundaries.
