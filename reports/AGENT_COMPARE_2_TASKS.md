# Evaluation Comparison Report

Generated: 2026-07-06T12:44:44

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report runs the same selected tasks across four memory/context configurations.

| Config | Mode | Memory | Context Compaction | Passed | Success Rate | Avg Tool Calls | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| memory-on_context-on | agent | enabled | enabled | 2/2 | 100.00% | 17.50 | 118.15s | 59886 | 2577 | $0.218313 | none |
| memory-off_context-on | agent | disabled | enabled | 2/2 | 100.00% | 14.50 | 106.74s | 49548 | 2008 | $0.178764 | none |
| memory-on_context-off | agent | enabled | disabled | 2/2 | 100.00% | 14.00 | 97.47s | 46082 | 2121 | $0.170061 | none |
| memory-off_context-off | agent | disabled | disabled | 2/2 | 100.00% | 14.00 | 117.05s | 56402 | 2330 | $0.204156 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
