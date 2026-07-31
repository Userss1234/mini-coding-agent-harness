# Evaluation Comparison Report

Generated: 2026-07-31T09:50:37

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Retrieval Strategy | Gate Active | Activation Rate | Avg Retrieval Schemas | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-off | agent | enabled | enabled | disabled | off | 0/8 | 0.00% | 0.00 | 8/8 | 100.00% | 17.62 | 0.00 | 0.00 | 3.50 | 0.00 | 0.00 | 115.20s | 287913 | 12078 | $1.044909 | none |
| retrieval-auto | agent | enabled | enabled | enabled | auto | 4/8 | 50.00% | 2.50 | 8/8 | 100.00% | 14.50 | 0.50 | 0.00 | 3.00 | 254.62 | 292.25 | 80.26s | 203672 | 10072 | $0.762096 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode the retrieval strategy can always expose, conditionally gate, or fully disable retrieval schemas and preflight evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
