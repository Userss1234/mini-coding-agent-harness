from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import anyio.to_thread
import mcp.types as types
from mcp.server import Server, ServerRequestContext
from mcp.shared.exceptions import MCPError

from .mcp_server import MCPToolServer, build_mcp_server

SERVER_NAME = "mini-coding-agent-harness"
SERVER_TITLE = "Mini Coding Agent Harness"
SERVER_VERSION = "0.1.0"
SERVER_INSTRUCTIONS = (
    "Use tools to inspect and maintain a local repository. "
    "Writes are governed by the harness permission policy."
)


def build_mcp_sdk_server(
    workspace: Path,
    trace_path: Path,
    *,
    allow_write: bool = False,
    fresh_trace: bool = False,
) -> Server[Any]:
    surface = build_mcp_server(
        workspace,
        trace_path,
        allow_write=allow_write,
        fresh_trace=fresh_trace,
        transport="mcp-sdk-v2",
    )
    return build_mcp_sdk_server_from_surface(surface)


def build_mcp_sdk_server_from_surface(surface: MCPToolServer) -> Server[Any]:
    async def list_tools(
        ctx: ServerRequestContext[Any],
        _params: types.PaginatedRequestParams | None,
    ) -> types.ListToolsResult:
        _trace_request(surface, ctx, "tools/list")
        return types.ListToolsResult.model_validate(
            _surface_result(surface, "tools/list"),
        )

    async def call_tool(
        ctx: ServerRequestContext[Any],
        params: types.CallToolRequestParams,
    ) -> types.CallToolResult:
        _trace_request(surface, ctx, "tools/call")
        result = await anyio.to_thread.run_sync(
            partial(
                _surface_result,
                surface,
                "tools/call",
                {"name": params.name, "arguments": params.arguments or {}},
            )
        )
        return types.CallToolResult.model_validate(result)

    async def list_resources(
        ctx: ServerRequestContext[Any],
        _params: types.PaginatedRequestParams | None,
    ) -> types.ListResourcesResult:
        _trace_request(surface, ctx, "resources/list")
        return types.ListResourcesResult.model_validate(
            _surface_result(surface, "resources/list"),
        )

    async def list_resource_templates(
        ctx: ServerRequestContext[Any],
        _params: types.PaginatedRequestParams | None,
    ) -> types.ListResourceTemplatesResult:
        _trace_request(surface, ctx, "resources/templates/list")
        return types.ListResourceTemplatesResult.model_validate(
            _surface_result(surface, "resources/templates/list"),
        )

    async def read_resource(
        ctx: ServerRequestContext[Any],
        params: types.ReadResourceRequestParams,
    ) -> types.ReadResourceResult:
        _trace_request(surface, ctx, "resources/read")
        result = await anyio.to_thread.run_sync(
            partial(
                _surface_result,
                surface,
                "resources/read",
                {"uri": params.uri},
            )
        )
        return types.ReadResourceResult.model_validate(result)

    async def list_prompts(
        ctx: ServerRequestContext[Any],
        _params: types.PaginatedRequestParams | None,
    ) -> types.ListPromptsResult:
        _trace_request(surface, ctx, "prompts/list")
        return types.ListPromptsResult.model_validate(
            _surface_result(surface, "prompts/list"),
        )

    async def get_prompt(
        ctx: ServerRequestContext[Any],
        params: types.GetPromptRequestParams,
    ) -> types.GetPromptResult:
        _trace_request(surface, ctx, "prompts/get")
        return types.GetPromptResult.model_validate(
            _surface_result(
                surface,
                "prompts/get",
                {"name": params.name, "arguments": params.arguments or {}},
            )
        )

    return Server(
        SERVER_NAME,
        title=SERVER_TITLE,
        version=SERVER_VERSION,
        instructions=SERVER_INSTRUCTIONS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
        on_list_resources=list_resources,
        on_list_resource_templates=list_resource_templates,
        on_read_resource=read_resource,
        on_list_prompts=list_prompts,
        on_get_prompt=get_prompt,
    )


def _surface_result(
    surface: MCPToolServer,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": "sdk-adapter",
        "method": method,
    }
    if params is not None:
        message["params"] = params
    response = surface.handle_message(message)
    if response is None:
        raise MCPError(-32603, f"No response from compatibility surface for {method}.")
    error = response.get("error")
    if isinstance(error, dict):
        raise MCPError(
            int(error.get("code", -32603)),
            str(error.get("message", "MCP compatibility surface error.")),
            error.get("data"),
        )
    result = response.get("result")
    if not isinstance(result, dict):
        raise MCPError(-32603, f"Invalid compatibility surface result for {method}.")
    return result


def _trace_request(
    surface: MCPToolServer,
    ctx: ServerRequestContext[Any],
    method: str,
) -> None:
    surface.registry.trace.log(
        "mcp_sdk_request",
        method=method,
        protocol_version=ctx.protocol_version,
    )
