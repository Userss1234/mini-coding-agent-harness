from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from harness.mcp_http import (
    MCP_PROTOCOL_HEADER,
    MCP_SESSION_HEADER,
    SUPPORTED_PROTOCOL_VERSION,
    MCPHTTPSessionStore,
    build_mcp_http_server,
    normalize_endpoint,
    normalize_origin,
)
from harness.mcp_server import build_mcp_server, serve_stdio

TOKEN = "test-mcp-bearer-token"


@contextmanager
def running_server(tmp_path: Path) -> Iterator[tuple[int, str]]:
    server = build_mcp_http_server(
        tmp_path,
        tmp_path / "mcp_http_trace.jsonl",
        port=0,
        auth_token=TOKEN,
        fresh_trace=True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        yield port, f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_security_rejects_missing_auth_and_bad_origin(tmp_path: Path) -> None:
    with running_server(tmp_path) as (port, origin):
        initialize = _initialize_message()
        missing_auth = _request(port, "POST", initialize, _headers(origin, auth=False))
        bad_origin = _request(
            port,
            "POST",
            initialize,
            _headers("https://attacker.example"),
        )
        preflight = _request(port, "OPTIONS", None, {
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        })

    assert missing_auth[0] == 401
    assert missing_auth[1]["www-authenticate"] == "Bearer"
    assert bad_origin[0] == 403
    assert "access-control-allow-origin" not in bad_origin[1]
    assert preflight[0] == 204
    assert preflight[1]["access-control-allow-origin"] == origin
    assert MCP_SESSION_HEADER in preflight[1]["access-control-expose-headers"]


def test_http_session_lifecycle_and_stdio_tool_parity(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# HTTP fixture\n", encoding="utf-8")
    with running_server(tmp_path) as (port, origin):
        initialized = _request(
            port,
            "POST",
            _initialize_message(),
            _headers(origin),
        )
        session_id = initialized[1][MCP_SESSION_HEADER.lower()]
        session_headers = _headers(origin, session_id=session_id, protocol=True)

        notification = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_headers,
        )
        listed = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            session_headers,
        )
        get_response = _request(port, "GET", None, session_headers)
        deleted = _request(port, "DELETE", None, session_headers)
        after_delete = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 3, "method": "ping"},
            session_headers,
        )

    assert initialized[0] == 200
    assert initialized[2]["result"]["protocolVersion"] == SUPPORTED_PROTOCOL_VERSION
    assert session_id
    assert notification[0] == 202
    assert notification[3] == b""
    assert listed[0] == 200
    http_tools = {item["name"] for item in listed[2]["result"]["tools"]}
    assert http_tools == _stdio_tool_names(tmp_path)
    assert get_response[0] == 405
    assert get_response[1]["allow"] == "POST, DELETE, OPTIONS"
    assert deleted[0] == 204
    assert after_delete[0] == 404

    trace = (tmp_path / "mcp_http_trace.jsonl").read_text(encoding="utf-8")
    assert '"transport": "mcp-streamable-http"' in trace
    assert '"event": "mcp_http_request"' in trace
    assert TOKEN not in trace
    assert session_id not in trace


def test_http_requires_session_and_matching_protocol_version(tmp_path: Path) -> None:
    with running_server(tmp_path) as (port, origin):
        no_session = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            _headers(origin),
        )
        initialized = _request(port, "POST", _initialize_message(), _headers(origin))
        session_id = initialized[1][MCP_SESSION_HEADER.lower()]
        bad_version_headers = _headers(origin, session_id=session_id)
        bad_version_headers[MCP_PROTOCOL_HEADER] = "1900-01-01"
        bad_version = _request(
            port,
            "POST",
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            bad_version_headers,
        )

    assert no_session[0] == 400
    assert bad_version[0] == 400


