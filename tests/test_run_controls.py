from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.agent import run_agent
from harness.model_clients import _parse_openai_response
from harness.run_controls import RunControlConfig, RunControls
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger
from tests.test_agent import FakeBlock, FakeClient, FakeResponse


def registry_at(path, config):
    registry = build_registry(path, TraceLogger(path / "trace.jsonl"), allow_write=True)
    registry.run_controls = RunControls(config, path)
    return registry


def test_tool_budget_stops_pending_call_before_marking_started_and_survives_resume(tmp_path):
    registry = registry_at(tmp_path, RunControlConfig(max_tools=1))
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    client = FakeClient([FakeResponse("tool_use", [
        FakeBlock("tool_use", id="one", name="write_file", input={"path": "one.py", "content": "one=1"}),
        FakeBlock("tool_use", id="two", name="write_file", input={"path": "two.py", "content": "two=2"}),
    ])])
    assert "tool_budget" in run_agent("write", registry, client=client, model="fixture",
                                      run_store=store, retrieval_preflight=False)
    run_id = store.list_runs()[0]["id"]
    assert [c["status"] for c in store.calls(run_id)] == ["completed", "pending"]
    assert not (tmp_path / "two.py").exists()
    restored = registry_at(tmp_path, RunControlConfig(max_tools=1))
    assert "tool_budget" in run_agent("", restored, client=FakeClient([]), run_store=store,
                                      resume_run_id=run_id, retrieval_preflight=False)
    assert store.load(run_id)["control_state"]["tools"] == 1
    assert [c["status"] for c in store.calls(run_id)] == ["completed", "pending"]


def test_unknown_usage_blocks_token_limited_run_without_tool_execution(tmp_path):
    registry = registry_at(tmp_path, RunControlConfig(max_tokens=100))
    client = FakeClient([FakeResponse("tool_use", [FakeBlock("tool_use", id="one", name="write_file",
                                    input={"path": "one.py", "content": "one=1"})])])
    assert "token_usage_unknown" in run_agent("write", registry, client=client, retrieval_preflight=False)
    assert not (tmp_path / "one.py").exists()
    assert _parse_openai_response({"choices": [{"message": {"content": "done"}}]}).usage is None


def test_reported_token_budget_and_pending_model_usage(tmp_path):
    registry = registry_at(tmp_path, RunControlConfig(max_tokens=10))
    response = FakeResponse("end_turn", [FakeBlock("text", text="done")])
    response.usage = SimpleNamespace(input_tokens=8, output_tokens=3)
    assert "token_budget" in run_agent("read", registry, client=FakeClient([response]), retrieval_preflight=False)
    controller = RunControls(RunControlConfig(max_tokens=100), tmp_path)
    controller.start({**registry.run_controls.state, "unknown_usage": False, "pending_model": True})
    assert controller.reason() == "token_usage_unknown"
    from harness.redaction import redact
    assert redact(registry.run_controls.policy())["max_tokens"] == 10


def test_time_budget_persists_and_cancellation_is_operator_owned(tmp_path):
    ticks = [0.0]
    controls = RunControls(RunControlConfig(max_seconds=3), tmp_path, clock=lambda: ticks[0])
    controls.start()
    ticks[0] = 2
    state = controls.checkpoint().copy()
    restored = RunControls(controls.config, tmp_path, clock=lambda: ticks[0])
    restored.start(state)
    ticks[0] = 4
    assert restored.reason() == "time_budget"
    with pytest.raises(ValueError, match="outside"):
        RunControls(RunControlConfig(cancel_file=str(tmp_path / "stop")), tmp_path)
    cancel = tmp_path.parent / (tmp_path.name + "-cancel")
    controls = RunControls(RunControlConfig(cancel_file=str(cancel)), tmp_path)
    controls.start()
    cancel.touch()
    try:
        assert controls.reason() == "cancelled"
    finally:
        cancel.unlink()


def test_consecutive_identical_observations_stop_and_are_durable(tmp_path):
    controls = RunControls(RunControlConfig(repeat_limit=2), tmp_path)
    controls.start()
    controls.observe("read_file", {"path": "a.py"}, True, "same")
    assert controls.reason() is None
    controls.observe("read_file", {"path": "a.py"}, True, "same")
    assert controls.reason() == "no_progress"
    again = RunControls(controls.config, tmp_path)
    again.start(controls.state.copy())
    assert again.reason() == "no_progress"


@pytest.mark.parametrize("options", [{"max_tools": 0}, {"max_tokens": True},
                                      {"max_seconds": float("nan")}, {"repeat_limit": -1}])
def test_invalid_limits_rejected(options):
    with pytest.raises(ValueError):
        RunControlConfig(**options)
