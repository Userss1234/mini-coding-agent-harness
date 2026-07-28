from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import time
from typing import Any, Callable

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover
    Anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from .tools import ToolRegistry, ToolResult
from .model_clients import create_default_model_client


BASE_SYSTEM_PROMPT = """You are a coding agent operating inside a local repository.
Use tools to inspect files and run checks. Prefer small, evidence-backed steps.
When making claims, mention the source file you inspected.
For multi-step work, your first tool call must be todo_write.
Update todo_write as steps move from pending to in_progress to completed.
Use plain ASCII punctuation and avoid decorative symbols in final answers.
"""

RETRIEVAL_TOOL_NAMES = frozenset({
    "index_workspace",
    "rag_search",
    "rag_explain",
    "retrieve_then_read",
    "context_pack",
})
_SOURCE_SUFFIXES = frozenset({".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs"})
_IGNORED_GATE_PARTS = frozenset({
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "eval_runs",
    "node_modules",
    "skills",
    "tests",
})
_MULTI_FILE_SIGNALS = (
    "multi file",
    "multiple files",
    "cross file",
    "cross module",
    "across modules",
    "across files",
    "repository wide",
    "codebase wide",
)
_DEPENDENCY_SIGNALS = (
    "integration",
    "dependency interaction",
    "configuration precedence",
    "call contract",
    "api contract",
    "registry",
    "plugin discovery",
    "nested package",
)
_DISCOVERY_SIGNALS = (
    "locate the implementation",
    "find the relevant files",
    "unknown file",
    "investigate across",
    "trace through",
)
_EXPLICIT_SOURCE_PATH = re.compile(
    r"(?:^|\s|`)[\w./\\-]+\.(?:py|js|jsx|ts|tsx|java|go|rs)(?:`|\s|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RetrievalPreflightBudget:
    limit: int = 2
    chunk_lines: int = 48
    read_window: int = 8
    max_chars_per_read: int = 1400
    max_chars: int = 2400

    @classmethod
    def from_env(cls) -> "RetrievalPreflightBudget":
        return cls(
            limit=_bounded_env_int("AGENT_RETRIEVAL_PREFLIGHT_LIMIT", 2, 1, 8),
            chunk_lines=_bounded_env_int("AGENT_RETRIEVAL_PREFLIGHT_CHUNK_LINES", 48, 8, 200),
            read_window=_bounded_env_int("AGENT_RETRIEVAL_PREFLIGHT_READ_WINDOW", 8, 0, 100),
            max_chars_per_read=_bounded_env_int(
                "AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS_PER_READ",
                1400,
                200,
                12000,
            ),
            max_chars=_bounded_env_int("AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS", 2400, 400, 24000),
        )


@dataclass(frozen=True)
class RetrievalGateDecision:
    mode: str
    enabled: bool
    score: int
    threshold: int
    reasons: tuple[str, ...]
    candidate_source_files: int


def decide_retrieval_activation(
    query: str,
    workspace: Path,
    mode: str = "on",
    threshold: int | None = None,
) -> RetrievalGateDecision:
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"on", "auto", "off"}:
        raise ValueError(f"Unsupported retrieval mode: {mode}")
    gate_threshold = (
        max(1, min(int(threshold), 10))
        if threshold is not None
        else _bounded_env_int("AGENT_RETRIEVAL_GATE_THRESHOLD", 2, 1, 10)
    )
    candidate_source_files = _count_candidate_source_files(workspace)
    if normalized_mode == "on":
        return RetrievalGateDecision(
            mode="on",
            enabled=True,
            score=gate_threshold,
            threshold=gate_threshold,
            reasons=("forced_on",),
            candidate_source_files=candidate_source_files,
        )
    if normalized_mode == "off":
        return RetrievalGateDecision(
            mode="off",
            enabled=False,
            score=0,
            threshold=gate_threshold,
            reasons=("forced_off",),
            candidate_source_files=candidate_source_files,
        )

    normalized_query = re.sub(r"[_-]+", " ", str(query).lower())
    score = 0
    reasons: list[str] = []
    if any(signal in normalized_query for signal in _MULTI_FILE_SIGNALS):
        score += 2
        reasons.append("multi_file_scope")
    if any(signal in normalized_query for signal in _DEPENDENCY_SIGNALS):
        score += 2
        reasons.append("dependency_or_contract_scope")
    if any(signal in normalized_query for signal in _DISCOVERY_SIGNALS):
        score += 2
        reasons.append("file_discovery_needed")
    if candidate_source_files >= 4:
        score += 1
        reasons.append("broad_workspace")
    if _EXPLICIT_SOURCE_PATH.search(str(query)):
        score = max(score - 1, 0)
        reasons.append("explicit_source_path")
    if not reasons:
        reasons.append("no_complexity_signal")
    return RetrievalGateDecision(
        mode="auto",
        enabled=score >= gate_threshold,
        score=score,
        threshold=gate_threshold,
        reasons=tuple(reasons),
        candidate_source_files=candidate_source_files,
    )


