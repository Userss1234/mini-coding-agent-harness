# Docker + Hybrid RAG + MCP Cross-Feature Validation

Status: **pass**

## Evidence Model

- Docker evidence source: `artifacts\docker-runtime-20261028-smoke.md`
- Docker evidence mode: committed or current CI runtime report inspection
- Hybrid RAG evidence mode: live `rag_search` call through localhost MCP Streamable HTTP
- Expected implementation evidence: `harness/mcp_sdk_http.py` within the top 3 matches

## Docker Boundary

| Check | Status |
|---|---|
| status | pass |
| backend | pass |
| non_root | pass |
| workspace | pass |
| network | pass |
| no_fallback | pass |

Docker result: **pass** (all Docker runtime markers present)

## Live MCP + Hybrid Retrieval

| Check | Observed |
|---|---|
| Initialize HTTP status | 200 |
| Session issued | yes |
| Initialized notification status | 202 |
| Tool HTTP status | 200 |
| Retrieval marker | `local_chunk_hybrid_scoring` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding preflight | 18.819s |
| Live validation duration | 46.964s |
| Expected implementation path found | yes |
| Embedding cache H/M/W | 17/192/1 |
| Tool/request error | none |

Top matches: `harness/mcp_sdk_http.py`, `harness/mcp_sdk_http.py`, `harness/mcp_http_smoke.py`

Live MCP + hybrid result: **pass**

## Interpretation

This report joins two evidence paths without claiming that the embedding model runs inside the Docker sandbox. The Docker report proves the command-execution boundary. The live HTTP call proves that an authenticated MCP session reaches the shared permission-checked registry, selects the local hybrid backend, and returns implementation evidence. A passing CI rerun rebuilds the Docker image before generating this report.
