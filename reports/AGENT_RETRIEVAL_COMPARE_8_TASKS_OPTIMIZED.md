# Evaluation Comparison Report

Generated: 2026-07-28T21:13:12

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-on | agent | enabled | enabled | enabled | 8/8 | 100.00% | 15.38 | 1.00 | 0.12 | 2.12 | 340.38 | 405.00 | 114.89s | 326366 | 11831 | $1.156563 | none |
| retrieval-off | agent | enabled | enabled | disabled | 8/8 | 100.00% | 16.50 | 0.00 | 0.00 | 3.38 | 0.00 | 0.00 | 121.06s | 287602 | 11612 | $1.036986 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode context retrieval controls whether retrieval tools are exposed and whether the agent loop can preload `retrieve_then_read` evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
