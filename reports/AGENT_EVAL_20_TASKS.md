# Evaluation Report

Generated: 2026-07-11T21:56:42

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **code_maintenance, configuration, documentation, multi_file, security, trace**
- Tasks: **20**
- Passed: **20**
- Success rate: **100.00%**
- Average tool calls: **15.30**
- Average duration: **111.63s**
- Input tokens: **655774**
- Output tokens: **25649**
- Estimated model cost: **$2.352057**
- Failure categories observed: **none**
- Tool-call mix: **todo_write=92, read_file=49, run_tests=31, list_memories=29, edit_file=21, retry_plan=20, list_python_files=15, shell=11**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| python_bugfix | code_maintenance | pass | 15 | 1 | 126.90s | `artifacts\agent_eval_20_runs_v2\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 15 | 0 | 119.84s | `artifacts\agent_eval_20_runs_v2\agent\python_add_tests.jsonl` |
| python_import_fix | code_maintenance | pass | 19 | 2 | 128.73s | `artifacts\agent_eval_20_runs_v2\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 12 | 1 | 77.67s | `artifacts\agent_eval_20_runs_v2\agent\config_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 19 | 1 | 120.97s | `artifacts\agent_eval_20_runs_v2\agent\multi_file_service_fix.jsonl` |
| json_config_update | configuration | pass | 25 | 2 | 129.55s | `artifacts\agent_eval_20_runs_v2\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 13 | 1 | 106.23s | `artifacts\agent_eval_20_runs_v2\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 15 | 1 | 130.00s | `artifacts\agent_eval_20_runs_v2\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 14 | 1 | 117.71s | `artifacts\agent_eval_20_runs_v2\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 11 | 0 | 95.88s | `artifacts\agent_eval_20_runs_v2\agent\date_format_fix.jsonl` |
| readme_update | documentation | pass | 15 | 0 | 106.14s | `artifacts\agent_eval_20_runs_v2\agent\readme_update.jsonl` |
| pagination_off_by_one | code_maintenance | pass | 16 | 1 | 127.99s | `artifacts\agent_eval_20_runs_v2\agent\pagination_off_by_one.jsonl` |
| secret_redaction_fix | security | pass | 10 | 0 | 78.41s | `artifacts\agent_eval_20_runs_v2\agent\secret_redaction_fix.jsonl` |
| path_normalization_fix | code_maintenance | pass | 17 | 2 | 127.75s | `artifacts\agent_eval_20_runs_v2\agent\path_normalization_fix.jsonl` |
| dependency_pin_update | configuration | pass | 16 | 1 | 127.77s | `artifacts\agent_eval_20_runs_v2\agent\dependency_pin_update.jsonl` |
| mutable_default_fix | code_maintenance | pass | 14 | 1 | 119.07s | `artifacts\agent_eval_20_runs_v2\agent\mutable_default_fix.jsonl` |
| multi_file_api_contract_fix | multi_file | pass | 16 | 1 | 108.03s | `artifacts\agent_eval_20_runs_v2\agent\multi_file_api_contract_fix.jsonl` |
| package_order_total_fix | multi_file | pass | 28 | 3 | 136.01s | `artifacts\agent_eval_20_runs_v2\agent\package_order_total_fix.jsonl` |
| context_pack_retrieval | trace | pass | 6 | 0 | 62.29s | `artifacts\agent_eval_20_runs_v2\agent\context_pack_retrieval.jsonl` |
| permission_policy_report | security | pass | 10 | 1 | 85.69s | `artifacts\agent_eval_20_runs_v2\agent\permission_policy_report.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
