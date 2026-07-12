from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any, Callable

from .tools import ToolRegistry, build_registry
from .trace import TraceLogger


@dataclass
class EvalTask:
    task_id: str
    category: str
    description: str
    runner: Callable[[ToolRegistry], bool]
    fixture_setup: Callable[[Path], None] | None = None
    verifier: Callable[[ToolRegistry], bool] | None = None


@dataclass
class EvalResult:
    task_id: str
    category: str
    description: str
    mode: str
    memory_enabled: bool
    context_enabled: bool
    retrieval_enabled: bool
    success: bool
    duration_seconds: float
    tool_calls: int
    failed_tool_calls: int
    tool_counts: dict[str, int]
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    failure_categories: list[str]
    trace_path: str


@dataclass
class EvalRunSummary:
    label: str
    mode: str
    memory_enabled: bool
    context_enabled: bool
    retrieval_enabled: bool
    task_count: int
    passed: int
    success_rate: float
    average_tool_calls: float
    average_context_pack_calls: float
    average_read_file_calls: float
    average_duration: float
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    tool_counts: dict[str, int]
    failure_categories: list[str]


def run_evaluation(
    workspace: Path,
    output_path: Path,
    trace_dir: Path,
    mode: str = "scripted",
    task_ids: list[str] | None = None,
    categories: list[str] | None = None,
    memory_enabled: bool = True,
    context_enabled: bool = True,
    retrieval_enabled: bool = True,
    compare: bool = False,
    compare_retrieval: bool = False,
    json_output_path: Path | None = None,
) -> str:
    """Run a small deterministic benchmark and write a Markdown report."""
    if mode not in {"scripted", "agent"}:
        raise ValueError(f"Unsupported evaluation mode: {mode}")

    workspace = workspace.resolve()
    trace_dir = trace_dir.resolve()
    trace_dir.mkdir(parents=True, exist_ok=True)

    tasks = select_tasks(default_tasks(), task_ids=task_ids, categories=categories)
    if compare and compare_retrieval:
        raise ValueError("Use either compare=True or compare_retrieval=True, not both.")
    if compare:
        report = run_evaluation_comparison(
            workspace,
            trace_dir,
            tasks,
            mode,
            retrieval_enabled=retrieval_enabled,
            json_output_path=json_output_path,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return report
    if compare_retrieval:
        report = run_retrieval_comparison(
            workspace,
            trace_dir,
            tasks,
            mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            json_output_path=json_output_path,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return report

    results = run_eval_tasks(
        workspace=workspace,
        trace_dir=trace_dir,
        tasks=tasks,
        mode=mode,
        memory_enabled=memory_enabled,
        context_enabled=context_enabled,
        retrieval_enabled=retrieval_enabled,
    )

    report = build_eval_report(workspace, results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    if json_output_path is not None:
        write_eval_json_report(workspace, results, json_output_path)
    return report


def run_eval_tasks(
    workspace: Path,
    trace_dir: Path,
    tasks: list[EvalTask],
    mode: str,
    memory_enabled: bool,
    context_enabled: bool,
    retrieval_enabled: bool,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    for task in tasks:
        trace_path = trace_dir / f"{task.task_id}.jsonl"
        if mode == "agent":
            trace_path = trace_dir / "agent" / f"{task.task_id}.jsonl"
        if trace_path.exists():
            trace_path.unlink()
        task_workspace = workspace
        if task.fixture_setup:
            task_workspace = trace_dir / "workspaces" / task.task_id
            reset_fixture_workspace(task_workspace, trace_dir)
            task.fixture_setup(task_workspace)
            if memory_enabled:
                copy_eval_memories(workspace, task_workspace)
        trace = TraceLogger(trace_path)
        trace.log(
            "session_start",
            workspace=str(task_workspace),
            eval_task=task.task_id,
            eval_mode=mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_enabled=retrieval_enabled,
            allow_write=True,
        )
        registry = build_registry(
            task_workspace,
            trace,
            allow_write=True,
            enable_context_pack=retrieval_enabled if mode == "agent" else True,
        )
        started = time.perf_counter()
        try:
            if mode == "scripted":
                success = bool(task.runner(registry))
            else:
                success = bool(run_agent_eval_task(
                    task,
                    registry,
                    memory_enabled=memory_enabled,
                    context_enabled=context_enabled,
                    retrieval_enabled=retrieval_enabled,
                ))
        except Exception as exc:
            success = False
            trace.log("eval_error", task=task.task_id, error=f"{type(exc).__name__}: {exc}")
        duration = time.perf_counter() - started
        metrics = trace_metrics(trace_path)
        results.append(EvalResult(
            task_id=task.task_id,
            category=task.category,
            description=task.description,
            mode=mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_enabled=retrieval_enabled,
            success=success,
            duration_seconds=duration,
            tool_calls=metrics["tool_calls"],
            failed_tool_calls=metrics["failed_tool_calls"],
            tool_counts=metrics["tool_counts"],
            input_tokens=metrics["input_tokens"],
            output_tokens=metrics["output_tokens"],
            estimated_cost_usd=estimate_cost_usd(metrics["input_tokens"], metrics["output_tokens"]),
            failure_categories=metrics["failure_categories"],
            trace_path=str(trace_path.relative_to(workspace)),
        ))
    return results


def run_evaluation_comparison(
    workspace: Path,
    trace_dir: Path,
    tasks: list[EvalTask],
    mode: str,
    retrieval_enabled: bool = True,
    json_output_path: Path | None = None,
) -> str:
    summaries: list[EvalRunSummary] = []
    for memory_enabled, context_enabled in [
        (True, True),
        (False, True),
        (True, False),
        (False, False),
    ]:
        label = eval_config_label(memory_enabled, context_enabled)
        config_trace_dir = trace_dir / "compare" / label
        config_trace_dir.mkdir(parents=True, exist_ok=True)
        results = run_eval_tasks(
            workspace=workspace,
            trace_dir=config_trace_dir,
            tasks=tasks,
            mode=mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_enabled=retrieval_enabled,
        )
        summaries.append(summarize_results(label, results))
    if json_output_path is not None:
        write_eval_comparison_json_report(workspace, summaries, json_output_path)
    return build_eval_comparison_report(workspace, summaries)


def run_retrieval_comparison(
    workspace: Path,
    trace_dir: Path,
    tasks: list[EvalTask],
    mode: str,
    memory_enabled: bool,
    context_enabled: bool,
    json_output_path: Path | None = None,
) -> str:
    summaries: list[EvalRunSummary] = []
    for retrieval_enabled in [True, False]:
        label = "retrieval-on" if retrieval_enabled else "retrieval-off"
        config_trace_dir = trace_dir / "compare_retrieval" / label
        config_trace_dir.mkdir(parents=True, exist_ok=True)
        results = run_eval_tasks(
            workspace=workspace,
            trace_dir=config_trace_dir,
            tasks=tasks,
            mode=mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_enabled=retrieval_enabled,
        )
        summaries.append(summarize_results(label, results))
    if json_output_path is not None:
        write_eval_comparison_json_report(workspace, summaries, json_output_path)
    return build_eval_comparison_report(workspace, summaries)


def eval_config_label(memory_enabled: bool, context_enabled: bool) -> str:
    memory = "memory-on" if memory_enabled else "memory-off"
    context = "context-on" if context_enabled else "context-off"
    return f"{memory}_{context}"


def copy_eval_memories(source_workspace: Path, task_workspace: Path) -> None:
    source = source_workspace / "skills"
    if not source.exists():
        return
    target = task_workspace / "skills"
    target.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.md"):
        shutil.copy2(path, target / path.name)


def select_tasks(
    tasks: list[EvalTask],
    task_ids: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[EvalTask]:
    selected = tasks
    if task_ids:
        by_id = {task.task_id: task for task in tasks}
        unknown = [task_id for task_id in task_ids if task_id not in by_id]
        if unknown:
            known = ", ".join(sorted(by_id))
            raise ValueError(f"Unknown eval task(s): {', '.join(unknown)}. Known tasks: {known}")
        selected = [by_id[task_id] for task_id in task_ids]

    if categories:
        known_categories = sorted({task.category for task in tasks})
        requested_categories = set(categories)
        unknown_categories = [
            category
            for category in categories
            if category not in known_categories
        ]
        if unknown_categories:
            known = ", ".join(known_categories)
            raise ValueError(
                f"Unknown eval category/categories: {', '.join(unknown_categories)}. "
                f"Known categories: {known}"
            )
        selected = [
            task
            for task in selected
            if task.category in requested_categories
        ]

    if task_ids and categories and not selected:
        raise ValueError("No eval tasks matched the selected task/category filters.")
    return selected


def default_tasks() -> list[EvalTask]:
    return [
        EvalTask(
            "syntax_check",
            "code_quality",
            "Compile all Python files with run_py_compile.",
            lambda registry: registry.call("run_py_compile").ok,
            verifier=lambda registry: registry.call("run_py_compile").ok,
        ),
        EvalTask(
            "pytest_suite",
            "tests",
            "Run the pytest suite with run_tests.",
            lambda registry: registry.call("run_tests", target="tests").ok,
            verifier=lambda registry: registry.call("run_tests", target="tests").ok,
        ),
        EvalTask(
            "context_compaction",
            "trace",
            "Create todos, read a file, and summarize the trace with compact_context.",
            run_context_compaction_task,
            verifier=verify_context_compaction_task,
        ),
        EvalTask(
            "read_file_line_range",
            "trace",
            "Read a specific line range from a larger file.",
            run_read_file_line_range_task,
            setup_read_file_line_range_fixture,
            run_read_file_line_range_task,
        ),
        EvalTask(
            "context_pack_retrieval",
            "trace",
            "Use context_pack with query 'invoice total rounding' to retrieve the billing/invoice.py snippet; no file edits are needed.",
            run_context_pack_retrieval_task,
            setup_context_pack_retrieval_fixture,
            run_context_pack_retrieval_task,
        ),
        EvalTask(
            "rag_symbol_retrieval",
            "retrieval",
            "Use rag_search to retrieve the correct symbol chunk across distractor files.",
            run_rag_symbol_retrieval_task,
            setup_rag_symbol_retrieval_fixture,
            run_rag_symbol_retrieval_task,
        ),
        EvalTask(
            "rag_sensitive_path_filter",
            "retrieval",
            "Verify rag_search indexes useful source files while excluding .env and generated artifacts.",
            run_rag_sensitive_path_filter_task,
            setup_rag_sensitive_path_filter_fixture,
            run_rag_sensitive_path_filter_task,
        ),
        EvalTask(
            "rag_read_plan_generation",
            "retrieval",
            "Use rag_explain to convert retrieved chunks into concrete read_file path and line-range arguments.",
            run_rag_read_plan_generation_task,
            setup_rag_read_plan_generation_fixture,
            run_rag_read_plan_generation_task,
        ),
        EvalTask(
            "mcp_rag_search_smoke",
            "retrieval",
            "Call rag_search through the MCP tools/call protocol and validate structured results.",
            run_mcp_rag_search_smoke_task,
            setup_mcp_rag_search_smoke_fixture,
            run_mcp_rag_search_smoke_task,
        ),
        EvalTask(
            "trace_html_report",
            "trace",
            "Render a JSONL trace as a static HTML report.",
            run_trace_html_report_task,
            setup_trace_html_report_fixture,
            run_trace_html_report_task,
        ),
        EvalTask(
            "agent_loop_simulation",
            "agent_loop",
            "Run the model-driven agent loop with an injected fake model client.",
            run_agent_loop_simulation_task,
            setup_agent_loop_simulation_fixture,
            run_agent_loop_simulation_task,
        ),
        EvalTask(
            "error_recovery",
            "recovery",
            "Trigger an edit failure and classify it with recover_errors.",
            run_error_recovery_task,
            setup_error_recovery_fixture,
            verify_error_recovery_task,
        ),
        EvalTask(
            "semantic_retry_plan",
            "recovery",
            "Trigger an edit failure and produce an ordered retry plan.",
            run_retry_plan_task,
            setup_error_recovery_fixture,
            verify_retry_plan_task,
        ),
        EvalTask(
            "memory_listing",
            "memory",
            "List saved workflow memories from skills/*.md.",
            run_memory_listing_task,
            verifier=run_memory_listing_task,
        ),
        EvalTask(
            "memory_relevance_ranking",
            "memory",
            "Rank workflow memories by query relevance.",
            run_memory_relevance_ranking_task,
            setup_memory_relevance_ranking_fixture,
            run_memory_relevance_ranking_task,
        ),
        EvalTask(
            "python_bugfix",
            "code_maintenance",
            "Fix a broken Python function in an isolated fixture workspace and make pytest pass.",
            run_python_bugfix_task,
            setup_python_bugfix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "python_add_tests",
            "code_maintenance",
            "Add missing pytest coverage for an existing Python helper.",
            run_python_add_tests_task,
            setup_python_add_tests_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "readme_update",
            "documentation",
            "Update a README placeholder with concrete pytest usage text.",
            run_readme_update_task,
            setup_readme_update_fixture,
            verify_readme_update_task,
        ),
        EvalTask(
            "python_import_fix",
            "code_maintenance",
            "Fix a Python import/name mismatch that breaks pytest collection.",
            run_python_import_fix_task,
            setup_python_import_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "config_default_fix",
            "configuration",
            "Fix an unsafe default configuration value and make pytest pass.",
            run_config_default_fix_task,
            setup_config_default_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "json_config_update",
            "configuration",
            "Update a JSON configuration value used by application code.",
            run_json_config_update_task,
            setup_json_config_update_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "cli_validation_fix",
            "code_maintenance",
            "Fix CLI argument validation for invalid input.",
            run_cli_validation_fix_task,
            setup_cli_validation_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "env_default_fix",
            "configuration",
            "Fix an environment-variable default used by application code.",
            run_env_default_fix_task,
            setup_env_default_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "csv_parser_fix",
            "code_maintenance",
            "Fix CSV parsing so empty cells are trimmed and ignored.",
            run_csv_parser_fix_task,
            setup_csv_parser_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "date_format_fix",
            "code_maintenance",
            "Fix date formatting so reports use ISO dates.",
            run_date_format_fix_task,
            setup_date_format_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "pagination_off_by_one",
            "code_maintenance",
            "Fix pagination page-count logic for partial final pages.",
            run_pagination_off_by_one_task,
            setup_pagination_off_by_one_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "secret_redaction_fix",
            "security",
            "Redact API tokens before logging user-visible messages.",
            run_secret_redaction_fix_task,
            setup_secret_redaction_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "shell_no_shell_execution",
            "security",
            "Run an allowlisted command without invoking a shell.",
            run_shell_no_shell_execution_task,
            verifier=run_shell_no_shell_execution_task,
        ),
        EvalTask(
            "permission_policy_report",
            "security",
            "Report write, shell, Git, and sandbox permission boundaries.",
            run_permission_policy_report_task,
            verifier=run_permission_policy_report_task,
        ),
        EvalTask(
            "path_normalization_fix",
            "code_maintenance",
            "Normalize path segments without duplicate separators.",
            run_path_normalization_fix_task,
            setup_path_normalization_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "dependency_pin_update",
            "configuration",
            "Pin a dependency version required by project validation.",
            run_dependency_pin_update_task,
            setup_dependency_pin_update_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "mutable_default_fix",
            "code_maintenance",
            "Fix shared mutable default state across function calls.",
            run_mutable_default_fix_task,
            setup_mutable_default_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "multi_file_service_fix",
            "multi_file",
            "Fix a service/repository contract bug across two Python modules.",
            run_multi_file_service_fix_task,
            setup_multi_file_service_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "multi_file_api_contract_fix",
            "multi_file",
            "Fix an API handler and response helper contract across multiple files.",
            run_multi_file_api_contract_fix_task,
            setup_multi_file_api_contract_fix_fixture,
            verify_tests_pass,
        ),
        EvalTask(
            "package_order_total_fix",
            "multi_file",
            "Fix order total calculation across a src/ package and cross-file tests.",
            run_package_order_total_fix_task,
            setup_package_order_total_fix_fixture,
            verify_tests_pass,
        ),
    ]


def run_agent_eval_task(
    task: EvalTask,
    registry: ToolRegistry,
    memory_enabled: bool,
    context_enabled: bool,
    retrieval_enabled: bool,
) -> bool:
    """Ask the model-driven loop to solve one task, then verify without scripted edits."""
    if task.verifier is None:
        registry.trace.log("eval_agent_unsupported", task=task.task_id)
        return False

    from .agent import run_agent

    support_prompt = build_agent_support_prompt(
        registry,
        memory_enabled,
        context_enabled,
        retrieval_enabled,
        memory_query=task.description,
    )
    prompt = build_agent_eval_prompt(task, support_prompt)
    answer = run_agent(prompt, registry, max_turns=_agent_eval_max_turns())
    registry.trace.log("eval_agent_answer", task=task.task_id, answer=answer)
    if answer.startswith("Error:"):
        return False
    registry.trace.log("eval_agent_verifier_start", task=task.task_id)
    if context_enabled:
        registry.call("compact_context")
    verified = bool(task.verifier(registry))
    registry.trace.log("eval_agent_verifier_end", task=task.task_id, success=verified)
    return verified


def build_agent_eval_prompt(task: EvalTask, support_prompt: str) -> str:
    """Build a constrained prompt for real model eval runs.

    The contract is intentionally operational: real models often spend too many
    turns on shell/git exploration when a small fixture only needs read/edit/test.
    """
    task_hints = []
    if "add_tests" in task.task_id:
        task_hints.append(
            "For add-tests tasks, an empty `tests/` directory usually means coverage is missing; "
            "read the helper module, then create a focused `tests/test_*.py` file with `write_file`."
        )
    if "readme" in task.task_id or task.category == "documentation":
        task_hints.append(
            "For README/documentation tasks, read `README.md` directly and update it with `edit_file`; "
            "use a concrete executable command when the task asks for usage text, and do not inspect Git history."
        )
    if task.category in {"code_maintenance", "configuration", "multi_file", "security"}:
        task_hints.append(
            "For code/config/security tasks, use `run_tests` early to reproduce the issue, "
            "then read the smallest relevant source file(s), edit, and rerun tests."
        )
    task_hint_text = "\n".join(f"- {hint}" for hint in task_hints)
    if not task_hint_text:
        task_hint_text = "- Use the task description to choose the narrowest useful tool path."

    return (
        f"Evaluation task `{task.task_id}`: {task.description}\n\n"
        f"{support_prompt}\n\n"
        "Agent-eval workflow contract:\n"
        "1. Start with `todo_write` and keep the todo list current.\n"
        "2. Prefer `read_file`, `grep`, `context_pack`, `write_file`, `edit_file`, and `run_tests` for fixture tasks.\n"
        "3. Avoid broad shell or Git exploration. Use `shell`/`git` only for a targeted check after file tools are insufficient.\n"
        "4. For change tasks, make the first file change by turn 6 unless a prior tool failure blocks the edit.\n"
        "5. Verify with `run_tests` for code tasks, or reread the changed document for documentation tasks.\n"
        "6. Finish with the files changed and verification result.\n\n"
        "Task-specific guidance:\n"
        f"{task_hint_text}"
    )


def _agent_eval_max_turns() -> int:
    value = os.getenv("AGENT_EVAL_MAX_TURNS", "12")
    try:
        turns = int(value)
    except ValueError:
        return 12
    return max(1, turns)


def build_agent_support_prompt(
    registry: ToolRegistry,
    memory_enabled: bool,
    context_enabled: bool,
    retrieval_enabled: bool,
    memory_query: str = "",
) -> str:
    parts: list[str] = []
    if memory_enabled:
        memories = registry.call("list_memories", query=memory_query, limit=5)
        parts.append(
            "Memory support is enabled. Review the available workflow memories if they are relevant.\n"
            f"Available memories:\n{memories.output}"
        )
    else:
        parts.append("Memory support is disabled for this evaluation run; do not rely on saved workflow memories.")

    if context_enabled:
        parts.append("Context compaction is enabled; use compact_context if the trace becomes long or you need a state summary.")
    else:
        parts.append("Context compaction is disabled for this evaluation run; continue only from the current tool results.")
    if retrieval_enabled and "context_pack" in registry.names():
        parts.append("Retrieval support is enabled; use context_pack before broad file reads when the relevant files are not obvious.")
    else:
        parts.append("Retrieval support is disabled for this evaluation run; use grep, list_python_files, and read_file directly.")
    return "\n\n".join(parts)


def verify_tests_pass(registry: ToolRegistry) -> bool:
    return registry.call("run_tests").ok


def verify_context_compaction_task(registry: ToolRegistry) -> bool:
    summary = registry.call("compact_context")
    return summary.ok and "README.md" in summary.output


def verify_error_recovery_task(registry: ToolRegistry) -> bool:
    recovery = registry.call("recover_errors")
    metadata = recovery.metadata or {}
    categories = {item.get("category") for item in metadata.get("recoveries", [])}
    return recovery.ok and "edit_match_failed" in categories


def verify_retry_plan_task(registry: ToolRegistry) -> bool:
    plan = registry.call("retry_plan")
    metadata = plan.metadata or {}
    categories = {item.get("category") for item in metadata.get("steps", [])}
    return plan.ok and "edit_match_failed" in categories and "read_file -> edit_file" in plan.output


def verify_readme_update_task(registry: ToolRegistry) -> bool:
    read = registry.call("read_file", path="README.md")
    return read.ok and "python -m pytest" in read.output


def run_context_compaction_task(registry: ToolRegistry) -> bool:
    registry.call("todo_write", todos=[
        {"task": "Read README", "status": "completed"},
        {"task": "Compact context", "status": "pending"},
    ])
    read = registry.call("read_file", path="README.md", max_chars=1000)
    summary = registry.call("compact_context")
    return read.ok and summary.ok and "README.md" in summary.output


def setup_read_file_line_range_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "large_module.py").write_text(
        "def first():\n"
        "    return 'first'\n\n"
        "def target():\n"
        "    return 'target'\n\n"
        "def last():\n"
        "    return 'last'\n",
        encoding="utf-8",
    )


def run_read_file_line_range_task(registry: ToolRegistry) -> bool:
    result = registry.call("read_file", path="large_module.py", start_line=4, end_line=5)
    metadata = result.metadata or {}
    return (
        result.ok
        and "def target()" in result.output
        and "def first()" not in result.output
        and metadata.get("returned_lines") == 2
    )


def setup_context_pack_retrieval_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "billing").mkdir(parents=True, exist_ok=True)
    (workspace / "billing" / "invoice.py").write_text(
        "class InvoiceCalculator:\n"
        "    def invoice_total(self, items):\n"
        "        subtotal = sum(item.price for item in items)\n"
        "        return round(subtotal, 2)\n",
        encoding="utf-8",
    )
    (workspace / "notifications.py").write_text(
        "def send_email(address, body):\n"
        "    return {'address': address, 'body': body}\n",
        encoding="utf-8",
    )


def run_context_pack_retrieval_task(registry: ToolRegistry) -> bool:
    result = registry.call("context_pack", query="invoice total rounding", glob="*.py", limit=1, window=1)
    metadata = result.metadata or {}
    matches = metadata.get("matches", [])
    first_path = str(matches[0].get("path", "")) if matches else ""
    return (
        result.ok
        and metadata.get("count") == 1
        and first_path.endswith("billing/invoice.py")
        and "invoice_total" in result.output
    )


def setup_rag_symbol_retrieval_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "billing").mkdir(parents=True, exist_ok=True)
    (workspace / "billing" / "invoice.py").write_text(
        "class InvoiceCalculator:\n"
        "    def invoice_total(self, items):\n"
        "        subtotal = sum(item.price for item in items)\n"
        "        return round(subtotal, 2)\n",
        encoding="utf-8",
    )
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "invoice.md").write_text(
        "# Invoice Notes\n\n"
        "Customer invoice wording and billing emails mention total amounts.\n",
        encoding="utf-8",
    )
    (workspace / "shipping.py").write_text(
        "def shipping_total(items):\n"
        "    return sum(item.weight for item in items)\n",
        encoding="utf-8",
    )


def run_rag_symbol_retrieval_task(registry: ToolRegistry) -> bool:
    result = registry.call(
        "rag_search",
        query="invoice total rounding",
        glob="*.py,*.md",
        limit=2,
        chunk_lines=20,
    )
    metadata = result.metadata or {}
    matches = metadata.get("matches", [])
    first = matches[0] if matches else {}
    return (
        result.ok
        and metadata.get("count") >= 1
        and str(first.get("path", "")).endswith("billing/invoice.py")
        and int(first.get("start_line", 0)) == 1
        and "invoice_total" in result.output
        and metadata.get("retrieval") == "local_chunk_lexical_scoring"
    )


def setup_rag_sensitive_path_filter_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "service.py").write_text(
        "def public_context():\n"
        "    return 'stable public retrieval context'\n",
        encoding="utf-8",
    )
    (workspace / ".env").write_text("SECRET_CONTEXT=hidden\n", encoding="utf-8")
    (workspace / "artifacts").mkdir(parents=True, exist_ok=True)
    (workspace / "artifacts" / "generated.py").write_text(
        "def generated_context():\n"
        "    return 'secret generated retrieval context'\n",
        encoding="utf-8",
    )


