# MCP Server

The project exposes its existing `ToolRegistry`, selected project reports, and task prompt
templates through official SDK v2 stdio and Streamable HTTP transports. Both negotiate modern
`2026-07-28` and legacy `2025-11-25` clients and delegate to the same permission-checked
registry implementation.

## Official SDK v2 Migration Status

The runtime dependency is locked to the current official MCP Python SDK `2.2.0`. The
`mcp-server` command now runs through the SDK's stdio transport. In-memory and real
subprocess tests prove tools, resources, resource templates, prompts, permission results, and
trace behavior in automatic `2026-07-28` mode and legacy `2025-11-25` mode.

The user-facing `mcp-http` command and its smoke and cross-feature consumers now use
`harness/mcp_sdk_http.py`. Real-network tests cover Bearer authentication, exact Origin/CORS
handling, session deletion and expiry, and official-client negotiation in both protocol eras.
The compatibility implementation remains only until the switched cross-feature path passes CI.

## Run

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

Enable write-capable tools only when you want the MCP client to edit files:

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl --allow-write mcp-server
```

`stdout` is reserved for JSON-RPC MCP messages. Operational trace data is written to the trace file.

### Streamable HTTP

Generate a dedicated local Bearer token and start the HTTP server:

```powershell
$env:HARNESS_MCP_AUTH_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
python main.py --workspace . --trace artifacts/mcp_http_trace.jsonl mcp-http
```

The endpoint is `http://127.0.0.1:8000/mcp`. Clients send `Authorization: Bearer <value-from-HARNESS_MCP_AUTH_TOKEN>` and an `Accept` header containing both `application/json` and `text/event-stream`. Initialization returns `MCP-Session-Id`; subsequent POST, GET, and DELETE requests reuse that header and may send `MCP-Protocol-Version: 2025-11-25`.

HTTP defaults are intentionally restrictive:

- bind to `127.0.0.1`;
- require a Bearer token from `HARNESS_MCP_AUTH_TOKEN`;
- allow only the bound `127.0.0.1` and `localhost` browser origins unless `--allow-origin` is repeated explicitly;
- require `--allow-remote` before binding outside localhost;
- permit `--no-auth` only on localhost as an explicit development choice;
- expire idle sessions after 3600 seconds by default and support explicit DELETE termination.

This implementation returns JSON for POST requests. Streamable HTTP may serve GET event streams; this does not enable the deprecated HTTP+SSE transport.

Run the committed security, lifecycle, and stdio parity smoke check with:

```powershell
python main.py --workspace . --trace artifacts/mcp_http_smoke_trace.jsonl mcp-http-smoke --output reports/MCP_HTTP_SMOKE.md
```

The transport uses the official MCP Python SDK v2 implementation and preserves a single endpoint, Origin validation, localhost-safe binding, JSON POST responses, session headers, and DELETE termination.

## Client Config

`examples/mcp_config.example.json` contains a copyable stdio MCP client configuration:

```json
{
  "mcpServers": {
    "mini-coding-agent-harness": {
      "command": "python",
      "args": [
        "/absolute/path/to/mini-coding-agent-harness/main.py",
        "--workspace",
        "/absolute/path/to/mini-coding-agent-harness",
        "--trace",
        "/absolute/path/to/mini-coding-agent-harness/artifacts/mcp_client_trace.jsonl",
        "mcp-server"
      ]
    }
  }
}
```

Replace `/absolute/path/to/mini-coding-agent-harness` with your local checkout path. Use the write-enabled entry in the example file only when the client should be allowed to edit existing files.

## Supported Methods

- `initialize`
- `notifications/initialized`
- `ping`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `resources/templates/list`
- `prompts/list`
- `prompts/get`

`tools/list` maps registered harness tools to MCP tools. The schema comes from each local tool's `input_schema`. Retrieval tools such as `index_workspace`, `rag_search`, `rag_explain`, `retrieve_then_read`, and `context_pack` are exposed through the same permission-checked path.

`tools/call` calls the same permission-checked `ToolRegistry.call(...)` path used by the CLI and agent loop. Tool failures are returned as MCP tool results with `isError: true`, while protocol errors use JSON-RPC error responses.

`resources/list` exposes a small whitelist of project documents and committed reports, including `README.md`, `MCP.md`, `EVAL.md`, agent-evaluation reports, lexical/hybrid retrieval quality, focused retrieval-backend agent evidence and analysis, `reports/MCP_HTTP_SMOKE.md`, `reports/CROSS_FEATURE_VALIDATION.md`, and `reports/DOCKER_SANDBOX_SMOKE.md`. It also exposes `harness://rag/index-summary`, a dynamic summary of the safe local retrieval index. Arbitrary file reads should use the permission-checked `read_file` tool instead.