def run_agent(
    prompt: str,
    registry: ToolRegistry,
    max_turns: int = 8,
    max_retries: int = 4,
    client: Any | None = None,
    model: str | None = None,
    retrieval_preflight: bool = True,
    retrieval_query: str | None = None,
    retrieval_preflight_budget: RetrievalPreflightBudget | None = None,
    retrieval_mode: str | None = None,
    retrieval_gate_decision: RetrievalGateDecision | None = None,
) -> str:
    """Run a minimal tool loop against an Anthropic-like client interface."""
    if client is None:
        if load_dotenv:
            load_dotenv()
            parent_env = Path.cwd().parent / ".env"
            if parent_env.exists():
                load_dotenv(parent_env, override=False)
        try:
            client, config = create_default_model_client(Anthropic)
        except RuntimeError as exc:
            return f"Error: {exc}"
        model = model or config.default_model
    model = model or os.getenv("MODEL_ID", "claude-3-5-sonnet-latest")
    preflight_budget = retrieval_preflight_budget or RetrievalPreflightBudget.from_env()
    effective_retrieval_mode = retrieval_mode or ("on" if retrieval_preflight else "off")
    if not retrieval_preflight:
        effective_retrieval_mode = "off"
    gate = retrieval_gate_decision or decide_retrieval_activation(
        retrieval_query or prompt,
        registry.workspace,
        mode=effective_retrieval_mode,
    )
    if not retrieval_preflight and gate.enabled:
        gate = decide_retrieval_activation(
            retrieval_query or prompt,
            registry.workspace,
            mode="off",
        )
    available_retrieval_schemas = len(RETRIEVAL_TOOL_NAMES.intersection(registry.names()))
    retrieval_active = gate.enabled and available_retrieval_schemas > 0
    model_tools = _model_tool_schemas(registry, retrieval_active)
    system_prompt = _build_system_prompt(registry, retrieval_active)
    evidence_terms: set[str] = set()
    registry.trace.log(
        "agent_start",
        prompt=prompt,
        model=model,
        retrieval_mode=gate.mode,
    )
    registry.trace.log(
        "agent_retrieval_gate",
        mode=gate.mode,
        activated=retrieval_active,
        decision_enabled=gate.enabled,
        score=gate.score,
        threshold=gate.threshold,
        reasons=list(gate.reasons),
        candidate_source_files=gate.candidate_source_files,
        exposed_retrieval_schema_count=available_retrieval_schemas if retrieval_active else 0,
        suppressed_retrieval_schema_count=0 if retrieval_active else available_retrieval_schemas,
    )
    preflight = _run_retrieval_preflight(
        retrieval_query or prompt,
        registry,
        enabled=retrieval_active,
        budget=preflight_budget,
    )
    task_prompt = _with_planning_contract(
        prompt,
        registry,
        preflight,
        retrieval_enabled=retrieval_active,
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": task_prompt}]
    if preflight:
        evidence_terms.add("retrieve_then_read")
        evidence_terms.update(preflight.get("paths", []))

    for turn in range(max_turns):
        try:
            response = _call_with_retries(
                lambda: client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=messages,
                    tools=model_tools,
                    max_tokens=4000,
                ),
                trace=registry.trace,
                event_name="model_request_retry",
                max_retries=max_retries,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            registry.trace.log("agent_error", error=error)
            return f"Error: model request failed after retries: {error}"
        messages.append({"role": "assistant", "content": response.content})
        registry.trace.log(
            "agent_response",
            turn=turn,
            stop_reason=response.stop_reason,
            usage=_response_usage(response),
        )

        if response.stop_reason != "tool_use":
            answer = _text_from_blocks(response.content)
            check = _check_answer_evidence(answer, evidence_terms)
            registry.trace.log("evidence_check", **check)
            registry.trace.log("agent_end", todos=registry.todos)
            return answer

        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            result = registry.call(block.name, **block.input)
            evidence_terms.add(block.name)
            if block.name == "read_file" and isinstance(block.input, dict):
                path = block.input.get("path")
                if path:
                    evidence_terms.add(str(path))
            if block.name == "context_pack":
                evidence_terms.add("context_pack")
            if block.name == "retrieve_then_read":
                evidence_terms.add("retrieve_then_read")
                if result.metadata:
                    for item in result.metadata.get("reads", []):
                        args = item.get("read_file_args") or {}
                        path = args.get("path")
                        if path:
                            evidence_terms.add(str(path))
            if block.name == "list_python_files":
                evidence_terms.add("list_python_files")
            if block.name == "run_py_compile":
                evidence_terms.add("run_py_compile")
            if block.name == "todo_write":
                registry.trace.log("todo_state", todos=registry.todos)
            content = _augment_failed_tool_result(block.name, result, registry)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": not result.ok,
            })
        messages.append({"role": "user", "content": tool_results})

    summary = _compact_on_max_turns(registry)
    registry.trace.log("agent_end", todos=registry.todos, stopped="max_turns")
    if summary:
        return f"Stopped: max_turns reached.\n\nContext summary:\n{summary}"
    return "Stopped: max_turns reached."


