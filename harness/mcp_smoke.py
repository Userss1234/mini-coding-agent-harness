from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mcp_server import MCPToolServer, build_mcp_server


def run_mcp_smoke(
    workspace: Path,
    trace_path: Path,
    output_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = True,
) -> str:
    server = build_mcp_server(
        workspace,
        trace_path,
        allow_write=allow_write,
        fresh_trace=fresh_trace,
    )
    transcript = _run_smoke_messages(server)
    report = _format_smoke_report(transcript, trace_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def _run_smoke_messages(server: MCPToolServer) -> list[dict[str, Any]]:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "mcp-smoke", "version": "0.1.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 4, "method": "resources/templates/list"},
        {"jsonrpc": "2.0", "id": 5, "method": "prompts/list"},
        {"jsonrpc": "2.0", "id": 6, "method": "resources/read", "params": {"uri": "harness://docs/mcp"}},
        {"jsonrpc": "2.0", "id": 7, "method": "prompts/get", "params": {"name": "code-maintenance-task", "arguments": {"task": "Fix a failing test and show evidence."}}},
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "permission_policy", "arguments": {}}},
    ]
    transcript = []
    for message in messages:
        response = server.handle_message(message)
        transcript.append({"request": message, "response": response})
    return transcript


def _format_smoke_report(transcript: list[dict[str, Any]], trace_path: Path) -> str:
    initialize = _response_for(transcript, 1)
    tools = _response_for(transcript, 2).get("result", {}).get("tools", [])
    resources = _response_for(transcript, 3).get("result", {}).get("resources", [])
    templates = _response_for(transcript, 4).get("result", {}).get("resourceTemplates", [])
    prompts = _response_for(transcript, 5).get("result", {}).get("prompts", [])
    permission = _response_for(transcript, 8).get("result", {})
    capability_names = sorted((initialize.get("result", {}).get("capabilities") or {}).keys())
    tool_names = sorted(item.get("name", "") for item in tools)
    resource_uris = sorted(item.get("uri", "") for item in resources)
    template_names = sorted(item.get("name", "") for item in templates)
    prompt_names = sorted(item.get("name", "") for item in prompts)

    return f"""# MCP Smoke Report

- Trace: `{trace_path}`
- Capabilities: {", ".join(capability_names)}
- Tool count: {len(tool_names)}
- Resource count: {len(resource_uris)}
- Resource template count: {len(template_names)}
- Prompt count: {len(prompt_names)}
- Permission policy call isError: `{permission.get("isError")}`

## Tools

{_bullet_rows(tool_names)}

## Resources

{_bullet_rows(resource_uris)}

## Resource Templates

{_bullet_rows(template_names)}

## Prompts

{_bullet_rows(prompt_names)}

## Transcript

```json
{json.dumps(transcript, ensure_ascii=False, indent=2)}
```
"""


def _response_for(transcript: list[dict[str, Any]], message_id: int) -> dict[str, Any]:
    for item in transcript:
        request = item.get("request") or {}
        if request.get("id") == message_id:
            return item.get("response") or {}
    return {}


def _bullet_rows(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items if item) or "- None."
