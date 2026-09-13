# MCP Python SDK v2 Migration

## Status

Stage 4 public HTTP consumer switch complete; cross-feature CI and compatibility retirement remain.

- Official dependency: `mcp==2.2.0`
- SDK server API: low-level `Server`, preserving explicit harness JSON Schemas
- Modern client negotiation: `2026-07-28`, pass
- Legacy client negotiation: `2025-11-25`, pass
- CLI stdio: official SDK v2 transport, pass in real subprocess tests
- Public HTTP runtime: official SDK v2 over a real localhost socket
- HTTP security/session tests: 5 passed
- Full regression: 199 tests passed at 79.63% branch coverage
- Scripted benchmark: 40/40 passed

## Verified Surface

| Capability | Modern | Legacy |
|---|---|---|
| Tool listing and original input schemas | pass | pass |
| Tool calls and structured results | pass | pass |
| Permission failures as visible tool errors | pass | pass |
| Resource listing and reading | pass | pass |
| Workspace resource templates | pass | pass |
| Prompt listing and rendering | pass | pass |
| Protocol errors | pass | pass |
| Protocol-version and tool-call trace evidence | pass | pass |
| Real CLI stdio subprocess | pass | pass |
| Real authenticated HTTP client | pass | pass |

The SDK adapter delegates every tool call to the existing `ToolRegistry.call(...)` path.
It adds an `mcp_sdk_request` trace event with the negotiated protocol version and does not
log request arguments.

The lock files pin `mcp==2.2.0` and preserve MCP's `pywin32` dependency behind a
`sys_platform == "win32"` marker so Linux CI and Docker do not attempt to install a
Windows-only wheel.

## Claim Boundary

This report proves in-memory, real CLI stdio, and public authenticated HTTP protocol-era parity
through the official SDK. The `mcp-http`, HTTP smoke, and cross-feature code paths now use the
SDK runtime. The project must not claim completed compatibility retirement until the switched
cross-feature path passes CI and the hand-written runtime is removed.

## Next Gate

1. Run the switched Docker + hybrid RAG + MCP cross-feature path in CI and commit its evidence.
2. Extract the remaining shared HTTP configuration helpers and remove the hand-written runtime.

## Sources

- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [SDK v2 changes](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md)
- [Serving legacy clients](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/legacy-clients.md)