def _text_from_blocks(blocks: list[Any]) -> str:
    chunks: list[str] = []
    for block in blocks:
        if getattr(block, "type", None) == "text":
            chunks.append(block.text)
    return "\n".join(chunks).strip()


def _build_system_prompt(registry: ToolRegistry, retrieval_enabled: bool = True) -> str:
    prompt = BASE_SYSTEM_PROMPT
    if retrieval_enabled and "retrieve_then_read" in registry.names():
        prompt += "The harness may preload a retrieve_then_read evidence pack before the first model turn; use it as the starting context before broad search.\n"
    if retrieval_enabled and "context_pack" in registry.names():
        prompt += "When the preloaded evidence is insufficient, use retrieve_then_read or context_pack to retrieve likely file snippets before detailed reads.\n"
    return prompt


def _with_planning_contract(
    prompt: str,
    registry: ToolRegistry,
    preflight: dict[str, Any] | None = None,
    retrieval_enabled: bool = True,
) -> str:
    tool_guidance = ""
    if retrieval_enabled and "retrieve_then_read" in registry.names():
        tool_guidance = "using the preloaded retrieve_then_read evidence before broad search, "
    if retrieval_enabled and "context_pack" in registry.names():
        tool_guidance += "using context_pack when you need more retrieval context, and "
    text = (
        "Before doing repository work, call todo_write with a concise plan. "
        f"Then use tools to execute the plan, {tool_guidance}updating todo_write as steps complete. "
        "Finish with a brief evidence-backed summary.\n\n"
        f"Task: {prompt}"
    )
    if preflight:
        text += (
            "\n\nPreloaded retrieval evidence from `retrieve_then_read`:\n"
            f"{preflight['output']}"
        )
    return text


def _run_retrieval_preflight(
    prompt: str,
    registry: ToolRegistry,
    enabled: bool = True,
    budget: RetrievalPreflightBudget | None = None,
) -> dict[str, Any] | None:
    budget = budget or RetrievalPreflightBudget.from_env()
    if not enabled or "retrieve_then_read" not in registry.names():
        registry.trace.log(
            "agent_retrieval_preflight_skipped",
            enabled=enabled,
            reason="disabled" if not enabled else "tool_unavailable",
        )
        return None

    result = registry.call(
        "retrieve_then_read",
        query=prompt,
        glob="*.py,*.md,*.txt,*.toml,*.json",
        limit=budget.limit,
        chunk_lines=budget.chunk_lines,
        read_window=budget.read_window,
        max_chars_per_read=budget.max_chars_per_read,
    )
    metadata = result.metadata or {}
    output, evidence_metrics = _build_preflight_evidence(metadata, budget.max_chars)
    paths = evidence_metrics["injected_paths"]
    registry.trace.log(
        "agent_retrieval_preflight",
        ok=result.ok,
        query=prompt,
        read_count=len(paths),
        paths=paths,
        matched_chunk_count=metadata.get("matched_chunk_count", 0),
        planned_read_count=metadata.get("count", 0),
        merged_read_count=metadata.get("merged_read_count", 0),
        raw_output_chars=len(result.output),
        raw_evidence_chars=evidence_metrics["raw_evidence_chars"],
        injected_chars=evidence_metrics["injected_chars"],
        duplicate_read_count=evidence_metrics["duplicate_read_count"],
        omitted_read_count=evidence_metrics["omitted_read_count"],
        truncated=evidence_metrics["truncated"],
        budget={
            "limit": budget.limit,
            "chunk_lines": budget.chunk_lines,
            "read_window": budget.read_window,
            "max_chars_per_read": budget.max_chars_per_read,
            "max_chars": budget.max_chars,
        },
    )
    if not result.ok or not output:
        return None
    return {
        "ok": result.ok,
        "output": output,
        "paths": paths,
        "metrics": evidence_metrics,
    }


