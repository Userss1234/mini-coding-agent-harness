# Conditional Retrieval Gating Analysis

Generated: 2026-07-28

## Goal

The budgeted retrieval preflight preserved 8/8 task success and reduced exploration, but retrieval-on still used 13.48% more input tokens and cost 11.53% more than retrieval-off. This iteration tests whether retrieval can be activated only for tasks with cross-file, dependency, contract, registry, or discovery signals.

## Implementation

- Added `on`, `auto`, and `off` retrieval strategies.
- Added a deterministic pre-model gate with a configurable threshold.
- Scored explainable task signals such as multi-file scope, cross-module contracts, integration dependencies, registry/discovery work, and workspace breadth.
- Suppressed all five retrieval tool schemas when an auto decision is inactive.
- Skipped preflight evidence when the gate is inactive.
- Recorded mode, score, threshold, reasons, source-file count, activation, exposed schemas, and suppressed schemas in JSONL.
- Added per-task and aggregate activation/schema metrics to Markdown and JSON eval reports.
- Added `--retrieval auto` support to both `ask` and `eval`; `--compare-retrieval --retrieval auto` compares auto with off.

## Deterministic Gate Distribution

| Task | Gate | Main reason |
|---|---|---|
| `python_bugfix` | off | no complexity signal |
| `python_add_tests` | off | no complexity signal |
| `cli_validation_fix` | off | no complexity signal |
| `secret_redaction_fix` | off | no complexity signal |
| `multi_file_service_fix` | on | multi-file scope |
| `multi_file_api_contract_fix` | on | multi-file and API-contract scope |
| `config_precedence_integration_fix` | on | cross-module integration and broad workspace |
| `nested_plugin_registry_fix` | on | registry and broad workspace |

Result: **4/8 activations**, **50.00% activation rate**, and **2.50 average retrieval schemas per task** instead of 5.00 with always-on retrieval.

## Prompt-Alignment Finding

The first real-agent auto/off run correctly gated schemas but used generic conditional support text before the gate result was reflected in the task prompt. Both conditions passed 8/8, but auto had 22.29% more input tokens and cost 19.05% more than off.

This exposed an experimental and product issue: gate-off tasks should receive the same support instructions as retrieval-off, while gate-on tasks should receive the same instructions as retrieval-on. The implementation was corrected to resolve the gate before building the support prompt. The original report remains committed as:

- `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_BEFORE_PROMPT_ALIGNMENT.md`
- `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_BEFORE_PROMPT_ALIGNMENT.json`

## Aligned Real-Agent Rerun

Source: `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS.md` and `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS.json`.

Both conditions used DeepSeek `deepseek-chat`, memory enabled, context compaction enabled, and the same eight tasks.

| Metric | Retrieval auto | Retrieval off | Auto vs off |
|---|---:|---:|---:|
| Passed | 8/8 | 8/8 | equal |
| Gate activations | 4/8 | 0/8 | +4 |
| Average retrieval schemas | 2.50 | 0.00 | +2.50 |
| Average tool calls | 15.625 | 16.875 | -7.41% |
| Average direct `read_file` calls | 2.750 | 3.250 | -15.38% |
| Average duration | 117.66s | 127.10s | -7.43% |
| Input tokens | 313,083 | 304,910 | +2.68% |
| Output tokens | 11,800 | 12,067 | -2.21% |
| Estimated cost | $1.116249 | $1.095735 | +1.87% |

Both rows completed without terminal provider or verifier failures.

## Retrieval Iteration Trend

| Retrieval strategy | Input-token premium vs paired off | Cost premium vs paired off |
|---|---:|---:|
| Original always-on preflight | +34.38% | +28.65% |
| Budgeted always-on preflight | +13.48% | +11.53% |
| Conditional auto, prompt-aligned | +2.68% | +1.87% |

These rows come from separate paired runs, so the trend is evidence of iterative improvement, not a controlled deterministic causal estimate.

## Conclusion

Conditional gating met the main engineering targets:

- preserved 8/8 success in both conditions;
- deterministically halved retrieval activation and model-facing retrieval schemas;
- retained fewer tool calls and direct reads than retrieval-off;
- narrowed the measured input-token and estimated-cost premiums to near parity;
- reduced average duration in the aligned paired run.

It did not prove that auto retrieval is cheaper than retrieval-off. The remaining 1.87% estimated-cost difference is smaller than the variance seen across repeated off rows, so further threshold tuning from this single run would be overfitting.

## Order-Varied Stability Rerun

The same eight tasks were repeated with retrieval-off first and retrieval-auto second. Sources:

- `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_OFF_FIRST.md`
- `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_OFF_FIRST.json`
- `reports/RETRIEVAL_GATING_STABILITY.md`

Both rows again passed 8/8. Auto again activated retrieval on 4/8 tasks and exposed an average of 2.50 retrieval schemas.

Across the selected-first and off-first pairs:

| Metric | Observed auto-vs-off range | Direction |
|---|---:|---|
| Average tool calls | -17.73% to -7.41% | stable lower |
| Average direct `read_file` calls | -15.38% to -14.29% | stable lower |
| Average duration | -30.32% to -7.43% | stable lower |
| Input tokens | -29.26% to +2.68% | mixed |
| Output tokens | -16.61% to -2.21% | stable lower |
| Estimated cost | -27.07% to +1.87% | mixed |

This strengthens the claim that the gate consistently suppresses unnecessary exploration on this task set without reducing pass rate. It does not establish stable token or cost superiority because those metrics changed direction.

The next rigorous step is to retain per-task comparison results, measure task-level paired variance, and add retrieval-dependent fixtures before tuning the threshold or signal weights.

## Limitations

- The aligned comparison now has two paired runs with opposite execution order, but only one run per order.
- Model sampling and provider latency were not controlled.
- Comparison JSON currently stores configuration summaries rather than task-level paired rows.
- The tasks are project-specific and all remain solvable without retrieval.
- The heuristic detects explicit complexity signals; it is not a learned classifier.
- Retrieval remains local lexical scoring without embeddings, a vector database, or reranking.
- Estimated cost uses the repository's configured pricing assumptions rather than a provider invoice.
