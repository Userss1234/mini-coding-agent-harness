# Evaluation Report

Generated: 2026-07-11T20:46:31

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **code_maintenance, configuration, documentation, multi_file, security, trace**
- Tasks: **20**
- Passed: **18**
- Success rate: **90.00%**
- Average tool calls: **14.05**
- Average duration: **107.85s**
- Input tokens: **578171**
- Output tokens: **23038**
- Estimated model cost: **$2.080083**
- Failure categories observed: **none**
- Tool-call mix: **todo_write=71, read_file=55, list_memories=26, run_tests=20, shell=20, edit_file=18, context_pack=15, list_python_files=15**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| python_bugfix | code_maintenance | pass | 11 | 0 | 74.67s | `artifacts\agent_eval_20_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | fail | 15 | 1 | 121.38s | `artifacts\agent_eval_20_runs\agent\python_add_tests.jsonl` |
| python_import_fix | code_maintenance | pass | 19 | 1 | 126.20s | `artifacts\agent_eval_20_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 15 | 0 | 126.97s | `artifacts\agent_eval_20_runs\agent\config_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 16 | 1 | 120.10s | `artifacts\agent_eval_20_runs\agent\multi_file_service_fix.jsonl` |
| json_config_update | configuration | pass | 15 | 1 | 106.07s | `artifacts\agent_eval_20_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 13 | 0 | 115.58s | `artifacts\agent_eval_20_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 11 | 0 | 94.75s | `artifacts\agent_eval_20_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 12 | 0 | 97.28s | `artifacts\agent_eval_20_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 12 | 0 | 97.04s | `artifacts\agent_eval_20_runs\agent\date_format_fix.jsonl` |
| readme_update | documentation | fail | 21 | 1 | 124.73s | `artifacts\agent_eval_20_runs\agent\readme_update.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 12 | 0 | 78.62s | `artifacts\agent_eval_20_runs\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 11 | 0 | 106.49s | `artifacts\agent_eval_20_runs\agent\secret_redaction_fix.jsonl` |
| path_normalization_fix | code_maintenance | pass | 17 | 1 | 127.76s | `artifacts\agent_eval_20_runs\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 12 | 0 | 96.45s | `artifacts\agent_eval_20_runs\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 17 | 0 | 126.88s | `artifacts\agent_eval_20_runs\agent\mutable_default_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 14 | 0 | 107.41s | `artifacts\agent_eval_20_runs\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 17 | 0 | 137.86s | `artifacts\agent_eval_20_runs\agent\package_order_total_fix.jsonl` |
| context_pack_retrieval | trace | pass | 4 | 0 | 41.51s | `artifacts\agent_eval_20_runs\agent\context_pack_retrieval.jsonl` |
| permission_policy_report | security | pass | 17 | 1 | 129.27s | `artifacts\agent_eval_20_runs\agent\permission_policy_report.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
