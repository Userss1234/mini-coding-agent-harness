# MCP Streamable HTTP Smoke Report

Status: **pass**

Protocol: **2025-11-25**

Transport: **Streamable HTTP with JSON responses**

## Checks

| Check | Status | Observed |
|---|---|---|
| Bearer authentication | pass | 401 |
| Origin rejection | pass | 403 |
| Initialize | pass | 200 |
| Secure session issued | pass | present |
| Notification accepted | pass | 202 |
| HTTP tools/list | pass | 200 |
| Transport tool parity | pass | 25/25 |
| GET without SSE | pass | 405 |
| Session deletion | pass | 204 |
| Deleted session rejected | pass | 404 |

## Boundary

- The smoke server binds to an ephemeral localhost port.
- Static Bearer authentication and an exact localhost Origin allowlist are enabled.
- Initialization issues a cryptographically random session ID; notification, request, GET, and DELETE paths reuse it.
- GET intentionally returns 405 because this implementation does not advertise an SSE listener.
- HTTP and stdio tool names are compared from the same permission-checked registry implementation.