def run_rag_sensitive_path_filter_task(registry: ToolRegistry) -> bool:
    index = registry.call("index_workspace", glob="*.py,*", chunk_lines=20)
    search = registry.call("rag_search", query="public retrieval context", glob="*.py,*", limit=5, chunk_lines=20)
    index_metadata = index.metadata or {}
    search_metadata = search.metadata or {}
    paths = [str(item.get("path", "")) for item in search_metadata.get("matches", [])]
    combined_output = index.output + "\n" + search.output
    return (
        index.ok
        and search.ok
        and int(index_metadata.get("files_indexed", 0)) >= 1
        and ".env" in (index_metadata.get("ignored_names") or [])
        and "artifacts" in (index_metadata.get("ignored_parts") or [])
        and "service.py" in paths
        and ".env" not in paths
        and all(not path.startswith("artifacts/") for path in paths)
        and "SECRET_CONTEXT" not in combined_output
        and "secret generated retrieval context" not in combined_output
    )


def setup_rag_read_plan_generation_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "billing_service.py").write_text(
        "class BillingService:\n"
        "    def invoice_total(self, items):\n"
        "        subtotal = sum(item.price for item in items)\n"
        "        return round(subtotal, 2)\n",
        encoding="utf-8",
    )
    (workspace / "billing_notes.md").write_text(
        "Invoice wording notes that mention total and rounding, but do not contain executable code.\n",
        encoding="utf-8",
    )


