# Evaluation Comparison Report

Generated: 2026-08-02T17:53:55

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, Context Retrieval, Retrieval Strategy, and Retrieval Backend columns show the controlled settings for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Retrieval Strategy | Retrieval Backend | Gate Active | Activation Rate | Avg Retrieval Schemas | Cache H/M/W | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-lexical | agent | enabled | enabled | enabled | on | lexical | 8/8 | 100.00% | 5.00 | 0/0/0 | 8/8 | 100.00% | 17.00 | 1.12 | 0.38 | 4.00 | 307.12 | 366.25 | 96.15s | 329536 | 13181 | $1.186323 | none |
| retrieval-hybrid | agent | enabled | enabled | enabled | on | hybrid | 8/8 | 100.00% | 5.00 | 37/2/4 | 7/8 | 87.50% | 18.38 | 1.50 | 0.25 | 4.00 | 317.62 | 384.88 | 90.70s | 374960 | 14605 | $1.343955 | none |

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode the retrieval strategy can always expose, conditionally gate, or fully disable retrieval schemas and preflight evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.

## Paired Task Results

All deltas are hybrid minus lexical. Cache H/M/W is reported for the hybrid side.

| Task | Lexical | Hybrid | Lexical Tools | Hybrid Tools | Delta | Lexical Reads | Hybrid Reads | Delta | Lexical Duration | Hybrid Duration | Delta | Hybrid Cache H/M/W |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| config_precedence_integration_fix | pass | pass | 16 | 15 | -1 | 5 | 5 | +0 | 91.48s | 100.30s | +8.82s | 3/0/0 |
| context_pack_retrieval | pass | pass | 9 | 6 | -3 | 1 | 1 | +0 | 51.37s | 71.46s | +20.09s | 3/1/1 |
| multi_file_service_fix | pass | pass | 18 | 26 | +8 | 5 | 7 | +2 | 118.77s | 136.90s | +18.13s | 3/0/0 |
| nested_plugin_registry_fix | pass | pass | 21 | 23 | +2 | 7 | 8 | +1 | 130.43s | 97.37s | -33.05s | 4/0/0 |
| python_bugfix | pass | pass | 12 | 16 | +4 | 2 | 2 | +0 | 85.48s | 85.69s | +0.21s | 2/0/0 |
| rag_read_plan_generation | pass | pass | 20 | 19 | -1 | 4 | 4 | +0 | 107.63s | 65.72s | -41.91s | 5/1/2 |
| rag_retrieve_then_read | pass | pass | 18 | 35 | +17 | 2 | 5 | +3 | 107.09s | 126.15s | +19.06s | 11/0/1 |
| rag_symbol_retrieval | pass | fail | 22 | 7 | -15 | 6 | 0 | -6 | 76.93s | 41.99s | -34.94s | 6/0/0 |
