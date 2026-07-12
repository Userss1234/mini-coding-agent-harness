# Evaluation Report

Generated: 2026-07-12T19:36:25

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**
- Tasks: **36**
- Passed: **36**
- Success rate: **100.00%**
- Average tool calls: **13.17**
- Average duration: **101.08s**
- Input tokens: **1362694**
- Output tokens: **38359**
- Estimated model cost: **$4.663467**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **todo_write=135, read_file=61, list_memories=40, retrieve_then_read=38, retry_plan=36, run_tests=34, shell=30, grep=28**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 5 | 0 | 44.58s | `artifacts\agent_eval_36_clean_v4_runs\agent\syntax_check.jsonl` |
| pytest_suite | tests | pass | 8 | 0 | 167.89s | `artifacts\agent_eval_36_clean_v4_runs\agent\pytest_suite.jsonl` |
| context_compaction | trace | pass | 7 | 0 | 65.62s | `artifacts\agent_eval_36_clean_v4_runs\agent\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 9 | 1 | 74.59s | `artifacts\agent_eval_36_clean_v4_runs\agent\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 6 | 0 | 53.29s | `artifacts\agent_eval_36_clean_v4_runs\agent\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 5 | 0 | 42.79s | `artifacts\agent_eval_36_clean_v4_runs\agent\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 29 | 2 | 125.53s | `artifacts\agent_eval_36_clean_v4_runs\agent\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 13 | 0 | 106.31s | `artifacts\agent_eval_36_clean_v4_runs\agent\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 11 | 0 | 75.99s | `artifacts\agent_eval_36_clean_v4_runs\agent\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 16 | 1 | 121.83s | `artifacts\agent_eval_36_clean_v4_runs\agent\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 26 | 5 | 124.03s | `artifacts\agent_eval_36_clean_v4_runs\agent\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 26 | 4 | 124.46s | `artifacts\agent_eval_36_clean_v4_runs\agent\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 17 | 1 | 125.46s | `artifacts\agent_eval_36_clean_v4_runs\agent\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 12 | 1 | 66.52s | `artifacts\agent_eval_36_clean_v4_runs\agent\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 8 | 0 | 64.63s | `artifacts\agent_eval_36_clean_v4_runs\agent\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 14 | 0 | 110.94s | `artifacts\agent_eval_36_clean_v4_runs\agent\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 11 | 1 | 95.78s | `artifacts\agent_eval_36_clean_v4_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 17 | 3 | 131.14s | `artifacts\agent_eval_36_clean_v4_runs\agent\python_add_tests.jsonl` |
| readme_update | documentation | pass | 9 | 0 | 52.75s | `artifacts\agent_eval_36_clean_v4_runs\agent\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 14 | 1 | 117.87s | `artifacts\agent_eval_36_clean_v4_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 11 | 1 | 95.53s | `artifacts\agent_eval_36_clean_v4_runs\agent\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 11 | 1 | 67.22s | `artifacts\agent_eval_36_clean_v4_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 14 | 1 | 116.98s | `artifacts\agent_eval_36_clean_v4_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 10 | 1 | 85.80s | `artifacts\agent_eval_36_clean_v4_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 13 | 1 | 121.26s | `artifacts\agent_eval_36_clean_v4_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 14 | 1 | 121.24s | `artifacts\agent_eval_36_clean_v4_runs\agent\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 9 | 1 | 77.00s | `artifacts\agent_eval_36_clean_v4_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 13 | 1 | 109.89s | `artifacts\agent_eval_36_clean_v4_runs\agent\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 21 | 2 | 137.12s | `artifacts\agent_eval_36_clean_v4_runs\agent\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 15 | 0 | 136.42s | `artifacts\agent_eval_36_clean_v4_runs\agent\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 13 | 1 | 119.93s | `artifacts\agent_eval_36_clean_v4_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 9 | 0 | 86.23s | `artifacts\agent_eval_36_clean_v4_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 12 | 1 | 107.65s | `artifacts\agent_eval_36_clean_v4_runs\agent\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 15 | 1 | 121.25s | `artifacts\agent_eval_36_clean_v4_runs\agent\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 13 | 0 | 107.66s | `artifacts\agent_eval_36_clean_v4_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 18 | 1 | 135.75s | `artifacts\agent_eval_36_clean_v4_runs\agent\package_order_total_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