def run_rag_read_plan_generation_task(registry: ToolRegistry) -> bool:
    result = registry.call(
        "rag_explain",
        query="invoice total rounding",
        glob="*.py,*.md",
        limit=1,
        chunk_lines=20,
        read_window=1,
    )
    metadata = result.metadata or {}
    plan = metadata.get("read_plan", [])
    first = plan[0] if plan else {}
    read_args = first.get("read_file_args") or {}
    return (
        result.ok
        and metadata.get("count") == 1
        and read_args.get("path") == "billing_service.py"
        and read_args.get("start_line") == 1
        and int(read_args.get("end_line", 0)) >= 4
        and 'read_file(path="billing_service.py"' in result.output
    )


def setup_mcp_rag_search_smoke_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "orders.py").write_text(
        "def order_total(lines):\n"
        "    return round(sum(line.price for line in lines), 2)\n",
        encoding="utf-8",
    )
    (workspace / "notes.md").write_text(
        "Order status notes that should not outrank the order_total function.\n",
        encoding="utf-8",
    )


def run_mcp_rag_search_smoke_task(registry: ToolRegistry) -> bool:
    from .mcp_server import build_mcp_server

    server = build_mcp_server(registry.workspace, registry.workspace / "mcp_rag_trace.jsonl", fresh_trace=True)
    response = server.handle_message({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "rag_search",
            "arguments": {"query": "order total rounding", "glob": "*.py,*.md", "limit": 1},
        },
    })
    result = response.get("result", {}) if isinstance(response, dict) else {}
    metadata = (result.get("structuredContent") or {}).get("metadata") or {}
    matches = metadata.get("matches", [])
    first = matches[0] if matches else {}
    return (
        result.get("isError") is False
        and (result.get("structuredContent") or {}).get("ok") is True
        and str(first.get("path", "")).endswith("orders.py")
        and "order_total" in str((result.get("content") or [{}])[0].get("text", ""))
    )