For the final focused path, `cross-feature-smoke` checks a passing Docker runtime report and performs a live `rag_search` call with `backend=hybrid` through an authenticated localhost HTTP session. It defaults to cache-only model loading so a missing MiniLM cache fails quickly; `--allow-model-download` is explicit and is used by the manual CI job.

`resources/templates/list` exposes `harness://workspace/{path}` for safe workspace text resources. Sensitive paths such as `.env`, `.git`, `artifacts`, and `eval_runs` are blocked.

`prompts/list` exposes reusable prompts for repository maintenance, RAG-first maintenance, and evaluation analysis. `prompts/get` fills those prompt templates with caller-provided arguments. The `repo-rag-maintenance` prompt requires a `retrieve_then_read` call before follow-up exact file reads. The `eval-analysis` prompt defaults to the committed agent, history, failure, stability, lexical retrieval, and hybrid retrieval report resources; pass `report_uri` to analyze one specific report instead.

## Example Messages

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","clientInfo":{"name":"demo","version":"0.1.0"},"capabilities":{}}}
```

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"read_file","arguments":{"path":"README.md","limit":20}}}
```

```json
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"context_pack","arguments":{"query":"pytest failing import fix","glob":"*.py","limit":3}}}
```

```json
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"rag_search","arguments":{"query":"pytest failing import fix","glob":"*.py,*.md","limit":3}}}
```

```json
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"rag_explain","arguments":{"query":"pytest failing import fix","glob":"*.py,*.md","limit":3}}}
```

```json
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"retrieve_then_read","arguments":{"query":"pytest failing import fix","glob":"*.py,*.md","limit":3}}}
```

```json
{"jsonrpc":"2.0","id":8,"method":"resources/read","params":{"uri":"harness://rag/index-summary"}}
```

```json
{"jsonrpc":"2.0","id":9,"method":"resources/read","params":{"uri":"harness://reports/agent-eval"}}
```

```json
{"jsonrpc":"2.0","id":10,"method":"resources/read","params":{"uri":"harness://reports/eval-history"}}
```

```json
{"jsonrpc":"2.0","id":11,"method":"resources/read","params":{"uri":"harness://reports/failure-modes"}}
```

```json
{"jsonrpc":"2.0","id":12,"method":"resources/read","params":{"uri":"harness://reports/eval-stability"}}
```

```json
{"jsonrpc":"2.0","id":13,"method":"resources/read","params":{"uri":"harness://reports/retrieval-stability"}}
```

```json
{"jsonrpc":"2.0","id":14,"method":"resources/read","params":{"uri":"harness://reports/retrieval-quality"}}
```

```json
{"jsonrpc":"2.0","id":15,"method":"resources/read","params":{"uri":"harness://reports/retrieval-hybrid"}}
```

```json
{"jsonrpc":"2.0","id":16,"method":"resources/read","params":{"uri":"harness://reports/retrieval-backend-agent"}}
```

```json
{"jsonrpc":"2.0","id":17,"method":"resources/read","params":{"uri":"harness://reports/retrieval-backend-analysis"}}
```

```json
{"jsonrpc":"2.0","id":18,"method":"resources/read","params":{"uri":"harness://reports/docker-sandbox"}}
```

```json
{"jsonrpc":"2.0","id":19,"method":"prompts/get","params":{"name":"code-maintenance-task","arguments":{"task":"Fix the failing calculator test and show evidence."}}}
```

```json
{"jsonrpc":"2.0","id":20,"method":"prompts/get","params":{"name":"repo-rag-maintenance","arguments":{"task":"Fix the failing calculator test and show evidence.","query":"calculator failing pytest assertion"}}}
```

```json
{"jsonrpc":"2.0","id":21,"method":"prompts/get","params":{"name":"eval-analysis","arguments":{}}}
```

## Boundaries

- The stdio and Streamable HTTP transports target the negotiated MCP `2025-11-25` compatibility surface used by this project.
- Streamable HTTP returns JSON responses and intentionally returns 405 for GET; SSE delivery, resumability, and event replay are not implemented.
- It exposes local harness tools, selected read-only resources, and prompt templates.
- Tool calls keep the harness permission policy.
- Lexical retrieval is the base-install default. Optional hybrid retrieval uses a local Sentence Transformers model and an incremental JSON embedding cache; it does not call a model API or require a vector database.
- Write tools still require `--allow-write` for existing files.
- Shell and Git commands still use the existing allowlist and `shell=False`.
- Host execution is policy-only. Optional Docker execution adds a container boundary for shell, pytest, and syntax checks, but it is not a VM or absolute security sandbox.
- HTTP authentication is a static Bearer token for local or controlled deployments, not the full MCP OAuth flow.
- It does not implement resource subscriptions.
