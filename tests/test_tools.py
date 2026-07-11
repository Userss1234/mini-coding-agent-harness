from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.tools import Tool, ToolRegistry, ToolResult, build_registry
from harness.trace import TraceLogger


def make_registry(workspace: Path, allow_write: bool = True):
    return build_registry(workspace, TraceLogger(workspace / "trace.jsonl"), allow_write=allow_write)


def test_edit_file_replaces_exactly_once_and_records_diff(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call(
        "edit_file",
        path="sample.txt",
        old_text="beta",
        new_text="BETA",
    )

    assert result.ok
    assert target.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"
    assert result.metadata["diff_summary"] == {
        "added_lines": 1,
        "removed_lines": 1,
        "hunks": 1,
    }
    assert result.metadata["edit"]["replacements"] == 1


def test_edit_file_rejects_ambiguous_matches(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("name = old\nother = old\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call(
        "edit_file",
        path="sample.txt",
        old_text="old",
        new_text="new",
    )

    assert not result.ok
    assert "appear exactly once" in result.output
    assert target.read_text(encoding="utf-8") == "name = old\nother = old\n"


def test_edit_file_requires_write_permission_for_existing_files(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("before\n", encoding="utf-8")
    registry = make_registry(tmp_path, allow_write=False)

    result = registry.call(
        "edit_file",
        path="sample.txt",
        old_text="before",
        new_text="after",
    )

    assert not result.ok
    assert "blocked_overwrite_requires_allow_write" in result.output
    assert target.read_text(encoding="utf-8") == "before\n"


def test_delete_file_requires_confirmation(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("delete me\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call("delete_file", path="sample.txt", confirm=False)

    assert not result.ok
    assert "blocked_delete_requires_confirmation" in result.output
    assert target.exists()


def test_delete_file_removes_confirmed_file_and_records_metadata(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("delete me\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call("read_file", path="sample.txt")

    result = registry.call("delete_file", path="sample.txt", confirm=True)

    assert result.ok
    assert not target.exists()
    assert result.metadata["before_chars"] == len("delete me\n")
    assert result.metadata["cache_invalidations"] == 1


def test_read_file_supports_line_ranges_and_cache_keys(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    first = registry.call("read_file", path="sample.txt", start_line=2, end_line=3)
    second = registry.call("read_file", path="sample.txt", start_line=2, end_line=3)
    full = registry.call("read_file", path="sample.txt")

    assert first.ok
    assert first.output == "beta\ngamma"
    assert first.metadata["lines"] == 4
    assert first.metadata["returned_lines"] == 2
    assert first.metadata["start_line"] == 2
    assert first.metadata["end_line"] == 3
    assert first.metadata["cache_hit"] is False
    assert second.metadata["cache_hit"] is True
    assert full.output.startswith("alpha")
    assert "delta" in full.output


def test_read_file_rejects_invalid_line_ranges(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call("read_file", path="sample.txt", start_line=3, end_line=2)

    assert not result.ok
    assert "end_line must be >= start_line" in result.output


def test_delete_file_refuses_directories(tmp_path: Path) -> None:
    target = tmp_path / "folder"
    target.mkdir()
    registry = make_registry(tmp_path)

    result = registry.call("delete_file", path="folder", confirm=True)

    assert not result.ok
    assert "Refusing to delete directory" in result.output
    assert target.exists()


def test_git_diff_returns_clear_error_outside_git_repo(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.call("git_diff")

    assert not result.ok
    assert "Not a Git repository" in result.output
    assert result.metadata["returncode"] != 0


def test_git_diff_returns_changes_inside_git_repo(tmp_path: Path) -> None:
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        pytest.skip("git is not available")

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    tracked.write_text("after\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call("git_diff")

    assert result.ok
    assert "-before" in result.output
    assert "+after" in result.output
    assert result.metadata["command"] == "git diff -- ."


def test_run_tests_executes_pytest_in_workspace(tmp_path: Path) -> None:
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_sample.py").write_text(
        "def test_sample():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    registry = make_registry(tmp_path)

    result = registry.call("run_tests", timeout=30)

    assert result.ok
    assert "1 passed" in result.output
    assert result.metadata["returncode"] == 0
    assert result.metadata["pytest_available"] is True
    assert result.metadata["timed_out"] is False
    assert result.metadata["target"] == "tests"


def test_run_tests_adds_workspace_to_pythonpath_for_test_imports(tmp_path: Path) -> None:
    (tmp_path / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    registry = make_registry(tmp_path)

    result = registry.call("run_tests", timeout=30)

    assert result.ok
    assert "1 passed" in result.output


def test_run_tests_clears_pycache_before_pytest(tmp_path: Path) -> None:
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "sample.cpython-310.pyc").write_bytes(b"stale")
    (tmp_path / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )
    registry = make_registry(tmp_path)

    result = registry.call("run_tests", timeout=30)

    assert result.ok
    assert result.metadata["cleared_pycache_dirs"] == 1
    assert not pycache.exists()


def test_run_tests_auto_target_allows_root_level_pytest_files(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "test_sample.py").write_text(
        "def test_sample():\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )
    registry = make_registry(tmp_path)

    result = registry.call("run_tests", timeout=30)

    assert result.ok
    assert "1 passed" in result.output
    assert result.metadata["returncode"] == 0
    assert result.metadata["target"] == ""
    assert result.metadata["command"].endswith("-m pytest --rootdir=.")


def test_non_write_tool_retries_transient_handler_failure(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = ToolRegistry(tmp_path, trace, max_tool_retries=2, retry_delay=0)
    attempts = {"count": 0}

    def flaky_read_tool() -> ToolResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("temporary read timeout")
        return ToolResult(True, "ok")

    registry.register(Tool("flaky_read", "Flaky read", {"type": "object", "properties": {}}, flaky_read_tool))

    result = registry.call("flaky_read")

    assert result.ok
    assert result.output == "ok"
    assert attempts["count"] == 2
    assert "tool_retry" in trace.path.read_text(encoding="utf-8")


def test_write_tool_does_not_retry_transient_handler_failure(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = ToolRegistry(tmp_path, trace, max_tool_retries=2, retry_delay=0, allow_write=True)
    attempts = {"count": 0}

    def flaky_write_tool() -> ToolResult:
        attempts["count"] += 1
        raise TimeoutError("temporary write timeout")

    registry.register(Tool("flaky_write", "Flaky write", {"type": "object", "properties": {}}, flaky_write_tool, risk="write"))

    result = registry.call("flaky_write")

    assert not result.ok
    assert "TimeoutError" in result.output
    assert attempts["count"] == 1
    assert "tool_retry" not in trace.path.read_text(encoding="utf-8")


def test_shell_allows_basic_allowlisted_command(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.call("shell", command='python -c "print(123)"', timeout=10)

    assert result.ok
    assert "123" in result.output
    assert result.metadata["shell"] is False
    assert result.metadata["argv"] == ["python", "-c", "print(123)"]


def test_shell_blocks_operators_and_unknown_commands(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    redirect = registry.call("shell", command="echo hello > out.txt")
    unknown = registry.call("shell", command="curl https://example.com")

    assert not redirect.ok
    assert "blocked_shell_operator" in redirect.output
    assert not unknown.ok
    assert "blocked_shell_not_allowlisted" in unknown.output
    assert not (tmp_path / "out.txt").exists()


def test_shell_handles_allowlisted_directory_listing_internally(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("hello\n", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    registry = make_registry(tmp_path)

    result = registry.call("shell", command="ls -la")

    assert result.ok
    assert "nested/" in result.output
    assert "sample.txt" in result.output
    assert result.metadata["builtin"] == "list_directory"
    assert result.metadata["shell"] is False


def test_shell_directory_listing_blocks_path_escape(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.call("shell", command="ls ..")

    assert not result.ok
    assert "Path escapes workspace" in result.output


def test_shell_blocks_mutating_git_commands(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    push = registry.call("shell", command="git push origin main")
    reset = registry.call("shell", command="git reset --hard HEAD")
    status = registry.call("shell", command="git status")

    assert not push.ok
    assert "blocked_git_not_allowlisted" in push.output
    assert not reset.ok
    assert "blocked_force_flag" in reset.output or "blocked_git_not_allowlisted" in reset.output
    assert status.ok or "not a git repository" in status.output.lower()


def test_permission_policy_reports_shell_git_and_sandbox_boundaries(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.call("permission_policy")

    assert result.ok
    assert "Permission Policy" in result.output
    assert "shell=False" in result.output
    assert "not an OS-level sandbox" in result.output
    assert result.metadata["shell_false"] is True
    assert result.metadata["os_sandbox"] is False
    assert "python" in result.metadata["allowed_shell_commands"]
    assert "status" in result.metadata["read_only_git_subcommands"]
    assert result.metadata["path_scope"] == "workspace_only"


def test_compact_context_summarizes_trace_state(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("before\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call(
        "todo_write",
        todos=[
            {"task": "Read sample file", "status": "completed"},
            {"task": "Run failing git diff", "status": "pending"},
        ],
    )
    registry.call("read_file", path="sample.txt")
    registry.call("edit_file", path="sample.txt", old_text="before", new_text="after")
    registry.call("git_diff")

    result = registry.call("compact_context")

    assert result.ok
    assert "Current goal: Run failing git diff" in result.output
    assert "Next step: Run failing git diff" in result.output
    assert "`sample.txt`" in result.output
    assert "git_diff: Not a Git repository" in result.output
    assert result.metadata["files_read"] == ["sample.txt"]
    assert result.metadata["files_changed"] == ["sample.txt"]
    assert result.metadata["failure_count"] == 1
    assert result.metadata["tool_counts"]["todo_write"] == 1


def test_context_pack_retrieves_ranked_file_snippets(tmp_path: Path) -> None:
    (tmp_path / "billing_service.py").write_text(
        "class BillingService:\n"
        "    def invoice_total(self, items):\n"
        "        subtotal = sum(item.price for item in items)\n"
        "        return round(subtotal, 2)\n",
        encoding="utf-8",
    )
    (tmp_path / "weather.py").write_text(
        "def forecast(city):\n"
        "    return f'sunny in {city}'\n",
        encoding="utf-8",
    )
    registry = make_registry(tmp_path)

    result = registry.call("context_pack", query="invoice total rounding", glob="*.py", limit=2, window=2)

    assert result.ok
    assert result.metadata["count"] >= 1
    assert result.metadata["matches"][0]["path"] == "billing_service.py"
    assert result.metadata["matches"][0]["start_line"] <= 2
    assert "invoice_total" in result.output
    assert "round(subtotal, 2)" in result.output
    assert "Retrieval: lexical path and line scoring" in result.output


def test_context_pack_skips_generated_and_hidden_paths(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("def public_api():\n    return 'stable context'\n", encoding="utf-8")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "generated.py").write_text("secret generated context\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET_CONTEXT=hidden\n", encoding="utf-8")
    registry = make_registry(tmp_path)

    result = registry.call("context_pack", query="context", glob="*.py,*", limit=10)

    assert result.ok
    paths = [item["path"] for item in result.metadata["matches"]]
    assert "service.py" in paths
    assert all(not path.startswith("artifacts/") for path in paths)
    assert ".env" not in paths
    assert "SECRET_CONTEXT" not in result.output


def test_context_pack_requires_searchable_query(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    result = registry.call("context_pack", query=" ")

    assert not result.ok
    assert "query must be non-empty" in result.output


def test_context_pack_can_be_disabled_for_retrieval_ablation(tmp_path: Path) -> None:
    registry = build_registry(
        tmp_path,
        TraceLogger(tmp_path / "trace.jsonl"),
        enable_context_pack=False,
    )

    assert "context_pack" not in registry.names()


def test_memory_tools_save_list_and_read_workflow(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    saved = registry.call(
        "save_memory",
        memory_name="Pytest Repair Workflow",
        summary="Use pytest output to identify a failing behavior, edit the smallest file, and rerun tests.",
        trigger="A repository has a failing pytest run.",
        steps=[
            "Run run_tests and read the first failing assertion.",
            "Use grep/read_file to inspect the code under test.",
            "Apply edit_file with an exact replacement.",
            "Run run_tests again.",
        ],
    )
    registry.call(
        "save_memory",
        memory_name="README Update Workflow",
        summary="Use read_file and edit_file to update documentation.",
        trigger="A repository needs documentation changes.",
    )
    listed = registry.call("list_memories")
    ranked = registry.call("list_memories", query="pytest failing assertion", limit=1)
    read = registry.call("read_memory", memory_name="pytest-repair-workflow")
    read_by_path = registry.call("read_memory", memory_name="skills\\pytest-repair-workflow.md")

    assert saved.ok
    assert saved.metadata["memory"]["slug"] == "pytest-repair-workflow"
    assert (tmp_path / "skills" / "pytest-repair-workflow.md").exists()
    assert listed.ok
    assert "`skills\\pytest-repair-workflow.md`" in listed.output or "`skills/pytest-repair-workflow.md`" in listed.output
    assert ranked.ok
    assert ranked.metadata["count"] == 1
    assert ranked.metadata["memories"][0]["path"].endswith("pytest-repair-workflow.md")
    assert "score" in ranked.output
    assert read.ok
    assert "# Pytest Repair Workflow" in read.output
    assert "Run run_tests again." in read.output
    assert read_by_path.ok
    assert "# Pytest Repair Workflow" in read_by_path.output


def test_save_memory_requires_allow_write_to_overwrite(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    first = registry.call(
        "save_memory",
        memory_name="Repeatable Workflow",
        summary="First version.",
    )
    blocked_registry = make_registry(tmp_path, allow_write=False)

    blocked = blocked_registry.call(
        "save_memory",
        memory_name="Repeatable Workflow",
        summary="Second version.",
    )

    assert first.ok
    assert not blocked.ok
    assert "blocked_overwrite_requires_allow_write" in blocked.output
    assert "First version." in (tmp_path / "skills" / "repeatable-workflow.md").read_text(encoding="utf-8")


def test_recover_errors_suggests_actions_for_failed_tools(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("old old\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call("git_diff")
    registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")

    result = registry.call("recover_errors")

    assert result.ok
    categories = {item["category"] for item in result.metadata["recoveries"]}
    assert "git_repo_missing" in categories
    assert "edit_match_failed" in categories
    assert "Run inside a Git worktree" in result.output
    assert "appears exactly once" in result.output


def test_recover_errors_reports_permission_blocks(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("before\n", encoding="utf-8")
    registry = make_registry(tmp_path, allow_write=False)
    registry.call("edit_file", path="sample.txt", old_text="before", new_text="after")

    result = registry.call("recover_errors")

    assert result.ok
    assert result.metadata["failure_count"] == 1
    assert result.metadata["recoveries"][0]["category"] == "permission_block"
    assert "explicit write permission" in result.output


def test_recover_errors_reports_delete_confirmation_blocks(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("before\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call("delete_file", path="sample.txt", confirm=False)

    result = registry.call("recover_errors")

    assert result.ok
    assert result.metadata["recoveries"][0]["category"] == "permission_block"
    assert "confirmation" in result.output.lower()


def test_retry_plan_turns_edit_failures_into_next_steps(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("old old\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")

    result = registry.call("retry_plan")

    assert result.ok
    assert result.metadata["failure_count"] == 1
    assert result.metadata["steps"][0]["category"] == "edit_match_failed"
    assert result.metadata["steps"][0]["suggested_tool"] == "read_file -> edit_file"
    assert "exact old_text snippet" in result.output


def test_retry_plan_keeps_permission_recovery_actions(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("before\n", encoding="utf-8")
    registry = make_registry(tmp_path)
    registry.call("delete_file", path="sample.txt", confirm=False)

    result = registry.call("retry_plan")

    assert result.ok
    assert result.metadata["steps"][0]["category"] == "permission_block"
    assert result.metadata["steps"][0]["suggested_tool"] == "delete_file"
    assert "confirm=true" in result.output
