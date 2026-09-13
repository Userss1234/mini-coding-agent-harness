from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .eval_tasks import (
    EvalTask,
    default_tasks,
)
from .eval_tasks import (
    run_rag_symbol_retrieval_task as run_rag_symbol_retrieval_task,
)
from .tools import ToolRegistry, build_registry
from .trace import TraceLogger


@dataclass
class EvalResult:
    task_id: str
    category: str
    description: str
    mode: str
    memory_enabled: bool
    context_enabled: bool
    retrieval_enabled: bool
    retrieval_mode: str
    retrieval_backend: str
    retrieval_gate_evaluated: bool
    retrieval_activated: bool
    retrieval_schema_count: int
    success: bool
    duration_seconds: float
    tool_calls: int
    failed_tool_calls: int
    tool_counts: dict[str, int]
    input_tokens: int
    output_tokens: int
    preflight_raw_chars: int
    preflight_injected_chars: int
    retrieval_cache_hits: int
    retrieval_cache_misses: int
    retrieval_cache_writes: int
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
    retrieval_mode: str
    retrieval_backend: str
    retrieval_gate_decisions: int
    retrieval_activations: int
    retrieval_activation_rate: float
    average_retrieval_schema_count: float
    task_count: int
    passed: int
    success_rate: float
    average_tool_calls: float
    average_retrieve_then_read_calls: float
    average_context_pack_calls: float
    average_read_file_calls: float
    average_duration: float
    total_input_tokens: int
    total_output_tokens: int
    average_preflight_raw_chars: float
    average_preflight_injected_chars: float
    retrieval_cache_hits: int
    retrieval_cache_misses: int
    retrieval_cache_writes: int
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
    retrieval_mode: str | None = None,
    retrieval_backend: str = "lexical",
    compare: bool = False,
    compare_retrieval: bool = False,
    retrieval_compare_order: str = "selected-first",
    compare_retrieval_backends: bool = False,
    retrieval_backend_compare_order: str = "lexical-first",
    json_output_path: Path | None = None,
) -> str:
    """Run a small deterministic benchmark and write a Markdown report."""
    if mode not in {"scripted", "agent"}:
        raise ValueError(f"Unsupported evaluation mode: {mode}")
    normalized_retrieval_mode = _normalize_retrieval_mode(
        retrieval_enabled,
        retrieval_mode,
    )
    retrieval_enabled = normalized_retrieval_mode != "off"
    normalized_retrieval_backend = _normalize_retrieval_backend(retrieval_backend)

    workspace = workspace.resolve()
    trace_dir = trace_dir.resolve()
    trace_dir.mkdir(parents=True, exist_ok=True)

    tasks = select_tasks(default_tasks(), task_ids=task_ids, categories=categories)
    comparison_count = sum(bool(value) for value in (
        compare,
        compare_retrieval,
        compare_retrieval_backends,
    ))
    if comparison_count > 1:
        raise ValueError(
            "Use only one of compare, compare_retrieval, or "
            "compare_retrieval_backends."
        )
    if compare:
        report = run_evaluation_comparison(
            workspace,
            trace_dir,
            tasks,
            mode,
            retrieval_enabled=retrieval_enabled,
            retrieval_mode=normalized_retrieval_mode,
            retrieval_backend=normalized_retrieval_backend,
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
            active_retrieval_mode=normalized_retrieval_mode,
            retrieval_backend=normalized_retrieval_backend,
            execution_order=retrieval_compare_order,
            json_output_path=json_output_path,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return report
    if compare_retrieval_backends:
        if not retrieval_enabled:
            raise ValueError(
                "Retrieval backend comparison requires retrieval mode on or auto."
            )
        report = run_retrieval_backend_comparison(
            workspace,
            trace_dir,
            tasks,
            mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_mode=normalized_retrieval_mode,
            execution_order=retrieval_backend_compare_order,
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
        retrieval_mode=normalized_retrieval_mode,
        retrieval_backend=normalized_retrieval_backend,
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
    retrieval_mode: str | None = None,
    retrieval_backend: str = "lexical",
) -> list[EvalResult]:
    normalized_retrieval_mode = _normalize_retrieval_mode(
        retrieval_enabled,
        retrieval_mode,
    )
    retrieval_enabled = normalized_retrieval_mode != "off"
    normalized_retrieval_backend = _normalize_retrieval_backend(retrieval_backend)
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
            retrieval_mode=normalized_retrieval_mode,
            retrieval_backend=normalized_retrieval_backend,
            allow_write=True,
        )
        registry = build_registry(
            task_workspace,
            trace,
            allow_write=True,
            enable_context_pack=retrieval_enabled if mode == "agent" else True,
            retrieval_backend=normalized_retrieval_backend,
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
                    retrieval_mode=normalized_retrieval_mode,
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
            retrieval_mode=normalized_retrieval_mode,
            retrieval_backend=normalized_retrieval_backend,
            retrieval_gate_evaluated=metrics["retrieval_gate_evaluated"],
            retrieval_activated=metrics["retrieval_activated"],
            retrieval_schema_count=metrics["retrieval_schema_count"],
            success=success,
            duration_seconds=duration,
            tool_calls=metrics["tool_calls"],
            failed_tool_calls=metrics["failed_tool_calls"],
            tool_counts=metrics["tool_counts"],
            input_tokens=metrics["input_tokens"],
            output_tokens=metrics["output_tokens"],
            preflight_raw_chars=metrics["preflight_raw_chars"],
            preflight_injected_chars=metrics["preflight_injected_chars"],
            retrieval_cache_hits=metrics["retrieval_cache_hits"],
            retrieval_cache_misses=metrics["retrieval_cache_misses"],
            retrieval_cache_writes=metrics["retrieval_cache_writes"],
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
    retrieval_mode: str | None = None,
    retrieval_backend: str = "lexical",
    json_output_path: Path | None = None,
) -> str:
    summaries: list[EvalRunSummary] = []
    results_by_label: dict[str, list[EvalResult]] = {}
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
            retrieval_mode=retrieval_mode,
            retrieval_backend=retrieval_backend,
        )
        results_by_label[label] = results
        summaries.append(summarize_results(label, results))
    if json_output_path is not None:
        write_eval_comparison_json_report(
            workspace,
            summaries,
            json_output_path,
            results_by_label=results_by_label,
        )
    return build_eval_comparison_report(workspace, summaries)


