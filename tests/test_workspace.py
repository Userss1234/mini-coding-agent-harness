from __future__ import annotations

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

import main
from harness.agent import run_agent
from harness.execution import DockerExecutionConfig, DockerExecutor
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.workspace import WorkspaceSession


@pytest.fixture
def session(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_bytes(b"old\r\n")
    (source / "delete.txt").write_bytes(b"delete")
    return WorkspaceSession.create(source, tmp_path / "session")


def changed(session):
    (session.workspace / "a.txt").write_bytes(b"new\r\n")
    (session.workspace / "delete.txt").unlink()
    (session.workspace / "nested").mkdir(exist_ok=True)
    (session.workspace / "nested" / "new.txt").write_bytes(b"added")
    return session.review()


def test_copy_and_review_do_not_change_source_and_apply_is_exact(session):
    review = changed(session)
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"
    assert len(review["entries"]) == 3
    assert "No newline at end of file" in review["patch"]
    calls = []
    session.apply(review["id"], lambda digest: calls.append(digest) or True)
    assert calls == [review["id"]]
    assert (session.source / "a.txt").read_bytes() == b"new\r\n"
    assert not (session.source / "delete.txt").exists()
    assert (session.source / "nested" / "new.txt").read_bytes() == b"added"
    assert json.loads((session.path / "application.json").read_text())["status"] == "applied"
    with pytest.raises(ValueError, match="already applied"):
        session.apply(review["id"], lambda _: True)


@pytest.mark.parametrize("kind", ["modified", "deleted", "added", "parent"])
def test_all_host_conflicts_are_checked_before_any_mutation(session, kind):
    review = changed(session)
    if kind == "modified":
        (session.source / "a.txt").write_text("user work")
    elif kind == "deleted":
        (session.source / "delete.txt").unlink()
    elif kind == "added":
        (session.source / "nested").mkdir()
        (session.source / "nested" / "new.txt").write_text("user work")
    else:
        (session.source / "nested").write_text("parent is file")
    with pytest.raises((ValueError, OSError)):
        session.apply(review["id"], lambda _: pytest.fail("approval must not be asked"))
    assert not (session.path / "application.json").exists()
    assert (session.source / "a.txt").read_bytes() == (b"user work" if kind == "modified" else b"old\r\n")


@pytest.mark.parametrize("kind", ["workspace", "baseline", "patch", "payload", "digest"])
def test_stale_or_tampered_review_is_rejected(session, kind):
    review = changed(session)
    if kind == "workspace":
        (session.workspace / "a.txt").write_text("later")
    elif kind == "baseline":
        (session.baseline / "a.txt").write_text("tamper")
    elif kind == "patch":
        (session.path / "review.patch").write_text("misleading patch")
    elif kind == "payload":
        value = json.loads((session.path / "review.json").read_text())
        value["entries"][0]["path"] = "../escape"
        (session.path / "review.json").write_text(json.dumps(value))
    else:
        review["id"] = "wrong"
    with pytest.raises(ValueError):
        session.apply(review["id"], lambda _: pytest.fail("must reject before approval"))
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"


def test_decline_and_edits_during_approval_never_apply(session):
    review = changed(session)
    with pytest.raises(ValueError, match="declined"):
        session.apply(review["id"], lambda _: False)

    def approve(_):
        (session.source / "a.txt").write_text("user edited while reading")
        return True

    with pytest.raises(ValueError, match="Host conflict"):
        session.apply(review["id"], approve)
    assert (session.source / "a.txt").read_text() == "user edited while reading"


def test_exception_rolls_back_completed_files(session, monkeypatch):
    review = changed(session)
    original = session._write_entry

    def failing(entry, *, restore=False):
        if entry["path"] == "delete.txt" and not restore:
            raise OSError("simulated disk failure")
        original(entry, restore=restore)

    monkeypatch.setattr(session, "_write_entry", failing)
    with pytest.raises(OSError, match="disk failure"):
        session.apply(review["id"], lambda _: True)
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"
    assert (session.source / "delete.txt").exists()
    assert json.loads((session.path / "application.json").read_text())["status"] == "rolled_back"


def test_real_child_exit_during_apply_is_fail_closed_and_recoverable(session):
    review = changed(session)
    code = '''
import os,sys
from pathlib import Path
from harness.workspace import WorkspaceSession
s=WorkspaceSession(Path(sys.argv[1]))
original=s._write_entry
def interrupted(entry, **kwargs):
    original(entry, **kwargs)
    os._exit(77)
s._write_entry=interrupted
s.apply(sys.argv[2], lambda _: True)
'''
    process = subprocess.run([sys.executable, "-c", code, str(session.path), review["id"]], timeout=20)
    assert process.returncode == 77
    assert (session.source / "a.txt").read_bytes() == b"new\r\n"
    with pytest.raises(ValueError, match="interrupted"):
        session.apply(review["id"], lambda _: True)
    with pytest.raises(ValueError, match="declined"):
        session.recover(lambda _: False)
    session.recover(lambda digest: digest == review["id"])
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"
    session.apply(review["id"], lambda _: True)


def test_recovery_does_not_overwrite_new_user_changes(session, monkeypatch):
    review = changed(session)
    original = session._write_entry

    def interrupt(entry, **kwargs):
        original(entry, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(session, "_write_entry", interrupt)
    with pytest.raises(KeyboardInterrupt):
        session.apply(review["id"], lambda _: True)
    (session.source / "a.txt").write_text("new user work")
    with pytest.raises(ValueError, match="Rollback conflict"):
        session.recover(lambda _: True)
    assert (session.source / "a.txt").read_text() == "new user work"


def test_source_lock_prevents_two_sessions_applying_concurrently(session):
    review = changed(session)
    other = WorkspaceSession.create(session.source, session.path.parent / "other")
    with other.source_operations.lock("apply"):
        with pytest.raises(RuntimeError, match="already active"):
            session.apply(review["id"], lambda _: True)


def test_copy_excludes_credentials_git_and_generated_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in (".git", ".aws", "node_modules", "artifacts"):
        (source / name).mkdir()
        (source / name / "secret").write_text("not copied")
    for name in (".env", ".env.local", "private.key", "runs.sqlite3", "trace.jsonl"):
        (source / name).write_text("not copied")
    (source / ".env.example").write_text("KEY=example")
    result = WorkspaceSession.create(source, tmp_path / "copy")
    assert list(path.name for path in result.workspace.iterdir()) == [".env.example"]
    for name in (".env", ".git"):
        target = result.workspace / name
        target.write_text("must not apply")
        with pytest.raises(ValueError, match="Protected"):
            result.review()
        target.unlink()


@pytest.mark.parametrize("kind", ["binary", "size", "nested", "link", "no_changes"])
def test_unsupported_operations_fail_closed(session, monkeypatch, kind):
    if kind == "binary":
        for content in (b"\x00binary", b"\xffinvalid", b"hidden\x1b[2Jpatch", b"hidden\x7fpatch"):
            (session.workspace / "a.txt").write_bytes(content)
            with pytest.raises(ValueError):
                session.review()
        return
    elif kind == "size":
        monkeypatch.setattr("harness.workspace.MAX_FILE_BYTES", 2)
    elif kind == "nested":
        with pytest.raises(ValueError, match="non-nested"):
            WorkspaceSession.create(session.source, session.source / "nested")
        return
    elif kind == "link":
        try:
            (session.workspace / "link.txt").symlink_to(session.source / "a.txt")
        except OSError:
            pytest.skip("Symlink privilege not available")
    else:
        review = session.review()
        with pytest.raises(ValueError, match="No changes"):
            session.apply(review["id"], lambda _: True)
        return
    with pytest.raises(ValueError):
        session.review()


def test_real_registry_edits_and_tests_only_copy_with_baseline_diff(session):
    (session.workspace / "test_sample.py").write_text("def test_sample(): assert True\n")
    registry = build_registry(session.workspace, TraceLogger(session.path / "trace.jsonl"), allow_write=True)
    registry.baseline_workspace = session.baseline
    assert registry.call("write_file", path="a.txt", content="new").ok
    assert registry.call("run_tests", timeout=30).ok
    assert "new" in registry.call("git_diff").output
    assert not registry.call("write_file", path="../escape", content="bad").ok
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"
    assert not {"workspace_apply", "workspace_recover"} & set(registry.names())


def test_docker_mount_targets_only_copy_and_keeps_restrictions(session):
    executor = DockerExecutor(session.workspace)
    argv = executor.docker_argv(["python", "-m", "pytest"])
    assert f"source={session.workspace}," in argv[argv.index("--mount") + 1]
    assert str(session.source) not in " ".join(argv)
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--user") + 1] == "10001:10001"
    assert "--read-only" in argv and "--pids-limit" in argv
    main._check_isolated_policy(SimpleNamespace(execution_backend="docker", execution_policy=executor.describe()))
    for config in (DockerExecutionConfig(network="host"), DockerExecutionConfig(user="0"),
                   DockerExecutionConfig(user="00"),
                   DockerExecutionConfig(read_only_root=False), DockerExecutionConfig(fallback_to_host=True)):
        with pytest.raises(SystemExit, match="require"):
            main._check_isolated_policy(SimpleNamespace(
                execution_backend="docker", execution_policy=DockerExecutor(session.workspace, config).describe()))


def test_cli_isolated_run_persists_and_resumes_in_copy(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "session"
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text="done")],
    )))

    def injected(prompt, registry, **kwargs):
        assert registry.workspace == path / "workspace"
        return run_agent(prompt, registry, client=client, model="fixture", **kwargs)

    monkeypatch.setattr(main, "run_agent", injected)
    monkeypatch.setenv("HARNESS_EXECUTION_BACKEND", "host")
    parser = main.build_parser()
    args = parser.parse_args(["--workspace", str(source), "ask", "inspect", "--isolate", str(path), "--retrieval", "off"])
    args.func(args)
    store = SQLiteRunStore(path / "runs.sqlite3")
    run_id = store.list_runs()[0]["id"]
    args = parser.parse_args(["resume", run_id, "--isolate", str(path)])
    args.func(args)
    assert "done" in capsys.readouterr().out
    assert list(source.iterdir()) == []


