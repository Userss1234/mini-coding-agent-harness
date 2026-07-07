from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, TextIO
from urllib.parse import unquote

from .tools import ToolRegistry, build_registry, safe_path
from .trace import TraceLogger


SUPPORTED_PROTOCOL_VERSION = "2025-11-25"
TEXT_MIME = "text/markdown"

ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603


class MCPToolServer:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.initialized = False
        self.resources = _build_resource_catalog(registry.workspace)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return _error_response(None, ERROR_INVALID_REQUEST, "Request must be a JSON object.")

        message_id = message.get("id")
        method = message.get("method")
        if not method:
            if message_id is None:
                return None
            return _error_response(message_id, ERROR_INVALID_REQUEST, "Missing method.")

        if method == "notifications/initialized":
            self.initialized = True
            return None
        if method == "initialize":
            return _response(message_id, self._initialize_result(message))
        if method == "ping":
            return _response(message_id, {})
        if method == "tools/list":
            return _response(message_id, {"tools": self._list_tools()})
        if method == "tools/call":
            return self._call_tool_response(message_id, message.get("params"))
        if method == "resources/list":
            return _response(message_id, {"resources": self._list_resources()})
        if method == "resources/templates/list":
            return _response(message_id, {"resourceTemplates": _list_resource_templates()})
        if method == "resources/read":
            return self._read_resource_response(message_id, message.get("params"))
        if method == "prompts/list":
            return _response(message_id, {"prompts": _list_prompts()})
        if method == "prompts/get":
            return self._get_prompt_response(message_id, message.get("params"))

        if message_id is None:
            return None
        return _error_response(message_id, ERROR_METHOD_NOT_FOUND, f"Unknown method: {method}")

    def _initialize_result(self, message: dict[str, Any]) -> dict[str, Any]:
        params = message.get("params") or {}
        requested = str(params.get("protocolVersion") or SUPPORTED_PROTOCOL_VERSION)
        return {
            "protocolVersion": requested if requested == SUPPORTED_PROTOCOL_VERSION else SUPPORTED_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": "mini-coding-agent-harness",
                "title": "Mini Coding Agent Harness",
                "version": "0.1.0",
            },
            "instructions": (
                "Use tools to inspect and maintain a local repository. "
                "Writes are governed by the harness permission policy."
            ),
        }

    def _list_resources(self) -> list[dict[str, Any]]:
        return [
            {
                "uri": item["uri"],
                "name": item["name"],
                "description": item["description"],
                "mimeType": item["mimeType"],
            }
            for item in self.resources
        ]

    def _read_resource_response(self, message_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error_response(message_id, ERROR_INVALID_PARAMS, "resources/read params must be an object.")
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri:
            return _error_response(message_id, ERROR_INVALID_PARAMS, "resources/read params.uri must be a string.")
        resource = next((item for item in self.resources if item["uri"] == uri), None)
        if resource is not None:
            path = resource["path"]
            mime_type = resource["mimeType"]
        else:
            resolved = _workspace_resource_path(self.registry.workspace, uri)
            if isinstance(resolved, str):
                return _error_response(message_id, ERROR_INVALID_PARAMS, resolved)
            path = resolved
            mime_type = _guess_text_mime(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return _error_response(message_id, ERROR_INTERNAL, f"Could not read resource {uri}: {exc}")
        return _response(message_id, {
            "contents": [{
                "uri": uri,
                "mimeType": mime_type,
                "text": text,
            }]
        })

    def _get_prompt_response(self, message_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error_response(message_id, ERROR_INVALID_PARAMS, "prompts/get params must be an object.")
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return _error_response(message_id, ERROR_INVALID_PARAMS, "prompts/get params.name must be a string.")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error_response(message_id, ERROR_INVALID_PARAMS, "prompts/get params.arguments must be an object.")
        prompt = _build_prompt(name, arguments)
        if prompt is None:
            return _error_response(message_id, ERROR_INVALID_PARAMS, f"Unknown prompt: {name}")
        return _response(message_id, prompt)

    def _list_tools(self) -> list[dict[str, Any]]:
        items = []
        for tool_name in self.registry.names():
            tool = self.registry._tools[tool_name]
            items.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "annotations": _tool_annotations(tool.risk),
            })
        return items

    def _call_tool_response(self, message_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return _error_response(message_id, ERROR_INVALID_PARAMS, "tools/call params must be an object.")

        name = params.get("name")
        if not isinstance(name, str) or not name:
            return _error_response(message_id, ERROR_INVALID_PARAMS, "tools/call params.name must be a string.")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error_response(message_id, ERROR_INVALID_PARAMS, "tools/call params.arguments must be an object.")
        if name not in self.registry.names():
            return _error_response(message_id, ERROR_METHOD_NOT_FOUND, f"Unknown tool: {name}")

        try:
            result = self.registry.call(name, **arguments)
        except TypeError as exc:
            return _error_response(message_id, ERROR_INVALID_PARAMS, f"Invalid arguments for {name}: {exc}")
        except Exception as exc:
            return _error_response(message_id, ERROR_INTERNAL, f"{type(exc).__name__}: {exc}")

        payload = {
            "content": [{"type": "text", "text": result.output}],
            "structuredContent": {
                "ok": result.ok,
                "metadata": result.metadata or {},
            },
            "isError": not result.ok,
        }
        return _response(message_id, payload)


def build_mcp_server(
    workspace: Path,
    trace_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = False,
) -> MCPToolServer:
    if fresh_trace and trace_path.exists():
        trace_path.unlink()
    trace = TraceLogger(trace_path)
    trace.log(
        "session_start",
        workspace=str(workspace.resolve()),
        transport="mcp-stdio",
        allow_write=allow_write,
    )
    return MCPToolServer(build_registry(workspace.resolve(), trace, allow_write=allow_write))


def serve_stdio(server: MCPToolServer, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    in_stream = stdin or sys.stdin
    out_stream = stdout or sys.stdout
    for line in in_stream:
        if not line.strip():
            continue
        response = _handle_json_line(server, line)
        if response is None:
            continue
        out_stream.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
        out_stream.flush()


def _handle_json_line(server: MCPToolServer, line: str) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        return _error_response(None, ERROR_PARSE, f"Parse error: {exc}")
    if isinstance(message, list):
        responses = []
        for item in message:
            response = server.handle_message(item)
            if response is not None:
                responses.append(response)
        return responses or None
    return server.handle_message(message)


def _tool_annotations(risk: str) -> dict[str, bool]:
    read_only = risk == "read"
    return {
        "readOnlyHint": read_only,
        "destructiveHint": risk == "write",
        "idempotentHint": read_only,
        "openWorldHint": risk == "shell",
    }


def _build_resource_catalog(workspace: Path) -> list[dict[str, Any]]:
    candidates = [
        ("harness://docs/readme", "README", "Project overview and usage guide.", workspace / "README.md"),
        ("harness://docs/readme-zh", "README.zh-CN", "Chinese project overview and usage guide.", workspace / "README.zh-CN.md"),
        ("harness://docs/mcp", "MCP", "MCP server usage and protocol boundary notes.", workspace / "MCP.md"),
        ("harness://reports/eval", "EVAL", "Latest scripted benchmark snapshot.", workspace / "EVAL.md"),
        ("harness://reports/agent-eval", "AGENT_EVAL", "Latest committed real-agent evaluation report.", workspace / "reports" / "AGENT_EVAL.md"),
        ("harness://reports/agent-compare", "AGENT_COMPARE_2_TASKS", "Committed memory/context ablation report.", workspace / "reports" / "AGENT_COMPARE_2_TASKS.md"),
        ("harness://reports/demo-python-bugfix", "DEMO_python_bugfix", "Committed deterministic local demo report.", workspace / "reports" / "DEMO_python_bugfix.md"),
    ]
    resources = []
    for uri, name, description, path in candidates:
        if path.exists() and path.is_file():
            resources.append({
                "uri": uri,
                "name": name,
                "description": description,
                "mimeType": TEXT_MIME,
                "path": path,
            })
    return resources


def _list_resource_templates() -> list[dict[str, Any]]:
    return [{
        "uriTemplate": "harness://workspace/{path}",
        "name": "workspace-file",
        "title": "Workspace File",
        "description": "Read a non-sensitive text file inside the configured workspace.",
        "mimeType": "text/plain",
        "annotations": {"audience": ["assistant"], "priority": 0.7},
    }]


def _workspace_resource_path(workspace: Path, uri: str) -> Path | str:
    prefix = "harness://workspace/"
    if not uri.startswith(prefix):
        return f"Unknown resource URI: {uri}"
    rel = unquote(uri[len(prefix):]).strip()
    if not rel:
        return "Workspace resource path must not be empty."
    try:
        target = safe_path(workspace, rel)
    except ValueError as exc:
        return str(exc)
    if not _is_allowed_workspace_resource(workspace, target):
        return f"Workspace resource is blocked by policy: {rel}"
    if not target.exists():
        return f"Workspace resource not found: {rel}"
    if not target.is_file():
        return f"Workspace resource is not a file: {rel}"
    return target


def _is_allowed_workspace_resource(workspace: Path, target: Path) -> bool:
    try:
        rel = target.resolve().relative_to(workspace.resolve())
    except ValueError:
        return False
    blocked_parts = {".git", ".venv", "__pycache__", ".pytest_cache", "artifacts", "eval_runs"}
    if any(part in blocked_parts for part in rel.parts):
        return False
    blocked_names = {".env", "trace.jsonl", "EVAL.json", "COMPARE.json"}
    return target.name not in blocked_names


def _guess_text_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".py":
        return "text/x-python"
    if suffix == ".json":
        return "application/json"
    if suffix in {".html", ".htm"}:
        return "text/html"
    return "text/plain"


def _list_prompts() -> list[dict[str, Any]]:
    return [
        {
            "name": "code-maintenance-task",
            "title": "Code Maintenance Task",
            "description": "Plan and execute a repository maintenance task with tool evidence.",
            "arguments": [
                {"name": "task", "description": "The maintenance task to perform.", "required": True}
            ],
        },
        {
            "name": "eval-analysis",
            "title": "Evaluation Analysis",
            "description": "Analyze benchmark or agent-eval results and summarize risks.",
            "arguments": [
                {"name": "report_uri", "description": "Optional MCP resource URI for the report.", "required": False}
            ],
        },
    ]


def _build_prompt(name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    if name == "code-maintenance-task":
        task = str(arguments.get("task") or "").strip()
        if not task:
            task = "Inspect the repository, identify the smallest safe change, run verification, and summarize evidence."
        return {
            "description": "Repository maintenance prompt with planning and verification requirements.",
            "messages": [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        "Use the available MCP tools to complete this repository maintenance task.\n"
                        "Start with todo_write, use context_pack when the relevant files are not obvious, "
                        "inspect relevant files, make the smallest safe change, "
                        "run run_tests or run_py_compile, inspect git_diff, and finish with files changed and evidence.\n\n"
                        f"Task: {task}"
                    ),
                },
            }],
        }
    if name == "eval-analysis":
        report_uri = str(arguments.get("report_uri") or "harness://reports/agent-eval").strip()
        return {
            "description": "Evaluation report analysis prompt.",
            "messages": [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Read MCP resource `{report_uri}` if available, then summarize pass rate, "
                        "tool-call cost, failure categories, residual risks, and the next evaluation step."
                    ),
                },
            }],
        }
    return None


def _response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error_response(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }
