from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.agent import run_agent
from harness.model_clients import _convert_messages
from harness.run_store import SQLiteRunStore
from tests.fixtures.run_crash_worker import final_response, registry_for

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).parent / "fixtures" / "run_crash_worker.py"


def killed_run(tmp_path: Path, stage: str) -> tuple[SQLiteRunStore, str]:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    process = subprocess.Popen(
        [sys.executable, str(WORKER), str(tmp_path), stage], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 20
        while not (tmp_path / "ready").exists() and process.poll() is None:
            if time.monotonic() > deadline:
                raise AssertionError("Child did not reach the requested interruption boundary")
            time.sleep(0.02)
        assert (tmp_path / "ready").exists(), process.communicate(timeout=5)
        store = SQLiteRunStore(tmp_path / "runs.sqlite3")
        run_id = store.list_runs()[0]["id"]
        with pytest.raises(RuntimeError, match="already active"):
            with store.lock(run_id):
                pass
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)
    return store, run_id


def resume(tmp_path: Path, store: SQLiteRunStore, run_id: str):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return final_response()

    answer = run_agent(
        "", registry_for(tmp_path), client=SimpleNamespace(messages=SimpleNamespace(create=create)),
        model="fixture", retrieval_preflight=False, run_store=store, resume_run_id=run_id,
    )
    return answer, calls


@pytest.mark.parametrize("stage", ["before_dispatch", "after_result", "model_wait"])
def test_real_process_termination_resumes_without_duplicate_effects(tmp_path: Path, stage: str):
    store, run_id = killed_run(tmp_path, stage)
    assert resume(tmp_path, store, run_id)[0] == "done"
    assert (tmp_path / "effects.txt").read_text().splitlines() == ["one", "two"]
    assert all(call["status"] == "completed" for call in store.calls(run_id))
    assert store.load(run_id)["status"] == "completed"
    # A finished run returns its durable answer without contacting a provider.
    assert run_agent("", registry_for(tmp_path), run_store=store, resume_run_id=run_id) == "done"


def test_unknown_tool_outcome_requires_reconciliation_and_never_reexecutes(tmp_path: Path):
    store, run_id = killed_run(tmp_path, "inside_tool")
    with pytest.raises(RuntimeError, match="unknown outcome"):
        resume(tmp_path, store, run_id)
    assert (tmp_path / "effects.txt").read_text().splitlines() == ["one"]
    assert store.load(run_id)["status"] == "blocked"
    store.reconcile(run_id, "first", "Verified one was recorded", is_error=False)
    assert resume(tmp_path, store, run_id)[0] == "done"
    assert (tmp_path / "effects.txt").read_text().splitlines() == ["one", "two"]
    with pytest.raises(RuntimeError, match="not started"):
        store.reconcile(run_id, "first", "again", is_error=False)


@pytest.mark.parametrize("change", ["workspace", "permission", "backend", "policy", "schema"])
def test_resume_rejects_changed_workspace_or_permissions(tmp_path: Path, change: str):
    store, run_id = killed_run(tmp_path, "before_dispatch")
    registry = registry_for(tmp_path)
    if change == "workspace":
        registry.workspace = tmp_path / "other"
    elif change == "permission":
        registry.allow_write = True
    elif change == "backend":
        registry.execution_backend = "docker"
    elif change == "policy":
        registry.execution_policy = {"network": "host"}
    else:
        registry._tools["record"].description = "A changed schema"
    with pytest.raises(ValueError, match="original workspace"):
        run_agent("", registry, run_store=store, resume_run_id=run_id)


def test_resume_rejects_changed_provider_endpoint(tmp_path: Path):
    store, run_id = killed_run(tmp_path, "before_dispatch")
    client = SimpleNamespace(messages=SimpleNamespace(base_url="https://different.example"))
    with pytest.raises(ValueError, match="original model provider"):
        run_agent("", registry_for(tmp_path), client=client, run_store=store, resume_run_id=run_id)
    assert not (tmp_path / "effects.txt").exists()


