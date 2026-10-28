# Durable Runs and Recovery

`ask` saves normalized model messages, tool-call state, todos, policy settings and checkpoints
to SQLite by default. The database uses Python's standard library and needs no service.
Evaluation and direct `run_agent` callers retain the existing in-memory behavior unless they
provide a `RunStore`. JSONL execution traces remain available alongside the run database.

## Commands

```powershell
python main.py --workspace . --trace artifacts/task_trace.jsonl --allow-write ask "Fix the failing test"
python main.py runs
python main.py runs --run-id RUN_ID
python main.py --workspace . --allow-write resume RUN_ID
python main.py runs --run-id RUN_ID --export artifacts/run-export.jsonl
```

The default database is `artifacts/runs.sqlite3`. Each command accepts `--run-db PATH` after
the subcommand. `ask --no-persist` opts out. `--max-turns` on `ask` and `resume` is a positive
number of additional model/tool turns for that invocation. A completed run returns its saved
answer without another model request. `runs` also identifies a run after a process dies before
the CLI prints its ID.

Resume with the original workspace, write permission, executor settings, retrieval backend,
tool schemas, and model provider/endpoint. The model ID comes from the checkpoint. Recreate
provider credentials in the environment; they are not restored from the database. Resume reuses
the original trace reference and rejects `--fresh-trace`. Use a distinct trace file for each task.

## Tool State and Crash Boundaries

| Durable tool state | Recovery action |
|---|---|
| `pending` | Execute through the permission-checked registry |
| `started` | Outcome is unknown after interruption; block automatic execution |
| `completed` | Reuse recorded result, including a recorded error, without executing again |

The model response, planned tool calls and checkpoint are committed in one transaction.
`started` commits before dispatch. Result recording and the resulting checkpoint commit in one
transaction after dispatch. On restart, an unfinished batch is reconstructed from the saved
assistant message and the ledger, preserving tool-use/result pairing and call order.

A process can die after a filesystem/command side effect but before its result commits. SQLite
cannot make an arbitrary external side effect transactional. This implementation blocks that
case rather than promising exactly-once execution or retrying a potentially completed write.
After inspecting files/tests/commands, an operator can record the verified outcome:

```powershell
python main.py run-resolve RUN_ID CALL_ID --result "Verified the intended edit is present" --succeeded
python main.py --workspace . --allow-write resume RUN_ID
```

Omit `--succeeded` to record a failed/uncertain operation as an error visible to the model.
Resolution never reruns a tool. If an effect is still uncertain, leave the run blocked. Only a
`started` call may be reconciled. Duplicate provider call IDs are rejected before execution.

## Storage and Concurrency

`RunStore` is the storage contract. `SQLiteRunStore` uses `runs`, `checkpoints`, `tool_calls`
and `artifacts` tables, foreign keys, full synchronous commits and schema version 1 through
`PRAGMA user_version`. Initialization migrates an empty version-0 database; future unsupported
versions fail visibly instead of being silently rewritten.

A separate per-run SQLite lock database holds an exclusive process lock for the invocation.
Checkpoint commits do not release it. Process exit releases the operating-system lock, so a
crashed process does not leave a stale application lease. Resume, reconciliation and export
share the same lock; a concurrent operation fails visibly. This targets a single host with
local-disk SQLite locking, not distributed/network-filesystem coordination.

Portable JSONL export includes run state, checkpoints, tool-call records and trace artifact
references. This is a durable-state export, not an import command or a replacement for the
existing execution trace format. Database and lock files are ignored by Git.

## Credential Handling and Limits

Durable snapshots, ledger records and exports redact sensitive-key fields, recognized Bearer
or key/value strings and exact credential values found in the current environment. This is
pattern-based redaction, not encryption or detection of every arbitrary secret. It leaves live
model messages unchanged. Redacted pending arguments cannot be automatically replayed; start
a new run with fresh input instead. Keep databases local and avoid credentials in prompts.

The existing execution trace has its own behavior; centralized trace redaction is Priority 3.
Priority 2 now saves compacted model messages, structured summaries and context-budget settings
in the same checkpoint path; see [Context-Window Management](CONTEXT_WINDOW.md). Recovery does not
approve host patches (Priority 3) or persist hidden model/provider state. Initial retrieval
preflight runs before the first durable checkpoint; interrupted initialization may need a new run.
External workspace changes are not rolled back or conflict-checked by resume.

## Verification

`tests/test_run_recovery.py` starts real child processes, waits at explicit durability boundaries,
terminates them, and resumes using a new registry/connection. It verifies interrupted pending
batches, completed-result reuse, waiting-model recovery, unknown-outcome blocking and operator
reconciliation. These tests use an injected deterministic client and require no model API key.
`tests/test_run_cli.py` covers default persistence, opt-out, cached CLI resume, inspection,
export and operator resolution. No new real-agent success-rate claim follows from these tests.
