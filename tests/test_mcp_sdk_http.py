from __future__ import annotations

import asyncio
import http.client
import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.client.streamable_http import (
    create_mcp_http_client,
    streamable_http_client,
)

from harness.mcp_http import MCP_PROTOCOL_HEADER, MCP_SESSION_HEADER
from harness.mcp_sdk_http import MCPSDKHTTPServer, build_mcp_sdk_http_server

TOKEN = "test-sdk-http-bearer-token"


@contextmanager
def running_server(tmp_path: Path) -> Iterator[tuple[MCPSDKHTTPServer, str]]:
    server = build_mcp_sdk_http_server(
        tmp_path,
        tmp_path / "mcp_sdk_http_trace.jsonl",
        port=0,
        auth_token=TOKEN,
        fresh_trace=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        raise RuntimeError("SDK HTTP server did not start.")
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}/mcp"
    try:
        yield server, url
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()


def test_sdk_http_preserves_auth_origin_and_cors(tmp_path: Path) -> None:
    with running_server(tmp_path) as (server, url):
        port = server.config.port
        origin = f"http://127.0.0.1:{port}"
        initialize = _initialize_message()
        unauthorized = _request(port, "POST", initialize, _headers(origin, auth=False))
        bad_origin = _request(
            port,
            "POST",
            initialize,
            _headers("https://attacker.example"),
        )
        preflight = _request(
            port,
            "OPTIONS",
            None,
            {
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )

    assert url.endswith("/mcp")
    assert unauthorized[0] == 401
    assert unauthorized[1]["www-authenticate"].startswith("Bearer")
    assert bad_origin[0] == 403
    assert "access-control-allow-origin" not in bad_origin[1]
    assert preflight[0] == 204
    assert preflight[1]["access-control-allow-origin"] == origin
    assert MCP_SESSION_HEADER in preflight[1]["access-control-expose-headers"]


@pytest.mark.parametrize(
    ("mode", "expected_version"),
    [
        ("auto", "2026-07-28"),
        ("legacy", "2025-11-25"),
    ],
)
def test_sdk_http_official_client_negotiates_both_protocol_eras(
    tmp_path: Path,
    mode: str,
    expected_version: str,
) -> None:
    (tmp_path / "README.md").write_text("# SDK HTTP\n", encoding="utf-8")
    with running_server(tmp_path) as (server, url):
        origin = f"http://127.0.0.1:{server.config.port}"
        result = asyncio.run(_exercise_http(url, origin, mode))

    assert result["protocol_version"] == expected_version
    assert "read_file" in result["tool_names"]
    assert result["tool_text"] == "# SDK HTTP\n"
    trace = (tmp_path / "mcp_sdk_http_trace.jsonl").read_text(encoding="utf-8")
    assert '"transport": "mcp-sdk-v2-http"' in trace
    assert f'"protocol_version": "{expected_version}"' in trace
    assert TOKEN not in trace


def test_sdk_http_legacy_session_delete_and_expiry(tmp_path: Path) -> None:
    server = build_mcp_sdk_http_server(
        tmp_path,
        tmp_path / "mcp_sdk_http_trace.jsonl",
        port=0,
        auth_token=TOKEN,
        fresh_trace=True,
        session_ttl_seconds=1,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    try:
        port = server.config.port
        origin = f"http://127.0.0.1:{port}"
        initialized = _request(
            port,
            "POST",
            _initialize_message(),
            _headers(origin),
        )
        session_id = initialized[1][MCP_SESSION_HEADER.lower()]
        session_headers = _headers(origin)
        session_headers[MCP_SESSION_HEADER] = session_id
        session_headers[MCP_PROTOCOL_HEADER] = "2025-11-25"
        deleted = _request(port, "DELETE", None, session_headers)
        after_delete = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            session_headers,
        )

        initialized_again = _request(
            port,
            "POST",
            _initialize_message(),
            _headers(origin),
        )
        expiring_headers = _headers(origin)
        expiring_headers[MCP_SESSION_HEADER] = initialized_again[1][
            MCP_SESSION_HEADER.lower()
        ]
        expiring_headers[MCP_PROTOCOL_HEADER] = "2025-11-25"
        time.sleep(1.2)
        after_expiry = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            expiring_headers,
        )
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()

    assert initialized[0] == 200
    assert deleted[0] in {200, 204}
    assert after_delete[0] == 404
    assert initialized_again[0] == 200
    assert after_expiry[0] == 404


def test_sdk_http_rejects_unsafe_defaults(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow_remote"):
        build_mcp_sdk_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            host="0.0.0.0",
            port=0,
            auth_token=TOKEN,
        )
    with pytest.raises(ValueError, match="requires a bearer token"):
        build_mcp_sdk_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            port=0,
            auth_token=None,
        )
    with pytest.raises(ValueError, match="limited to localhost"):
        build_mcp_sdk_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            host="0.0.0.0",
            port=0,
            auth_token=None,
            allow_remote=True,
            allow_unauthenticated=True,
        )
    with pytest.raises(ValueError, match="TTL"):
        build_mcp_sdk_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            port=0,
            auth_token=TOKEN,
            session_ttl_seconds=0,
        )


async def _exercise_http(
    url: str,
    origin: str,
    mode: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Origin": origin,
    }
    async with create_mcp_http_client(headers=headers) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(transport, mode=mode) as client:
            tools = await client.list_tools()
            called = await client.call_tool("read_file", {"path": "README.md"})
            return {
                "protocol_version": client.protocol_version,
                "tool_names": {tool.name for tool in tools.tools},
                "tool_text": called.content[0].text,
            }


def _initialize_message() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.1.0"},
        },
    }


def _headers(origin: str, *, auth: bool = True) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": origin,
    }
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def _request(
    port: int,
    method: str,
    payload: Any | None,
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
        raw_body = response.read()
        response_headers = {
            name.lower(): value for name, value in response.getheaders()
        }
        return response.status, response_headers, raw_body
    finally:
        connection.close()
