# Evaluation Comparison Report

Generated: 2026-08-02T17:59:53

Workspace: `D:\-\hello-agent\mini-coding-agent-harness`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, Context Retrieval, Retrieval Strategy, and Retrieval Backend columns show the controlled settings for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Retrieval Strategy | Retrieval Backend | Gate Active | Activation Rate | Avg Retrieval Schemas | Cache H/M/W | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retrieval-lexical | agent | enabled | enabled | enabled | on | lexical | 1/1 | 100.00% | 5.00 | 0/0/0 | 1/1 | 100.00% | 17.00 | 1.00 | 0.00 | 3.00 | 230.00 | 293.00 | 89.12s | 31560 | 1735 | $0.120705 | none |
| retrieval-hybrid | agent | enabled | enabled | enabled | on | hybrid | 1/1 | 100.00% | 5.00 | 13/3/2 | 1/1 | 100.00% | 30.00 | 1.00 | 2.00 | 6.00 | 230.00 | 293.00 | 144.91s | 48499 | 1365 | $0.165972 | none |

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
| rag_symbol_retrieval | pass | pass | 17 | 30 | +13 | 3 | 6 | +3 | 89.12s | 144.91s | +55.79s | 13/3/2 |
