# Docker + Hybrid RAG + MCP Cross-Feature Validation

Status: **pass**

## Verified Run

- Workflow: [GitHub Actions run 34760601827](https://github.com/Userss1234/mini-coding-agent-harness/actions/runs/34760601827)
- Commit: `9da0a8bfb49172dc907af62a89581435e4bb9a61`
- Cross-feature job: **pass**
- Validate job: **pass**
- Python quality matrix: **3.10 / 3.11 / 3.12 pass**

## Behavioral Gates

| Gate | Result |
|---|---|
| Docker image build | pass |
| Current Docker runtime evidence | pass |
| Non-root user, workspace mount, blocked network, no host fallback | pass |
| Authenticated localhost MCP Streamable HTTP session | pass |
| Official SDK HTTP runtime | pass |
| Hybrid retrieval marker `local_chunk_hybrid_scoring` | pass |
| Expected implementation `harness/mcp_sdk_http.py` in top 3 | pass |
| Cross-feature artifact upload | pass |

The workflow step requires the generated report to contain both `Status: **pass**` and
`local_chunk_hybrid_scoring`. The command's pass state also requires successful initialization,
session creation, initialized notification, tool invocation, a non-error hybrid result, and the
expected SDK HTTP implementation path in the returned matches.

## Boundary

This report joins two independently observable paths. Docker runtime evidence covers the command
execution boundary. The live MCP call proves that the authenticated official SDK HTTP transport
reaches the shared permission-checked registry and selects local hybrid retrieval. It does not
claim that MiniLM executes inside the Docker sandbox or that hybrid retrieval improves agent
efficiency.

Exact per-run latency and embedding-cache counters remain in the uploaded CI artifact and are not
repeated here because they are environment-specific rather than pass criteria.
