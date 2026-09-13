from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from mcp.server import Server
from mcp.shared.exceptions import MCPError

from harness.mcp_sdk import build_mcp_sdk_server


@pytest.mark.parametrize(
    ("mode", "expected_version"),
    [
        ("auto", "2026-07-28"),
        ("legacy", "2025-11-25"),
    ],
)
def test_sdk_server_preserves_surface_across_protocol_eras(
    tmp_path: Path,
    mode: str,
    expected_version: str,
) -> None:
    (tmp_path / "README.md").write_text("# SDK bridge\n", encoding="utf-8")
    trace_path = tmp_path / f"{mode}.jsonl"
    server = build_mcp_sdk_server(tmp_path, trace_path, fresh_trace=True)

    result = asyncio.run(_exercise_surface(server, mode))

    assert result["protocol_version"] == expected_version
    assert "read_file" in result["tool_names"]
    assert result["read_file_required"] == ["path"]
    assert result["read_file_read_only"] is True
    assert result["tool_text"] == "# SDK bridge\n"
    assert result["tool_ok"] is True
    assert "harness://docs/readme" in result["resource_uris"]
    assert result["resource_text"] == "# SDK bridge\n"
    assert "harness://workspace/{path}" in result["template_uris"]
    assert "code-maintenance-task" in result["prompt_names"]
    assert "Fix SDK parity." in result["prompt_text"]

    trace = trace_path.read_text(encoding="utf-8")
    assert '"transport": "mcp-sdk-v2"' in trace
    assert f'"protocol_version": "{expected_version}"' in trace
    assert '"event": "tool_call"' in trace


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_sdk_server_keeps_permission_failures_as_tool_results(
    tmp_path: Path,
    mode: str,
) -> None:
    target = tmp_path / "README.md"
    target.write_text("# Original\n", encoding="utf-8")
    server = build_mcp_sdk_server(
        tmp_path,
        tmp_path / f"{mode}.jsonl",
        fresh_trace=True,
    )

    result = asyncio.run(_blocked_write(server, mode))

    assert result.is_error is True
    assert result.structured_content["ok"] is False
    assert "blocked_overwrite_requires_allow_write" in result.content[0].text
    assert target.read_text(encoding="utf-8") == "# Original\n"


def test_sdk_server_maps_surface_errors_to_mcp_errors(tmp_path: Path) -> None:
    server = build_mcp_sdk_server(
        tmp_path,
        tmp_path / "sdk.jsonl",
        fresh_trace=True,
    )

    error = asyncio.run(_read_unknown_resource(server))

    assert error.code == -32602
    assert "Unknown resource URI" in error.message


async def _exercise_surface(server: Server[Any], mode: str) -> dict[str, Any]:
    async with Client(server, mode=mode) as client:
        tools = await client.list_tools()
        read_file = next(tool for tool in tools.tools if tool.name == "read_file")
        called = await client.call_tool("read_file", {"path": "README.md"})
        resources = await client.list_resources()
        resource = await client.read_resource("harness://docs/readme")
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()
        prompt = await client.get_prompt(
            "code-maintenance-task",
            {"task": "Fix SDK parity."},
        )
        return {
            "protocol_version": client.protocol_version,
            "tool_names": {tool.name for tool in tools.tools},
            "read_file_required": read_file.input_schema["required"],
            "read_file_read_only": read_file.annotations.read_only_hint,
            "tool_text": called.content[0].text,
            "tool_ok": called.structured_content["ok"],
            "resource_uris": {str(item.uri) for item in resources.resources},
            "resource_text": resource.contents[0].text,
            "template_uris": {
                str(item.uri_template) for item in templates.resource_templates
            },
            "prompt_names": {item.name for item in prompts.prompts},
            "prompt_text": prompt.messages[0].content.text,
        }


async def _blocked_write(server: Server[Any], mode: str):
    async with Client(server, mode=mode) as client:
        return await client.call_tool(
            "write_file",
            {"path": "README.md", "content": "# Changed\n"},
        )


async def _read_unknown_resource(server: Server[Any]) -> MCPError:
    async with Client(server) as client:
        try:
            await client.read_resource("file:///etc/passwd")
        except MCPError as exc:
            return exc
    raise AssertionError("Expected resources/read to fail.")
