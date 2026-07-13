# Evaluation Report

Generated: 2026-07-13T10:08:05

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

- Mode: **agent**
- Memory: **enabled**
- Context compaction: **enabled**
- Context retrieval: **enabled**
- Categories: **recovery**
- Tasks: **1**
- Passed: **1**
- Success rate: **100.00%**
- Average tool calls: **9.00**
- Average duration: **84.04s**
- Input tokens: **22540**
- Output tokens: **804**
- Estimated model cost: **$0.079680**
- Failure categories observed: **edit_match_failed**
- Tool-call mix: **todo_write=3, edit_file=1, list_memories=1, read_file=1, recover_errors=1, retrieve_then_read=1, retry_plan=1**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
| error_recovery | recovery | pass | 9 | 1 | 84.04s | `artifacts\error_recovery_agent_fix_runs\agent\error_recovery.jsonl` |

## Notes

- This report uses the model-driven agent loop against isolated code-maintenance fixtures.
- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.
- Use `--compare` to run memory/context ablation rows for the selected mode and tasks.
