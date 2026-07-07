from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Callable

from .tools import build_registry
from .trace import TraceLogger
from .trace_viewer import build_trace_report


@dataclass
class DemoResult:
    task_id: str
    workspace: Path
    trace_path: Path
    html_path: Path
    report_path: Path
    success: bool
    report: str


DEMO_TASKS = {"python_bugfix"}


def run_demo(task_id: str, output_dir: Path, fresh: bool = True) -> DemoResult:
    if task_id not in DEMO_TASKS:
        raise ValueError(f"Unknown demo task: {task_id}. Available tasks: {', '.join(sorted(DEMO_TASKS))}")

    demo_dir = output_dir.resolve() / task_id
    workspace = demo_dir / "workspace"
    trace_path = demo_dir / "trace.jsonl"
    html_path = demo_dir / "TRACE.html"
    report_path = demo_dir / "DEMO.md"

    if fresh:
        _reset_demo_dir(demo_dir, output_dir.resolve())
    demo_dir.mkdir(parents=True, exist_ok=True)
    _setup_python_bugfix_workspace(workspace)

    trace = TraceLogger(trace_path)
    trace.log("session_start", workspace=str(workspace), demo_task=task_id, allow_write=True)
    registry = build_registry(workspace, trace, allow_write=True)

    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "in_progress"},
            {"task": "Read calculator implementation", "status": "pending"},
            {"task": "Edit calculator bug", "status": "pending"},
            {"task": "Rerun tests", "status": "pending"},
            {"task": "Show git diff", "status": "pending"},
        ],
    )
    before = registry.call("run_tests")
    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "completed"},
            {"task": "Read calculator implementation", "status": "in_progress"},
            {"task": "Edit calculator bug", "status": "pending"},
            {"task": "Rerun tests", "status": "pending"},
            {"task": "Show git diff", "status": "pending"},
        ],
    )
    read = registry.call("read_file", path="calculator.py")
    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "completed"},
            {"task": "Read calculator implementation", "status": "completed"},
            {"task": "Edit calculator bug", "status": "in_progress"},
            {"task": "Rerun tests", "status": "pending"},
            {"task": "Show git diff", "status": "pending"},
        ],
    )
    edit = registry.call("edit_file", path="calculator.py", old_text="return a - b", new_text="return a + b")
    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "completed"},
            {"task": "Read calculator implementation", "status": "completed"},
            {"task": "Edit calculator bug", "status": "completed"},
            {"task": "Rerun tests", "status": "in_progress"},
            {"task": "Show git diff", "status": "pending"},
        ],
    )
    after = registry.call("run_tests")
    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "completed"},
            {"task": "Read calculator implementation", "status": "completed"},
            {"task": "Edit calculator bug", "status": "completed"},
            {"task": "Rerun tests", "status": "completed"},
            {"task": "Show git diff", "status": "in_progress"},
        ],
    )
    diff = registry.call("git_diff")
    registry.call(
        "todo_write",
        todos=[
            {"task": "Run failing tests", "status": "completed"},
            {"task": "Read calculator implementation", "status": "completed"},
            {"task": "Edit calculator bug", "status": "completed"},
            {"task": "Rerun tests", "status": "completed"},
            {"task": "Show git diff", "status": "completed"},
        ],
    )

    html = build_trace_report(trace_path, html_path)
    success = (not before.ok) and read.ok and edit.ok and after.ok
    report = _format_demo_report(
        task_id=task_id,
        workspace=workspace,
        trace_path=trace_path,
        html_path=html_path,
        before_output=before.output,
        after_output=after.output,
        diff_output=diff.output,
        html_chars=len(html),
        success=success,
    )
    report_path.write_text(report, encoding="utf-8")
    return DemoResult(task_id, workspace, trace_path, html_path, report_path, success, report)


def _reset_demo_dir(demo_dir: Path, output_dir: Path) -> None:
    if not demo_dir.exists():
        return
    resolved_demo = demo_dir.resolve()
    if not resolved_demo.is_relative_to(output_dir):
        raise ValueError(f"Refusing to reset demo directory outside output dir: {resolved_demo}")
    shutil.rmtree(resolved_demo, onerror=_remove_readonly)


def _remove_readonly(func: Callable[[str], None], path: str, _exc_info: object) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _setup_python_bugfix_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "calculator.py").write_text(
        "def add(a, b):\n"
        "    return a - b\n",
        encoding="utf-8",
    )
    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    _init_git_baseline(workspace)


def _init_git_baseline(workspace: Path) -> None:
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        return
    subprocess.run(["git", "init"], cwd=workspace, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Demo User",
            "-c",
            "user.email=demo@example.com",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
    )


def _format_demo_report(
    *,
    task_id: str,
    workspace: Path,
    trace_path: Path,
    html_path: Path,
    before_output: str,
    after_output: str,
    diff_output: str,
    html_chars: int,
    success: bool,
) -> str:
    return f"""# Demo Report

- Task: `{task_id}`
- Success: **{success}**
- Workspace: `{workspace}`
- Trace: `{trace_path}`
- HTML trace: `{html_path}` ({html_chars} chars)

## Tool Flow

1. `todo_write` creates a repair plan.
2. `run_tests` reproduces the failing calculator test.
3. `read_file` inspects `calculator.py`.
4. `edit_file` changes `return a - b` to `return a + b`.
5. `run_tests` verifies the fix.
6. `git_diff` shows the final code change.
7. `trace-report` renders the JSONL trace as static HTML.

## Before

```text
{_first_lines(before_output)}
```

## After

```text
{_first_lines(after_output)}
```

## Diff

```diff
{_first_lines(diff_output, limit=40)}
```
"""


def _first_lines(text: str, limit: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text.strip()
    return "\n".join(lines[:limit]).strip() + f"\n... ({len(lines) - limit} more lines)"
