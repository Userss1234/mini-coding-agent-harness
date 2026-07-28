# Retrieval Preflight Budget Optimization

Generated: 2026-07-28

## Goal

The original paired 8-task DeepSeek ablation showed that retrieval reduced agent exploration but increased input tokens and estimated cost. This change tests whether a smaller, measurable preflight evidence budget can preserve task success and most of the exploration reduction while narrowing that overhead.

## Implementation

- Reduced default retrieval preflight matches from 3 to 2.
- Reduced chunk size from 80 to 48 lines and the read window from 20 to 8 lines.
- Reduced the per-read cap from 4,000 to 1,400 characters.
- Added a 2,400-character total injected-evidence cap.
- Merged overlapping or adjacent ranges for the same file.
- Removed exact duplicate evidence reads.
- Added trace and eval metrics for matched chunks, merged reads, raw evidence characters, injected characters, omissions, and truncation.
- Exposed all five budget values through `AGENT_RETRIEVAL_PREFLIGHT_*` environment variables.

## Offline Replay

The original eight retrieval queries were replayed against fresh deterministic fixtures without model calls.

| Metric | Original format | Budgeted format | Change |
|---|---:|---:|---:|
| Total injected characters | 5,789 | 3,240 | -44.03% |
| Average injected characters per task | 723.62 | 405.00 | -44.03% |
| Tasks retaining evidence | 8/8 | 8/8 | unchanged |

This replay measures evidence text footprint only. It does not measure model behavior, tool-schema tokens, or provider variance.

## Real-Agent Paired Rerun

Source: `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.md` and `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.json`.

Both conditions used DeepSeek `deepseek-chat`, memory enabled, context compaction enabled, and the same eight ordinary repository-maintenance tasks.

| Metric | Retrieval on | Retrieval off | On vs off |
|---|---:|---:|---:|
| Passed | 8/8 | 8/8 | equal |
| Average tool calls | 15.375 | 16.500 | -6.82% |
| Average direct `read_file` calls | 2.125 | 3.375 | -37.04% |
| Average duration | 114.89s | 121.06s | -5.10% |
| Input tokens | 326,366 | 287,602 | +13.48% |
| Output tokens | 11,831 | 11,612 | +1.89% |
| Estimated cost | $1.156563 | $1.036986 | +11.53% |
| Average raw evidence text | 340.38 chars | 0 | n/a |
| Average injected evidence | 405.00 chars | 0 | n/a |

Injected evidence is larger than raw evidence text because it includes compact path and line-range headers.

## Before And After

| Retrieval-on/off gap | Original preflight | Budgeted preflight | Improvement |
|---|---:|---:|---:|
| Input-token overhead | +34.38% | +13.48% | -20.90 percentage points |
| Estimated-cost overhead | +28.65% | +11.53% | -17.12 percentage points |
| Tool-call reduction | -13.28% | -6.82% | smaller reduction |
| Direct-read reduction | -46.43% | -37.04% | smaller reduction |
| Duration change | +4.18% | -5.10% | 9.28 percentage points better |

Comparing retrieval-on runs directly, the budgeted run used 7.85% fewer input tokens, 5.08% fewer output tokens, and 7.44% lower estimated cost than the original retrieval-on run. Tool-call counts varied in the other direction, so the result should not be treated as a deterministic causal estimate from one repeat.

## Conclusion

The evidence-budget change met the primary goal:

- task success remained 8/8;
- retrieval still reduced tool calls and direct reads relative to retrieval-off;
- the input-token and cost premiums narrowed materially;
- retrieval-on was faster than retrieval-off in the new paired run.

The optimization did not make retrieval cheaper than retrieval-off. The remaining overhead is likely not evidence text alone: enabling retrieval also exposes additional tool schemas and can change later model behavior. This is an inference from the measured gap, not a directly isolated result.

The next retrieval experiment should add conditional preflight/tool exposure so simple tasks can skip retrieval while multi-file or uncertain tasks can use it. That experiment should reuse the same paired task set and preserve the original and budgeted reports as baselines.

## Limitations

- Each configuration was run once in sequence, retrieval-on before retrieval-off.
- Model sampling and provider latency were not controlled.
- The task set is project-specific and all eight tasks were already solvable without retrieval.
- The cost calculation uses the repository's configured estimate rather than a provider invoice.
- No embedding model, vector database, or reranker is involved; retrieval remains local lexical scoring.
