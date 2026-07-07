# Evaluation Comparison Report

Generated: 2026-07-06T17:08:22

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Passed | Success Rate | Avg Tool Calls | Avg context_pack | Avg read_file | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-on | agent | enabled | enabled | enabled | 1/1 | 100.00% | 8.00 | 1.00 | 1.00 | 83.71s | 18652 | 833 | $0.068451 | none |
| retrieval-off | agent | enabled | enabled | disabled | 0/1 | 0.00% | 21.00 | 0.00 | 2.00 | 123.57s | 31028 | 913 | $0.106779 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode context retrieval controls whether `context_pack` is exposed to the model.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
