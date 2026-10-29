# Bounded Plans and Scope-Safe Checks

Date: 2026-10-29. Baseline revision: `1ec52ee`; implementation is in this report's commit.
Status: targeted context/scope mechanisms verified; no aggregate agent success-rate gain claimed.
No task prompt, reference implementation, external acceptance, total input ceiling or turn
allowance changed. No automatic repair of failed submissions, push or remote CI.

## Mechanisms

Summary schema v2 separates bounded historical observations from the complete current plan.
History retains the 1800-unit byte-based allowance; the full plan, history, task, schemas and
recent complete tool batches still share the original 24000 total estimated-input ceiling.
Plan fields are not truncated. Updates refresh the plan after compaction; legacy v1 summaries
retain their rendering until upgraded. Oversized protected envelopes still stop before a model
call. This explicitly changes summary allocation, not the total budget.

The Docker-only `run_python_check` uses direct Python argv, not a relaxed shell allowlist.
It adds a read-only workspace mount to the existing non-root/no-network/read-only-root profile,
rejects host fallback, bounds snippet/timeout, disables bytecode/pytest cache generation and
never automatically retries. It does not create helper scripts. Model-authored checks are not
trusted acceptance or a Python-language security sandbox. See
[scope-safe verification](../docs/SCOPE_SAFE_VERIFICATION.md).

## Offline Replay of Actual Failed Checkpoints

The three prior context-stopped SQLite states were loaded and passed to the new ContextWindow
in memory, including their saved task/messages/tool schemas/todos and the corresponding turn
guidance. They were not resumed with a model, applied to files or rescored. Full todo dictionaries
were checked for equality. All keep the original 24000/1800 settings:

| Prior checkpoint | Before | After | History | Full-plan contribution |
|---|---:|---:|---:|---:|
| 0-lexical/reservation_atomicity | 24629 | 15170 | 1600 | 1426 |
| 2-hybrid/reservation_atomicity | 26719 | 18090 | 1665 | 1731 |
| 3-lexical/retention_groups | 24974 | 16583 | 1499 | 1426 |

These are conservative byte-based estimates, not measured provider tokens. The underlying
frozen experiment artifacts remain in `artifacts/challenge-guidance-abba-20261029/`; portable
synthetic equivalents and migration/refresh/fail-closed assertions are in the unit suite.

## Actual Docker Probe

Operator-run calls through the actual tool, with a trace outside the source workspace:

- Workspace module import and a small assertion pass.
- A workspace-file write raises EROFS; external socket access is blocked; UID is non-root.
- An intentional failed assertion returns exit 1, not a passing result.
- A 30-second sleep under a 1-second timeout is stopped and container cleanup succeeds.
  Independent Docker listing confirms that named container has been removed.
- Before/after file-content hashes of the selected workspace are identical; no helper file,
  bytecode or cache was left behind by these probes.

Local trace: `artifacts/inline-check-live-20261029.jsonl`. These probes are actual local Docker
evidence, not fake-executor tests or an exhaustive security certification. The parent agent can
still use separate file tools; do not generalize a read-only check to all agent operations.

## Complete Actual Agent Sequence

[Portable result](CHALLENGE_SCOPE_SAFE_ABBA_20261029.json): one fresh DeepSeek `deepseek-chat`
sequence in lexical/hybrid/hybrid/lexical order, three public author-known tasks, 12 turns each,
line-window retrieval, guidance explicitly on, same Docker image and protected acceptance.
All 12 baselines execute expected case counts and fail before model requests. All protected
inputs remain unchanged. All 12 final file sets pass the unchanged submission-scope check.

| Trial | Backend | Reservation | Retention | Cursor | Accepted |
|---|---|---|---|---|---:|
| 0 | lexical | pass | pass | pass | 3/3 |
| 1 | hybrid | pass | pass | fail | 2/3 |
| 2 | hybrid | pass | pass | fail | 2/3 |
| 3 | lexical | pass | pass | fail | 2/3 |

The CLI exits 1 because acceptance is not universal, not because the sequence was interrupted.
No failed submission was deleted, sanitized or rerun.

| Observation | Guidance v1 | This follow-up |
|---|---:|---:|
| Raw external acceptance | 9/12 | 9/12 |
| Lexical / hybrid acceptance | 5/6 / 4/6 | 5/6 / 4/6 |
| Context-budget stops | 3 | 0 |
| Submission-scope failures | 3 | 0 |
| Normal conversational ends | 7 | 9 |
| Max-turn stops | 2 | 3 |
| Normal ends that also pass acceptance | 7 | 6 |
| Model responses | 117 | 107 |
| Tool calls including preflight | 213 | 185 |
| Failed tool calls | 31 | 17 |
| Reported input tokens | 515260 | 473488 |
| Reported output tokens | 35721 | 40497 |

There are 25 actual inline-check calls, 8 failed check calls and 9 history compactions. Maximum
post-management input estimate is 23573, below the unchanged 24000 limit. Three accepted
submissions stop at the turn allowance; 9/12 is not nine normal autonomous completions.
The overall success count is unchanged; some counters improve and output tokens increase.
This single inspected comparison cannot isolate causal effects, establish a stable backend
advantage or prove generalization/cost savings. Guidance remains off by default.

## Newly Exposed Acceptance Ambiguity

All three failures occur in `cursor_pages`: each passes four of six external cases but raises
`TypeError` for boolean/non-integer size where the verifier specifically requires `ValueError`.
The task says size must be a positive integer and not a boolean; it does not state the required
exception class, and the original four-line implementation documents no such validation contract.
The generated implementations reject the invalid input, but choose a different exception type.

Keep the **raw 9/12** result. It would be misleading either to silently relax acceptance and
publish 12/12, or to treat this exact exception-class disagreement as established algorithmic
failure. The next evaluation improvement should audit prompt/API/acceptance consistency, freeze
an explicit behavioral contract and label any new task-set version before another comparison.
Do not add task-specific exception hints to the generic agent prompt. The historical two 9/12
reports remain unchanged: their failures have different causes.

## Final Gates and Stop Boundary

- Focused context/inline tests: 37 passed.
- Full tests: 319 passed, one optional Windows symlink skip; 83.01% branch-enabled coverage.
- Ruff, mypy (33 source files), compileall: pass.
- Legacy scripted compatibility regression: 40/40. Local artifacts:
  `artifacts/scope-safe-20261029-EVAL.md`, `.json` and matching trace directory.

Stop after this stage and report; no further API run, resume rewrite or push. Next priority is evaluation-contract
audit, then the outstanding Windows MCP shutdown warning. Do not extend the technology list.