def setup_trace_html_report_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "sample.txt").write_text("old old\n", encoding="utf-8")


def run_trace_html_report_task(registry: ToolRegistry) -> bool:
    from .trace_viewer import build_trace_report

    registry.call("read_file", path="sample.txt")
    registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")
    output_path = registry.workspace / "TRACE.html"
    html = build_trace_report(registry.trace.path, output_path)
    return (
        output_path.exists()
        and "Mini Coding Agent Trace" in html
        and "edit_file" in html
        and "failed" in html
    )


class FakeModelBlock:
    def __init__(self, block_type: str, **kwargs: Any):
        self.type = block_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeModelResponse:
    def __init__(self, stop_reason: str, content: list[FakeModelBlock]):
        self.stop_reason = stop_reason
        self.content = content
        self.usage = None


class FakeModelMessages:
    def __init__(self, responses: list[FakeModelResponse]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeModelResponse:
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeModelClient:
    def __init__(self, responses: list[FakeModelResponse]):
        self.messages = FakeModelMessages(responses)


def setup_agent_loop_simulation_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text("# Agent Loop Fixture\n", encoding="utf-8")


def run_agent_loop_simulation_task(registry: ToolRegistry) -> bool:
    from .agent import run_agent

    client = FakeModelClient([
        FakeModelResponse(
            "tool_use",
            [
                FakeModelBlock(
                    "tool_use",
                    id="toolu_plan",
                    name="todo_write",
                    input={"todos": [{"task": "Read README", "status": "in_progress"}]},
                )
            ],
        ),
        FakeModelResponse(
            "tool_use",
            [
                FakeModelBlock(
                    "tool_use",
                    id="toolu_read",
                    name="read_file",
                    input={"path": "README.md"},
                )
            ],
        ),
        FakeModelResponse("end_turn", [FakeModelBlock("text", text="Read README.md with read_file.")]),
    ])
    answer = run_agent(
        "Inspect README with a fake model client.",
        registry,
        client=client,
        model="fake-model",
    )
    return (
        answer == "Read README.md with read_file."
        and len(client.messages.calls) == 3
        and bool(registry.todos)
    )


def run_error_recovery_task(registry: ToolRegistry) -> bool:
    registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")
    recovery = registry.call("recover_errors")
    metadata = recovery.metadata or {}
    categories = {item.get("category") for item in metadata.get("recoveries", [])}
    return recovery.ok and "edit_match_failed" in categories


def run_retry_plan_task(registry: ToolRegistry) -> bool:
    edit = registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")
    plan = registry.call("retry_plan")
    metadata = plan.metadata or {}
    categories = {item.get("category") for item in metadata.get("steps", [])}
    return (not edit.ok) and plan.ok and "edit_match_failed" in categories


def setup_error_recovery_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "sample.txt").write_text("old old\n", encoding="utf-8")


