from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from harness.agent import run_agent
from harness.context_window import (
    ContextBudgetExceeded,
    ContextConfig,
    ContextWindow,
    complete_groups,
    estimate_input_tokens,
)
from harness.run_store import SQLiteRunStore, redact
from tests.fixtures.context_workload import CONFIG, registry_for, run_workload


def pair(index: int, size: int = 600):
    return [
        {"role": "assistant", "content": [{"type": "tool_use", "id": str(index),
          "name": "read_file", "input": {"path": f"file{index}.py"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": str(index),
          "content": "x" * size, "is_error": False}]},
    ]


def test_compaction_replaces_history_preserves_task_and_recent_complete_batch():
    task = {"role": "user", "content": "Keep all original requirements. ORIGINAL_TASK"}
    messages = [task] + [message for i in range(8) for message in pair(i)]
    window = ContextWindow(ContextConfig(2600, 1000, 1))
    result, metrics = window.prepare("system", [], messages, [{"task": "verify", "status": "pending"}])
    assert result[0] == task and result[-2:] == pair(7)
    assert len(result) == 4 and len(messages) == 17
    assert metrics["compacted"] and metrics["after_estimated_tokens"] <= 2600
    assert window.state["summary"]["tool_counts"]["read_file"] == 7
    assert window.state["summary"]["todos"][0]["task"] == "verify"
    assert len(complete_groups(result[2:])) == 1
    json.dumps(window.state)


def test_repeated_compaction_merges_summary_without_counting_history_twice():
    window = ContextWindow(ContextConfig(2600, 1000, 1))
    messages = [{"role": "user", "content": "task"}]
    for index in range(10):
        messages.extend(pair(index))
        messages, _metrics = window.prepare("system", [], messages, [])
    summary_count = window.state["summary"]["tool_counts"]["read_file"]
    assert summary_count + len(complete_groups(messages[2:])) == 10
    assert window.state["revision"] > 1


@pytest.mark.parametrize("malformed", [
    [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x"}]}],
    pair(1)[:1],
    [pair(1)[0], {"role": "assistant", "content": "missing result"}],
    [pair(1)[0], pair(2)[1]],
])
def test_incomplete_or_orphan_tool_history_is_rejected(malformed):
    with pytest.raises(ValueError):
        complete_groups(malformed)


def test_oversized_pinned_task_and_recent_result_stop_without_slicing():
    messages = [{"role": "user", "content": "important " * 1000}] + pair(1)
    window = ContextWindow(ContextConfig(1800, 400, 1))
    before = json.dumps(messages)
    with pytest.raises(ContextBudgetExceeded):
        window.prepare("system", [], messages, [])
    assert json.dumps(messages) == before
    assert window.state["revision"] == 0


def test_summary_cannot_discard_active_todos_to_meet_budget():
    messages = [{"role": "user", "content": "task"}] + sum([pair(i) for i in range(8)], [])
    window = ContextWindow(ContextConfig(2200, 400, 1))
    with pytest.raises(ContextBudgetExceeded, match="todos"):
        window.prepare("system", [], messages, [{"task": "must keep " * 1000, "status": "pending"}])


def test_large_recent_batch_is_not_dropped_even_when_older_history_can_be_summarized():
    messages = [{"role": "user", "content": "task"}] + pair(1, 100) + pair(2, 5000)
    window = ContextWindow(ContextConfig(1800, 400, 1))
    with pytest.raises(ContextBudgetExceeded, match="protected recent turns"):
        window.prepare("system", [], messages, [])
    assert len(messages[-1]["content"][0]["content"]) == 5000


def test_budget_counts_system_tool_schema_and_utf8_bytes():
    messages = [{"role": "user", "content": "task"}]
    assert estimate_input_tokens("system", [{"description": "large" * 100}], messages) > 500
    assert estimate_input_tokens("", [], [{"role": "user", "content": "\u4e2d"}]) > estimate_input_tokens(
        "", [], [{"role": "user", "content": "a"}],
    )
    window = ContextWindow(ContextConfig(1200, 300, 1))
    with pytest.raises(ContextBudgetExceeded):
        window.prepare("system" * 400, [], messages, [])


def test_numeric_token_metrics_survive_redaction_but_credentials_do_not():
    assert redact({"max_input_tokens": 12000, "summary_tokens": 1800,
                   "after_estimated_tokens": 9000, "token": "private-value"}) == {
        "max_input_tokens": 12000, "summary_tokens": 1800,
        "after_estimated_tokens": 9000, "token": "[REDACTED]",
    }
    assert redact({"max_input_tokens": "private-value"})["max_input_tokens"] == "[REDACTED]"


def test_long_task_continues_with_bounded_context_and_persisted_summary(tmp_path: Path):
    managed = run_workload(tmp_path / "managed")
    baseline = run_workload(tmp_path / "baseline", ContextConfig(enabled=False))
    assert managed["completed"] and baseline["completed"]
    assert managed["compactions"] > 1
    assert managed["peak_estimated_input_tokens"] <= CONFIG.max_input_tokens
    assert managed["total_estimated_input_tokens"] < baseline["total_estimated_input_tokens"]
    assert managed["state"]["context_state"]["summary"]["files_changed"] == ["progress.txt"]


def test_real_process_restart_uses_compacted_checkpoint(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root))
    process = subprocess.Popen([
        sys.executable, "-c", "from tests.fixtures.context_workload import main; main()",
        "--interrupt-workspace", str(tmp_path),
    ], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while not (tmp_path / "ready").exists() and process.poll() is None:
            if time.monotonic() > deadline:
                raise AssertionError("Child did not reach its compacted checkpoint")
            time.sleep(0.02)
        assert (tmp_path / "ready").exists(), process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    run_id = store.list_runs()[0]["id"]
    state = store.load(run_id)
    assert state["context_state"]["revision"] >= 1
    assert "Historical execution summary" in state["messages"][1]["content"]
    assert run_workload(tmp_path, None, resume_id=run_id)["completed"]


def test_budget_stop_is_checkpointed_before_any_model_request(tmp_path: Path):
    from types import SimpleNamespace

    def forbidden(**_kwargs):
        raise AssertionError("Oversized context must not reach the model")

    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    answer = run_agent(
        "task", registry_for(tmp_path), client=SimpleNamespace(messages=SimpleNamespace(create=forbidden)),
        retrieval_preflight=False, run_store=store, context_config=ContextConfig(1200, 300, 1),
    )
    assert "context budget exceeded" in answer
    state = store.load(store.list_runs()[0]["id"])
    assert state["status"] == "paused" and state["stop_reason"] == "context_budget"


@pytest.mark.parametrize("config", [
    {"max_input_tokens": 100}, {"summary_tokens": 100},
    {"max_input_tokens": 1000, "summary_tokens": 1000}, {"keep_recent_turns": 0},
])
def test_invalid_context_budgets_fail_early(config):
    with pytest.raises(ValueError):
        ContextConfig(**config)


def test_multi_tool_batch_is_retained_as_one_atomic_group():
    group = pair(1)
    group[0]["content"].extend(pair(2)[0]["content"])
    group[1]["content"].extend(pair(2)[1]["content"])
    messages = [{"role": "user", "content": "task"}] + pair(0, 4000) + group
    result, _ = ContextWindow(ContextConfig(3000, 1000, 1)).prepare("system", [], messages, [])
    assert result[-2:] == group
    assert len(complete_groups(result[2:])) == 1


def test_failed_file_operations_are_not_summarized_as_completed_changes_or_reads():
    groups = [pair(i, 1200) for i in range(6)]
    groups[0][0]["content"][0]["name"] = "write_file"
    for group in groups[:2]:
        group[1]["content"][0]["is_error"] = True
    messages = [{"role": "user", "content": "task"}] + sum(groups, [])
    window = ContextWindow(ContextConfig(7000, 4000, 1))
    window.prepare("system", [], messages, [])
    summary = window.state["summary"]
    assert summary["files_changed"] == []
    assert "file1.py" not in summary["files_read"]
    assert len(summary["failures"]) == 2


def test_inconsistent_saved_summary_is_rejected():
    messages = [{"role": "user", "content": "task"}] + sum([pair(i) for i in range(8)], [])
    window = ContextWindow(ContextConfig(2600, 1000, 1))
    result, _ = window.prepare("system", [], messages, [])
    result[1] = {"role": "user", "content": "changed summary"}
    with pytest.raises(ValueError, match="summary"):
        window.prepare("system", [], result, [])


def test_explicit_budget_increase_can_resume_a_paused_run(tmp_path: Path):
    from types import SimpleNamespace

    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text="finished")],
    )))
    assert "context budget exceeded" in run_agent(
        "task", registry_for(tmp_path), client=client, model="fixture", run_store=store,
        retrieval_preflight=False, context_config=ContextConfig(1200, 300, 1),
    )
    run_id = store.list_runs()[0]["id"]
    assert run_agent("", registry_for(tmp_path), client=client, run_store=store,
                     resume_run_id=run_id, context_config=ContextConfig()) == "finished"
    assert store.load(run_id)["context_config"]["max_input_tokens"] == 24000


