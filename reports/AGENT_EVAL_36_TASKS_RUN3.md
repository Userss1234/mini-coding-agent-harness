# Evaluation Report

Generated: 2026-07-13T11:15:27

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
- Average tool calls: **12.33**
- Average duration: **101.32s**
- Input tokens: **1387180**
- Output tokens: **37483**
- Estimated model cost: **$4.723785**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **todo_write=129, read_file=58, list_memories=43, retrieve_then_read=41, run_tests=32, retry_plan=31, shell=24, edit_file=22**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 5 | 0 | 46.84s | `artifacts\agent_eval_36_run3_runs\agent\syntax_check.jsonl` |
| pytest_suite | tests | pass | 5 | 0 | 137.82s | `artifacts\agent_eval_36_run3_runs\agent\pytest_suite.jsonl` |
| context_compaction | trace | pass | 7 | 0 | 64.25s | `artifacts\agent_eval_36_run3_runs\agent\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 13 | 1 | 116.56s | `artifacts\agent_eval_36_run3_runs\agent\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 6 | 0 | 52.69s | `artifacts\agent_eval_36_run3_runs\agent\context_pack_retrieval.jsonl` |
| rag_symbol_retrieval | retrieval | pass | 15 | 0 | 127.45s | `artifacts\agent_eval_36_run3_runs\agent\rag_symbol_retrieval.jsonl` |
| rag_sensitive_path_filter | retrieval | pass | 23 | 2 | 128.02s | `artifacts\agent_eval_36_run3_runs\agent\rag_sensitive_path_filter.jsonl` |
| rag_read_plan_generation | retrieval | pass | 14 | 1 | 115.50s | `artifacts\agent_eval_36_run3_runs\agent\rag_read_plan_generation.jsonl` |
| rag_retrieve_then_read | retrieval | pass | 9 | 0 | 75.39s | `artifacts\agent_eval_36_run3_runs\agent\rag_retrieve_then_read.jsonl` |
| mcp_rag_search_smoke | retrieval | pass | 21 | 3 | 125.49s | `artifacts\agent_eval_36_run3_runs\agent\mcp_rag_search_smoke.jsonl` |
| trace_html_report | trace | pass | 21 | 4 | 124.96s | `artifacts\agent_eval_36_run3_runs\agent\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 22 | 3 | 124.39s | `artifacts\agent_eval_36_run3_runs\agent\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 9 | 1 | 76.20s | `artifacts\agent_eval_36_run3_runs\agent\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 11 | 1 | 103.50s | `artifacts\agent_eval_36_run3_runs\agent\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 6 | 0 | 52.72s | `artifacts\agent_eval_36_run3_runs\agent\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 14 | 0 | 109.43s | `artifacts\agent_eval_36_run3_runs\agent\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 9 | 0 | 83.66s | `artifacts\agent_eval_36_run3_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 14 | 1 | 130.45s | `artifacts\agent_eval_36_run3_runs\agent\python_add_tests.jsonl` |
| readme_update | documentation | pass | 9 | 0 | 84.73s | `artifacts\agent_eval_36_run3_runs\agent\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 19 | 2 | 130.75s | `artifacts\agent_eval_36_run3_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 8 | 0 | 65.39s | `artifacts\agent_eval_36_run3_runs\agent\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 10 | 1 | 86.94s | `artifacts\agent_eval_36_run3_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 12 | 1 | 107.57s | `artifacts\agent_eval_36_run3_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 10 | 1 | 87.83s | `artifacts\agent_eval_36_run3_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 10 | 0 | 86.05s | `artifacts\agent_eval_36_run3_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 11 | 1 | 97.40s | `artifacts\agent_eval_36_run3_runs\agent\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 15 | 1 | 131.96s | `artifacts\agent_eval_36_run3_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 10 | 0 | 85.21s | `artifacts\agent_eval_36_run3_runs\agent\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 15 | 0 | 133.81s | `artifacts\agent_eval_36_run3_runs\agent\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 16 | 0 | 132.46s | `artifacts\agent_eval_36_run3_runs\agent\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 11 | 1 | 96.38s | `artifacts\agent_eval_36_run3_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 12 | 1 | 95.48s | `artifacts\agent_eval_36_run3_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 11 | 1 | 96.96s | `artifacts\agent_eval_36_run3_runs\agent\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 15 | 1 | 129.79s | `artifacts\agent_eval_36_run3_runs\agent\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 10 | 1 | 87.22s | `artifacts\agent_eval_36_run3_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 16 | 1 | 116.43s | `artifacts\agent_eval_36_run3_runs\agent\package_order_total_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