def run_retrieval_comparison(
    workspace: Path,
    trace_dir: Path,
    tasks: list[EvalTask],
    mode: str,
    memory_enabled: bool,
    context_enabled: bool,
    active_retrieval_mode: str = "on",
    retrieval_backend: str = "lexical",
    execution_order: str = "selected-first",
    json_output_path: Path | None = None,
) -> str:
    summaries: list[EvalRunSummary] = []
    results_by_label: dict[str, list[EvalResult]] = {}
    comparison_mode = (
        active_retrieval_mode
        if active_retrieval_mode in {"on", "auto"}
        else "on"
    )
    if execution_order not in {"selected-first", "off-first"}:
        raise ValueError(f"Unsupported retrieval comparison order: {execution_order}")
    retrieval_modes = (
        [comparison_mode, "off"]
        if execution_order == "selected-first"
        else ["off", comparison_mode]
    )
    for current_retrieval_mode in retrieval_modes:
        retrieval_enabled = current_retrieval_mode != "off"
        label = f"retrieval-{current_retrieval_mode}"
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
            retrieval_mode=current_retrieval_mode,
            retrieval_backend=retrieval_backend,
        )
        results_by_label[label] = results
        summaries.append(summarize_results(label, results))
    if json_output_path is not None:
        write_eval_comparison_json_report(
            workspace,
            summaries,
            json_output_path,
            comparison_kind="retrieval",
            execution_order=[summary.label for summary in summaries],
            selected_retrieval_mode=comparison_mode,
            results_by_label=results_by_label,
        )
    return build_eval_comparison_report(workspace, summaries)


