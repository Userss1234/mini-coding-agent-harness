# Retrieval Backend 8-Task Analysis

## Question

Does the optional local MiniLM hybrid backend improve the coding-agent workflow when retrieval is always active, compared with the lexical backend under the same model, memory, context, task set, and execution order?

## Method

The committed run used DeepSeek `deepseek-chat` on eight retrieval-heavy or cross-file tasks. Lexical ran first and hybrid ran second. Both configurations used retrieval `on`, memory enabled, context compaction enabled, and the same verifier contract. The comparison JSON preserves every task result and a lexical/hybrid pair for each task.

Sources:

- `reports/AGENT_RETRIEVAL_BACKEND_COMPARE_8_TASKS.md`
- `reports/AGENT_RETRIEVAL_BACKEND_COMPARE_8_TASKS.json`
- `reports/AGENT_RETRIEVAL_BACKEND_RAG_SYMBOL_FIX.md`
- `reports/AGENT_RETRIEVAL_BACKEND_RAG_SYMBOL_FIX.json`

## Initial Result

| Metric | Lexical | Hybrid | Direction |
|---|---:|---:|---|
| Passed | 8/8 | 7/8 | Hybrid lower in the original report |
| Average tool calls | 17.00 | 18.38 | Hybrid +8.09% |
| Average direct reads | 4.00 | 4.00 | Equal |
| Average duration | 96.15s | 90.70s | Hybrid -5.67% |
| Input tokens | 329,536 | 374,960 | Hybrid +13.78% |
| Output tokens | 13,181 | 14,605 | Hybrid +10.80% |
| Estimated cost | $1.186323 | $1.343955 | Hybrid +13.29% |
| Hybrid embedding cache H/M/W | n/a | 37/2/4 | Cache path exercised |

The aggregate result does not support an agent-level hybrid superiority claim. Hybrid kept direct reads flat and average duration lower in this single order, but used more tools, tokens, and estimated cost.

## Verifier Defect Found

The only reported hybrid failure, `rag_symbol_retrieval`, was not a ranking miss. Its hybrid trace ranked `billing/invoice.py` first on every `rag_search` call. The verifier nevertheless required the literal metadata value `local_chunk_lexical_scoring`, so a correct hybrid result could never pass.

The verifier now checks the configured registry backend. A targeted lexical/hybrid real-agent rerun passed 1/1 on both sides. This report preserves the original 7/8 result instead of rewriting it, and links the post-fix validation separately.

## Post-Fix Targeted Result

| Metric | Lexical | Hybrid |
|---|---:|---:|
| Passed | 1/1 | 1/1 |
| Tool calls | 17 | 30 |
| Direct reads | 3 | 6 |
| Duration | 89.12s | 144.91s |
| Input tokens | 31,560 | 48,499 |
| Hybrid embedding cache H/M/W | n/a | 13/3/2 |

The targeted rerun closes the verifier defect but still does not show an exploration advantage for hybrid retrieval.

## Conclusion

The project now has two distinct evidence levels:

- Ranking evidence: hybrid improves the committed 10-query fixture from 0.8000 to 0.9000 MRR and Recall@3/5 from 0.80 to 1.00.
- Agent evidence: one lexical-first 8-task run found no stable workflow advantage; it exposed a backend-biased verifier, and the targeted fix rerun passed on both backends while hybrid still used more exploration.

Do not claim that embeddings improve agent success rate, tool efficiency, token use, or cost. The next major engineering stage is MCP Streamable HTTP. A future retrieval iteration should first improve how the agent consumes retrieved evidence, then repeat the backend pair in reverse order before making stability claims.

## Limits

- This is one model and one lexical-first execution order.
- The task set is project-specific and most tasks remain solvable through ordinary file tools.
- Provider/model variance is not separated from backend effects by one pair.
- Duration includes model latency and the hybrid side's local encoder work.
- The targeted post-fix rerun validates the corrected verifier but is not a replacement 8-task full rerun.
