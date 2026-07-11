# Agent Eval Prompt Improvement Report

Generated from the committed 20-task DeepSeek `deepseek-chat` agent-mode evaluation reports.

## Summary

The expanded 20-task real-agent evaluation initially passed 18/20 tasks. Trace review showed that the two failed tasks did not expose missing tool capabilities; they exposed weak agent-eval guidance. The model spent too many turns on broad shell/Git exploration or wrote documentation that was plausible but did not satisfy the verifier.

The harness was updated with an explicit `build_agent_eval_prompt(...)` workflow contract and a more precise README task description. After rerunning the same 20-task set, the report passed 20/20.

## Metric Comparison

| Metric | Before prompt contract | After prompt contract |
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

## Failed Tasks Before

| Task | Category | Tool Calls | Failed Tool Calls | Trace |
|---|---|---:|---:|---|
| `python_add_tests` | code_maintenance | 15 | 1 | `artifacts\agent_eval_20_runs\agent\python_add_tests.jsonl` |
| `readme_update` | documentation | 21 | 1 | `artifacts\agent_eval_20_runs\agent\readme_update.jsonl` |

Failed tasks after the prompt-contract change: none.

## Failure Modes Observed

- `python_add_tests`: the model inspected `string_utils.py` but spent most turns exploring the workspace with shell/grep and reached `max_turns` before writing `tests/test_string_utils.py`.
- `readme_update`: the model used shell/Git history exploration and did not make the verifier-required README change in the first 20-task run. In an intermediate rerun, it edited README but wrote broad skill usage text instead of concrete pytest usage text.

## Change Made

Implemented a dedicated agent-eval prompt contract in `harness/evaluation.py`:

- Start every eval task with `todo_write`.
- Prefer `read_file`, `grep`, `context_pack`, `write_file`, `edit_file`, and `run_tests` for fixture tasks.
- Avoid broad shell or Git exploration unless file tools are insufficient.
- For change tasks, make the first file change by turn 6 unless a tool failure blocks the edit.
- Verify code tasks with `run_tests`; verify documentation tasks by rereading the changed document.
- Add task-specific guidance for add-tests and README tasks.

The README fixture task description was also tightened from generic usage text to concrete pytest usage text.

## Interpretation

This is an agent-engineering improvement, not a benchmark shortcut. The model still performs the repairs with tools, but the harness now gives a clearer operating contract that reduces unproductive exploration and makes the evaluation target less ambiguous.

The result demonstrates the intended engineering loop:

```text
trace review -> failure-mode classification -> harness prompt contract -> rerun eval -> metric comparison
```

## Current Evidence

- Before report: commit `9022517`, `reports/AGENT_EVAL_20_TASKS.json`, 18/20.
- After report: current `reports/AGENT_EVAL_20_TASKS.json`, 20/20.
- Current CI still validates unit tests, compile checks, scripted benchmark, trace report rendering, and MCP smoke.
