# Evaluation Report

Generated: 2026-07-06T12:29:50

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Categories: **code_maintenance, configuration, multi_file**
- Tasks: **10**
- Passed: **10**
- Success rate: **100.00%**
- Average tool calls: **18.40**
- Average duration: **118.47s**
- Input tokens: **284716**
- Output tokens: **11747**
- Estimated model cost: **$1.030353**
- Failure categories observed: **none**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| python_bugfix | code_maintenance | pass | 16 | 1 | 79.60s | `artifacts\agent_eval_10_runs\agent\python_bugfix.jsonl` |
| python_add_tests | code_maintenance | pass | 21 | 1 | 132.32s | `artifacts\agent_eval_10_runs\agent\python_add_tests.jsonl` |
| python_import_fix | code_maintenance | pass | 22 | 1 | 130.69s | `artifacts\agent_eval_10_runs\agent\python_import_fix.jsonl` |
| config_default_fix | configuration | pass | 12 | 0 | 122.23s | `artifacts\agent_eval_10_runs\agent\config_default_fix.jsonl` |
| multi_file_service_fix | multi_file | pass | 19 | 0 | 130.17s | `artifacts\agent_eval_10_runs\agent\multi_file_service_fix.jsonl` |
| json_config_update | configuration | pass | 22 | 1 | 129.16s | `artifacts\agent_eval_10_runs\agent\json_config_update.jsonl` |
| cli_validation_fix | code_maintenance | pass | 20 | 1 | 132.65s | `artifacts\agent_eval_10_runs\agent\cli_validation_fix.jsonl` |
| env_default_fix | configuration | pass | 17 | 1 | 109.52s | `artifacts\agent_eval_10_runs\agent\env_default_fix.jsonl` |
| csv_parser_fix | code_maintenance | pass | 22 | 3 | 131.32s | `artifacts\agent_eval_10_runs\agent\csv_parser_fix.jsonl` |
| date_format_fix | code_maintenance | pass | 13 | 0 | 87.08s | `artifacts\agent_eval_10_runs\agent\date_format_fix.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