def run_retrieval_backend_comparison(
    workspace: Path,
    trace_dir: Path,
    tasks: list[EvalTask],
    mode: str,
    memory_enabled: bool,
    context_enabled: bool,
    retrieval_mode: str = "on",
    execution_order: str = "lexical-first",
    json_output_path: Path | None = None,
) -> str:
    if execution_order not in {"lexical-first", "hybrid-first"}:
        raise ValueError(
            f"Unsupported retrieval backend comparison order: {execution_order}"
        )
    backends = (
        ["lexical", "hybrid"]
        if execution_order == "lexical-first"
        else ["hybrid", "lexical"]
    )
    summaries: list[EvalRunSummary] = []
    results_by_label: dict[str, list[EvalResult]] = {}
    for backend in backends:
        label = f"retrieval-{backend}"
        config_trace_dir = trace_dir / "compare_retrieval_backend" / label
        config_trace_dir.mkdir(parents=True, exist_ok=True)
        results = run_eval_tasks(
            workspace=workspace,
            trace_dir=config_trace_dir,
            tasks=tasks,
            mode=mode,
            memory_enabled=memory_enabled,
            context_enabled=context_enabled,
            retrieval_enabled=True,
            retrieval_mode=retrieval_mode,
            retrieval_backend=backend,
        )
        results_by_label[label] = results
        summaries.append(summarize_results(label, results))
    if json_output_path is not None:
        write_eval_comparison_json_report(
            workspace,
            summaries,
            json_output_path,
            comparison_kind="retrieval_backend",
            execution_order=[summary.label for summary in summaries],
            results_by_label=results_by_label,
        )
    return build_retrieval_backend_comparison_report(
        workspace,
        summaries,
        results_by_label,
    )


def eval_config_label(memory_enabled: bool, context_enabled: bool) -> str:
    memory = "memory-on" if memory_enabled else "memory-off"
    context = "context-on" if context_enabled else "context-off"
    return f"{memory}_{context}"


def _normalize_retrieval_mode(
    retrieval_enabled: bool,
    retrieval_mode: str | None,
) -> str:
    if not retrieval_enabled:
        return "off"
    mode = "on" if retrieval_mode is None else str(retrieval_mode).strip().lower()
    if mode not in {"on", "auto", "off"}:
        raise ValueError(f"Unsupported retrieval mode: {retrieval_mode}")
    return mode


def _normalize_retrieval_backend(retrieval_backend: str | None) -> str:
    backend = "lexical" if retrieval_backend is None else str(retrieval_backend).strip().lower()
    if backend not in {"lexical", "hybrid"}:
        raise ValueError(f"Unsupported retrieval backend: {retrieval_backend}")
    return backend


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


