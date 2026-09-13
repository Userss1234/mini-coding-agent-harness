from __future__ import annotations

import http.client
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from .hybrid_retrieval import (
    DEFAULT_EMBEDDING_MODEL,
    get_sentence_transformer_embedder,
)
from .mcp_http import (
    MCP_PROTOCOL_HEADER,
    MCP_SESSION_HEADER,
    SUPPORTED_PROTOCOL_VERSION,
)
from .mcp_sdk_http import build_mcp_sdk_http_server

CROSS_FEATURE_TOKEN = "cross-feature-local-token"
CROSS_FEATURE_QUERY = "Streamable HTTP Origin authentication session lifecycle"
EXPECTED_IMPLEMENTATION_PATH = "harness/mcp_sdk_http.py"


def run_cross_feature_smoke(
    workspace: Path,
    trace_path: Path,
    docker_report_path: Path,
    output_path: Path,
    *,
    fresh_trace: bool = False,
    allow_model_download: bool = False,
) -> str:
    workspace = workspace.resolve()
    docker_evidence = inspect_docker_report(docker_report_path)
    live_started = time.perf_counter()
    mcp_evidence = run_live_hybrid_mcp_check(
        workspace,
        trace_path,
        fresh_trace=fresh_trace,
        allow_model_download=allow_model_download,
    )
    mcp_evidence["validation_duration_seconds"] = round(
        time.perf_counter() - live_started,
        3,
    )
    if not docker_evidence["passed"]:
        status = "blocked" if docker_evidence["missing"] else "fail"
    elif mcp_evidence["blocked"]:
        status = "blocked"
    elif mcp_evidence["passed"]:
        status = "pass"
    else:
        status = "fail"
    report = build_cross_feature_report(
        status,
        docker_report_path,
        docker_evidence,
        mcp_evidence,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def inspect_docker_report(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "passed": False,
            "missing": True,
            "details": f"Could not read Docker report: {exc}",
        }
    required = {
        "status": "Status: **pass**" in text,
        "backend": "Execution backend: **docker**" in text,
        "non_root": "uid=10001" in text,
        "workspace": "workspace=ok" in text,
        "network": "network=blocked" in text,
        "no_fallback": "Host fallback | `False`" in text,
    }
    return {
        "passed": all(required.values()),
        "missing": False,
        "checks": required,
        "details": "all Docker runtime markers present" if all(required.values()) else "one or more Docker runtime markers missing",
    }


def run_live_hybrid_mcp_check(
    workspace: Path,
    trace_path: Path,
    *,
    fresh_trace: bool = False,
    allow_model_download: bool = False,
) -> dict[str, Any]:
    preflight = preflight_embedding_model(
        allow_model_download=allow_model_download,
    )
    if not preflight["passed"]:
        return {
            "passed": False,
            "blocked": True,
            "initialize_status": 0,
            "notification_status": 0,
            "tool_status": 0,
            "session_issued": False,
            "retrieval": "missing",
            "embedding_model": DEFAULT_EMBEDDING_MODEL,
            "embedding_preflight_seconds": preflight["duration_seconds"],
            "match_paths": [],
            "expected_path_found": False,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_written": False,
            "tool_error": preflight["error"],
        }
    server = build_mcp_sdk_http_server(
        workspace,
        trace_path,
        fresh_trace=fresh_trace,
        port=0,
        auth_token=CROSS_FEATURE_TOKEN,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server(server, thread)
    port = int(server.server_address[1])
    origin = f"http://127.0.0.1:{port}"
    headers = {
        "Authorization": f"Bearer {CROSS_FEATURE_TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Origin": origin,
    }
    initialized: tuple[int, dict[str, str], dict[str, Any]] = (0, {}, {})
    notification: tuple[int, dict[str, str], dict[str, Any]] = (0, {}, {})
    searched: tuple[int, dict[str, str], dict[str, Any]] = (0, {}, {})
    session_id = ""
    request_error = ""
    try:
        initialized = _request(port, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": SUPPORTED_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "cross-feature-smoke", "version": "0.1.0"},
            },
        }, headers)
        session_id = initialized[1].get(MCP_SESSION_HEADER.lower(), "")
        session_headers = dict(headers)
        session_headers[MCP_SESSION_HEADER] = session_id
        session_headers[MCP_PROTOCOL_HEADER] = SUPPORTED_PROTOCOL_VERSION
        notification = _request(
            port,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_headers,
        )
        searched = _request(port, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "rag_search",
                "arguments": {
                    "query": CROSS_FEATURE_QUERY,
                    "glob": "harness/*.py,MCP.md",
                    "limit": 3,
                    "backend": "hybrid",
                },
            },
        }, session_headers)
        _request(port, None, session_headers, method="DELETE")
    except Exception as exc:
        request_error = f"{type(exc).__name__}: {exc}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    if request_error:
        return {
            "passed": False,
            "blocked": False,
            "initialize_status": initialized[0],
            "notification_status": notification[0],
            "tool_status": searched[0],
            "session_issued": bool(session_id),
            "retrieval": "missing",
            "embedding_model": "missing",
            "embedding_preflight_seconds": preflight["duration_seconds"],
            "match_paths": [],
            "expected_path_found": False,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_written": False,
            "tool_error": request_error,
        }

    payload = searched[2]
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    structured = result.get("structuredContent", {}) if isinstance(result, dict) else {}
    metadata = structured.get("metadata", {}) if isinstance(structured, dict) else {}
    matches = metadata.get("matches", []) if isinstance(metadata, dict) else []
    match_paths = [
        str(item.get("path", ""))
        for item in matches
        if isinstance(item, dict)
    ]
    hybrid = metadata.get("hybrid", {}) if isinstance(metadata, dict) else {}
    cache = hybrid.get("cache", {}) if isinstance(hybrid, dict) else {}
    output_text = ""
    content = result.get("content", []) if isinstance(result, dict) else []
    if content and isinstance(content[0], dict):
        output_text = str(content[0].get("text", ""))
    dependency_blocked = (
        bool(result.get("isError"))
        and "Hybrid retrieval requires the optional local dependency" in output_text
    )
    passed = all([
        initialized[0] == 200,
        bool(session_id),
        notification[0] == 202,
        searched[0] == 200,
        result.get("isError") is False,
        metadata.get("retrieval") == "local_chunk_hybrid_scoring",
        EXPECTED_IMPLEMENTATION_PATH in match_paths,
    ])
    return {
        "passed": passed,
        "blocked": dependency_blocked,
        "initialize_status": initialized[0],
        "notification_status": notification[0],
        "tool_status": searched[0],
        "session_issued": bool(session_id),
        "retrieval": metadata.get("retrieval", "missing") if isinstance(metadata, dict) else "missing",
        "embedding_model": hybrid.get("embedding_model", "missing") if isinstance(hybrid, dict) else "missing",
        "embedding_preflight_seconds": preflight["duration_seconds"],
        "match_paths": match_paths,
        "expected_path_found": EXPECTED_IMPLEMENTATION_PATH in match_paths,
        "cache_hits": int(cache.get("hits", 0) or 0) if isinstance(cache, dict) else 0,
        "cache_misses": int(cache.get("misses", 0) or 0) if isinstance(cache, dict) else 0,
        "cache_written": bool(cache.get("written", False)) if isinstance(cache, dict) else False,
        "tool_error": output_text if result.get("isError") else "none",
    }


