import json
import threading

import pytest

from harness.agent import run_agent
from harness.run_store import SQLiteRunStore
from harness.tools import Tool, ToolRegistry, ToolResult, build_registry
from harness.trace import TraceLogger
from tests.test_agent import FakeBlock, FakeClient, FakeResponse


def test_schema_validation_has_stable_errors_before_side_effects(tmp_path):
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    for arguments in ({"path": 1}, {"path": "new.txt", "content": "x", "extra": 1}):
        result = registry.call("write_file", **arguments)
        assert not result.ok and result.metadata["tool_error"]["code"] == "invalid_arguments"
    assert not (tmp_path / "new.txt").exists()
    assert not registry.call("read_file", path="../outside.txt").ok
    assert registry.call("not_a_tool").metadata["tool_error"]["code"] == "unknown_tool"
    schema = next(item for item in registry.schemas() if item["name"] == "write_file")
    assert schema["input_schema"]["additionalProperties"] is False


def test_parallel_reads_preserve_order_and_durable_result_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_TOOL_READ_WORKERS", "2")
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    barrier = threading.Barrier(2)

    def read(path):
        barrier.wait(timeout=5)
        return ToolResult(True, path)

    registry.register(Tool("read_file", "read", {"type": "object", "properties": {
        "path": {"type": "string"}}, "required": ["path"]}, read))
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="a", name="read_file", input={"path": "a"}),
                                  FakeBlock("tool_use", id="b", name="read_file", input={"path": "b"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="Read a and b.")]),
    ])
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    run_agent("read", registry, client=client, model="fake", run_store=store,
              retrieval_preflight=False)
    calls = store.calls(store.list_runs()[0]["id"])
    assert [call["status"] for call in calls] == ["completed", "completed"]
    assert [call["result"]["content"] for call in calls] == ["a", "b"]
    assert all(json.loads(line) for line in registry.trace.path.read_text().splitlines())


def test_mixed_batch_stays_serial_and_external_writes_require_permission(tmp_path):
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    order = []
    for name in ["read_file", "mutate"]:
        registry.register(Tool(name, name, {"type": "object"},
                               lambda name=name: (order.append(name) or ToolResult(True, name))))
    registry.call_batch([("read_file", {}), ("mutate", {})], workers=4)
    assert order == ["read_file", "mutate"]
    registry.register(Tool("mcp__demo__write", "remote", {"type": "object"},
                           lambda: pytest.fail("must not execute"), risk="external_write"))
    result = registry.call("mcp__demo__write")
    assert result.metadata["tool_error"]["code"] == "permission_denied"


def test_duplicate_provider_ids_rejected_before_nonpersistent_execution(tmp_path):
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    blocks = [FakeBlock("tool_use", id="same", name="write_file",
                        input={"path": str(i), "content": "x"}) for i in range(2)]
    with pytest.raises(ValueError, match="Duplicate"):
        run_agent("write", registry, client=FakeClient([FakeResponse("tool_use", blocks)]),
                  model="fake", retrieval_preflight=False)
    assert not (tmp_path / "0").exists()


def test_registration_collision_does_not_override_existing_handler(tmp_path):
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    registry.register(Tool("one", "one", {"type": "object"}, lambda: ToolResult(True, "one")))
    with pytest.raises(ValueError, match="already"):
        registry.register(Tool("one", "two", {"type": "object"}, lambda: ToolResult(True, "two")))
    assert registry.call("one").output == "one"


def test_tool_schemas_cannot_fetch_remote_references(tmp_path):
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    for keyword in ("$ref", "$dynamicRef", "$recursiveRef"):
        with pytest.raises(ValueError, match="External schema"):
            registry.register(Tool("remote_ref", "ref", {keyword: "http://127.0.0.1/private"},
                                   lambda: ToolResult(True, "must not execute")))


def test_non_object_arguments_are_completed_as_errors_without_execution(tmp_path):
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    registry.register(Tool("danger", "must not run", {"type": "object"},
                           lambda: pytest.fail("malformed arguments must not execute"), risk="write"))
    blocks = [FakeBlock("tool_use", id=str(i), name="danger", input=value)
              for i, value in enumerate([[], "{invalid", None, 0])]
    client = FakeClient([FakeResponse("tool_use", blocks),
                         FakeResponse("end_turn", [FakeBlock("text", text="Handled errors.")])])
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    run_agent("test", registry, client=client, model="fake", run_store=store,
              retrieval_preflight=False, max_turns=2)
    calls = store.calls(store.list_runs()[0]["id"])
    assert len(calls) == 4 and all(call["result"]["is_error"] for call in calls)


def test_parser_preserves_invalid_arguments_instead_of_turning_them_into_empty_object():
    from harness.model_clients import _parse_openai_response

    for value in ["{invalid", "", "[]", "0", None]:
        response = _parse_openai_response({"choices": [{"message": {"tool_calls": [{
            "id": "call", "function": {"name": "danger", "arguments": value},
        }]}}]})
        assert not isinstance(response.content[0].input, dict)


def test_unknown_external_write_remains_blocked_for_operator_reconciliation(tmp_path):
    registry = ToolRegistry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"), allow_write=True)
    registry.register(Tool("mcp__demo__write", "remote", {"type": "object"},
                           lambda: ToolResult(False, "timed out", {"remote_outcome_unknown": True}),
                           risk="external_write"))
    registry.external_tool_policy["mcp__demo__write"] = {"risk": "write", "server_fingerprint": "fixture"}
    block = FakeBlock("tool_use", id="remote-write", name="mcp__demo__write", input={})
    client = FakeClient([FakeResponse("tool_use", [block])])
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    answer = run_agent("write", registry, client=client, model="fake", run_store=store,
                       retrieval_preflight=False)
    run_id = store.list_runs()[0]["id"]
    assert "outcome is unknown" in answer
    assert store.calls(run_id)[0]["status"] == "started"
    assert store.load(run_id)["status"] == "blocked"
    with pytest.raises(RuntimeError, match="unknown outcome"):
        run_agent("", registry, client=client, run_store=store, resume_run_id=run_id)