def run_agent_eval_task(
    task: EvalTask,
    registry: ToolRegistry,
    memory_enabled: bool,
    context_enabled: bool,
    retrieval_enabled: bool,
    retrieval_mode: str = "on",
) -> bool:
    """Ask the model-driven loop to solve one task, then verify without scripted edits."""
    if task.verifier is None:
        registry.trace.log("eval_agent_unsupported", task=task.task_id)
        return False

    from .agent import decide_retrieval_activation, run_agent

    retrieval_query = f"{task.task_id}: {task.description}"
    gate = decide_retrieval_activation(
        retrieval_query,
        registry.workspace,
        mode=retrieval_mode,
    )
    retrieval_active = (
        gate.enabled
        and retrieval_enabled
        and "retrieve_then_read" in registry.names()
    )
    support_prompt = build_agent_support_prompt(
        registry,
        memory_enabled,
        context_enabled,
        retrieval_enabled,
        retrieval_mode,
        retrieval_active=retrieval_active,
        memory_query=task.description,
    )
    prompt = build_agent_eval_prompt(task, support_prompt)
    answer = run_agent(
        prompt,
        registry,
        max_turns=_agent_eval_max_turns(),
        retrieval_query=retrieval_query,
        retrieval_mode=retrieval_mode,
        retrieval_gate_decision=gate,
    )
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
    if task.task_id == "context_compaction":
        task_hints.append(
            "For this trace task, call `todo_write`, then `read_file` on `README.md`, then `compact_context`; "
            "finish after the compacted summary mentions `README.md`."
        )
    if task.task_id == "readme_update":
        task_hints.append(
            "For this documentation task, do not inspect tests, shell, Git, or memories after reading `README.md`; "
            "replace exactly `Usage: TODO` with `Usage: run python -m pytest.` and reread `README.md`."
        )
    if task.task_id == "semantic_retry_plan":
        task_hints.append(
            "For this recovery task, call `edit_file` on `sample.txt` with `old_text=\"old\"` first; "
            "the snippet appears more than once, so the failure should be classified as `edit_match_failed`. "
            "Then call `retry_plan` and finish with the ordered plan."
        )
    if task.task_id == "error_recovery":
        task_hints.append(
            "For this recovery task, do not explore with shell, Git, list_python_files, or path probes. "
            "First call `edit_file` on `sample.txt` with `old_text=\"old\"` and `new_text=\"new\"`; "
            "the snippet appears more than once, so the edit must fail as `edit_match_failed`. "
            "Then call `recover_errors` and finish once the recovery report includes `edit_match_failed`."
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
        "2. Prefer `retrieve_then_read`, `read_file`, `grep`, `context_pack`, `write_file`, `edit_file`, and `run_tests` for fixture tasks.\n"
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
    retrieval_mode: str = "on",
    retrieval_active: bool | None = None,
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
    active = retrieval_enabled if retrieval_active is None else retrieval_active
    if active and "retrieve_then_read" in registry.names():
        parts.append(
            "Retrieval support is enabled; the agent loop preloads a retrieve_then_read evidence pack before the first model turn. "
            "Use that evidence before broad file reads, and call retrieve_then_read or context_pack again only when more retrieval context is needed."
        )
    else:
        parts.append("Retrieval support is disabled for this evaluation run; use grep, list_python_files, and read_file directly.")
    return "\n\n".join(parts)


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
    preflight_raw_chars = 0
    preflight_injected_chars = 0
    retrieval_gate_evaluated = False
    retrieval_activated = False
    retrieval_schema_count = 0
    retrieval_cache_hits = 0
    retrieval_cache_misses = 0
    retrieval_cache_writes = 0
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
        if event_name == "agent_retrieval_gate":
            data = event.get("data") or {}
            retrieval_gate_evaluated = True
            retrieval_activated = bool(data.get("activated", False))
            retrieval_schema_count = int(data.get("exposed_retrieval_schema_count", 0) or 0)
            continue
        if event_name == "agent_retrieval_preflight":
            data = event.get("data") or {}
            preflight_raw_chars += int(data.get("raw_evidence_chars", 0) or 0)
            preflight_injected_chars += int(data.get("injected_chars", 0) or 0)
            continue
        if event_name == "agent_error":
            if "model_request_failed" not in failure_categories:
                failure_categories.append("model_request_failed")
            continue
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
        hybrid = (data.get("metadata") or {}).get("hybrid") or {}
        cache = hybrid.get("cache") or {}
        retrieval_cache_hits += int(cache.get("hits", 0) or 0)
        retrieval_cache_misses += int(cache.get("misses", 0) or 0)
        retrieval_cache_writes += int(bool(cache.get("written", False)))
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
        "preflight_raw_chars": preflight_raw_chars,
        "preflight_injected_chars": preflight_injected_chars,
        "retrieval_gate_evaluated": retrieval_gate_evaluated,
        "retrieval_activated": retrieval_activated,
        "retrieval_schema_count": retrieval_schema_count,
        "retrieval_cache_hits": retrieval_cache_hits,
        "retrieval_cache_misses": retrieval_cache_misses,
        "retrieval_cache_writes": retrieval_cache_writes,
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
    retrieval_gate_decisions = sum(
        1 for item in results if item.retrieval_gate_evaluated
    )
    retrieval_activations = sum(
        1 for item in results if item.retrieval_activated
    )
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
        retrieval_mode=results[0].retrieval_mode if results else "off",
        retrieval_backend=results[0].retrieval_backend if results else "lexical",
        retrieval_gate_decisions=retrieval_gate_decisions,
        retrieval_activations=retrieval_activations,
        retrieval_activation_rate=(
            retrieval_activations / retrieval_gate_decisions
            if retrieval_gate_decisions else 0.0
        ),
        average_retrieval_schema_count=(
            sum(item.retrieval_schema_count for item in results) / total
            if total else 0.0
        ),
        task_count=total,
        passed=passed,
        success_rate=(passed / total) if total else 0.0,
        average_tool_calls=(
            sum(item.tool_calls for item in results) / total
            if total else 0.0
        ),
        average_retrieve_then_read_calls=(tool_counts.get("retrieve_then_read", 0) / total if total else 0.0),
        average_context_pack_calls=(tool_counts.get("context_pack", 0) / total if total else 0.0),
        average_read_file_calls=(tool_counts.get("read_file", 0) / total if total else 0.0),
        average_duration=(
            sum(item.duration_seconds for item in results) / total
            if total else 0.0
        ),
        total_input_tokens=sum(item.input_tokens for item in results),
        total_output_tokens=sum(item.output_tokens for item in results),
        average_preflight_raw_chars=(
            sum(item.preflight_raw_chars for item in results) / total
            if total else 0.0
        ),
        average_preflight_injected_chars=(
            sum(item.preflight_injected_chars for item in results) / total
            if total else 0.0
        ),
        retrieval_cache_hits=sum(item.retrieval_cache_hits for item in results),
        retrieval_cache_misses=sum(item.retrieval_cache_misses for item in results),
        retrieval_cache_writes=sum(item.retrieval_cache_writes for item in results),
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
    comparison_kind: str | None = None,
    execution_order: list[str] | None = None,
    selected_retrieval_mode: str | None = None,
    results_by_label: Mapping[str, list[EvalResult]] | None = None,
) -> None:
    payload = {
        "schema_version": 2,
        "workspace": str(workspace),
        "comparison": [asdict(item) for item in summaries],
    }
    if comparison_kind is not None:
        payload["comparison_kind"] = comparison_kind
    if execution_order is not None:
        payload["execution_order"] = execution_order
    if selected_retrieval_mode is not None:
        payload["selected_retrieval_mode"] = selected_retrieval_mode
    if results_by_label is not None:
        payload["task_results"] = {
            label: [asdict(item) for item in results]
            for label, results in results_by_label.items()
        }
    if comparison_kind == "retrieval" and results_by_label is not None:
        selected_label = f"retrieval-{selected_retrieval_mode or 'on'}"
        payload["paired_tasks"] = build_retrieval_task_pairs(
            results_by_label,
            selected_label=selected_label,
            off_label="retrieval-off",
        )
    if comparison_kind == "retrieval_backend" and results_by_label is not None:
        payload["paired_tasks"] = build_retrieval_backend_task_pairs(
            results_by_label
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_retrieval_task_pairs(
    results_by_label: Mapping[str, list[EvalResult]],
    *,
    selected_label: str,
    off_label: str,
) -> list[dict[str, Any]]:
    selected_results = {
        item.task_id: item for item in results_by_label.get(selected_label, [])
    }
    off_results = {
        item.task_id: item for item in results_by_label.get(off_label, [])
    }
    task_ids = sorted(set(selected_results) | set(off_results))
    pairs: list[dict[str, Any]] = []
    for task_id in task_ids:
        selected = selected_results.get(task_id)
        off = off_results.get(task_id)
        selected_metrics = _retrieval_task_metrics(selected)
        off_metrics = _retrieval_task_metrics(off)
        pairs.append({
            "task_id": task_id,
            "selected_label": selected_label,
            "off_label": off_label,
            "selected": selected_metrics,
            "off": off_metrics,
            "deltas": _retrieval_task_deltas(selected_metrics, off_metrics),
        })
    return pairs


def build_retrieval_backend_task_pairs(
    results_by_label: Mapping[str, list[EvalResult]],
) -> list[dict[str, Any]]:
    lexical_label = "retrieval-lexical"
    hybrid_label = "retrieval-hybrid"
    lexical_results = {
        item.task_id: item for item in results_by_label.get(lexical_label, [])
    }
    hybrid_results = {
        item.task_id: item for item in results_by_label.get(hybrid_label, [])
    }
    task_ids = sorted(set(lexical_results) | set(hybrid_results))
    pairs: list[dict[str, Any]] = []
    for task_id in task_ids:
        lexical = _retrieval_task_metrics(lexical_results.get(task_id))
        hybrid = _retrieval_task_metrics(hybrid_results.get(task_id))
        pairs.append({
            "task_id": task_id,
            "lexical_label": lexical_label,
            "hybrid_label": hybrid_label,
            "lexical": lexical,
            "hybrid": hybrid,
            "deltas": _retrieval_task_deltas(hybrid, lexical),
        })
    return pairs


def _retrieval_task_metrics(result: EvalResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "success": result.success,
        "retrieval_backend": result.retrieval_backend,
        "retrieval_activated": result.retrieval_activated,
        "retrieval_schema_count": result.retrieval_schema_count,
        "tool_calls": result.tool_calls,
        "read_file_calls": int(result.tool_counts.get("read_file", 0)),
        "retrieve_then_read_calls": int(result.tool_counts.get("retrieve_then_read", 0)),
        "context_pack_calls": int(result.tool_counts.get("context_pack", 0)),
        "duration_seconds": result.duration_seconds,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "estimated_cost_usd": result.estimated_cost_usd,
        "retrieval_cache_hits": result.retrieval_cache_hits,
        "retrieval_cache_misses": result.retrieval_cache_misses,
        "retrieval_cache_writes": result.retrieval_cache_writes,
        "trace_path": result.trace_path,
    }


def _retrieval_task_deltas(
    selected: Mapping[str, Any] | None,
    off: Mapping[str, Any] | None,
) -> dict[str, float] | None:
    if selected is None or off is None:
        return None
    metrics = [
        "tool_calls",
        "read_file_calls",
        "retrieve_then_read_calls",
        "context_pack_calls",
        "duration_seconds",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "retrieval_cache_hits",
        "retrieval_cache_misses",
        "retrieval_cache_writes",
    ]
    return {
        metric: float(selected.get(metric, 0) or 0) - float(off.get(metric, 0) or 0)
        for metric in metrics
    }


def build_eval_report(workspace: Path, results: list[EvalResult]) -> str:
    generated = datetime.now().isoformat(timespec="seconds")
    total = len(results)
    passed = sum(1 for item in results if item.success)
    mode = results[0].mode if results else "scripted"
    memory_enabled = results[0].memory_enabled if results else True
    context_enabled = results[0].context_enabled if results else True
    retrieval_enabled = results[0].retrieval_enabled if results else True
    retrieval_mode = results[0].retrieval_mode if results else "off"
    retrieval_backend = results[0].retrieval_backend if results else "lexical"
    retrieval_gate_decisions = sum(
        1 for item in results if item.retrieval_gate_evaluated
    )
    retrieval_activations = sum(
        1 for item in results if item.retrieval_activated
    )
    retrieval_activation_rate = (
        retrieval_activations / retrieval_gate_decisions
        if retrieval_gate_decisions else 0.0
    )
    average_retrieval_schema_count = (
        sum(item.retrieval_schema_count for item in results) / total
        if total else 0.0
    )
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
    average_preflight_raw_chars = (
        sum(item.preflight_raw_chars for item in results) / total
        if total else 0.0
    )
    average_preflight_injected_chars = (
        sum(item.preflight_injected_chars for item in results) / total
        if total else 0.0
    )
    retrieval_cache_hits = sum(item.retrieval_cache_hits for item in results)
    retrieval_cache_misses = sum(item.retrieval_cache_misses for item in results)
    retrieval_cache_writes = sum(item.retrieval_cache_writes for item in results)
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
        "| {task_id} | {category} | {status} | {retrieval_active} | {retrieval_schemas} | {tool_calls} | {failed} | {duration:.2f}s | `{trace}` |".format(
            task_id=item.task_id,
            category=item.category,
            status="pass" if item.success else "fail",
            retrieval_active="yes" if item.retrieval_activated else "no",
            retrieval_schemas=item.retrieval_schema_count,
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
- Retrieval strategy: **{retrieval_mode}**
- Retrieval backend: **{retrieval_backend}**
- Retrieval gate activations: **{retrieval_activations}/{retrieval_gate_decisions} ({retrieval_activation_rate:.2%})**
- Retrieval embedding cache (hits/misses/writes): **{retrieval_cache_hits}/{retrieval_cache_misses}/{retrieval_cache_writes}**
- Average exposed retrieval schemas: **{average_retrieval_schema_count:.2f}**
- Categories: **{selected_category_text}**
- Tasks: **{total}**
- Passed: **{passed}**
- Success rate: **{success_rate:.2%}**
- Average tool calls: **{average_tool_calls:.2f}**
- Average duration: **{average_duration:.2f}s**
- Input tokens: **{total_input_tokens}**
- Output tokens: **{total_output_tokens}**
- Average preflight evidence chars (raw -> injected): **{average_preflight_raw_chars:.2f} -> {average_preflight_injected_chars:.2f}**
- Estimated model cost: **${estimated_cost:.6f}**
- Failure categories observed: **{category_text}**
- Tool-call mix: **{tool_mix_text}**

## Tasks

| Task | Category | Status | Retrieval Active | Retrieval Schemas | Tool Calls | Failed Tool Calls | Duration | Trace |
|---|---|---|---|---:|---:|---:|---:|---|
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
        "| {label} | {mode} | {memory} | {context} | {retrieval} | {retrieval_mode} | {retrieval_backend} | {activations}/{gate_decisions} | {activation_rate:.2%} | {retrieval_schemas:.2f} | {cache_hits}/{cache_misses}/{cache_writes} | {passed}/{total} | {success_rate:.2%} | {tool_calls:.2f} | {retrieve_then_read_calls:.2f} | {context_pack_calls:.2f} | {read_file_calls:.2f} | {preflight_raw_chars:.2f} | {preflight_injected_chars:.2f} | {duration:.2f}s | {input_tokens} | {output_tokens} | ${cost:.6f} | {failures} |".format(
            label=item.label,
            mode=item.mode,
            memory=_enabled_text(item.memory_enabled),
            context=_enabled_text(item.context_enabled),
            retrieval=_enabled_text(item.retrieval_enabled),
            retrieval_mode=item.retrieval_mode,
            retrieval_backend=item.retrieval_backend,
            activations=item.retrieval_activations,
            gate_decisions=item.retrieval_gate_decisions,
            activation_rate=item.retrieval_activation_rate,
            retrieval_schemas=item.average_retrieval_schema_count,
            cache_hits=item.retrieval_cache_hits,
            cache_misses=item.retrieval_cache_misses,
            cache_writes=item.retrieval_cache_writes,
            passed=item.passed,
            total=item.task_count,
            success_rate=item.success_rate,
            tool_calls=item.average_tool_calls,
            retrieve_then_read_calls=item.average_retrieve_then_read_calls,
            context_pack_calls=item.average_context_pack_calls,
            read_file_calls=item.average_read_file_calls,
            preflight_raw_chars=item.average_preflight_raw_chars,
            preflight_injected_chars=item.average_preflight_injected_chars,
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

This report compares selected evaluation configurations on the same task set. The Memory, Context Compaction, Context Retrieval, Retrieval Strategy, and Retrieval Backend columns show the controlled settings for each run.

| Config | Mode | Memory | Context Compaction | Context Retrieval | Retrieval Strategy | Retrieval Backend | Gate Active | Activation Rate | Avg Retrieval Schemas | Cache H/M/W | Passed | Success Rate | Avg Tool Calls | Avg retrieve_then_read | Avg context_pack | Avg read_file | Avg Preflight Raw Chars | Avg Preflight Injected Chars | Avg Duration | Input Tokens | Output Tokens | Est. Cost | Failure Categories |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
{rows}

## Notes

- In scripted mode these switches are reported for comparability, but task logic remains deterministic.
- In agent mode memory changes the task prompt with available workflow memories.
- In agent mode context compaction controls whether the run produces a compact trace summary before final verification.
- In agent mode the retrieval strategy can always expose, conditionally gate, or fully disable retrieval schemas and preflight evidence.
- Cost is estimated from traced model usage with a configurable placeholder rate in the code.
"""


def build_retrieval_backend_comparison_report(
    workspace: Path,
    summaries: list[EvalRunSummary],
    results_by_label: Mapping[str, list[EvalResult]],
) -> str:
    report = build_eval_comparison_report(workspace, summaries).rstrip()
    pairs = build_retrieval_backend_task_pairs(results_by_label)
    rows = []
    for pair in pairs:
        lexical = pair.get("lexical") or {}
        hybrid = pair.get("hybrid") or {}
        deltas = pair.get("deltas") or {}
        rows.append(
            "| {task} | {lexical_status} | {hybrid_status} | {lexical_tools:.0f} | "
            "{hybrid_tools:.0f} | {tool_delta:+.0f} | {lexical_reads:.0f} | "
            "{hybrid_reads:.0f} | {read_delta:+.0f} | {lexical_duration:.2f}s | "
            "{hybrid_duration:.2f}s | {duration_delta:+.2f}s | {cache_hits:.0f}/"
            "{cache_misses:.0f}/{cache_writes:.0f} |".format(
                task=pair["task_id"],
                lexical_status="pass" if lexical.get("success") else "fail",
                hybrid_status="pass" if hybrid.get("success") else "fail",
                lexical_tools=float(lexical.get("tool_calls", 0) or 0),
                hybrid_tools=float(hybrid.get("tool_calls", 0) or 0),
                tool_delta=float(deltas.get("tool_calls", 0) or 0),
                lexical_reads=float(lexical.get("read_file_calls", 0) or 0),
                hybrid_reads=float(hybrid.get("read_file_calls", 0) or 0),
                read_delta=float(deltas.get("read_file_calls", 0) or 0),
                lexical_duration=float(lexical.get("duration_seconds", 0) or 0),
                hybrid_duration=float(hybrid.get("duration_seconds", 0) or 0),
                duration_delta=float(deltas.get("duration_seconds", 0) or 0),
                cache_hits=float(hybrid.get("retrieval_cache_hits", 0) or 0),
                cache_misses=float(hybrid.get("retrieval_cache_misses", 0) or 0),
                cache_writes=float(hybrid.get("retrieval_cache_writes", 0) or 0),
            )
        )
    task_table = "\n".join(rows) or "| (none) | n/a | n/a | 0 | 0 | +0 | 0 | 0 | +0 | 0.00s | 0.00s | +0.00s | 0/0/0 |"
    return f"""{report}

## Paired Task Results

All deltas are hybrid minus lexical. Cache H/M/W is reported for the hybrid side.

| Task | Lexical | Hybrid | Lexical Tools | Hybrid Tools | Delta | Lexical Reads | Hybrid Reads | Delta | Lexical Duration | Hybrid Duration | Delta | Hybrid Cache H/M/W |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{task_table}
"""


def _enabled_text(value: bool) -> str:
    return "enabled" if value else "disabled"
