from __future__ import annotations

import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import uvicorn
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .mcp_http import (
    DEFAULT_HTTP_ENDPOINT,
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
    DEFAULT_SESSION_TTL_SECONDS,
    MAX_REQUEST_BYTES,
    MCP_SESSION_HEADER,
    MCPHTTPConfig,
    normalize_endpoint,
    normalize_origin,
)
from .mcp_sdk import build_mcp_sdk_server
from .trace import TraceLogger


class StaticTokenVerifier:
    def __init__(self, expected_token: str):
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self._expected_token):
            return None
        return AccessToken(
            token="[redacted]",
            client_id="mini-coding-agent-harness",
            scopes=[],
        )


@dataclass
class MCPSDKHTTPServer:
    config: MCPHTTPConfig
    _socket: socket.socket
    _server: uvicorn.Server

    @property
    def server_address(self) -> tuple[Any, ...]:
        address = self._socket.getsockname()
        return address if isinstance(address, tuple) else (address,)

    @property
    def started(self) -> bool:
        return self._server.started

    def serve_forever(self, poll_interval: float = 0.2) -> None:
        del poll_interval
        self._server.run(sockets=[self._socket])

    def shutdown(self) -> None:
        self._server.should_exit = True

    def server_close(self) -> None:
        try:
            self._socket.close()
        except OSError:
            pass


class _ExactCORSTraceMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        config: MCPHTTPConfig,
        trace: TraceLogger,
    ):
        self.app = app
        self.config = config
        self.trace = trace

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method = str(scope.get("method", ""))
        path = str(scope.get("path", ""))
        origin = headers.get("origin")
        origin_allowed = _origin_allowed(origin, self.config.allowed_origins)

        if method == "OPTIONS" and path == self.config.endpoint:
            status = 204 if origin_allowed else 403
            response_headers = _cors_headers(origin) if origin and origin_allowed else {}
            response_headers.update(
                {
                    "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": (
                        "Authorization, Content-Type, Accept, MCP-Session-Id, "
                        "MCP-Protocol-Version"
                    ),
                }
            )
            await Response(status_code=status, headers=response_headers)(
                scope,
                receive,
                send,
            )
            self._trace_request(method, path, status, headers)
            return

        traced = False

        async def send_with_cors(message: Message) -> None:
            nonlocal traced
            if message["type"] == "http.response.start":
                status = int(message["status"])
                if origin and origin_allowed:
                    response_headers = MutableHeaders(scope=message)
                    for name, value in _cors_headers(origin).items():
                        response_headers[name] = value
                if not traced:
                    self._trace_request(method, path, status, headers)
                    traced = True
            await send(message)

        await self.app(scope, receive, send_with_cors)

    def _trace_request(
        self,
        method: str,
        path: str,
        status: int,
        headers: Headers,
    ) -> None:
        self.trace.log(
            "mcp_http_request",
            method=method,
            path=path,
            status=status,
            origin_present=bool(headers.get("origin")),
            session_present=bool(headers.get(MCP_SESSION_HEADER)),
        )


