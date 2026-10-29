from pathlib import Path

import pytest

from harness.agent import VERIFICATION_GUIDANCE, _budgeted_system_prompt, run_agent
from harness.tools import build_registry, todo_verification_summary
from harness.trace import TraceLogger
from tests.test_agent import FakeBlock, FakeClient, FakeResponse


def registry_at(path):
    return build_registry(path, TraceLogger(path / "trace.jsonl"))


def test_legacy_todos_still_work_without_requirement_fields(tmp_path: Path):
    registry = registry_at(tmp_path)
    result = registry.call("todo_write", todos="Read source")
    assert result.ok
    assert registry.todos == [{"task": "Read source", "status": "pending"}]
    assert result.metadata["verification"]["requirement_items"] == 0


def test_requirement_mapping_is_preserved_but_not_attested(tmp_path: Path):
    registry = registry_at(tmp_path)
    items = [
        {"task": "Verify boundary", "status": "completed", "requirement": "Strict cutoff",
         "check": "Compare just below and exactly at cutoff"},
        {"task": "Verify immutability", "requirement": "Do not mutate input"},
    ]
    result = registry.call("todo_write", todos=items)
    assert result.ok
    assert registry.todos[0]["check"] == items[0]["check"]
    summary = result.metadata["verification"]
    assert summary["requirement_items"] == 2
    assert summary["without_check"] == 1
    assert summary["completed_without_evidence"] == 1
    assert summary["open_items"] == 1
    assert "do not prove" in result.output
    items[0]["evidence"] = "not run: unavailable dependency"
    registry.call("todo_write", todos=items)
    # Even an explicit unverified observation fills a self-report field, not a proof.
    assert todo_verification_summary(registry.todos)["completed_without_evidence"] == 0
    assert "not complete requirement coverage" in summary["interpretation"]


@pytest.mark.parametrize("value", [None, 123, "x" * 601])
def test_invalid_mapping_does_not_replace_existing_plan(tmp_path: Path, value):
    registry = registry_at(tmp_path)
    registry.call("todo_write", todos="Read source")
    result = registry.call("todo_write", todos=[{"task": "Verify input", "check": value}])
    assert not result.ok
    assert registry.todos == [{"task": "Read source", "status": "pending"}]


def test_dynamic_budget_guidance_is_bounded_and_non_task_specific():
    large = [{"task": "x" * 10000, "requirement": "y" * 600, "status": "pending"}]
    prompt = _budgeted_system_prompt("base", 2, large)
    assert "2 model request(s) remain" in prompt
    assert "Verification/finalization budget" in prompt
    assert "missing_checks=1" in prompt
    assert len(prompt) < 1000
    assert "x" * 100 not in prompt
    assert "Derive checks from those clauses" in VERIFICATION_GUIDANCE


def test_budget_counts_down_without_extra_model_turns(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HARNESS_VERIFICATION_GUIDANCE", "on")
    from harness.context_window import ContextWindow

    prepared = []
    original = ContextWindow.prepare

    def prepare(self, system, *args):
        prepared.append(system)
        return original(self, system, *args)

    monkeypatch.setattr(ContextWindow, "prepare", prepare)
    (tmp_path / "source.py").write_text("value = 1\n")
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="read", name="read_file",
                                           input={"path": "source.py"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="Read source.py.")]),
    ])
    answer = run_agent("Read source.py", registry_at(tmp_path), max_turns=2,
                       client=client, model="fixture", retrieval_preflight=False)
    assert answer == "Read source.py."
    assert len(client.messages.calls) == 2
    assert "2 model request(s) remain" in prepared[0]
    assert "1 model request(s) remain" in prepared[1]
    assert [call["system"] for call in client.messages.calls] == prepared
    assert len(client.messages.calls[-1]["messages"]) == 4


def test_default_prompt_does_not_promote_experimental_guidance(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("HARNESS_VERIFICATION_GUIDANCE", raising=False)
    client = FakeClient([FakeResponse("end_turn", [FakeBlock("text", text="No changes.")])])
    run_agent("Inspect", registry_at(tmp_path), client=client, model="fixture",
              retrieval_preflight=False)
    assert "Harness turn budget:" not in client.messages.calls[0]["system"]
    assert "Derive checks from those clauses" not in client.messages.calls[0]["system"]


def test_resume_keeps_saved_guidance_mode_after_environment_changes(tmp_path: Path, monkeypatch):
    from harness.run_store import SQLiteRunStore

    monkeypatch.setenv("HARNESS_VERIFICATION_GUIDANCE", "on")
    (tmp_path / "source.py").write_text("value = 1\n")
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    client = FakeClient([
        FakeResponse("tool_use", [FakeBlock("tool_use", id="read", name="read_file",
                                           input={"path": "source.py"})]),
        FakeResponse("end_turn", [FakeBlock("text", text="Read source.py.")]),
    ])
    answer = run_agent("Read source.py", registry_at(tmp_path), max_turns=1,
                       client=client, model="fixture", retrieval_preflight=False, run_store=store)
    assert answer.startswith("Stopped: max_turns")
    run_id = store.list_runs()[0]["id"]
    assert store.load(run_id)["verification_guidance"] is True
    monkeypatch.setenv("HARNESS_VERIFICATION_GUIDANCE", "off")
    answer = run_agent("", registry_at(tmp_path), max_turns=1, client=client,
                       run_store=store, resume_run_id=run_id)
    assert answer == "Read source.py."
    assert "1 model request(s) remain" in client.messages.calls[-1]["system"]