def test_sqlite_schema_and_secret_redacted_export(tmp_path: Path, monkeypatch):
    secret = "test-provider-key-123456"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    state = {"status": "paused", "messages": ["use " + secret],
             "credentials": {"api_key": secret}, "note": "Bearer private-access-value"}
    store.create("sample", state)
    output = tmp_path / "export.jsonl"
    store.export("sample", output)
    assert secret not in output.read_text()
    assert secret.encode() not in store.path.read_bytes()
    assert "private-access-value" not in output.read_text()
    assert "[REDACTED]" in output.read_text()
    assert all(isinstance(json.loads(line), dict) for line in output.read_text().splitlines())
    assert SQLiteRunStore(store.path).load("sample")["status"] == "paused"
    with sqlite3.connect(store.path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        db.execute("PRAGMA user_version = 99")
    with pytest.raises(ValueError, match="Unsupported"):
        SQLiteRunStore(store.path)


def test_model_adapter_accepts_restored_assistant_blocks():
    messages = [{"role": "assistant", "content": [
        {"type": "tool_use", "id": "call", "name": "read_file", "input": {"path": "a.py"}}
    ]}]
    assert _convert_messages("system", messages)[1]["tool_calls"][0]["function"]["name"] == "read_file"


def test_pause_at_turn_budget_resumes_with_saved_messages_and_todos(tmp_path: Path):
    from harness.tools import build_registry
    from harness.trace import TraceLogger

    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    response = SimpleNamespace(stop_reason="tool_use", content=[SimpleNamespace(
        type="tool_use", id="todo", name="todo_write", input={"todos": [
            {"task": "Inspect source", "status": "in_progress"},
            {"task": "Verify tests", "status": "pending"},
        ]},
    )])
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))
    assert "max_turns" in run_agent(
        "maintain repo", registry, client=client, model="fixture", max_turns=1,
        retrieval_preflight=False, run_store=store,
    )
    run_id = store.list_runs()[0]["id"]
    state = store.load(run_id)
    assert state["status"] == "paused" and state["turn"] == 1
    assert state["todos"] and state["summary"]
    restored = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    seen = []

    def finish(**kwargs):
        seen.append(kwargs["messages"])
        return final_response()

    client.messages.create = finish
    assert run_agent("", restored, client=client, run_store=store, resume_run_id=run_id) == "done"
    assert restored.todos == state["todos"]
    assert seen[0][0] == state["messages"][0]
    assert seen[0][-2]["content"][0]["tool_use_id"] == "todo"


def test_duplicate_provider_call_ids_leave_last_valid_checkpoint(tmp_path: Path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    block = SimpleNamespace(type="tool_use", id="same", name="record", input={"value": "one"})
    response = SimpleNamespace(stop_reason="tool_use", content=[block])
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))
    with pytest.raises(ValueError, match="Duplicate"):
        run_agent("do it", registry_for(tmp_path), client=client, model="fixture",
                  retrieval_preflight=False, run_store=store)
    run_id = store.list_runs()[0]["id"]
    assert store.load(run_id)["phase"] == "model"
    assert (tmp_path / "effects.txt").read_text().splitlines() == ["one"]
    assert resume(tmp_path, store, run_id)[0] == "done"


def test_model_failure_retains_resumable_checkpoint(tmp_path: Path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")

    def fail(**_kwargs):
        raise ValueError("bad provider response")

    answer = run_agent(
        "do it", registry_for(tmp_path), client=SimpleNamespace(messages=SimpleNamespace(create=fail)),
        model="fixture", retrieval_preflight=False, run_store=store,
    )
    run_id = store.list_runs()[0]["id"]
    assert answer.startswith("Error:")
    assert store.load(run_id)["status"] == "paused"
    assert resume(tmp_path, store, run_id)[0] == "done"


def test_pending_redacted_arguments_never_execute_on_resume(tmp_path: Path, monkeypatch):
    store, run_id = killed_run(tmp_path, "before_dispatch")
    state = store.load(run_id)
    state["messages"][-1]["content"][0]["input"]["value"] = "[REDACTED]"
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE tool_calls SET arguments = ? WHERE call_id = 'first'",
                   (json.dumps({"value": "[REDACTED]"}),))
    store.save(run_id, state)
    with pytest.raises(RuntimeError, match="redacted"):
        resume(tmp_path, store, run_id)
    assert not (tmp_path / "effects.txt").exists()


def test_store_guards_unknown_ids_paths_and_duplicate_execution(tmp_path: Path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    with pytest.raises(ValueError, match="Unknown run"):
        store.load("missing")
    with pytest.raises(ValueError, match="Invalid run ID"):
        with store.lock("../escape"):
            pass
    state = {"status": "running"}
    store.create("test", state)
    store.plan("test", state, [{"id": "call", "name": "record", "input": {}}])
    store.start_call("test", "call")
    with pytest.raises(RuntimeError, match="duplicate execution"):
        store.start_call("test", "call")
    with pytest.raises(ValueError, match="overwrite"):
        store.export("test", store.path)


def test_live_sensitive_argument_is_not_replaced_before_execution(tmp_path: Path, monkeypatch):
    secret = "fixture-sensitive-value-123"
    monkeypatch.setenv("TEST_API_KEY", secret)
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    responses = [SimpleNamespace(stop_reason="tool_use", content=[SimpleNamespace(
        type="tool_use", id="call", name="record", input={"value": secret},
    )]), final_response()]
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: responses.pop(0)))
    assert run_agent("record it", registry_for(tmp_path), client=client, model="fixture",
                     retrieval_preflight=False, run_store=store) == "done"
    assert (tmp_path / "effects.txt").read_text().strip() == secret
    assert secret.encode() not in store.path.read_bytes()
