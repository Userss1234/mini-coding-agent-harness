from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import main
from harness.agent import run_agent
from harness.run_store import SQLiteRunStore


def invoke(*argv: str):
    args = main.build_parser().parse_args(list(argv))
    args.func(args)


@pytest.mark.parametrize("persist", [True, False])
def test_ask_cli_persists_by_default_and_supports_opt_out(tmp_path: Path, monkeypatch, capsys, persist):
    db = tmp_path / "runs.sqlite3"
    trace = tmp_path / "trace.jsonl"
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text="done")],
    )))

    def injected(prompt, registry, **kwargs):
        return run_agent(prompt, registry, client=client, model="fixture", **kwargs)

    monkeypatch.setattr(main, "run_agent", injected)
    invoke("--workspace", str(tmp_path), "--trace", str(trace), "ask", "inspect",
           "--retrieval", "off", "--run-db", str(db), *([] if persist else ["--no-persist"]))
    assert "done" in capsys.readouterr().out
    assert db.exists() is persist
    if not persist:
        return
    run_id = SQLiteRunStore(db).list_runs()[0]["id"]
    # Remove the injected provider: completed CLI resume must need no credentials.
    monkeypatch.setattr(main, "run_agent", run_agent)
    invoke("--workspace", str(tmp_path), "resume", run_id, "--run-db", str(db))
    assert capsys.readouterr().out.strip() == "done"
    invoke("runs", "--run-db", str(db))
    assert json.loads(capsys.readouterr().out)[0]["id"] == run_id
    invoke("runs", "--run-db", str(db), "--run-id", run_id)
    assert json.loads(capsys.readouterr().out)["state"]["status"] == "completed"
    output = tmp_path / "export.jsonl"
    invoke("runs", "--run-db", str(db), "--run-id", run_id, "--export", str(output))
    assert output.exists()
    with pytest.raises(SystemExit, match="cannot delete"):
        invoke("--fresh-trace", "resume", run_id, "--run-db", str(db))
    with pytest.raises(SystemExit, match="requires --run-id"):
        invoke("runs", "--run-db", str(db), "--export", str(output))


def test_cli_operator_resolution_only_records_verified_result(tmp_path: Path):
    db = tmp_path / "runs.sqlite3"
    store = SQLiteRunStore(db)
    state = {"status": "running"}
    store.create("sample", state)
    store.plan("sample", state, [{"id": "call", "name": "write_file", "input": {}}])
    store.start_call("sample", "call")
    invoke("run-resolve", "sample", "call", "--run-db", str(db),
           "--result", "Inspected: change already applied", "--succeeded")
    assert store.calls("sample")[0]["result"]["is_error"] is False
    assert store.load("sample")["reconciliation"]["source"] == "operator"


def test_cli_context_options_override_or_inherit_checkpoint_config():
    saved = {"max_input_tokens": 12000, "summary_tokens": 1500,
             "keep_recent_turns": 1, "enabled": False}
    parser = main.build_parser()
    inherited = parser.parse_args(["resume", "sample"])
    assert main._context_config(inherited, saved).enabled is False
    changed = parser.parse_args(["resume", "sample", "--context-budget", "20000", "--context-management"])
    config = main._context_config(changed, saved)
    assert config.enabled and config.max_input_tokens == 20000
    assert config.summary_tokens == 1500 and config.keep_recent_turns == 1
    disabled = parser.parse_args(["ask", "task", "--no-context-management"])
    assert main._context_config(disabled).enabled is False
