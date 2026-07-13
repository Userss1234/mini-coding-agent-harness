# Eval Stability Report

## Summary

This report checks whether repeated evaluation runs stay stable across the same task set. Use it when only one model API is available and you need repeated-run evidence instead of cross-model comparison.

- Runs analyzed: **2**
- Repeated-run status: **repeated-run variance measured across the selected reports**
- Common tasks across all runs: **36**
- Unstable tasks: **`error_recovery`**
- Success-rate range: **97.22% - 100.00%**
- Average tool-call range: **13.17 - 13.53**
- Average duration range: **101.08s - 102.66s**
- Estimated cost range: **$4.663467 - $4.698669**

## Run Summary

| Run | Source | Passed | Success Rate | Avg Tool Calls | Avg Duration | Est. Cost | Failed Tasks |
|---|---|---:|---:|---:|---:|---:|---|
| full-36-v1 | `reports/AGENT_EVAL_36_TASKS.json` | 36/36 | 100.00% | 13.17 | 101.08s | $4.663467 | none |
| full-36-v2 | `reports/AGENT_EVAL_36_TASKS_RUN2.json` | 35/36 | 97.22% | 13.53 | 102.66s | $4.698669 | `error_recovery` |

## Task Stability

| Task | Statuses | Passes | Failures | Missing | Stability |
|---|---|---:|---:|---:|---|
| `agent_loop_simulation` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `cli_validation_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `config_default_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `context_compaction` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `context_pack_retrieval` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `csv_parser_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `date_format_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `dependency_pin_update` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `env_default_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `error_recovery` | pass -> fail | 1 | 1 | 0 | `unstable` |
| `json_config_update` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `mcp_rag_search_smoke` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `memory_listing` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `memory_relevance_ranking` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `multi_file_api_contract_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `multi_file_service_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `mutable_default_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `package_order_total_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `pagination_off_by_one` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `path_normalization_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `permission_policy_report` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `pytest_suite` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `python_add_tests` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `python_bugfix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `python_import_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `rag_read_plan_generation` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `rag_retrieve_then_read` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `rag_sensitive_path_filter` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `rag_symbol_retrieval` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `read_file_line_range` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `readme_update` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `secret_redaction_fix` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `semantic_retry_plan` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `shell_no_shell_execution` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `syntax_check` | pass -> pass | 2 | 0 | 0 | `stable_pass` |
| `trace_html_report` | pass -> pass | 2 | 0 | 0 | `stable_pass` |

## Interpretation

For a resume or interview, one 36/36 run proves the full suite can pass end to end; two or more same-suite runs are stronger evidence because they show whether the result survives model randomness. When adding new runs, keep the same task set and model/provider settings unless the report is explicitly a comparison.