def _build_preflight_evidence(
    metadata: dict[str, Any],
    max_chars: int,
) -> tuple[str, dict[str, Any]]:
    char_budget = max(int(max_chars), 400)
    sections: list[str] = []
    injected_paths: list[str] = []
    fingerprints: set[tuple[str, str]] = set()
    duplicate_read_count = 0
    readable_items = [
        item
        for item in metadata.get("reads", [])
        if item.get("ok") and str(item.get("text", "")).strip()
    ]
    raw_evidence_chars = sum(len(str(item.get("text", "")).strip()) for item in readable_items)
    truncated = False
    budget_exhausted = False

    for item in readable_items:
        args = item.get("read_file_args") or {}
        path = str(args.get("path", "")).strip()
        text = str(item.get("text", "")).strip()
        if not path or not text:
            continue
        fingerprint = (path, text)
        if fingerprint in fingerprints:
            duplicate_read_count += 1
            continue
        fingerprints.add(fingerprint)
        if budget_exhausted:
            truncated = True
            continue

        header = (
            f"`{path}` lines {args.get('start_line', 1)}-"
            f"{args.get('end_line', args.get('start_line', 1))}"
        )
        current_chars = len("\n\n".join(sections))
        separator_chars = 2 if sections else 0
        available = char_budget - current_chars - separator_chars
        marker = "\n... [evidence truncated]"
        minimum_section_chars = len(header) + 1 + len(marker)
        if available < minimum_section_chars:
            truncated = True
            budget_exhausted = True
            continue
        section = f"{header}\n{text}"
        if len(section) > available:
            keep = max(available - len(header) - len(marker) - 1, 0)
            section = f"{header}\n{text[:keep].rstrip()}{marker}"
            truncated = True
            budget_exhausted = True
        sections.append(section)
        injected_paths.append(path)

    output = "\n\n".join(sections)
    return output, {
        "raw_evidence_chars": raw_evidence_chars,
        "injected_chars": len(output),
        "injected_paths": injected_paths,
        "duplicate_read_count": duplicate_read_count,
        "omitted_read_count": max(len(readable_items) - len(sections) - duplicate_read_count, 0),
        "truncated": truncated,
    }


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _model_tool_schemas(
    registry: ToolRegistry,
    retrieval_enabled: bool,
) -> list[dict[str, Any]]:
    schemas = registry.schemas()
    if retrieval_enabled:
        return schemas
    return [
        schema
        for schema in schemas
        if str(schema.get("name", "")) not in RETRIEVAL_TOOL_NAMES
    ]


def _count_candidate_source_files(workspace: Path, limit: int = 50) -> int:
    count = 0
    try:
        paths = workspace.rglob("*")
        for path in paths:
            try:
                relative = path.relative_to(workspace)
                if any(part in _IGNORED_GATE_PARTS for part in relative.parts):
                    continue
                if not path.is_file() or path.suffix.lower() not in _SOURCE_SUFFIXES:
                    continue
            except OSError:
                continue
            count += 1
            if count >= limit:
                return limit
    except OSError:
        return count
    return count


def _check_answer_evidence(answer: str, evidence_terms: set[str]) -> dict[str, Any]:
    normalized = answer.lower()
    matched = sorted(term for term in evidence_terms if term.lower() in normalized)
    return {
        "ok": bool(matched),
        "matched_terms": matched,
        "available_terms": sorted(evidence_terms),
    }


def _augment_failed_tool_result(
    tool_name: str,
    result: ToolResult,
    registry: ToolRegistry,
) -> str:
    if result.ok or tool_name == "retry_plan" or "retry_plan" not in registry.names():
        return result.output

    plan = registry.call("retry_plan", max_items=3)
    if not plan.ok:
        return result.output

    registry.trace.log("agent_retry_plan_injected", failed_tool=tool_name)
    return f"{result.output}\n\nAutomatic retry plan:\n{plan.output}"


def _compact_on_max_turns(registry: ToolRegistry) -> str:
    if "compact_context" not in registry.names():
        return ""
    result = registry.call("compact_context", max_items=10)
    if not result.ok:
        return ""
    registry.trace.log("agent_max_turns_context", chars=len(result.output))
    return result.output


def _response_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


def _call_with_retries(
    operation: Callable[[], Any],
    trace: Any,
    event_name: str,
    max_retries: int = 4,
    base_delay: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> Any:
    attempt = 0
    while True:
        try:
            return operation()
        except Exception as exc:
            if attempt >= max_retries or not _is_transient_exception(exc):
                raise
            delay = base_delay * (2 ** attempt)
            trace.log(
                event_name,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay_seconds=delay,
                error=f"{type(exc).__name__}: {exc}",
            )
            sleeper(delay)
            attempt += 1


def _is_transient_exception(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    transient_markers = [
        "timeout",
        "temporarily",
        "connection",
        "too many requests",
        "rate limit",
        "ratelimit",
        "429",
        "overloaded",
        "service unavailable",
        "502",
        "503",
        "504",
    ]
    return any(marker in name or marker in text for marker in transient_markers)
