# Evaluation Report

Generated: 2026-07-12T23:39:06

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**
- Tasks: **36**
- Passed: **35**
- Success rate: **97.22%**
- Average tool calls: **13.53**
- Average duration: **102.66s**
- Input tokens: **1374403**
- Output tokens: **38364**
- Estimated model cost: **$4.698669**
- Failure categories observed: **none**
- Tool-call mix: **todo_write=136, read_file=64, list_memories=40, retrieve_then_read=38, grep=34, run_tests=32, retry_plan=31, shell=28**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 7 | 0 | 59.49s | `artifacts\agent_eval_36_run2_runs\agent\syntax_check.jsonl` |
| pytest_suite | tests | pass | 5 | 0 | 143.95s | `artifacts\agent_eval_36_run2_runs\agent\pytest_suite.jsonl` |
| context_compaction | trace | pass | 8 | 0 | 76.94s | `artifacts\agent_eval_36_run2_runs\agent\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 7 | 0 | 65.24s | `artifacts\agent_eval_36_run2_runs\agent\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 6 | 0 | 53.01s | `artifacts\agent_eval_36_run2_runs\agent\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 13 | 0 | 87.28s | `artifacts\agent_eval_36_run2_runs\agent\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 24 | 1 | 127.37s | `artifacts\agent_eval_36_run2_runs\agent\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 10 | 0 | 86.78s | `artifacts\agent_eval_36_run2_runs\agent\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 24 | 4 | 128.11s | `artifacts\agent_eval_36_run2_runs\agent\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 22 | 1 | 130.48s | `artifacts\agent_eval_36_run2_runs\agent\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 22 | 3 | 125.67s | `artifacts\agent_eval_36_run2_runs\agent\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 21 | 3 | 125.68s | `artifacts\agent_eval_36_run2_runs\agent\agent_loop_simulation.jsonl` |
| error_recovery | recovery | fail | 22 | 3 | 125.24s | `artifacts\agent_eval_36_run2_runs\agent\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 13 | 1 | 116.72s | `artifacts\agent_eval_36_run2_runs\agent\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 7 | 0 | 65.35s | `artifacts\agent_eval_36_run2_runs\agent\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 10 | 0 | 80.10s | `artifacts\agent_eval_36_run2_runs\agent\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 11 | 0 | 77.20s | `artifacts\agent_eval_36_run2_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 14 | 1 | 80.24s | `artifacts\agent_eval_36_run2_runs\agent\python_add_tests.jsonl` |
| readme_update | documentation | pass | 8 | 0 | 62.38s | `artifacts\agent_eval_36_run2_runs\agent\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 15 | 1 | 118.73s | `artifacts\agent_eval_36_run2_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 10 | 1 | 75.55s | `artifacts\agent_eval_36_run2_runs\agent\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 18 | 1 | 130.06s | `artifacts\agent_eval_36_run2_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 13 | 1 | 88.04s | `artifacts\agent_eval_36_run2_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 10 | 1 | 85.51s | `artifacts\agent_eval_36_run2_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 13 | 1 | 115.97s | `artifacts\agent_eval_36_run2_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 10 | 1 | 86.77s | `artifacts\agent_eval_36_run2_runs\agent\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 13 | 1 | 118.63s | `artifacts\agent_eval_36_run2_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 13 | 1 | 117.44s | `artifacts\agent_eval_36_run2_runs\agent\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 17 | 0 | 135.30s | `artifacts\agent_eval_36_run2_runs\agent\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 16 | 0 | 132.92s | `artifacts\agent_eval_36_run2_runs\agent\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 12 | 1 | 108.37s | `artifacts\agent_eval_36_run2_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 9 | 0 | 84.64s | `artifacts\agent_eval_36_run2_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 10 | 0 | 85.52s | `artifacts\agent_eval_36_run2_runs\agent\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 18 | 1 | 128.90s | `artifacts\agent_eval_36_run2_runs\agent\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 17 | 1 | 129.10s | `artifacts\agent_eval_36_run2_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 19 | 1 | 137.21s | `artifacts\agent_eval_36_run2_runs\agent\package_order_total_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
