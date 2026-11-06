import json
import sys
import threading
import time
from pathlib import Path

import pytest

from harness.mcp_client import ExternalMCPTools, load_client_config
from harness.mcp_sdk_http import build_mcp_sdk_http_server
from harness.tools import build_registry
from harness.trace import TraceLogger


def save_config(path, server):
    path.write_text(json.dumps({"version": 1, "servers": [server]}))
    return path


def test_real_stdio_discovery_namespacing_permissions_and_shutdown(tmp_path):
    workspace = tmp_path / "source"
    workspace.mkdir()
    (workspace / "note.txt").write_text("external evidence")
    root = Path(__file__).resolve().parents[1]
    config = save_config(tmp_path / "client.json", {
        "name": "fixture", "transport": "stdio", "command": sys.executable,
        "args": [str(root / "main.py"), "--workspace", str(workspace), "--trace",
                 str(tmp_path / "remote.jsonl"), "mcp-server"],
        "cwd": str(root), "timeout": 20,
        "tools": {"read_file": "read", "write_file": "write"},
    })
    registry = build_registry(workspace, TraceLogger(tmp_path / "local.jsonl"))
    with ExternalMCPTools(registry, config):
        assert "mcp__fixture__read_file" in registry.names()
        assert registry.call("mcp__fixture__read_file", path="note.txt").output.startswith("external evidence")
        blocked = registry.call("mcp__fixture__write_file", path="created.txt", content="x")
        assert not blocked.ok and not (workspace / "created.txt").exists()
        assert registry.external_tool_policy
    assert "mcp__fixture__read_file" not in registry.names()
    assert not any(thread.name == "mcp-fixture" for thread in threading.enumerate())


def test_real_authenticated_http_client_and_server_shutdown(tmp_path, monkeypatch):
    (tmp_path / "note.txt").write_text("HTTP evidence")
    server = build_mcp_sdk_http_server(tmp_path, tmp_path / "server.jsonl", port=0,
                                      auth_token="local-integration-secret")
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.02)
        monkeypatch.setenv("TEST_MCP_BEARER", "local-integration-secret")
        config = save_config(tmp_path / "client.json", {
            "name": "httpfixture", "transport": "http",
            "url": f"http://127.0.0.1:{server.server_address[1]}/mcp",
            "token_env": "TEST_MCP_BEARER", "tools": {"read_file": "read"}, "timeout": 10,
        })
        local = tmp_path / "agent_workspace"
        local.mkdir()
        registry = build_registry(local, TraceLogger(tmp_path / "local.jsonl"))
        with ExternalMCPTools(registry, config):
            result = registry.call("mcp__httpfixture__read_file", path="note.txt")
            assert result.ok and result.output.startswith("HTTP evidence")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=15)
    assert not thread.is_alive()


@pytest.mark.parametrize("server", [
    {"name": "x", "command": "python", "tools": {}},
    {"name": "x", "command": "python", "tools": {"read": "admin"}},
    {"name": "x", "transport": "http", "url": "http://example.com/mcp", "tools": {"read": "read"}},
    {"name": "x", "transport": "http", "url": "https://u:p@example.com/mcp", "tools": {"read": "read"}},
    {"name": "x", "command": "python", "args": "-c code", "tools": {"read": "read"}},
])
def test_config_rejects_implicit_permissions_and_unsafe_endpoints(tmp_path, server):
    with pytest.raises(ValueError):
        load_client_config(save_config(tmp_path / "bad.json", server))


def test_remote_errors_deadline_and_no_automatic_reconnect(tmp_path):
    config = save_config(tmp_path / "client.json", {
        "name": "bounded", "command": sys.executable,
        "args": [str(Path(__file__).parent / "fixtures" / "external_mcp_server.py")],
        "timeout": 5, "tools": {"echo": "read", "fail": "read", "slow": "write"},
    })
    local = tmp_path / "agent_workspace"
    local.mkdir()
    registry = build_registry(local, TraceLogger(tmp_path / "trace.jsonl"), allow_write=True)
    with ExternalMCPTools(registry, config):
        result = registry.call("mcp__bounded__fail")
        assert not result.ok and result.metadata["tool_error"]["code"] == "mcp_tool_error"
        assert registry.call("mcp__bounded__echo", value="still connected", name="argument named name").ok
        slow = registry.call("mcp__bounded__slow")
        assert not slow.ok and slow.metadata["tool_error"]["code"] == "mcp_timeout"
        assert registry.call("mcp__bounded__echo", value="no retry").metadata["tool_error"]["code"] == "mcp_disconnected"
    assert not any(thread.name == "mcp-bounded" for thread in threading.enumerate())


def test_agent_uses_real_external_tool_through_durable_ledger(tmp_path):
    from harness.agent import run_agent
    from harness.run_store import SQLiteRunStore
    from tests.test_agent import FakeBlock, FakeClient, FakeResponse

    config = save_config(tmp_path / "client.json", {
        "name": "agent", "command": sys.executable,
        "args": [str(Path(__file__).parent / "fixtures" / "external_mcp_server.py")],
        "timeout": 10, "tools": {"echo": "read"},
    })
    local = tmp_path / "agent_workspace"
    local.mkdir()
    registry = build_registry(local, TraceLogger(tmp_path / "trace.jsonl"))
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="remote", name="mcp__agent__echo",
                                           input={"value": "external evidence"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="Used mcp__agent__echo.")]),
    ])
    with ExternalMCPTools(registry, config):
        answer = run_agent("Use external evidence", registry, client=client, model="fixture",
                           run_store=store, retrieval_preflight=False)
    run_id = store.list_runs()[0]["id"]
    assert answer == "Used mcp__agent__echo."
    assert store.calls(run_id)[0]["result"]["content"] == "external evidence"
    assert store.load(run_id)["policy"]["external_tools"]


def test_mutable_or_changed_client_policy_rejected_before_process_launch(tmp_path, monkeypatch):
    from harness.mcp_client import MCPConnection

    config = save_config(tmp_path / "client.json", {
        "name": "policy", "command": sys.executable, "tools": {"read": "read"},
    })
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    monkeypatch.setattr(MCPConnection, "__enter__", lambda _: pytest.fail("must not launch"))
    with pytest.raises(ValueError, match="outside"):
        with ExternalMCPTools(registry, config):
            pass
    local = tmp_path / "agent_workspace"
    local.mkdir()
    registry = build_registry(local, TraceLogger(tmp_path / "local.jsonl"))
    with pytest.raises(ValueError, match="policy changed"):
        with ExternalMCPTools(registry, config, expected_policy={}):
            pass
