# Eval History Report

## Summary

This report tracks evaluation runs over time so benchmark changes can be discussed as an engineering trend, not a single snapshot.

- Runs compared: **3**
- Success-rate change: **+10.00%**
- Average tool-call change: **-0.88**
- Estimated cost change: **$+2.583384**

## Run Trend

| Run | Source | Mode | Memory | Context | Retrieval | Passed | Success Rate | Avg Tool Calls | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failed Tasks |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| before-prompt-contract | `reports/AGENT_EVAL_20_TASKS_BEFORE.json` | agent | on | on | on | 18/20 | 90.00% | 14.05 | 107.85s | 578171 | 23038 | $2.080083 | `python_add_tests`, `readme_update` |
| after-prompt-contract | `reports/AGENT_EVAL_20_TASKS.json` | agent | on | on | on | 20/20 | 100.00% | 15.30 | 111.63s | 655774 | 25649 | $2.352057 | none |
| full-36-task | `reports/AGENT_EVAL_36_TASKS.json` | agent | on | on | on | 36/36 | 100.00% | 13.17 | 101.08s | 1362694 | 38359 | $4.663467 | none |

## Key Tool Calls

| Run | todo_write | run_tests | shell | git_diff | read_file | context_pack | edit/write |
|---|---:|---:|---:|---:|---:|---:|---:|
| before-prompt-contract | 71 | 20 | 20 | 6 | 55 | 15 | 19 |
| after-prompt-contract | 92 | 31 | 11 | 2 | 49 | 10 | 23 |
| full-36-task | 135 | 34 | 30 | 0 | 61 | 6 | 27 |

## Task Outcome Changes

| Task | Outcome Trend |
|---|---|
| `python_add_tests` | fail -> pass -> pass |
| `readme_update` | fail -> pass -> pass |

## Interpretation

Use this history report to explain whether a harness change improved success rate, reduced exploratory tool use, changed verification behavior, or raised model cost. Keep claims tied to the rows above.
