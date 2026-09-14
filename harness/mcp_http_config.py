from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

MCP_SESSION_HEADER = "MCP-Session-Id"
MCP_PROTOCOL_HEADER = "MCP-Protocol-Version"
LEGACY_PROTOCOL_VERSION = "2025-11-25"
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


def normalize_endpoint(value: str) -> str:
    endpoint = value.strip()
    if not endpoint.startswith("/") or "?" in endpoint or "#" in endpoint:
        raise ValueError(
            "MCP HTTP endpoint must be an absolute path without query or fragment."
        )
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
