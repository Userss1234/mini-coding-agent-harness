# Retrieval Gating Stability Report

## Summary

This report compares repeated retrieval-on/auto versus retrieval-off evaluations and checks whether paired conclusions survive a changed execution order.

- Paired runs analyzed: **2**
- Evaluation modes: **`agent`**
- Execution orders covered: **`selected-first`, `off-first`**
- All selected/off configurations fully passed: **yes**
- Metrics with a stable direction: **4/6**
- Overall conclusion: **task outcomes are stable, but at least one efficiency metric changes direction**

## Paired Runs

All deltas are `(selected retrieval - retrieval off) / retrieval off`; negative values mean the selected retrieval strategy used less of that metric.

| Run | Order | Selected | Off | Activation | Avg Schemas | Tool Calls | read_file | Duration | Input Tokens | Output Tokens | Cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| selected-first | `selected-first` | 8/8 | 8/8 | 50.00% | 2.50 | -7.41% | -15.38% | -7.43% | +2.68% | -2.21% | +1.87% |
| off-first | `off-first` | 8/8 | 8/8 | 50.00% | 2.50 | -17.73% | -14.29% | -30.32% | -29.26% | -16.61% | -27.07% |

## Direction Stability

| Metric | Mean Delta | Range | Direction |
|---|---:|---:|---|
| Tool calls | -12.57% | -17.73% to -7.41% | `stable: lower` |
| Direct read_file calls | -14.84% | -15.38% to -14.29% | `stable: lower` |
| Duration | -18.88% | -30.32% to -7.43% | `stable: lower` |
| Input tokens | -13.29% | -29.26% to +2.68% | `mixed: higher -> lower` |
| Output tokens | -9.41% | -16.61% to -2.21% | `stable: lower` |
| Estimated cost | -12.60% | -27.07% to +1.87% | `mixed: higher -> lower` |

## Task-Level Paired Variance

- Runs with task detail: **0/2**
- Status: **unavailable for legacy comparison JSON**

The selected files predate `task_results` and `paired_tasks`. Rerun the same comparison command with the current harness to enable task-level outcome, tool-call, and direct-read variance without changing this CLI.


## Scope

The selected legacy comparison JSON stores configuration-level summaries, so this run can measure only aggregate paired stability. New comparison JSON includes task-level data; rerun the same command to enable paired variance.

## Interpretation

Use pass-rate stability as the quality guardrail and treat efficiency deltas as noisy model-backed measurements. A resume claim should use the observed range or describe the result as directional unless repeated runs keep the same sign.
