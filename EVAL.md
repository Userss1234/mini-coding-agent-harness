# Evaluation Report

Generated: 2026-07-28T12:21:19

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **scripted**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**
- Tasks: **40**
- Passed: **40**
- Success rate: **100.00%**
- Average tool calls: **3.17**
- Average duration: **2.40s**
- Input tokens: **0**
- Output tokens: **0**
- Estimated model cost: **$0.000000**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **run_tests=43, read_file=36, edit_file=30, list_memories=2, rag_search=2, retrieve_then_read=2, todo_write=2, compact_context=1**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 1 | 0 | 2.52s | `artifacts\eval_40_tasks\syntax_check.jsonl` |
| pytest_suite | tests | pass | 1 | 0 | 58.39s | `artifacts\eval_40_tasks\pytest_suite.jsonl` |
| context_compaction | trace | pass | 3 | 0 | 0.02s | `artifacts\eval_40_tasks\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 1 | 0 | 0.00s | `artifacts\eval_40_tasks\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 1 | 0 | 0.01s | `artifacts\eval_40_tasks\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 1 | 0 | 0.01s | `artifacts\eval_40_tasks\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 2 | 0 | 0.01s | `artifacts\eval_40_tasks\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 1 | 0 | 0.00s | `artifacts\eval_40_tasks\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 1 | 0 | 0.01s | `artifacts\eval_40_tasks\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 0 | 0 | 0.01s | `artifacts\eval_40_tasks\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 2 | 1 | 0.01s | `artifacts\eval_40_tasks\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 3 | 0 | 0.01s | `artifacts\eval_40_tasks\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 2 | 1 | 0.01s | `artifacts\eval_40_tasks\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 2 | 1 | 0.01s | `artifacts\eval_40_tasks\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 1 | 0 | 0.00s | `artifacts\eval_40_tasks\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 1 | 0 | 0.00s | `artifacts\eval_40_tasks\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 4 | 1 | 1.65s | `artifacts\eval_40_tasks\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 4 | 1 | 1.60s | `artifacts\eval_40_tasks\python_add_tests.jsonl` |
| readme_update | documentation | pass | 3 | 0 | 0.01s | `artifacts\eval_40_tasks\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 4 | 1 | 1.72s | `artifacts\eval_40_tasks\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 4 | 1 | 1.66s | `artifacts\eval_40_tasks\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 4 | 1 | 1.65s | `artifacts\eval_40_tasks\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 4 | 1 | 1.63s | `artifacts\eval_40_tasks\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 4 | 1 | 1.63s | `artifacts\eval_40_tasks\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 4 | 1 | 1.62s | `artifacts\eval_40_tasks\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 4 | 1 | 1.64s | `artifacts\eval_40_tasks\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 4 | 1 | 1.67s | `artifacts\eval_40_tasks\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 4 | 1 | 1.63s | `artifacts\eval_40_tasks\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 1 | 0 | 0.10s | `artifacts\eval_40_tasks\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 1 | 0 | 0.00s | `artifacts\eval_40_tasks\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 4 | 1 | 1.62s | `artifacts\eval_40_tasks\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 4 | 1 | 1.63s | `artifacts\eval_40_tasks\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 4 | 1 | 1.64s | `artifacts\eval_40_tasks\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 6 | 1 | 1.65s | `artifacts\eval_40_tasks\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 6 | 1 | 1.64s | `artifacts\eval_40_tasks\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 6 | 1 | 1.64s | `artifacts\eval_40_tasks\package_order_total_fix.jsonl` |
| nested_package_export_fix | multi_file | pass | 7 | 1 | 1.69s | `artifacts\eval_40_tasks\nested_package_export_fix.jsonl` |
| config_precedence_integration_fix | configuration | pass | 6 | 1 | 1.66s | `artifacts\eval_40_tasks\config_precedence_integration_fix.jsonl` |
| dependency_compatibility_fix | configuration | pass | 6 | 1 | 1.74s | `artifacts\eval_40_tasks\dependency_compatibility_fix.jsonl` |
| nested_plugin_registry_fix | multi_file | pass | 6 | 1 | 1.68s | `artifacts\eval_40_tasks\nested_plugin_registry_fix.jsonl` |

## Notes

- This benchmark includes deterministic harness checks plus isolated code-maintenance fixtures.
- It is now a scripted benchmark with small and multi-file fixtures; use agent mode for real model-driven attempts.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