def run_memory_listing_task(registry: ToolRegistry) -> bool:
    result = registry.call("list_memories")
    return result.ok and (result.metadata or {}).get("count", 0) >= 1


def setup_memory_relevance_ranking_fixture(workspace: Path) -> None:
    memory_dir = workspace / "skills"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "pytest-repair.md").write_text(
        "# Pytest Repair\n\n"
        "Use failing pytest assertions to find the smallest code edit, then rerun tests.\n",
        encoding="utf-8",
    )
    (memory_dir / "readme-update.md").write_text(
        "# README Update\n\n"
        "Use read_file and edit_file to update project documentation.\n",
        encoding="utf-8",
    )


def run_memory_relevance_ranking_task(registry: ToolRegistry) -> bool:
    result = registry.call("list_memories", query="pytest failing assertion", limit=1)
    metadata = result.metadata or {}
    memories = metadata.get("memories", [])
    return (
        result.ok
        and metadata.get("count") == 1
        and bool(memories)
        and str(memories[0].get("path", "")).endswith("pytest-repair.md")
    )


def setup_python_bugfix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "calculator.py").write_text(
        "def add(a, b):\n"
        "    return a - b\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )


def run_python_bugfix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="calculator.py")
    edit = registry.call(
        "edit_file",
        path="calculator.py",
        old_text="return a - b",
        new_text="return a + b  # fixed",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_python_add_tests_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "string_utils.py").write_text(
        "def normalize_title(value):\n"
        "    return value.strip().title()\n",
        encoding="utf-8",
    )


def run_python_add_tests_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="string_utils.py")
    write = registry.call(
        "write_file",
        path="tests/test_string_utils.py",
        content=(
            "from string_utils import normalize_title\n\n"
            "def test_normalize_title():\n"
            "    assert normalize_title('  hello agent  ') == 'Hello Agent'\n"
        ),
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and write.ok and after.ok


def setup_readme_update_fixture(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text(
        "# Fixture Project\n\n"
        "Usage: TODO\n",
        encoding="utf-8",
    )


def run_readme_update_task(registry: ToolRegistry) -> bool:
    read = registry.call("read_file", path="README.md")
    edit = registry.call(
        "edit_file",
        path="README.md",
        old_text="Usage: TODO",
        new_text="Usage: run `python -m pytest` before submitting changes.",
    )
    reread = registry.call("read_file", path="README.md")
    return (
        read.ok
        and edit.ok
        and reread.ok
        and "python -m pytest" in reread.output
    )


def setup_python_import_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "math_utils.py").write_text(
        "def add_numbers(values):\n"
        "    return sum(values)\n",
        encoding="utf-8",
    )
    (workspace / "app.py").write_text(
        "from math_utils import add_number\n\n"
        "def total(values):\n"
        "    return add_number(values)\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_app.py").write_text(
        "from app import total\n\n"
        "def test_total():\n"
        "    assert total([1, 2, 3]) == 6\n",
        encoding="utf-8",
    )


def run_python_import_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="app.py")
    edit = registry.call(
        "edit_file",
        path="app.py",
        old_text=(
            "from math_utils import add_number\n\n"
            "def total(values):\n"
            "    return add_number(values)"
        ),
        new_text=(
            "from math_utils import add_numbers\n\n"
            "def total(values):\n"
            "    return add_numbers(values)"
        ),
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_config_default_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "settings.py").write_text(
        "DEBUG = True\n"
        "RETRY_LIMIT = 3\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_settings.py").write_text(
        "import settings\n\n"
        "def test_debug_disabled_by_default():\n"
        "    assert settings.DEBUG is False\n",
        encoding="utf-8",
    )


def run_config_default_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="settings.py")
    edit = registry.call(
        "edit_file",
        path="settings.py",
        old_text="DEBUG = True",
        new_text="DEBUG = False",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_json_config_update_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "settings.json").write_text(
        "{\n"
        "  \"mode\": \"dev\",\n"
        "  \"timeout\": 30\n"
        "}\n",
        encoding="utf-8",
    )
    (workspace / "config_loader.py").write_text(
        "import json\n"
        "from pathlib import Path\n\n"
        "def load_mode():\n"
        "    data = json.loads(Path('settings.json').read_text())\n"
        "    return data['mode']\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_config_loader.py").write_text(
        "from config_loader import load_mode\n\n"
        "def test_load_mode():\n"
        "    assert load_mode() == 'prod'\n",
        encoding="utf-8",
    )


def run_json_config_update_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="settings.json")
    edit = registry.call(
        "edit_file",
        path="settings.json",
        old_text='"mode": "dev"',
        new_text='"mode": "prod"',
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_cli_validation_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "cli.py").write_text(
        "def parse_limit(value):\n"
        "    return int(value)\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_cli.py").write_text(
        "import pytest\n"
        "from cli import parse_limit\n\n"
        "def test_parse_limit_rejects_zero():\n"
        "    with pytest.raises(ValueError):\n"
        "        parse_limit('0')\n\n"
        "def test_parse_limit_accepts_positive():\n"
        "    assert parse_limit('3') == 3\n",
        encoding="utf-8",
    )


