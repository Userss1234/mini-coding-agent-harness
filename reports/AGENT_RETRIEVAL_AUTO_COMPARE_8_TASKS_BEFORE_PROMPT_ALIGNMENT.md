# Evaluation Comparison Report

Generated: 2026-07-28T22:07:39

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Retrieval Strategy | Gate Active | Activation Rate | Avg Retrieval Schemas | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-auto | agent | enabled | enabled | enabled | auto | 4/8 | 50.00% | 2.50 | 8/8 | 100.00% | 16.50 | 0.50 | 0.00 | 3.50 | 254.62 | 292.25 | 122.49s | 327974 | 12041 | $1.164537 | none |
| retrieval-off | agent | enabled | enabled | disabled | off | 0/8 | 0.00% | 0.00 | 8/8 | 100.00% | 16.25 | 0.00 | 0.00 | 3.38 | 0.00 | 0.00 | 114.68s | 268183 | 11576 | $0.978189 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode context retrieval controls whether retrieval tools are exposed and whether the agent loop can preload `retrieve_then_read` evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