def test_cli_approval_rejects_pipe_and_requires_full_digest(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit, match="interactive"):
        main._approve_workspace("123")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert not main._approve_workspace("123")
    monkeypatch.setattr("builtins.input", lambda _: "APPLY 123")
    assert main._approve_workspace("123")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
@pytest.mark.parametrize("location", ["source", "workspace", "host_parent"])
def test_windows_junction_is_rejected_without_following_target(session, location):
    outside = session.path.parent / "outside"
    outside.mkdir()
    (outside / "sentinel").write_text("preserve")
    root = session.workspace if location == "workspace" else session.source
    junction = root / ("nested" if location == "host_parent" else "junction")
    if location == "host_parent":
        review = changed(session)
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    try:
        with pytest.raises(ValueError, match="link|Links"):
            if location == "workspace":
                session.review()
            elif location == "source":
                WorkspaceSession.create(session.source, session.path.parent / "linked-copy")
            else:
                session.apply(review["id"], lambda _: pytest.fail("must block before approval"))
        assert (outside / "sentinel").read_text() == "preserve"
    finally:
        # rmdir removes only the verified junction, never its target tree.
        assert junction.parent in (session.source, session.workspace)
        assert junction.resolve() == outside.resolve()
        junction.rmdir()


def test_workspace_changes_during_approval_are_rejected(session):
    review = changed(session)

    def approve(_):
        (session.workspace / "a.txt").write_text("later agent edit")
        return True

    with pytest.raises(ValueError, match="Workspace changed"):
        session.apply(review["id"], approve)
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"