def run_cli_validation_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="cli.py")
    edit = registry.call(
        "edit_file",
        path="cli.py",
        old_text="def parse_limit(value):\n    return int(value)",
        new_text=(
            "def parse_limit(value):\n"
            "    limit = int(value)\n"
            "    if limit <= 0:\n"
            "        raise ValueError('limit must be positive')\n"
            "    return limit"
        ),
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_env_default_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "env_config.py").write_text(
        "import os\n\n"
        "def service_url():\n"
        "    return os.getenv('SERVICE_URL', 'http://localhost')\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_env_config.py").write_text(
        "from env_config import service_url\n\n"
        "def test_default_service_url():\n"
        "    assert service_url() == 'https://api.example.com'\n",
        encoding="utf-8",
    )


def run_env_default_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="env_config.py")
    edit = registry.call(
        "edit_file",
        path="env_config.py",
        old_text="return os.getenv('SERVICE_URL', 'http://localhost')",
        new_text="return os.getenv('SERVICE_URL', 'https://api.example.com')",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_csv_parser_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "csv_utils.py").write_text(
        "def parse_tags(value):\n"
        "    return value.split(',')\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_csv_utils.py").write_text(
        "from csv_utils import parse_tags\n\n"
        "def test_parse_tags_strips_and_drops_empty_cells():\n"
        "    assert parse_tags(' alpha, ,beta ') == ['alpha', 'beta']\n",
        encoding="utf-8",
    )


def run_csv_parser_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="csv_utils.py")
    edit = registry.call(
        "edit_file",
        path="csv_utils.py",
        old_text="return value.split(',')",
        new_text="return [item.strip() for item in value.split(',') if item.strip()]",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_date_format_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "reporting.py").write_text(
        "def format_report_date(date):\n"
        "    return f'{date.month}/{date.day}/{date.year}'\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_reporting.py").write_text(
        "from datetime import date\n"
        "from reporting import format_report_date\n\n"
        "def test_format_report_date_uses_iso_format():\n"
        "    assert format_report_date(date(2026, 7, 4)) == '2026-07-04'\n",
        encoding="utf-8",
    )


def run_date_format_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="reporting.py")
    edit = registry.call(
        "edit_file",
        path="reporting.py",
        old_text="return f'{date.month}/{date.day}/{date.year}'",
        new_text="return date.isoformat()",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_pagination_off_by_one_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "pagination.py").write_text(
        "def page_count(total_items, page_size):\n"
        "    return total_items // page_size\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_pagination.py").write_text(
        "from pagination import page_count\n\n"
        "def test_page_count_includes_partial_final_page():\n"
        "    assert page_count(11, 10) == 2\n\n"
        "def test_page_count_exact_page_boundary():\n"
        "    assert page_count(20, 10) == 2\n",
        encoding="utf-8",
    )


def run_pagination_off_by_one_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="pagination.py")
    edit = registry.call(
        "edit_file",
        path="pagination.py",
        old_text="return total_items // page_size",
        new_text="return (total_items + page_size - 1) // page_size",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_secret_redaction_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "log_filter.py").write_text(
        "def sanitize_message(message):\n"
        "    return message\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_log_filter.py").write_text(
        "from log_filter import sanitize_message\n\n"
        "def test_sanitize_message_redacts_api_token():\n"
        "    message = 'calling service with token=abc123'\n"
        "    assert sanitize_message(message) == 'calling service with token=[REDACTED]'\n",
        encoding="utf-8",
    )


def run_secret_redaction_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="log_filter.py")
    edit = registry.call(
        "edit_file",
        path="log_filter.py",
        old_text="return message",
        new_text="return message.replace('token=abc123', 'token=[REDACTED]')",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def run_shell_no_shell_execution_task(registry: ToolRegistry) -> bool:
    result = registry.call("shell", command='python -c "print(123)"', timeout=10)
    metadata = result.metadata or {}
    return (
        result.ok
        and "123" in result.output
        and metadata.get("shell") is False
        and metadata.get("argv") == ["python", "-c", "print(123)"]
    )


def run_permission_policy_report_task(registry: ToolRegistry) -> bool:
    result = registry.call("permission_policy")
    metadata = result.metadata or {}
    return (
        result.ok
        and "Permission Policy" in result.output
        and "not an OS-level sandbox" in result.output
        and metadata.get("shell_false") is True
        and metadata.get("os_sandbox") is False
        and metadata.get("path_scope") == "workspace_only"
        and "python" in metadata.get("allowed_shell_commands", [])
        and "status" in metadata.get("read_only_git_subcommands", [])
    )


def setup_path_normalization_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "path_utils.py").write_text(
        "def join_url_path(*parts):\n"
        "    return '/'.join(parts)\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_path_utils.py").write_text(
        "from path_utils import join_url_path\n\n"
        "def test_join_url_path_normalizes_slashes():\n"
        "    assert join_url_path('/api/', '/v1', 'users/') == 'api/v1/users'\n",
        encoding="utf-8",
    )


def run_path_normalization_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="path_utils.py")
    edit = registry.call(
        "edit_file",
        path="path_utils.py",
        old_text="return '/'.join(parts)",
        new_text="return '/'.join(part.strip('/') for part in parts if part.strip('/'))",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_dependency_pin_update_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "requirements.txt").write_text(
        "requests>=2.0\n",
        encoding="utf-8",
    )
    (workspace / "dependency_policy.py").write_text(
        "from pathlib import Path\n\n"
        "def requirements_text():\n"
        "    return Path('requirements.txt').read_text(encoding='utf-8')\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_dependency_policy.py").write_text(
        "from dependency_policy import requirements_text\n\n"
        "def test_requests_is_pinned():\n"
        "    assert 'requests==2.32.0' in requirements_text()\n",
        encoding="utf-8",
    )


def run_dependency_pin_update_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="requirements.txt")
    edit = registry.call(
        "edit_file",
        path="requirements.txt",
        old_text="requests>=2.0",
        new_text="requests==2.32.0",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_mutable_default_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "collector.py").write_text(
        "def collect_item(item, bucket=[]):\n"
        "    bucket.append(item)\n"
        "    return bucket\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_collector.py").write_text(
        "from collector import collect_item\n\n"
        "def test_collect_item_does_not_share_state():\n"
        "    assert collect_item('a') == ['a']\n"
        "    assert collect_item('b') == ['b']\n",
        encoding="utf-8",
    )


def run_mutable_default_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read = registry.call("read_file", path="collector.py")
    edit = registry.call(
        "edit_file",
        path="collector.py",
        old_text=(
            "def collect_item(item, bucket=[]):\n"
            "    bucket.append(item)\n"
            "    return bucket"
        ),
        new_text=(
            "def collect_item(item, bucket=None):\n"
            "    if bucket is None:\n"
            "        bucket = []\n"
            "    bucket.append(item)\n"
            "    return bucket"
        ),
    )
    after = registry.call("run_tests")
    return (not before.ok) and read.ok and edit.ok and after.ok


def setup_multi_file_service_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "repository.py").write_text(
        "USERS = {\n"
        "    1: {'id': 1, 'name': 'Ada', 'active': True},\n"
        "    2: {'id': 2, 'name': 'Grace', 'active': False},\n"
        "}\n\n"
        "def get_user(user_id):\n"
        "    return USERS[user_id]\n",
        encoding="utf-8",
    )
    (workspace / "service.py").write_text(
        "from repository import get_user\n\n"
        "def describe_user(user_id):\n"
        "    user = get_user(user_id)\n"
        "    return f\"{user['name']} is active\"\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_service.py").write_text(
        "import pytest\n"
        "from service import describe_user\n\n"
        "def test_describe_user_handles_inactive_user():\n"
        "    assert describe_user(2) == 'Grace is inactive'\n\n"
        "def test_describe_user_raises_for_missing_user():\n"
        "    with pytest.raises(ValueError):\n"
        "        describe_user(99)\n",
        encoding="utf-8",
    )


