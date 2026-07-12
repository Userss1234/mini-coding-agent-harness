from __future__ import annotations

import os
from pathlib import Path
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


def run_agent(
    prompt: str,
    registry: ToolRegistry,
    max_turns: int = 8,
    max_retries: int = 2,
    client: Any | None = None,
    model: str | None = None,
    retrieval_preflight: bool = True,
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
    system_prompt = _build_system_prompt(registry)
    evidence_terms: set[str] = set()
    registry.trace.log("agent_start", prompt=prompt, model=model)
    preflight = _run_retrieval_preflight(prompt, registry, enabled=retrieval_preflight)
    task_prompt = _with_planning_contract(prompt, registry, preflight)
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
                    tools=registry.schemas(),
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


def _build_system_prompt(registry: ToolRegistry) -> str:
    prompt = BASE_SYSTEM_PROMPT
    if "retrieve_then_read" in registry.names():
        prompt += "The harness may preload a retrieve_then_read evidence pack before the first model turn; use it as the starting context before broad search.\n"
    if "context_pack" in registry.names():
        prompt += "When the preloaded evidence is insufficient, use retrieve_then_read or context_pack to retrieve likely file snippets before detailed reads.\n"
    return prompt


def _with_planning_contract(
    prompt: str,
    registry: ToolRegistry,
    preflight: dict[str, Any] | None = None,
) -> str:
    tool_guidance = ""
    if "retrieve_then_read" in registry.names():
        tool_guidance = "using the preloaded retrieve_then_read evidence before broad search, "
    if "context_pack" in registry.names():
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
) -> dict[str, Any] | None:
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
        limit=3,
        chunk_lines=80,
        read_window=20,
        max_chars_per_read=4000,
    )
    metadata = result.metadata or {}
    paths = []
    for item in metadata.get("reads", []):
        args = item.get("read_file_args") or {}
        path = args.get("path")
        if path:
            paths.append(str(path))
    registry.trace.log(
        "agent_retrieval_preflight",
        ok=result.ok,
        query=prompt,
        read_count=len(paths),
        paths=paths,
    )
    if not result.ok:
        return None
    return {
        "ok": result.ok,
        "output": result.output,
        "paths": paths,
    }


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
    max_retries: int = 2,
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