def _wait_for_server(server: Any, thread: threading.Thread) -> None:
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        raise RuntimeError("SDK HTTP cross-feature server did not start.")


def preflight_embedding_model(*, allow_model_download: bool) -> dict[str, Any]:
    previous = {
        name: os.environ.get(name)
        for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    }
    if not allow_model_download:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    started = time.perf_counter()
    try:
        embedder = get_sentence_transformer_embedder(DEFAULT_EMBEDDING_MODEL)
        vector = embedder.encode_query(CROSS_FEATURE_QUERY)
        if not vector:
            raise RuntimeError("Embedding preflight returned an empty vector.")
    except Exception as exc:
        return {
            "passed": False,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return {
        "passed": True,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "error": "none",
    }


def build_cross_feature_report(
    status: str,
    docker_report_path: Path,
    docker: dict[str, Any],
    mcp: dict[str, Any],
) -> str:
    docker_checks = docker.get("checks", {})
    docker_rows = "\n".join(
        f"| {name} | {'pass' if passed else 'fail'} |"
        for name, passed in docker_checks.items()
    ) or "| report | fail |"
    matches = ", ".join(f"`{path}`" for path in mcp.get("match_paths", [])) or "none"
    tool_error = str(mcp.get("tool_error", "none")).replace("|", "\\|").replace("\n", " ")[:500]
    return f"""# Docker + Hybrid RAG + MCP Cross-Feature Validation

Status: **{status}**

## Evidence Model

- Docker evidence source: `{docker_report_path}`
- Docker evidence mode: committed or current CI runtime report inspection
- Hybrid RAG evidence mode: live `rag_search` call through localhost MCP Streamable HTTP
- Expected implementation evidence: `{EXPECTED_IMPLEMENTATION_PATH}` within the top 3 matches

## Docker Boundary

| Check | Status |
|---|---|
{docker_rows}

Docker result: **{'pass' if docker.get('passed') else 'fail'}** ({docker.get('details', 'no details')})

## Live MCP + Hybrid Retrieval

| Check | Observed |
|---|---|
| Initialize HTTP status | {mcp.get('initialize_status', 'missing')} |
| Session issued | {'yes' if mcp.get('session_issued') else 'no'} |
| Initialized notification status | {mcp.get('notification_status', 'missing')} |
| Tool HTTP status | {mcp.get('tool_status', 'missing')} |
| Retrieval marker | `{mcp.get('retrieval', 'missing')}` |
| Embedding model | `{mcp.get('embedding_model', 'missing')}` |
| Embedding preflight | {mcp.get('embedding_preflight_seconds', 0)}s |
| Live validation duration | {mcp.get('validation_duration_seconds', 0)}s |
| Expected implementation path found | {'yes' if mcp.get('expected_path_found') else 'no'} |
| Embedding cache H/M/W | {mcp.get('cache_hits', 0)}/{mcp.get('cache_misses', 0)}/{'1' if mcp.get('cache_written') else '0'} |
| Tool/request error | {tool_error} |

Top matches: {matches}

Live MCP + hybrid result: **{'pass' if mcp.get('passed') else ('blocked' if mcp.get('blocked') else 'fail')}**

## Interpretation

This report joins two evidence paths without claiming that the embedding model runs inside the Docker sandbox. The Docker report proves the command-execution boundary. The live HTTP call proves that an authenticated MCP session reaches the shared permission-checked registry, selects the local hybrid backend, and returns implementation evidence. A passing CI rerun rebuilds the Docker image before generating this report.
"""


def _request(
    port: int,
    payload: dict[str, Any] | None,
    headers: dict[str, str],
    *,
    method: str = "POST",
) -> tuple[int, dict[str, str], dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = dict(headers)
    if body is not None:
        request_headers["Content-Length"] = str(len(body))
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=600)
    try:
        connection.request(method, "/mcp", body=body, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        response_headers = {name.lower(): value for name, value in response.getheaders()}
        decoded = json.loads(raw.decode("utf-8")) if raw else {}
        return response.status, response_headers, decoded
    finally:
        connection.close()