def run_multi_file_service_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read_repo = registry.call("read_file", path="repository.py")
    read_service = registry.call("read_file", path="service.py")
    edit_repo = registry.call(
        "edit_file",
        path="repository.py",
        old_text="def get_user(user_id):\n    return USERS[user_id]",
        new_text=(
            "def get_user(user_id):\n"
            "    user = USERS.get(user_id)\n"
            "    if user is None:\n"
            "        raise ValueError('user not found')\n"
            "    return user"
        ),
    )
    edit_service = registry.call(
        "edit_file",
        path="service.py",
        old_text="return f\"{user['name']} is active\"",
        new_text="return f\"{user['name']} is {'active' if user['active'] else 'inactive'}\"",
    )
    after = registry.call("run_tests")
    return (not before.ok) and read_repo.ok and read_service.ok and edit_repo.ok and edit_service.ok and after.ok


def setup_multi_file_api_contract_fix_fixture(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "responses.py").write_text(
        "def ok(data):\n"
        "    return {'status': 200, 'data': data}\n\n"
        "def error(message):\n"
        "    return {'status': 200, 'error': message}\n",
        encoding="utf-8",
    )
    (workspace / "handlers.py").write_text(
        "from responses import error, ok\n\n"
        "def get_profile(user_id):\n"
        "    if user_id <= 0:\n"
        "        return error('invalid user id')\n"
        "    return ok({'id': user_id})\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_handlers.py").write_text(
        "from handlers import get_profile\n\n"
        "def test_get_profile_rejects_invalid_id_with_400():\n"
        "    assert get_profile(0) == {'status': 400, 'error': 'invalid user id'}\n\n"
        "def test_get_profile_returns_profile_payload():\n"
        "    assert get_profile(7) == {'status': 200, 'data': {'id': 7, 'kind': 'profile'}}\n",
        encoding="utf-8",
    )


def run_multi_file_api_contract_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read_responses = registry.call("read_file", path="responses.py")
    read_handlers = registry.call("read_file", path="handlers.py")
    edit_responses = registry.call(
        "edit_file",
        path="responses.py",
        old_text="def error(message):\n    return {'status': 200, 'error': message}",
        new_text="def error(message, status=400):\n    return {'status': status, 'error': message}",
    )
    edit_handlers = registry.call(
        "edit_file",
        path="handlers.py",
        old_text="return ok({'id': user_id})",
        new_text="return ok({'id': user_id, 'kind': 'profile'})",
    )
    after = registry.call("run_tests")
    return (
        (not before.ok)
        and read_responses.ok
        and read_handlers.ok
        and edit_responses.ok
        and edit_handlers.ok
        and after.ok
    )


def setup_package_order_total_fix_fixture(workspace: Path) -> None:
    package_dir = workspace / "src" / "shop"
    package_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "src" / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "pricing.py").write_text(
        "TAX_RATE = 0.08\n\n"
        "def discounted_subtotal(items):\n"
        "    return sum(item['price'] for item in items)\n\n"
        "def apply_tax(amount):\n"
        "    return round(amount + TAX_RATE, 2)\n",
        encoding="utf-8",
    )
    (package_dir / "cart.py").write_text(
        "from src.shop.pricing import apply_tax, discounted_subtotal\n\n"
        "def order_total(items, discount=0):\n"
        "    subtotal = discounted_subtotal(items)\n"
        "    return apply_tax(subtotal) - discount\n",
        encoding="utf-8",
    )
    (workspace / "tests" / "test_cart.py").write_text(
        "from src.shop.cart import order_total\n\n"
        "def test_order_total_applies_quantities_discount_and_tax():\n"
        "    items = [\n"
        "        {'sku': 'a', 'price': 10.0, 'quantity': 2},\n"
        "        {'sku': 'b', 'price': 5.0, 'quantity': 1},\n"
        "    ]\n"
        "    assert order_total(items, discount=5.0) == 21.6\n\n"
        "def test_order_total_never_goes_negative():\n"
        "    items = [{'sku': 'c', 'price': 2.0, 'quantity': 1}]\n"
        "    assert order_total(items, discount=10.0) == 0.0\n",
        encoding="utf-8",
    )


def run_package_order_total_fix_task(registry: ToolRegistry) -> bool:
    before = registry.call("run_tests")
    read_cart = registry.call("read_file", path="src/shop/cart.py")
    read_pricing = registry.call("read_file", path="src/shop/pricing.py")
    edit_pricing = registry.call(
        "edit_file",
        path="src/shop/pricing.py",
        old_text=(
            "def discounted_subtotal(items):\n"
            "    return sum(item['price'] for item in items)\n\n"
            "def apply_tax(amount):\n"
            "    return round(amount + TAX_RATE, 2)"
        ),
        new_text=(
            "def discounted_subtotal(items):\n"
            "    return sum(item['price'] * item.get('quantity', 1) for item in items)\n\n"
            "def apply_tax(amount):\n"
            "    return round(amount * (1 + TAX_RATE), 2)"
        ),
    )
    edit_cart = registry.call(
        "edit_file",
        path="src/shop/cart.py",
        old_text=(
            "def order_total(items, discount=0):\n"
            "    subtotal = discounted_subtotal(items)\n"
            "    return apply_tax(subtotal) - discount"
        ),
        new_text=(
            "def order_total(items, discount=0):\n"
            "    subtotal = max(discounted_subtotal(items) - discount, 0)\n"
            "    return apply_tax(subtotal)"
        ),
    )
    after = registry.call("run_tests")
    return (
        (not before.ok)
        and read_cart.ok
        and read_pricing.ok
        and edit_pricing.ok
        and edit_cart.ok
        and after.ok
    )


def reset_fixture_workspace(path: Path, trace_dir: Path) -> None:
    root = (trace_dir / "workspaces").resolve()
    target = path.resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Refusing to reset fixture outside eval workspaces: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def trace_metrics(trace_path: Path) -> dict:
    tool_calls = 0
    failed_tool_calls = 0
    input_tokens = 0
    output_tokens = 0
    tool_counts: dict[str, int] = {}
    failure_categories: list[str] = []
    in_agent_verifier = False
    for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "agent_response":
            usage = (event.get("data") or {}).get("usage") or {}
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)
            continue
        event_name = event.get("event")
        if event_name == "eval_agent_verifier_start":
            in_agent_verifier = True
            continue
        if event_name == "eval_agent_verifier_end":
            in_agent_verifier = False
            continue
        if event_name != "tool_call" or in_agent_verifier:
            continue
        tool_calls += 1
        data = event.get("data", {})
        tool_name = str(data.get("tool", "unknown"))
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        if not data.get("ok", False):
            failed_tool_calls += 1
        if data.get("tool") == "recover_errors":
            for item in (data.get("metadata") or {}).get("recoveries", []):
                category = str(item.get("category", "unknown_failure"))
                if category not in failure_categories:
                    failure_categories.append(category)
    return {
        "tool_calls": tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "tool_counts": tool_counts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "failure_categories": failure_categories,
    }


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    input_cost_per_million = 3.0
    output_cost_per_million = 15.0
    return (
        (input_tokens / 1_000_000) * input_cost_per_million
        + (output_tokens / 1_000_000) * output_cost_per_million
    )


