from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from typing import Callable
from urllib.parse import urlsplit

from .mcp_server import (
    ERROR_INVALID_REQUEST,
    MCPToolServer,
    SUPPORTED_PROTOCOL_VERSION,
)
from .tools import build_registry
from .trace import TraceLogger


MCP_SESSION_HEADER = "MCP-Session-Id"
MCP_PROTOCOL_HEADER = "MCP-Protocol-Version"
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000
DEFAULT_HTTP_ENDPOINT = "/mcp"
DEFAULT_SESSION_TTL_SECONDS = 3600
MAX_REQUEST_BYTES = 1_048_576


@dataclass(frozen=True)
class MCPHTTPConfig:
    host: str
    port: int
    endpoint: str
    allowed_origins: tuple[str, ...]
    session_ttl_seconds: int
    auth_token: str | None = field(repr=False)


@dataclass
class _HTTPSession:
    server: MCPToolServer
    protocol_version: str
    expires_at: float
    lock: threading.Lock = field(default_factory=threading.Lock)


class MCPHTTPSessionStore:
    def __init__(
        self,
        server_factory: Callable[[], MCPToolServer],
        ttl_seconds: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ):
        if ttl_seconds <= 0:
            raise ValueError("MCP HTTP session TTL must be greater than zero.")
        self._server_factory = server_factory
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, _HTTPSession] = {}
        self._lock = threading.Lock()

    def create(self, protocol_version: str) -> tuple[str, _HTTPSession]:
        with self._lock:
            self._remove_expired_locked()
            session_id = secrets.token_urlsafe(32)
            while session_id in self._sessions:
                session_id = secrets.token_urlsafe(32)
            session = _HTTPSession(
                server=self._server_factory(),
                protocol_version=protocol_version,
                expires_at=self._clock() + self._ttl_seconds,
            )
            self._sessions[session_id] = session
            return session_id, session

    def get(self, session_id: str) -> _HTTPSession | None:
        with self._lock:
            self._remove_expired_locked()
            session = self._sessions.get(session_id)
            if session is not None:
                session.expires_at = self._clock() + self._ttl_seconds
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            self._remove_expired_locked()
            return self._sessions.pop(session_id, None) is not None

    def _remove_expired_locked(self) -> None:
        now = self._clock()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for session_id in expired:
            del self._sessions[session_id]


class MCPStreamableHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        config: MCPHTTPConfig,
        sessions: MCPHTTPSessionStore,
        trace: TraceLogger,
    ):
        self.config = config
        self.sessions = sessions
        self.trace = trace
        super().__init__(server_address, MCPStreamableHTTPRequestHandler)


class MCPStreamableHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MiniCodingAgentMCP/0.1"

    def do_OPTIONS(self) -> None:
        if not self._validate_endpoint_and_origin():
            return
        self.send_response(204)
        self._write_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "POST, GET, DELETE, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, Accept, MCP-Session-Id, MCP-Protocol-Version",
        )
        self.send_header("Content-Length", "0")
        self.end_headers()
        self._trace_request(204)

    def do_POST(self) -> None:
        if not self._validate_request(require_auth=True):
            return
        if not self._accepts_streamable_http():
            self._send_error_json(
                406,
                "Accept must include application/json and text/event-stream.",
            )
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send_error_json(415, "Content-Type must be application/json.")
            return

        message = self._read_json_message()
        if message is None:
            return

        session_id = self.headers.get(MCP_SESSION_HEADER, "").strip()
        method = message.get("method")
        if method == "initialize":
            if session_id:
                self._send_error_json(400, "Initialize must not include MCP-Session-Id.")
                return
            params = message.get("params") or {}
            if not isinstance(params, dict):
                self._send_error_json(400, "Initialize params must be a JSON object.")
                return
            requested = str(
                params.get("protocolVersion")
                or SUPPORTED_PROTOCOL_VERSION
            )
            negotiated = (
                requested
                if requested == SUPPORTED_PROTOCOL_VERSION
                else SUPPORTED_PROTOCOL_VERSION
            )
            session_id, session = self.server.sessions.create(negotiated)
            with session.lock:
                response = session.server.handle_message(message)
            self._send_json(200, response, {MCP_SESSION_HEADER: session_id})
            return

        session = self._require_session(session_id)
        if session is None:
            return
        if not self._validate_protocol_version(session):
            return

        if not method and ("result" in message or "error" in message):
            self._send_empty(202)
            return
        with session.lock:
            response = session.server.handle_message(message)
        if response is None:
            self._send_empty(202)
            return
        self._send_json(200, response)

    def do_GET(self) -> None:
        if not self._validate_request(require_auth=True):
            return
        session = self._require_session(
            self.headers.get(MCP_SESSION_HEADER, "").strip()
        )
        if session is None:
            return
        if not self._validate_protocol_version(session):
            return
        self._send_error_json(
            405,
            "This server returns JSON responses and does not provide an SSE listener.",
            headers={"Allow": "POST, DELETE, OPTIONS"},
        )

    def do_DELETE(self) -> None:
        if not self._validate_request(require_auth=True):
            return
        session_id = self.headers.get(MCP_SESSION_HEADER, "").strip()
        if not session_id:
            self._send_error_json(400, "MCP-Session-Id is required.")
            return
        session = self.server.sessions.get(session_id)
        if session is None:
            self._send_error_json(404, "MCP session not found or expired.")
            return
        if not self._validate_protocol_version(session):
            return
        self.server.sessions.delete(session_id)
        self._send_empty(204)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _validate_request(self, *, require_auth: bool) -> bool:
        if not self._validate_endpoint_and_origin():
            return False
        if require_auth and not self._validate_auth():
            return False
        return True

    def _validate_endpoint_and_origin(self) -> bool:
        if urlsplit(self.path).path != self.server.config.endpoint:
            self._send_error_json(404, "MCP endpoint not found.")
            return False
        origin = self.headers.get("Origin")
        if origin:
            try:
                normalized = normalize_origin(origin)
            except ValueError:
                self._send_error_json(403, "Origin is not allowed.")
                return False
            if normalized not in self.server.config.allowed_origins:
                self._send_error_json(403, "Origin is not allowed.")
                return False
        return True

    def _validate_auth(self) -> bool:
        token = self.server.config.auth_token
        if token is None:
            return True
        supplied = self.headers.get("Authorization", "")
        if not secrets.compare_digest(supplied, f"Bearer {token}"):
            self._send_error_json(
                401,
                "Bearer authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            return False
        return True

    def _accepts_streamable_http(self) -> bool:
        accepted = {
            item.split(";", 1)[0].strip().lower()
            for item in self.headers.get("Accept", "").split(",")
        }
        return "application/json" in accepted and "text/event-stream" in accepted

    def _read_json_message(self) -> dict | None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_json(400, "Content-Length must be an integer.")
            return None
        if content_length <= 0:
            self._send_error_json(400, "Request body must not be empty.")
            return None
        if content_length > MAX_REQUEST_BYTES:
            self._send_error_json(413, "Request body exceeds the server limit.")
            return None
        try:
            raw = self.rfile.read(content_length)
            message = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_error_json(400, f"Invalid UTF-8 JSON request: {exc}")
            return None
        if not isinstance(message, dict):
            self._send_error_json(400, "Streamable HTTP requires one JSON-RPC object per POST.")
            return None
        return message

    def _require_session(self, session_id: str) -> _HTTPSession | None:
        if not session_id:
            self._send_error_json(400, "MCP-Session-Id is required after initialization.")
            return None
        session = self.server.sessions.get(session_id)
        if session is None:
            self._send_error_json(404, "MCP session not found or expired.")
            return None
        return session

    def _validate_protocol_version(self, session: _HTTPSession) -> bool:
        supplied = self.headers.get(MCP_PROTOCOL_HEADER)
        if supplied and supplied.strip() != session.protocol_version:
            self._send_error_json(400, "Unsupported MCP-Protocol-Version.")
            return False
        return True

    def _send_error_json(
        self,
        status: int,
        message: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.close_connection = True
        payload = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": ERROR_INVALID_REQUEST, "message": message},
        }
        response_headers = {"Connection": "close", **(headers or {})}
        self._send_json(status, payload, response_headers)

    def _send_json(
        self,
        status: int,
        payload: object,
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)
        self._trace_request(status)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self._write_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()
        self._trace_request(status)

    def _write_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if not origin:
            return
        try:
            normalized = normalize_origin(origin)
        except ValueError:
            return
        if normalized not in self.server.config.allowed_origins:
            return
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Expose-Headers", MCP_SESSION_HEADER)
        self.send_header("Vary", "Origin")

    def _trace_request(self, status: int) -> None:
        self.server.trace.log(
            "mcp_http_request",
            method=self.command,
            path=urlsplit(self.path).path,
            status=status,
            origin_present=bool(self.headers.get("Origin")),
            session_present=bool(self.headers.get(MCP_SESSION_HEADER)),
        )


def build_mcp_http_server(
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
) -> MCPStreamableHTTPServer:
    host = host.strip().lower()
    if host not in {"127.0.0.1", "localhost"} and not allow_remote:
        raise ValueError(
            "Remote MCP HTTP binding requires explicit allow_remote=True."
        )
    if not auth_token and not allow_unauthenticated:
        raise ValueError(
            "MCP HTTP requires a bearer token; set HARNESS_MCP_AUTH_TOKEN or "
            "explicitly allow unauthenticated localhost development."
        )
    if not auth_token and host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Unauthenticated MCP HTTP is limited to localhost.")
    if port < 0 or port > 65535:
        raise ValueError("MCP HTTP port must be between 0 and 65535.")
    endpoint = normalize_endpoint(endpoint)
    workspace = workspace.resolve()
    if fresh_trace and trace_path.exists():
        trace_path.unlink()
    trace = TraceLogger(trace_path)
    trace.log(
        "session_start",
        workspace=str(workspace),
        transport="mcp-streamable-http",
        allow_write=allow_write,
        host=host,
        port=port,
        endpoint=endpoint,
        authentication="bearer" if auth_token else "disabled-localhost-only",
    )

    def server_factory() -> MCPToolServer:
        registry = build_registry(workspace, trace, allow_write=allow_write)
        return MCPToolServer(registry)

    sessions = MCPHTTPSessionStore(server_factory, session_ttl_seconds)
    provisional = MCPHTTPConfig(
        host=host,
        port=port,
        endpoint=endpoint,
        allowed_origins=(),
        session_ttl_seconds=session_ttl_seconds,
        auth_token=auth_token,
    )
    server = MCPStreamableHTTPServer((host, port), provisional, sessions, trace)
    actual_port = int(server.server_address[1])
    origin_values = allowed_origins or [
        f"http://127.0.0.1:{actual_port}",
        f"http://localhost:{actual_port}",
    ]
    normalized_origins = tuple(
        sorted({normalize_origin(value) for value in origin_values})
    )
    server.config = MCPHTTPConfig(
        host=host,
        port=actual_port,
        endpoint=endpoint,
        allowed_origins=normalized_origins,
        session_ttl_seconds=session_ttl_seconds,
        auth_token=auth_token,
    )
    return server


def serve_streamable_http(server: MCPStreamableHTTPServer) -> None:
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


def normalize_endpoint(value: str) -> str:
    endpoint = value.strip()
    if not endpoint.startswith("/") or "?" in endpoint or "#" in endpoint:
        raise ValueError("MCP HTTP endpoint must be an absolute path without query or fragment.")
    if endpoint != "/":
        endpoint = endpoint.rstrip("/")
    return endpoint


def normalize_origin(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Invalid MCP HTTP origin: {value}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"Invalid MCP HTTP origin: {value}")
    if parsed.path not in {"", "/"}:
        raise ValueError(f"Invalid MCP HTTP origin: {value}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Invalid MCP HTTP origin: {value}") from exc
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return f"{parsed.scheme}://{parsed.hostname.lower()}:{port}"
