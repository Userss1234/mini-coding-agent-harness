# Evaluation Comparison Report

Generated: 2026-07-28T20:07:19

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-on | agent | enabled | enabled | enabled | 8/8 | 100.00% | 13.88 | 1.00 | 0.00 | 1.88 | 119.04s | 354187 | 12464 | $1.249521 | none |
| retrieval-off | agent | enabled | enabled | disabled | 8/8 | 100.00% | 16.00 | 0.00 | 0.00 | 3.50 | 114.26s | 263565 | 12036 | $0.971235 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode context retrieval controls whether retrieval tools are exposed and whether the agent loop can preload `retrieve_then_read` evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
