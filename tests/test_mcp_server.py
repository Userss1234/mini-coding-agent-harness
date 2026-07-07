from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from harness.mcp_server import build_mcp_server, serve_stdio


def test_mcp_initialize_and_list_tools(tmp_path: Path) -> None:
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    initialize = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"},
    })
    listed = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert initialize["result"]["serverInfo"]["name"] == "mini-coding-agent-harness"
    assert "tools" in initialize["result"]["capabilities"]
    assert "resources" in initialize["result"]["capabilities"]
    assert "prompts" in initialize["result"]["capabilities"]
    tools = {item["name"]: item for item in listed["result"]["tools"]}
    assert "read_file" in tools
    assert "context_pack" in tools
    assert "run_tests" in tools
    assert tools["read_file"]["inputSchema"]["required"] == ["path"]
    assert tools["context_pack"]["inputSchema"]["required"] == ["query"]
    assert tools["read_file"]["annotations"]["readOnlyHint"] is True
    assert tools["write_file"]["annotations"]["destructiveHint"] is True


def test_mcp_tools_call_returns_text_and_structured_content(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {"name": "read_file", "arguments": {"path": "README.md"}},
    })

    assert response["id"] == "call-1"
    assert response["result"]["content"] == [{"type": "text", "text": "# Demo\n"}]
    assert response["result"]["structuredContent"]["ok"] is True
    assert response["result"]["isError"] is False
    assert "tool_call" in (tmp_path / "mcp_trace.jsonl").read_text(encoding="utf-8")


def test_mcp_tools_call_reports_permission_errors_as_tool_errors(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", allow_write=False, fresh_trace=True)

    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "write_file",
            "arguments": {"path": "README.md", "content": "# Changed\n"},
        },
    })

    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["ok"] is False
    assert "blocked_overwrite_requires_allow_write" in response["result"]["content"][0]["text"]
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "# Demo\n"


def test_mcp_resources_list_and_read_whitelisted_docs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "MCP.md").write_text("# MCP\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    listed = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
    resources = {item["uri"]: item for item in listed["result"]["resources"]}
    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/read",
        "params": {"uri": "harness://docs/readme"},
    })

    assert "harness://docs/readme" in resources
    assert resources["harness://docs/readme"]["mimeType"] == "text/markdown"
    assert response["result"]["contents"] == [{
        "uri": "harness://docs/readme",
        "mimeType": "text/markdown",
        "text": "# Demo\n",
    }]


def test_mcp_resources_reject_unknown_uri(tmp_path: Path) -> None:
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "resources/read",
        "params": {"uri": "file:///etc/passwd"},
    })

    assert response["error"]["code"] == -32602
    assert "Unknown resource URI" in response["error"]["message"]


def test_mcp_resource_templates_read_workspace_files(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("print('ok')\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    templates = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "resources/templates/list"})
    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/read",
        "params": {"uri": "harness://workspace/sample.py"},
    })

    assert templates["result"]["resourceTemplates"][0]["uriTemplate"] == "harness://workspace/{path}"
    assert response["result"]["contents"][0]["mimeType"] == "text/x-python"
    assert response["result"]["contents"][0]["text"] == "print('ok')\n"


def test_mcp_workspace_resource_blocks_sensitive_paths(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "trace.jsonl").write_text("{}\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    env_response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "resources/read",
        "params": {"uri": "harness://workspace/.env"},
    })
    artifact_response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/read",
        "params": {"uri": "harness://workspace/artifacts/trace.jsonl"},
    })

    assert env_response["error"]["code"] == -32602
    assert artifact_response["error"]["code"] == -32602
    assert "blocked by policy" in env_response["error"]["message"]
    assert "blocked by policy" in artifact_response["error"]["message"]


def test_mcp_workspace_resource_blocks_path_escape(tmp_path: Path) -> None:
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "resources/read",
        "params": {"uri": "harness://workspace/../outside.txt"},
    })

    assert response["error"]["code"] == -32602
    assert "Path escapes workspace" in response["error"]["message"]


def test_mcp_prompts_list_and_get_prompt(tmp_path: Path) -> None:
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)

    listed = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})
    prompt = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "prompts/get",
        "params": {
            "name": "code-maintenance-task",
            "arguments": {"task": "Fix failing calculator tests."},
        },
    })

    names = {item["name"] for item in listed["result"]["prompts"]}
    text = prompt["result"]["messages"][0]["content"]["text"]
    assert "code-maintenance-task" in names
    assert "eval-analysis" in names
    assert "todo_write" in text
    assert "Fix failing calculator tests." in text


def test_mcp_stdio_writes_jsonrpc_responses(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("hello\n", encoding="utf-8")
    server = build_mcp_server(tmp_path, tmp_path / "mcp_trace.jsonl", fresh_trace=True)
    stdin = StringIO(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
        + json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "sample.txt"}},
        }) + "\n"
    )
    stdout = StringIO()

    serve_stdio(server, stdin=stdin, stdout=stdout)

    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert len(responses) == 2
    assert responses[0] == {"jsonrpc": "2.0", "id": 1, "result": {}}
    assert responses[1]["result"]["content"][0]["text"] == "hello\n"
