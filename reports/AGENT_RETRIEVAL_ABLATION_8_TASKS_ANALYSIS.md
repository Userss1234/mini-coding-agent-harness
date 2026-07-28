# 8-Task Retrieval Ablation Analysis

Generated: 2026-07-28

## Experiment Design

This paired DeepSeek `deepseek-chat` ablation compares the same eight repository-maintenance tasks with retrieval enabled and disabled. Memory and context compaction remain enabled in both conditions.

The selected tasks avoid retrieval-specific verifiers so the comparison measures whether retrieval preflight helps normal maintenance work:

- `python_bugfix`
- `python_add_tests`
- `cli_validation_fix`
- `secret_redaction_fix`
- `multi_file_service_fix`
- `multi_file_api_contract_fix`
- `config_precedence_integration_fix`
- `nested_plugin_registry_fix`

Source: `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.md` and `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.json`

## Results

| Metric | Retrieval On | Retrieval Off | On vs Off |
|---|---:|---:|---:|
| Passed | 8/8 | 8/8 | no change |
| Average tool calls | 13.88 | 16.00 | -13.28% |
| Average `retrieve_then_read` calls | 1.00 | 0.00 | +1.00 per task |
| Average `read_file` calls | 1.88 | 3.50 | -46.43% |
| Average duration | 119.04s | 114.26s | +4.18% |
| Input tokens | 354,187 | 263,565 | +34.38% |
| Output tokens | 12,464 | 12,036 | +3.56% |
| Estimated cost | $1.249521 | $0.971235 | +28.65% |

Combined estimated model cost: **$2.220756**.

## Interpretation

Retrieval did not improve success rate on this sample: both conditions passed all eight tasks. It did reduce exploratory behavior, with fewer total tool calls and substantially fewer direct file reads. However, the preloaded evidence increased input tokens, latency, and estimated cost.

The supported claim is therefore a tradeoff, not a quality win: the current retrieval preflight replaces some agent exploration with an upfront evidence pack, but that pack is too expensive for these already-solvable tasks.

Do not claim that retrieval improved task success from this experiment.

## Limitations

- Each condition was run once with one model and provider.
- The runner executes retrieval-on before retrieval-off, so order and provider variance are not randomized.
- The sample covers eight representative tasks, not the complete 40-task suite.
- Aggregate comparison JSON does not preserve paired per-task deltas.

## Next Experiment

Reduce the retrieval preflight evidence budget by limiting top chunks, line ranges, duplicate context, or total characters. Then rerun this exact paired task set. The target is to retain 8/8 success and the tool-call reduction while materially lowering input tokens and cost.
