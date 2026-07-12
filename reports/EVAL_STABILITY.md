# Eval Stability Report

## Summary

This report checks whether repeated evaluation runs stay stable across the same task set. Use it when only one model API is available and you need repeated-run evidence instead of cross-model comparison.

- Runs analyzed: **1**
- Repeated-run status: **single-run baseline only; repeat the same eval command to measure variance**
- Common tasks across all runs: **36**
- Unstable tasks: **none**
- Success-rate range: **100.00% - 100.00%**
- Average tool-call range: **13.17 - 13.17**
- Average duration range: **101.08s - 101.08s**
- Estimated cost range: **$4.663467 - $4.663467**

## Run Summary

| Run | Source | Passed | Success Rate | Avg Tool Calls | Avg Duration | Est. Cost | Failed Tasks |
|---|---|---:|---:|---:|---:|---:|---|
| full-36-v1 | `reports/AGENT_EVAL_36_TASKS.json` | 36/36 | 100.00% | 13.17 | 101.08s | $4.663467 | none |

## Task Stability

| Task | Statuses | Passes | Failures | Missing | Stability |
|---|---|---:|---:|---:|---|
| `agent_loop_simulation` | pass | 1 | 0 | 0 | `stable_pass` |
| `cli_validation_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `config_default_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `context_compaction` | pass | 1 | 0 | 0 | `stable_pass` |
| `context_pack_retrieval` | pass | 1 | 0 | 0 | `stable_pass` |
| `csv_parser_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `date_format_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `dependency_pin_update` | pass | 1 | 0 | 0 | `stable_pass` |
| `env_default_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `error_recovery` | pass | 1 | 0 | 0 | `stable_pass` |
| `json_config_update` | pass | 1 | 0 | 0 | `stable_pass` |
| `mcp_rag_search_smoke` | pass | 1 | 0 | 0 | `stable_pass` |
| `memory_listing` | pass | 1 | 0 | 0 | `stable_pass` |
| `memory_relevance_ranking` | pass | 1 | 0 | 0 | `stable_pass` |
| `multi_file_api_contract_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `multi_file_service_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `mutable_default_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `package_order_total_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `pagination_off_by_one` | pass | 1 | 0 | 0 | `stable_pass` |
| `path_normalization_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `permission_policy_report` | pass | 1 | 0 | 0 | `stable_pass` |
| `pytest_suite` | pass | 1 | 0 | 0 | `stable_pass` |
| `python_add_tests` | pass | 1 | 0 | 0 | `stable_pass` |
| `python_bugfix` | pass | 1 | 0 | 0 | `stable_pass` |
| `python_import_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `rag_read_plan_generation` | pass | 1 | 0 | 0 | `stable_pass` |
| `rag_retrieve_then_read` | pass | 1 | 0 | 0 | `stable_pass` |
| `rag_sensitive_path_filter` | pass | 1 | 0 | 0 | `stable_pass` |
| `rag_symbol_retrieval` | pass | 1 | 0 | 0 | `stable_pass` |
| `read_file_line_range` | pass | 1 | 0 | 0 | `stable_pass` |
| `readme_update` | pass | 1 | 0 | 0 | `stable_pass` |
| `secret_redaction_fix` | pass | 1 | 0 | 0 | `stable_pass` |
| `semantic_retry_plan` | pass | 1 | 0 | 0 | `stable_pass` |
| `shell_no_shell_execution` | pass | 1 | 0 | 0 | `stable_pass` |
| `syntax_check` | pass | 1 | 0 | 0 | `stable_pass` |
| `trace_html_report` | pass | 1 | 0 | 0 | `stable_pass` |

## Interpretation

For a resume or interview, one 36/36 run proves the full suite can pass end to end; two or more same-suite runs are stronger evidence because they show whether the result survives model randomness. When adding new runs, keep the same task set and model/provider settings unless the report is explicitly a comparison.
