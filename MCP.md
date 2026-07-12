# MCP Server

The project exposes its existing `ToolRegistry`, selected project reports, and task prompt templates through a minimal MCP stdio server.

## Run

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

Enable write-capable tools only when you want the MCP client to edit files:

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl --allow-write mcp-server
```

`stdout` is reserved for JSON-RPC MCP messages. Operational trace data is written to the trace file.

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

`tools/list` maps registered harness tools to MCP tools. The schema comes from each local tool's `input_schema`.

`tools/call` calls the same permission-checked `ToolRegistry.call(...)` path used by the CLI and agent loop. Tool failures are returned as MCP tool results with `isError: true`, while protocol errors use JSON-RPC error responses.

`resources/list` exposes a small whitelist of project documents and committed reports, including `README.md`, `MCP.md`, `EVAL.md`, `reports/AGENT_EVAL.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, and the demo report. Arbitrary file reads should use the permission-checked `read_file` tool instead.

`resources/templates/list` exposes `harness://workspace/{path}` for safe workspace text resources. Sensitive paths such as `.env`, `.git`, `artifacts`, and `eval_runs` are blocked.

`prompts/list` exposes reusable prompts for repository maintenance and evaluation analysis. `prompts/get` fills those prompt templates with caller-provided arguments.

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
{"jsonrpc":"2.0","id":5,"method":"resources/read","params":{"uri":"harness://reports/agent-eval"}}
```

```json
{"jsonrpc":"2.0","id":6,"method":"resources/read","params":{"uri":"harness://reports/eval-history"}}
```

```json
{"jsonrpc":"2.0","id":7,"method":"resources/read","params":{"uri":"harness://reports/failure-modes"}}
```

```json
{"jsonrpc":"2.0","id":8,"method":"prompts/get","params":{"name":"code-maintenance-task","arguments":{"task":"Fix the failing calculator test and show evidence."}}}
```

## Boundaries

- This is a stdio MCP server, not an HTTP/SSE server.
- It exposes local harness tools, selected read-only resources, and prompt templates.
- Tool calls keep the harness permission policy.
- Write tools still require `--allow-write` for existing files.
- Shell and Git commands still use the existing allowlist and `shell=False`.
- It is not an OS-level sandbox.
- It does not implement OAuth or resource subscriptions.
