# Evaluation Report

Generated: 2026-07-06T16:45:38

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **scripted**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, security, tests, trace**
- Tasks: **31**
- Passed: **31**
- Success rate: **100.00%**
- Average tool calls: **3.10**
- Average duration: **2.48s**
- Input tokens: **0**
- Output tokens: **0**
- Estimated model cost: **$0.000000**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **run_tests=35, read_file=26, edit_file=23, list_memories=2, todo_write=2, compact_context=1, context_pack=1, permission_policy=1**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| syntax_check | code_quality | pass | 1 | 0 | 0.44s | `artifacts\eval_runs\syntax_check.jsonl` |
| pytest_suite | tests | pass | 1 | 0 | 45.62s | `artifacts\eval_runs\pytest_suite.jsonl` |
| context_compaction | trace | pass | 3 | 0 | 0.01s | `artifacts\eval_runs\context_compaction.jsonl` |
| read_file_line_range | trace | pass | 1 | 0 | 0.00s | `artifacts\eval_runs\read_file_line_range.jsonl` |
| context_pack_retrieval | trace | pass | 1 | 0 | 0.00s | `artifacts\eval_runs\context_pack_retrieval.jsonl` |
| trace_html_report | trace | pass | 2 | 1 | 0.01s | `artifacts\eval_runs\trace_html_report.jsonl` |
| agent_loop_simulation | agent_loop | pass | 2 | 0 | 0.01s | `artifacts\eval_runs\agent_loop_simulation.jsonl` |
| error_recovery | recovery | pass | 2 | 1 | 0.01s | `artifacts\eval_runs\error_recovery.jsonl` |
| semantic_retry_plan | recovery | pass | 2 | 1 | 0.01s | `artifacts\eval_runs\semantic_retry_plan.jsonl` |
| memory_listing | memory | pass | 1 | 0 | 0.00s | `artifacts\eval_runs\memory_listing.jsonl` |
| memory_relevance_ranking | memory | pass | 1 | 0 | 0.00s | `artifacts\eval_runs\memory_relevance_ranking.jsonl` |
| python_bugfix | code_maintenance | pass | 4 | 1 | 1.67s | `artifacts\eval_runs\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 4 | 1 | 1.52s | `artifacts\eval_runs\python_add_tests.jsonl` |
| readme_update | documentation | pass | 3 | 0 | 0.01s | `artifacts\eval_runs\readme_update.jsonl` |
| python_import_fix | code_maintenance | pass | 4 | 1 | 1.66s | `artifacts\eval_runs\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 4 | 1 | 1.67s | `artifacts\eval_runs\config_default_fix.jsonl` |
| json_config_update | configuration | pass | 4 | 1 | 1.60s | `artifacts\eval_runs\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 4 | 1 | 3.38s | `artifacts\eval_runs\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 4 | 1 | 1.60s | `artifacts\eval_runs\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 4 | 1 | 1.58s | `artifacts\eval_runs\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 4 | 1 | 1.59s | `artifacts\eval_runs\date_format_fix.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 4 | 1 | 1.60s | `artifacts\eval_runs\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 4 | 1 | 1.59s | `artifacts\eval_runs\secret_redaction_fix.jsonl` |
| shell_no_shell_execution | security | pass | 1 | 0 | 0.10s | `artifacts\eval_runs\shell_no_shell_execution.jsonl` |
| permission_policy_report | security | pass | 1 | 0 | 0.00s | `artifacts\eval_runs\permission_policy_report.jsonl` |
| path_normalization_fix | code_maintenance | pass | 4 | 1 | 1.61s | `artifacts\eval_runs\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 4 | 1 | 1.60s | `artifacts\eval_runs\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 4 | 1 | 3.24s | `artifacts\eval_runs\mutable_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 6 | 1 | 1.60s | `artifacts\eval_runs\multi_file_service_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 6 | 1 | 1.61s | `artifacts\eval_runs\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 6 | 1 | 1.63s | `artifacts\eval_runs\package_order_total_fix.jsonl` |

## Notes

- This benchmark includes deterministic harness checks plus isolated code-maintenance fixtures.
- It is now a scripted benchmark with small and multi-file fixtures; use agent mode for real model-driven attempts.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
