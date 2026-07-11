# Eval Analysis Report

## Summary

This report compares two machine-readable evaluation reports and highlights behavior changes in the agent run.

| Metric | Before | After |
|---|---:|---:|
| Passed | 18/20 | 20/20 |
| Success rate | 90.00% | 100.00% |
| Average tool calls | 14.05 | 15.30 |
| Average duration | 107.85s | 111.63s |
| Input tokens | 578171 | 655774 |
| Output tokens | 23038 | 25649 |
| Estimated cost | $2.080083 | $2.352057 |
| todo_write calls | 71 | 92 |
| run_tests calls | 20 | 31 |
| shell calls | 20 | 11 |
| git_diff calls | 6 | 2 |
| edit_file/write_file calls | 19 | 23 |

## Tool-Call Delta

| Tool | Before | After | Delta |
|---|---:|---:|---:|
| `compact_context` | 8 | 4 | -4 |
| `context_pack` | 15 | 10 | -5 |
| `edit_file` | 18 | 21 | +3 |
| `git_diff` | 6 | 2 | -4 |
| `grep` | 4 | 8 | +4 |
| `list_memories` | 26 | 29 | +3 |
| `list_python_files` | 15 | 15 | +0 |
| `permission_policy` | 2 | 1 | -1 |
| `read_file` | 55 | 49 | -6 |
| `read_memory` | 7 | 8 | +1 |
| `retry_plan` | 7 | 20 | +13 |
| `run_py_compile` | 6 | 3 | -3 |
| `run_tests` | 20 | 31 | +11 |
| `shell` | 20 | 11 | -9 |
| `todo_write` | 71 | 92 | +21 |
| `write_file` | 1 | 2 | +1 |

## Failed Tasks Before

| Task | Category | Tool Calls | Failed Tool Calls | Patterns | Trace |
|---|---|---:|---:|---|---|
| `python_add_tests` | code_maintenance | 15 | 1 | `max_turns`, `no_file_change`, `verification_failed`, `over_exploration`, `tool_failures` | `artifacts\agent_eval_20_runs\agent\python_add_tests.jsonl` |
| `readme_update` | documentation | 21 | 1 | `max_turns`, `no_file_change`, `verification_failed`, `over_exploration`, `tool_failures` | `artifacts\agent_eval_20_runs\agent\readme_update.jsonl` |

## Failed Tasks After

No failed tasks.

## Failure Pattern Legend

- `max_turns`: the trace ended because the agent hit the turn budget.
- `no_file_change`: no successful `edit_file` or `write_file` call was observed.
- `over_exploration`: shell/Git exploration dominated before the repair.
- `verification_failed`: the task verifier reported failure or tests failed after attempted work.
- `tool_failures`: one or more tool calls failed during the task.
- `trace_unavailable`: the JSON report references a trace that was not available locally.

## Interpretation

Use this report to connect benchmark movement to agent behavior, not only pass rate. A useful improvement should explain which tool patterns changed and which failure modes disappeared.