def test_http_enforces_content_negotiation_and_single_message(tmp_path: Path) -> None:
    with running_server(tmp_path) as (port, origin):
        json_only = _headers(origin)
        json_only["Accept"] = "application/json"
        unacceptable = _request(port, "POST", _initialize_message(), json_only)

        wrong_type = _headers(origin)
        wrong_type["Content-Type"] = "text/plain"
        unsupported_media = _request(
            port,
            "POST",
            _initialize_message(),
            wrong_type,
        )
        batch = _request(
            port,
            "POST",
            [_initialize_message()],
            _headers(origin),
        )

    assert unacceptable[0] == 406
    assert unsupported_media[0] == 415
    assert batch[0] == 400
    assert "one JSON-RPC object" in batch[2]["error"]["message"]


def test_http_rejects_remote_or_unauthenticated_unsafe_defaults(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="allow_remote"):
        build_mcp_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            host="0.0.0.0",
            port=0,
            auth_token=TOKEN,
        )
    with pytest.raises(ValueError, match="requires a bearer token"):
        build_mcp_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            port=0,
            auth_token=None,
        )
    with pytest.raises(ValueError, match="limited to localhost"):
        build_mcp_http_server(
            tmp_path,
            tmp_path / "trace.jsonl",
            host="0.0.0.0",
            port=0,
            auth_token=None,
            allow_remote=True,
            allow_unauthenticated=True,
        )
    local_dev_server = build_mcp_http_server(
        tmp_path,
        tmp_path / "local-dev-trace.jsonl",
        port=0,
        auth_token=None,
        allow_unauthenticated=True,
    )
    local_dev_server.server_close()


def test_http_session_store_expires_idle_sessions(tmp_path: Path) -> None:
    now = [100.0]
    protocol_server = build_mcp_server(tmp_path, tmp_path / "trace.jsonl")
    store = MCPHTTPSessionStore(
        lambda: protocol_server,
        10,
        clock=lambda: now[0],
    )

    session_id, _session = store.create(SUPPORTED_PROTOCOL_VERSION)
    now[0] = 111.0

    assert store.get(session_id) is None
    assert store.delete(session_id) is False


def test_http_endpoint_and_origin_normalization() -> None:
    assert normalize_endpoint("/mcp/") == "/mcp"
    assert normalize_origin("https://Example.com") == "https://example.com:443"
    assert normalize_origin("http://localhost:8000/") == "http://localhost:8000"
    with pytest.raises(ValueError, match="absolute path"):
        normalize_endpoint("mcp")
    with pytest.raises(ValueError, match="Invalid MCP HTTP origin"):
        normalize_origin("https://example.com/path")


def _initialize_message() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": SUPPORTED_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.1.0"},
        },
    }


def _headers(
    origin: str,
    *,
    auth: bool = True,
    session_id: str | None = None,
    protocol: bool = False,
) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": origin,
    }
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if session_id:
        headers[MCP_SESSION_HEADER] = session_id
    if protocol:
        headers[MCP_PROTOCOL_HEADER] = SUPPORTED_PROTOCOL_VERSION
    return headers


def _request(
    port: int,
    method: str,
    payload: Any | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], dict[str, Any], bytes]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = dict(headers)
    if body is not None:
        request_headers["Content-Length"] = str(len(body))
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, "/mcp", body=body, headers=request_headers)
        response = connection.getresponse()
        raw_body = response.read()
        response_headers = {name.lower(): value for name, value in response.getheaders()}
        decoded = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        return response.status, response_headers, decoded, raw_body
    finally:
        connection.close()


def _stdio_tool_names(tmp_path: Path) -> set[str]:
    server = build_mcp_server(
        tmp_path,
        tmp_path / "mcp_stdio_trace.jsonl",
        fresh_trace=True,
    )
    stdin = StringIO(json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }) + "\n")
    stdout = StringIO()
    serve_stdio(server, stdin=stdin, stdout=stdout)
    response = json.loads(stdout.getvalue())
    return {item["name"] for item in response["result"]["tools"]}
