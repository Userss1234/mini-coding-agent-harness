# MCP Python SDK v2 Migration

## Status

Stage 1 adapter complete; transport migration remains in progress.

- Official dependency: `mcp==2.2.0`
- SDK server API: low-level `Server`, preserving explicit harness JSON Schemas
- Modern client negotiation: `2026-07-28`, pass
- Legacy client negotiation: `2025-11-25`, pass
- Focused tests: 22 passed across the SDK adapter and compatibility surface
- Full regression: 192 tests passed at 79.58% branch coverage
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

The SDK adapter delegates every tool call to the existing `ToolRegistry.call(...)` path.
It adds an `mcp_sdk_request` trace event with the negotiated protocol version and does not
log request arguments.

The lock files pin `mcp==2.2.0` and preserve MCP's `pywin32` dependency behind a
`sys_platform == "win32"` marker so Linux CI and Docker do not attempt to install a
Windows-only wheel.

## Claim Boundary

This report proves in-memory protocol-era parity through the official SDK. The CLI stdio command
and the authenticated Streamable HTTP command still use the project's hand-written compatibility
transports. The project must not claim completed SDK transport migration or end-to-end
`2026-07-28` support until those entry points and their smoke reports move to the SDK.

## Next Gate

1. Switch `mcp-server` to the SDK stdio runner and add a real subprocess client test.
2. Replace the custom HTTP protocol/session implementation with the SDK Streamable HTTP app while
   preserving localhost, Origin, and Bearer-token controls.
3. Regenerate stdio/HTTP smoke reports, run cross-feature CI, and retire the compatibility
   transport only after both protocol eras pass.

## Sources

- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [SDK v2 changes](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md)
- [Serving legacy clients](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/legacy-clients.md)
