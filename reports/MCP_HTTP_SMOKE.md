# MCP Streamable HTTP Smoke Report

Status: **pass**

Protocols: **2026-07-28 and 2025-11-25**

Transport: **Official MCP Python SDK v2 Streamable HTTP**

## Checks

| Check | Status | Observed |
|---|---|---|
| Bearer authentication | pass | 401 |
| Origin rejection | pass | 403 |
| Official client modern negotiation | pass | 2026-07-28 |
| Official client legacy negotiation | pass | 2025-11-25 |
| Protocol-era tool parity | pass | 25/25 |
| Legacy initialize | pass | 200 |
| Secure session issued | pass | present |
| Notification accepted | pass | 202 |
| Session deletion | pass | 200 |
| Deleted session rejected | pass | 404 |

## Boundary

- The smoke server binds to an ephemeral localhost port.
- Static Bearer authentication and an exact localhost Origin allowlist are enabled.
- Official SDK clients negotiate the modern and legacy protocol eras against the same server.
- Legacy initialization issues a session ID; notification and DELETE paths reuse it.
- Streamable HTTP may serve GET event streams; this is not the deprecated HTTP+SSE transport.
- Tool names are compared across both protocol eras on the shared permission-checked registry.
