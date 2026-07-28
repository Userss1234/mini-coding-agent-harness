# Evaluation Report

Generated: 2026-07-28T19:20:06

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**
- Tasks: **40**
- Passed: **40**
- Success rate: **100.00%**
- Average tool calls: **13.15**
- Average duration: **103.91s**
- Input tokens: **1590593**
- Output tokens: **44750**
- Estimated model cost: **$5.443029**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **todo_write=151, read_file=69, list_memories=43, retrieve_then_read=42, run_tests=42, retry_plan=37, shell=32, edit_file=30**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 5 | 0 | 46.81s | `artifacts\agent_eval_40_tasks_run2_runs\agent\syntax_check.jsonl` |
| pytest_suite | tests | pass | 5 | 0 | 159.53s | `artifacts\agent_eval_40_tasks_run2_runs\agent\pytest_suite.jsonl` |
| context_compaction | trace | pass | 6 | 0 | 43.94s | `artifacts\agent_eval_40_tasks_run2_runs\agent\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 4 | 0 | 31.94s | `artifacts\agent_eval_40_tasks_run2_runs\agent\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 6 | 0 | 51.40s | `artifacts\agent_eval_40_tasks_run2_runs\agent\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 10 | 0 | 83.23s | `artifacts\agent_eval_40_tasks_run2_runs\agent\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 26 | 3 | 123.23s | `artifacts\agent_eval_40_tasks_run2_runs\agent\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 19 | 2 | 126.59s | `artifacts\agent_eval_40_tasks_run2_runs\agent\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 14 | 0 | 123.31s | `artifacts\agent_eval_40_tasks_run2_runs\agent\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 18 | 2 | 121.11s | `artifacts\agent_eval_40_tasks_run2_runs\agent\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 24 | 4 | 122.24s | `artifacts\agent_eval_40_tasks_run2_runs\agent\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 19 | 3 | 124.71s | `artifacts\agent_eval_40_tasks_run2_runs\agent\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 10 | 1 | 83.40s | `artifacts\agent_eval_40_tasks_run2_runs\agent\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 11 | 1 | 95.23s | `artifacts\agent_eval_40_tasks_run2_runs\agent\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 6 | 0 | 54.25s | `artifacts\agent_eval_40_tasks_run2_runs\agent\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 15 | 1 | 97.02s | `artifacts\agent_eval_40_tasks_run2_runs\agent\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 11 | 1 | 94.31s | `artifacts\agent_eval_40_tasks_run2_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 16 | 1 | 129.83s | `artifacts\agent_eval_40_tasks_run2_runs\agent\python_add_tests.jsonl` |
| readme_update | documentation | pass | 8 | 0 | 52.59s | `artifacts\agent_eval_40_tasks_run2_runs\agent\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 12 | 1 | 95.51s | `artifacts\agent_eval_40_tasks_run2_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 10 | 0 | 84.97s | `artifacts\agent_eval_40_tasks_run2_runs\agent\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 15 | 1 | 117.37s | `artifacts\agent_eval_40_tasks_run2_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 15 | 1 | 128.72s | `artifacts\agent_eval_40_tasks_run2_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 10 | 0 | 85.91s | `artifacts\agent_eval_40_tasks_run2_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 10 | 1 | 86.74s | `artifacts\agent_eval_40_tasks_run2_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 8 | 0 | 76.14s | `artifacts\agent_eval_40_tasks_run2_runs\agent\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 13 | 1 | 108.13s | `artifacts\agent_eval_40_tasks_run2_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 12 | 1 | 97.10s | `artifacts\agent_eval_40_tasks_run2_runs\agent\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 19 | 0 | 148.24s | `artifacts\agent_eval_40_tasks_run2_runs\agent\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 16 | 0 | 133.06s | `artifacts\agent_eval_40_tasks_run2_runs\agent\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 13 | 1 | 109.35s | `artifacts\agent_eval_40_tasks_run2_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 11 | 1 | 88.50s | `artifacts\agent_eval_40_tasks_run2_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 13 | 1 | 118.26s | `artifacts\agent_eval_40_tasks_run2_runs\agent\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 17 | 1 | 129.27s | `artifacts\agent_eval_40_tasks_run2_runs\agent\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 16 | 1 | 130.28s | `artifacts\agent_eval_40_tasks_run2_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 17 | 2 | 133.73s | `artifacts\agent_eval_40_tasks_run2_runs\agent\package_order_total_fix.jsonl` |
| nested_package_export_fix | multi_file | pass | 17 | 1 | 131.79s | `artifacts\agent_eval_40_tasks_run2_runs\agent\nested_package_export_fix.jsonl` |
| config_precedence_integration_fix | configuration | pass | 19 | 1 | 139.90s | `artifacts\agent_eval_40_tasks_run2_runs\agent\config_precedence_integration_fix.jsonl` |
| dependency_compatibility_fix | configuration | pass | 13 | 1 | 118.69s | `artifacts\agent_eval_40_tasks_run2_runs\agent\dependency_compatibility_fix.jsonl` |
| nested_plugin_registry_fix | multi_file | pass | 17 | 1 | 130.19s | `artifacts\agent_eval_40_tasks_run2_runs\agent\nested_plugin_registry_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
