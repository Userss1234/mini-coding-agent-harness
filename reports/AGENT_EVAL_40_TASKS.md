# Evaluation Report

Generated: 2026-07-28T17:01:33

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**
- Tasks: **40**
- Passed: **39**
- Success rate: **97.50%**
- Average tool calls: **12.95**
- Average duration: **101.21s**
- Input tokens: **1510966**
- Output tokens: **44294**
- Estimated model cost: **$5.197308**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **todo_write=154, read_file=73, list_memories=48, retrieve_then_read=42, run_tests=39, retry_plan=31, edit_file=29, shell=28**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 7 | 0 | 66.00s | `artifacts\agent_eval_40_tasks_runs\agent\syntax_check.jsonl` |
| pytest_suite | tests | pass | 5 | 0 | 158.94s | `artifacts\agent_eval_40_tasks_runs\agent\pytest_suite.jsonl` |
| context_compaction | trace | pass | 7 | 0 | 63.98s | `artifacts\agent_eval_40_tasks_runs\agent\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 7 | 0 | 63.92s | `artifacts\agent_eval_40_tasks_runs\agent\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 3 | 0 | 21.48s | `artifacts\agent_eval_40_tasks_runs\agent\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 9 | 0 | 73.90s | `artifacts\agent_eval_40_tasks_runs\agent\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 29 | 3 | 126.43s | `artifacts\agent_eval_40_tasks_runs\agent\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 16 | 0 | 126.39s | `artifacts\agent_eval_40_tasks_runs\agent\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 11 | 0 | 84.23s | `artifacts\agent_eval_40_tasks_runs\agent\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 18 | 0 | 123.98s | `artifacts\agent_eval_40_tasks_runs\agent\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 27 | 4 | 122.44s | `artifacts\agent_eval_40_tasks_runs\agent\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 20 | 3 | 121.61s | `artifacts\agent_eval_40_tasks_runs\agent\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 10 | 1 | 64.20s | `artifacts\agent_eval_40_tasks_runs\agent\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 10 | 1 | 84.64s | `artifacts\agent_eval_40_tasks_runs\agent\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 9 | 1 | 75.52s | `artifacts\agent_eval_40_tasks_runs\agent\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 12 | 0 | 105.32s | `artifacts\agent_eval_40_tasks_runs\agent\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 15 | 1 | 125.97s | `artifacts\agent_eval_40_tasks_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 13 | 1 | 106.92s | `artifacts\agent_eval_40_tasks_runs\agent\python_add_tests.jsonl` |
| readme_update | documentation | pass | 9 | 0 | 72.49s | `artifacts\agent_eval_40_tasks_runs\agent\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 18 | 1 | 129.81s | `artifacts\agent_eval_40_tasks_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 10 | 0 | 95.31s | `artifacts\agent_eval_40_tasks_runs\agent\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 12 | 1 | 96.19s | `artifacts\agent_eval_40_tasks_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 13 | 1 | 107.48s | `artifacts\agent_eval_40_tasks_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 12 | 1 | 106.00s | `artifacts\agent_eval_40_tasks_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 10 | 0 | 84.63s | `artifacts\agent_eval_40_tasks_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 10 | 0 | 84.44s | `artifacts\agent_eval_40_tasks_runs\agent\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 10 | 1 | 89.40s | `artifacts\agent_eval_40_tasks_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 13 | 1 | 117.56s | `artifacts\agent_eval_40_tasks_runs\agent\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | fail | 6 | 0 | 74.68s | `artifacts\agent_eval_40_tasks_runs\agent\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 17 | 0 | 131.17s | `artifacts\agent_eval_40_tasks_runs\agent\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 11 | 1 | 96.52s | `artifacts\agent_eval_40_tasks_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 12 | 1 | 105.11s | `artifacts\agent_eval_40_tasks_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 14 | 1 | 125.24s | `artifacts\agent_eval_40_tasks_runs\agent\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 15 | 1 | 106.18s | `artifacts\agent_eval_40_tasks_runs\agent\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 18 | 0 | 127.30s | `artifacts\agent_eval_40_tasks_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 17 | 1 | 129.47s | `artifacts\agent_eval_40_tasks_runs\agent\package_order_total_fix.jsonl` |
| nested_package_export_fix | multi_file | pass | 21 | 1 | 126.36s | `artifacts\agent_eval_40_tasks_runs\agent\nested_package_export_fix.jsonl` |
| config_precedence_integration_fix | configuration | pass | 16 | 1 | 89.18s | `artifacts\agent_eval_40_tasks_runs\agent\config_precedence_integration_fix.jsonl` |
| dependency_compatibility_fix | configuration | pass | 12 | 1 | 109.68s | `artifacts\agent_eval_40_tasks_runs\agent\dependency_compatibility_fix.jsonl` |
| nested_plugin_registry_fix | multi_file | pass | 14 | 1 | 128.31s | `artifacts\agent_eval_40_tasks_runs\agent\nested_plugin_registry_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.

## Provider Failure Annotation

`shell_no_shell_execution` stopped before verification after the DeepSeek endpoint returned HTTP 503 through the original retry budget. At generation time, terminal `agent_error` events were not yet included in the report's failure-category summary. The retry policy and failure classification were hardened afterward, and the task passed a targeted 1/1 rerun. See `reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`.