def test_session_lock_blocks_review_while_agent_is_active(session):
    other = WorkspaceSession(session.path)
    with session.operations.lock("workspace"):
        with pytest.raises(RuntimeError, match="already active"):
            other.review()


def test_workspace_cli_create_review_apply_and_recover(session, monkeypatch, capsys):
    parser = main.build_parser()
    other = session.path.parent / "cli-copy"
    args = parser.parse_args(["--workspace", str(session.source), "workspace-create", str(other)])
    args.func(args)
    assert (other / "workspace" / "a.txt").read_bytes() == b"old\r\n"
    review = changed(session)
    args = parser.parse_args(["workspace-review", str(session.path)])
    args.func(args)
    assert review["id"] in capsys.readouterr().out
    monkeypatch.setattr(main, "_approve_workspace", lambda _: True)
    args = parser.parse_args(["workspace-apply", str(session.path), "--review", review["id"]])
    args.func(args)
    assert (session.source / "a.txt").read_bytes() == b"new\r\n"
    journal_path = session.path / "application.json"
    journal = json.loads(journal_path.read_text())
    journal["status"] = "applying"
    journal_path.write_text(json.dumps(journal))
    args = parser.parse_args(["workspace-recover", str(session.path)])
    args.func(args)
    assert (session.source / "a.txt").read_bytes() == b"old\r\n"


def test_isolated_cli_rejects_no_persist_before_creating_copy(session):
    path = session.path.parent / "no-persist"
    args = main.build_parser().parse_args([
        "--workspace", str(session.source), "ask", "task", "--isolate", str(path), "--no-persist",
    ])
    with pytest.raises(SystemExit, match="require persistence"):
        args.func(args)
    assert not path.exists()


def test_isolated_cli_defaults_to_docker_when_no_backend_is_configured(session, monkeypatch):
    monkeypatch.delenv("HARNESS_EXECUTION_BACKEND", raising=False)
    monkeypatch.setattr(main, "run_agent", lambda prompt, registry, **_: registry.execution_backend)
    args = main.build_parser().parse_args([
        "--workspace", str(session.source), "ask", "task", "--isolate", str(session.path.parent / "docker-default"),
    ])
    args.func(args)
    assert os.environ["HARNESS_EXECUTION_BACKEND"] == "docker"


@pytest.mark.parametrize("limit", ["MAX_FILES", "MAX_TOTAL_BYTES"])
def test_copy_limits_do_not_create_partial_session(session, monkeypatch, limit):
    monkeypatch.setattr("harness.workspace." + limit, 1)
    path = session.path.parent / "too-large"
    with pytest.raises(ValueError, match="limit exceeded"):
        WorkspaceSession.create(session.source, path)
    assert not path.exists()


def test_invalid_version_and_permission_only_changes_fail_closed(session):
    metadata_path = session.path / "session.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["version"] = 99
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="version"):
        WorkspaceSession(session.path)
    target = session.workspace / "a.txt"
    target.chmod(0o444)
    try:
        with pytest.raises(ValueError, match="permission"):
            session.review()
    finally:
        target.chmod(0o666)
