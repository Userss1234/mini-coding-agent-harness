# Evaluation Report

Generated: 2026-07-28T17:05:51

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **security**
- Tasks: **1**
- Passed: **1**
- Success rate: **100.00%**
- Average tool calls: **17.00**
- Average duration: **137.46s**
- Input tokens: **85198**
- Output tokens: **1178**
- Estimated model cost: **$0.273264**
- Failure categories observed: **none**
- Tool-call mix: **grep=10, compact_context=1, context_pack=1, list_memories=1, read_file=1, read_memory=1, retrieve_then_read=1, todo_write=1**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| shell_no_shell_execution | security | pass | 17 | 0 | 137.46s | `artifacts\agent_eval_40_tasks_provider_retry_runs\agent\shell_no_shell_execution.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
