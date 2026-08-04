from __future__ import annotations

import http.client
import json
from pathlib import Path
import threading
from typing import Any

from .mcp_http import (
    MCP_PROTOCOL_HEADER,
    MCP_SESSION_HEADER,
    SUPPORTED_PROTOCOL_VERSION,
    build_mcp_http_server,
)
from .mcp_server import build_mcp_server


SMOKE_TOKEN = "mcp-http-smoke-token"


def run_mcp_http_smoke(
    workspace: Path,
    trace_path: Path,
    output_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = False,
) -> str:
    server = build_mcp_http_server(
        workspace,
        trace_path,
        allow_write=allow_write,
        fresh_trace=fresh_trace,
        port=0,
        auth_token=SMOKE_TOKEN,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    origin = f"http://127.0.0.1:{port}"
    base_headers = {
        "Authorization": f"Bearer {SMOKE_TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": origin,
    }
    checks: list[tuple[str, bool, str]] = []
    try:
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": SUPPORTED_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcp-http-smoke", "version": "0.1.0"},
            },
        }
        unauthorized = _request(port, "POST", initialize, {
            "Accept": base_headers["Accept"],
            "Content-Type": "application/json",
            "Origin": origin,
        })
        checks.append(("Bearer authentication", unauthorized[0] == 401, str(unauthorized[0])))

        bad_origin_headers = dict(base_headers)
        bad_origin_headers["Origin"] = "https://attacker.example"
        bad_origin = _request(port, "POST", initialize, bad_origin_headers)
        checks.append(("Origin rejection", bad_origin[0] == 403, str(bad_origin[0])))

        initialized = _request(port, "POST", initialize, base_headers)
        session_id = initialized[1].get(MCP_SESSION_HEADER.lower(), "")
        checks.append(("Initialize", initialized[0] == 200, str(initialized[0])))
        checks.append(("Secure session issued", bool(session_id), "present" if session_id else "missing"))

        session_headers = dict(base_headers)
        session_headers[MCP_SESSION_HEADER] = session_id
        session_headers[MCP_PROTOCOL_HEADER] = SUPPORTED_PROTOCOL_VERSION
        notification = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_headers,
        )
        checks.append(("Notification accepted", notification[0] == 202, str(notification[0])))

        tools_response = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            session_headers,
        )
        tools_payload = _json_body(tools_response[2])
        http_tools = {
            item["name"]
            for item in tools_payload.get("result", {}).get("tools", [])
        }
        stdio_server = build_mcp_server(
            workspace,
            trace_path.with_name("mcp_stdio_parity_trace.jsonl"),
            allow_write=allow_write,
            fresh_trace=True,
        )
        stdio_response = stdio_server.handle_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }) or {}
        stdio_tools = {
            item["name"]
            for item in stdio_response.get("result", {}).get("tools", [])
        }
        checks.append(("HTTP tools/list", tools_response[0] == 200, str(tools_response[0])))
        checks.append(("Transport tool parity", http_tools == stdio_tools, f"{len(http_tools)}/{len(stdio_tools)}"))

        get_response = _request(port, "GET", None, session_headers)
        checks.append(("GET without SSE", get_response[0] == 405, str(get_response[0])))

        delete_response = _request(port, "DELETE", None, session_headers)
        checks.append(("Session deletion", delete_response[0] == 204, str(delete_response[0])))
        expired_response = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            session_headers,
        )
        checks.append(("Deleted session rejected", expired_response[0] == 404, str(expired_response[0])))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    passed = all(ok for _, ok, _ in checks)
    report = build_mcp_http_smoke_report(checks, passed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def build_mcp_http_smoke_report(
    checks: list[tuple[str, bool, str]],
    passed: bool,
) -> str:
    rows = "\n".join(
        f"| {name} | {'pass' if ok else 'fail'} | {observed} |"
        for name, ok, observed in checks
    )
    return f"""# MCP Streamable HTTP Smoke Report

Status: **{'pass' if passed else 'fail'}**

Protocol: **{SUPPORTED_PROTOCOL_VERSION}**

Transport: **Streamable HTTP with JSON responses**

## Checks

| Check | Status | Observed |
|---|---|---|
{rows}

## Boundary

- The smoke server binds to an ephemeral localhost port.
- Static Bearer authentication and an exact localhost Origin allowlist are enabled.
- Initialization issues a cryptographically random session ID; notification, request, GET, and DELETE paths reuse it.
- GET intentionally returns 405 because this implementation does not advertise an SSE listener.
- HTTP and stdio tool names are compared from the same permission-checked registry implementation.
"""


def _request(
    port: int,
    method: str,
    payload: dict[str, Any] | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = dict(headers)
    if body is not None:
        request_headers["Content-Length"] = str(len(body))
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request(method, "/mcp", body=body, headers=request_headers)
        response = connection.getresponse()
        response_body = response.read()
        response_headers = {name.lower(): value for name, value in response.getheaders()}
        return response.status, response_headers, response_body
    finally:
        connection.close()


def _json_body(body: bytes) -> dict[str, Any]:
    if not body:
        return {}
    value = json.loads(body.decode("utf-8"))
    return value if isinstance(value, dict) else {}