def summarize_results(label: str, results: list[EvalResult]) -> EvalRunSummary:
    total = len(results)
    passed = sum(1 for item in results if item.success)
    tool_counts = merge_tool_counts(results)
    failure_categories = sorted({
        category
        for item in results
        for category in item.failure_categories
    })
    return EvalRunSummary(
        label=label,
        mode=results[0].mode if results else "scripted",
        memory_enabled=results[0].memory_enabled if results else False,
        context_enabled=results[0].context_enabled if results else False,
        retrieval_enabled=results[0].retrieval_enabled if results else False,
        task_count=total,
        passed=passed,
        success_rate=(passed / total) if total else 0.0,
        average_tool_calls=(
            sum(item.tool_calls for item in results) / total
            if total else 0.0
        ),
        average_context_pack_calls=(tool_counts.get("context_pack", 0) / total if total else 0.0),
        average_read_file_calls=(tool_counts.get("read_file", 0) / total if total else 0.0),
        average_duration=(
            sum(item.duration_seconds for item in results) / total
            if total else 0.0
        ),
        total_input_tokens=sum(item.input_tokens for item in results),
        total_output_tokens=sum(item.output_tokens for item in results),
        estimated_cost_usd=sum(item.estimated_cost_usd for item in results),
        tool_counts=tool_counts,
        failure_categories=failure_categories,
    )


def merge_tool_counts(results: list[EvalResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        for tool_name, count in result.tool_counts.items():
            counts[tool_name] = counts.get(tool_name, 0) + int(count)
    return dict(sorted(counts.items()))


def write_eval_json_report(
    workspace: Path,
    results: list[EvalResult],
    output_path: Path,
) -> None:
    summary = summarize_results("selected", results)
    payload = {
        "workspace": str(workspace),
        "summary": asdict(summary),
        "tasks": [asdict(item) for item in results],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_eval_comparison_json_report(
    workspace: Path,
    summaries: list[EvalRunSummary],
    output_path: Path,
) -> None:
    payload = {
        "workspace": str(workspace),
        "comparison": [asdict(item) for item in summaries],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_eval_report(workspace: Path, results: list[EvalResult]) -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    total = len(results)
    passed = sum(1 for item in results if item.success)
    mode = results[0].mode if results else "scripted"
    memory_enabled = results[0].memory_enabled if results else True
    context_enabled = results[0].context_enabled if results else True
    retrieval_enabled = results[0].retrieval_enabled if results else True
    success_rate = (passed / total) if total else 0.0
    average_tool_calls = (
        sum(item.tool_calls for item in results) / total
        if total else 0.0
    )
    average_duration = (
        sum(item.duration_seconds for item in results) / total
        if total else 0.0
    )
    total_input_tokens = sum(item.input_tokens for item in results)
    total_output_tokens = sum(item.output_tokens for item in results)
    estimated_cost = sum(item.estimated_cost_usd for item in results)
    tool_counts = merge_tool_counts(results)
    tool_mix_text = _format_tool_mix(tool_counts)
    failure_categories = sorted({
        category
        for item in results
        for category in item.failure_categories
    })
    category_text = ", ".join(failure_categories) if failure_categories else "none"
    selected_categories = sorted({item.category for item in results})
    selected_category_text = ", ".join(selected_categories) if selected_categories else "none"
    rows = "\n".join(
        "| {task_id} | {category} | {status} | {tool_calls} | {failed} | {duration:.2f}s | `{trace}` |".format(
            task_id=item.task_id,
            category=item.category,
            status="pass" if item.success else "fail",
            tool_calls=item.tool_calls,
            failed=item.failed_tool_calls,
            duration=item.duration_seconds,
            trace=item.trace_path,
        )
        for item in results
    )
    notes = _eval_report_notes(mode)
    return f"""# Evaluation Report

Generated: {generated}

Workspace: `{workspace}`

## Summary

- Mode: **{mode}**
- Memory: **{_enabled_text(memory_enabled)}**
- Context compaction: **{_enabled_text(context_enabled)}**
- Context retrieval: **{_enabled_text(retrieval_enabled)}**
- Categories: **{selected_category_text}**
- Tasks: **{total}**
- Passed: **{passed}**
- Success rate: **{success_rate:.2%}**
- Average tool calls: **{average_tool_calls:.2f}**
- Average duration: **{average_duration:.2f}s**
- Input tokens: **{total_input_tokens}**
- Output tokens: **{total_output_tokens}**
- Estimated model cost: **${estimated_cost:.6f}**
- Failure categories observed: **{category_text}**
- Tool-call mix: **{tool_mix_text}**

## Tasks

| Task | Category | Status | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---:|---:|---:|---|
{rows}

## Notes

{notes}
"""


def _eval_report_notes(mode: str) -> str:
    if mode == "agent":
        return (
            "- This report uses the model-driven agent loop against isolated code-maintenance fixtures.\n"
            "- Inspect the per-task JSONL traces to review tool choices, permission decisions, retries, and final verification.\n"
            "- Use `--compare` to run memory/context ablation rows for the selected mode and tasks."
        )
    return (
        "- This benchmark includes deterministic harness checks plus isolated code-maintenance fixtures.\n"
        "- It is now a scripted benchmark with small and multi-file fixtures; use agent mode for real model-driven attempts.\n"
        "- Use `--compare` to run memory/context ablation rows for the selected mode and tasks."
    )


def _format_tool_mix(tool_counts: dict[str, int], limit: int = 8) -> str:
    if not tool_counts:
        return "none"
    ranked = sorted(tool_counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name}={count}" for name, count in ranked[:limit])


def build_eval_comparison_report(workspace: Path, summaries: list[EvalRunSummary]) -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    rows = "\n".join(
        "| {label} | {mode} | {memory} | {context} | {retrieval} | {passed}/{total} | {success_rate:.2%} | {tool_calls:.2f} | {context_pack_calls:.2f} | {read_file_calls:.2f} | {duration:.2f}s | {input_tokens} | {output_tokens} | ${cost:.6f} | {failures} |".format(
            label=item.label,
            mode=item.mode,
            memory=_enabled_text(item.memory_enabled),
            context=_enabled_text(item.context_enabled),
            retrieval=_enabled_text(item.retrieval_enabled),
            passed=item.passed,
            total=item.task_count,
            success_rate=item.success_rate,
            tool_calls=item.average_tool_calls,
            context_pack_calls=item.average_context_pack_calls,
            read_file_calls=item.average_read_file_calls,
            duration=item.average_duration,
            input_tokens=item.total_input_tokens,
            output_tokens=item.total_output_tokens,
            cost=item.estimated_cost_usd,
            failures=", ".join(item.failure_categories) if item.failure_categories else "none",
        )
        for item in summaries
    )
    return f"""# Evaluation Comparison Report

Generated: {generated}

Workspace: `{workspace}`

## Summary

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, and Context Retrieval columns show which supports were enabled for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Passed | Success Rate | Avg Tool Calls | Avg context_pack | Avg read_file | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
{rows}

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode context retrieval controls whether `context_pack` is exposed to the model.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
"""


def _enabled_text(value: bool) -> str:
    return "enabled" if value else "disabled"