def build_mcp_sdk_http_server(
    workspace: Path,
    trace_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = False,
    host: str = DEFAULT_HTTP_HOST,
    port: int = DEFAULT_HTTP_PORT,
    endpoint: str = DEFAULT_HTTP_ENDPOINT,
    auth_token: str | None,
    allowed_origins: list[str] | None = None,
    allow_remote: bool = False,
    allow_unauthenticated: bool = False,
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> MCPSDKHTTPServer:
    host = host.strip().lower()
    _validate_http_options(
        host=host,
        port=port,
        auth_token=auth_token,
        allow_remote=allow_remote,
        allow_unauthenticated=allow_unauthenticated,
        session_ttl_seconds=session_ttl_seconds,
    )
    endpoint = normalize_endpoint(endpoint)
    server_socket = _bind_socket(host, port)
    actual_port = int(server_socket.getsockname()[1])
    origin_values = allowed_origins or [
        f"http://127.0.0.1:{actual_port}",
        f"http://localhost:{actual_port}",
    ]
    normalized_origins = tuple(
        sorted({normalize_origin(value) for value in origin_values})
    )
    config = MCPHTTPConfig(
        host=host,
        port=actual_port,
        endpoint=endpoint,
        allowed_origins=normalized_origins,
        session_ttl_seconds=session_ttl_seconds,
        auth_token=auth_token,
    )

    try:
        sdk_server = build_mcp_sdk_server(
            workspace.resolve(),
            trace_path,
            allow_write=allow_write,
            fresh_trace=fresh_trace,
            transport="mcp-sdk-v2-http",
        )
        trace = TraceLogger(trace_path)
        trace.log(
            "mcp_http_runtime",
            host=host,
            port=actual_port,
            endpoint=endpoint,
            authentication="bearer" if auth_token else "disabled-localhost-only",
        )
        auth = None
        token_verifier = None
        if auth_token:
            auth = AuthSettings(
                issuer_url=f"http://{host}:{actual_port}",
                resource_server_url=None,
                required_scopes=[],
            )
            token_verifier = StaticTokenVerifier(auth_token)
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=_allowed_hosts(host, actual_port, normalized_origins),
            allowed_origins=_transport_origins(normalized_origins),
        )
        app = sdk_server.streamable_http_app(
            streamable_http_path=endpoint,
            json_response=True,
            stateless_http=False,
            max_request_body_size=MAX_REQUEST_BYTES,
            session_idle_timeout=float(session_ttl_seconds),
            transport_security=security,
            host=host,
            auth=auth,
            token_verifier=token_verifier,
        )
        wrapped_app = _ExactCORSTraceMiddleware(app, config=config, trace=trace)
        uvicorn_config = uvicorn.Config(
            wrapped_app,
            host=host,
            port=actual_port,
            log_level="warning",
            access_log=False,
            lifespan="on",
            timeout_graceful_shutdown=5,
        )
        return MCPSDKHTTPServer(
            config=config,
            _socket=server_socket,
            _server=uvicorn.Server(uvicorn_config),
        )
    except Exception:
        server_socket.close()
        raise


def serve_mcp_sdk_http(server: MCPSDKHTTPServer) -> None:
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _validate_http_options(
    *,
    host: str,
    port: int,
    auth_token: str | None,
    allow_remote: bool,
    allow_unauthenticated: bool,
    session_ttl_seconds: int,
) -> None:
    if host not in {"127.0.0.1", "localhost"} and not allow_remote:
        raise ValueError("Remote MCP HTTP binding requires explicit allow_remote=True.")
    if not auth_token and not allow_unauthenticated:
        raise ValueError(
            "MCP HTTP requires a bearer token; set HARNESS_MCP_AUTH_TOKEN or "
            "explicitly allow unauthenticated localhost development."
        )
    if not auth_token and host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Unauthenticated MCP HTTP is limited to localhost.")
    if port < 0 or port > 65535:
        raise ValueError("MCP HTTP port must be between 0 and 65535.")
    if session_ttl_seconds <= 0:
        raise ValueError("MCP HTTP session TTL must be greater than zero.")


def _bind_socket(host: str, port: int) -> socket.socket:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    server_socket = socket.socket(family=family)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((host, port))
        server_socket.set_inheritable(True)
        return server_socket
    except Exception:
        server_socket.close()
        raise


def _allowed_hosts(
    host: str,
    port: int,
    origins: tuple[str, ...],
) -> list[str]:
    hosts = {f"{host}:{port}"}
    if host in {"127.0.0.1", "localhost"}:
        hosts.update({f"127.0.0.1:{port}", f"localhost:{port}"})
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.netloc:
            hosts.add(parsed.netloc)
    return sorted(hosts)


def _origin_allowed(origin: str | None, allowed_origins: tuple[str, ...]) -> bool:
    if not origin:
        return True
    try:
        return normalize_origin(origin) in allowed_origins
    except ValueError:
        return False


def _transport_origins(origins: tuple[str, ...]) -> list[str]:
    values = set(origins)
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme, parsed.port) in {("http", 80), ("https", 443)}:
            values.add(f"{parsed.scheme}://{parsed.hostname}")
    return sorted(values)


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Expose-Headers": MCP_SESSION_HEADER,
        "Vary": "Origin",
    }
