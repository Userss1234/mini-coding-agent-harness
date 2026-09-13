from __future__ import annotations

import asyncio
import http.client
import json
import threading
import time
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from .mcp_http import MCP_PROTOCOL_HEADER, MCP_SESSION_HEADER
from .mcp_sdk_http import build_mcp_sdk_http_server

SMOKE_TOKEN = "mcp-http-smoke-token"
MODERN_PROTOCOL_VERSION = "2026-07-28"
LEGACY_PROTOCOL_VERSION = "2025-11-25"


def run_mcp_http_smoke(
    workspace: Path,
    trace_path: Path,
    output_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = False,
) -> str:
    server = build_mcp_sdk_http_server(
        workspace,
        trace_path,
        allow_write=allow_write,
        fresh_trace=fresh_trace,
        port=0,
        auth_token=SMOKE_TOKEN,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server(server, thread)
    port = int(server.server_address[1])
    origin = f"http://127.0.0.1:{port}"
    url = f"{origin}{server.config.endpoint}"
    base_headers = {
        "Authorization": f"Bearer {SMOKE_TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": origin,
    }
    checks: list[tuple[str, bool, str]] = []
    try:
        initialize = _initialize_message()
        unauthorized = _request(
            port,
            "POST",
            initialize,
            {
                "Accept": base_headers["Accept"],
                "Content-Type": "application/json",
                "Origin": origin,
            },
        )
        checks.append(
            ("Bearer authentication", unauthorized[0] == 401, str(unauthorized[0]))
        )

        bad_origin_headers = dict(base_headers)
        bad_origin_headers["Origin"] = "https://attacker.example"
        bad_origin = _request(port, "POST", initialize, bad_origin_headers)
        checks.append(("Origin rejection", bad_origin[0] == 403, str(bad_origin[0])))

        modern = asyncio.run(_exercise_official_client(url, origin, "auto"))
        legacy = asyncio.run(_exercise_official_client(url, origin, "legacy"))
        checks.extend([
            (
                "Official client modern negotiation",
                modern["protocol_version"] == MODERN_PROTOCOL_VERSION,
                str(modern["protocol_version"]),
            ),
            (
                "Official client legacy negotiation",
                legacy["protocol_version"] == LEGACY_PROTOCOL_VERSION,
                str(legacy["protocol_version"]),
            ),
            (
                "Protocol-era tool parity",
                modern["tool_names"] == legacy["tool_names"],
                f"{len(modern['tool_names'])}/{len(legacy['tool_names'])}",
            ),
        ])

        initialized = _request(port, "POST", initialize, base_headers)
        session_id = initialized[1].get(MCP_SESSION_HEADER.lower(), "")
        checks.append(("Legacy initialize", initialized[0] == 200, str(initialized[0])))
        checks.append(
            ("Secure session issued", bool(session_id), "present" if session_id else "missing")
        )

        session_headers = dict(base_headers)
        session_headers[MCP_SESSION_HEADER] = session_id
        session_headers[MCP_PROTOCOL_HEADER] = LEGACY_PROTOCOL_VERSION
        notification = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_headers,
        )
        checks.append(
            ("Notification accepted", notification[0] == 202, str(notification[0]))
        )

        delete_response = _request(port, "DELETE", None, session_headers)
        checks.append(
            (
                "Session deletion",
                delete_response[0] in {200, 204},
                str(delete_response[0]),
            )
        )
        deleted_response = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            session_headers,
        )
        checks.append(
            (
                "Deleted session rejected",
                deleted_response[0] == 404,
                str(deleted_response[0]),
            )
        )
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()

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

Protocols: **{MODERN_PROTOCOL_VERSION} and {LEGACY_PROTOCOL_VERSION}**

Transport: **Official MCP Python SDK v2 Streamable HTTP**

## Checks

| Check | Status | Observed |
|---|---|---|
{rows}

## Boundary

- The smoke server binds to an ephemeral localhost port.
- Static Bearer authentication and an exact localhost Origin allowlist are enabled.
- Official SDK clients negotiate the modern and legacy protocol eras against the same server.
- Legacy initialization issues a session ID; notification and DELETE paths reuse it.
- Streamable HTTP may serve GET event streams; this is not the deprecated HTTP+SSE transport.
- Tool names are compared across both protocol eras on the shared permission-checked registry.
"""


async def _exercise_official_client(
    url: str,
    origin: str,
    mode: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {SMOKE_TOKEN}",
        "Origin": origin,
    }
    async with create_mcp_http_client(headers=headers) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(transport, mode=mode) as client:
            tools = await client.list_tools()
            return {
                "protocol_version": client.protocol_version,
                "tool_names": {tool.name for tool in tools.tools},
            }


def _wait_for_server(server: Any, thread: threading.Thread) -> None:
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        raise RuntimeError("SDK HTTP smoke server did not start.")


def _initialize_message() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": LEGACY_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcp-http-smoke", "version": "0.1.0"},
        },
    }


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
        response_headers = {
            name.lower(): value for name, value in response.getheaders()
        }
        return response.status, response_headers, response_body
    finally:
        connection.close()
