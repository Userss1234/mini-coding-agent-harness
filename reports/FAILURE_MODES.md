# Eval Failure Dashboard

## Summary

This report aggregates failed eval tasks by failure mode so agent behavior can be debugged across runs.

- Runs analyzed: **3**
- Failed tasks in first run: **2**
- Failed tasks in latest run: **0**
- Failed task observations: **2**
- Failure patterns observed: **`max_turns`, `no_file_change`, `over_exploration`, `tool_failures`, `verification_failed`**

## Failure Pattern Counts

| Pattern | Meaning | before-prompt-contract | after-prompt-contract | full-36-task |
|---|---|---:|---:|---:|
| `max_turns` | the trace ended because the agent hit the turn budget | 2 | 0 | 0 |
| `no_file_change` | no successful edit_file or write_file call was observed | 2 | 0 | 0 |
| `over_exploration` | shell/Git exploration dominated before the repair | 2 | 0 | 0 |
| `tool_failures` | one or more tool calls failed during the task | 2 | 0 | 0 |
| `trace_unavailable` | the JSON report references a trace that was not available locally | 0 | 0 | 0 |
| `verification_failed` | the verifier reported failure or tests failed after attempted work | 2 | 0 | 0 |

## Failed Task Details

| Run | Task | Category | Tool Calls | Failed Tool Calls | Patterns | Trace |
|---|---|---|---:|---:|---|---|
| before-prompt-contract | `python_add_tests` | code_maintenance | 15 | 1 | `max_turns`, `no_file_change`, `verification_failed`, `over_exploration`, `tool_failures` | `artifacts/agent_eval_20_runs/agent/python_add_tests.jsonl` |
| before-prompt-contract | `readme_update` | documentation | 21 | 1 | `max_turns`, `no_file_change`, `verification_failed`, `over_exploration`, `tool_failures` | `artifacts/agent_eval_20_runs/agent/readme_update.jsonl` |

## First-To-Latest Failure Movement

- Resolved failures: **`python_add_tests`, `readme_update`**
- Introduced failures: **none**
- Persistent failures: **none**

## Interpretation

Use this dashboard to decide whether the next harness change should reduce exploration, force earlier file edits, improve verification, or raise the turn budget. A useful change should move tasks out of these buckets, not only improve a single aggregate score.