def test_rich_plan_is_lossless_outside_history_allowance_but_inside_total_budget():
    todos = [{"task": f"Verify clause {i}", "status": "pending",
              "requirement": f"clause-{i}:" + "r" * 250,
              "check": "c" * 200, "evidence": "not run yet"} for i in range(5)]
    messages = [{"role": "user", "content": "Original full task"}] + sum(
        [pair(i, 1600) for i in range(8)], [])
    window = ContextWindow(ContextConfig(10000, 1000, 1))
    result, metrics = window.prepare("system", [], messages, todos)
    assert window.state["summary"]["schema_version"] == 2
    assert window.state["summary"]["todos"] == todos
    assert window._summary_size(window.state["summary"]) <= 1000
    assert metrics["current_plan_estimated_tokens"] > 1000
    assert metrics["after_estimated_tokens"] == estimate_input_tokens("system", [], result)
    assert metrics["after_estimated_tokens"] <= 10000
    assert result[0] == messages[0] and result[-2:] == pair(7, 1600)
    for item in todos:
        assert item["requirement"] in result[1]["content"]


def test_current_plan_refreshes_after_compaction_without_stale_requirements():
    window = ContextWindow(ContextConfig(5000, 1000, 1))
    task = {"role": "user", "content": "task"}
    result, _ = window.prepare("system", [], [task] + sum([pair(i) for i in range(8)], []),
                               [{"task": "Verify", "requirement": "old", "status": "pending"}])
    state = json.loads(json.dumps(window.state))
    restored = ContextWindow(window.config, state)
    todos = [{"task": "Verify", "requirement": "current-exact-clause", "status": "completed",
              "check": "run boundary assertions", "evidence": "passed"}]
    refreshed, metrics = restored.prepare("system", [], result, todos)
    assert "current-exact-clause" in refreshed[1]["content"]
    assert restored.state["summary"]["todos"] == todos
    assert not metrics["compacted"]
    assert refreshed[-2:] == result[-2:]
    before = json.dumps(restored.state)
    with pytest.raises(ContextBudgetExceeded):
        restored.prepare("system", [], refreshed, [{"task": "x" * 10000, "status": "pending"}])
    assert json.dumps(restored.state) == before


def test_legacy_summary_can_load_then_upgrade_without_losing_plan():
    window = ContextWindow(ContextConfig(5000, 1000, 1))
    task = {"role": "user", "content": "task"}
    todos = [{"task": "Verify", "requirement": "keep this clause", "status": "pending"}]
    result, _ = window.prepare("system", [], [task] + sum([pair(i) for i in range(8)], []), todos)
    state = json.loads(json.dumps(window.state))
    state["summary"]["schema_version"] = 1
    result[1] = window._summary_message(state["summary"])
    restored = ContextWindow(window.config, state)
    loaded, _ = restored.prepare("system", [], result, todos)
    assert loaded == result
    upgraded, metrics = restored.prepare("system", [], loaded + pair(9, 6000) + pair(10), todos)
    assert metrics["compacted"]
    assert restored.state["summary"]["schema_version"] == 2
    assert restored.state["summary"]["todos"] == todos
    assert upgraded[-2:] == pair(10)
