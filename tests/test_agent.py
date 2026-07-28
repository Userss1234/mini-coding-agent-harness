from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.agent import (
    RetrievalPreflightBudget,
    _augment_failed_tool_result,
    _build_preflight_evidence,
    _call_with_retries,
    _compact_on_max_turns,
    _response_usage,
)
from harness.agent import run_agent
from harness.tools import ToolResult, build_registry
from harness.trace import TraceLogger


class FakeBlock:
    def __init__(self, block_type: str, **kwargs):
        self.type = block_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeResponse:
    def __init__(self, stop_reason: str, content: list[FakeBlock]):
        self.stop_reason = stop_reason
        self.content = content
        self.usage = None


class FakeMessages:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[FakeResponse]):
        self.messages = FakeMessages(responses)


def test_call_with_retries_recovers_from_transient_errors(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    attempts = {"count": 0}
    sleeps: list[float] = []

    def flaky_operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("temporary model timeout")
        return "ok"

    result = _call_with_retries(
        flaky_operation,
        trace=trace,
        event_name="model_request_retry",
        max_retries=2,
        base_delay=0.1,
        sleeper=sleeps.append,
    )

    events = [
        json.loads(line)
        for line in trace.path.read_text(encoding="utf-8").splitlines()
    ]

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleeps == [0.1, 0.2]
    assert [event["event"] for event in events] == ["model_request_retry", "model_request_retry"]


def test_call_with_retries_does_not_retry_non_transient_errors(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    attempts = {"count": 0}

    def broken_operation() -> str:
        attempts["count"] += 1
        raise ValueError("bad request")

    with pytest.raises(ValueError):
        _call_with_retries(
            broken_operation,
            trace=trace,
            event_name="model_request_retry",
            max_retries=2,
            base_delay=0,
            sleeper=lambda delay: None,
        )

    assert attempts["count"] == 1
    assert trace.path.exists() is False


def test_call_with_retries_treats_rate_limit_as_transient(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    attempts = {"count": 0}

    def rate_limited_once() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("429 too many requests")
        return "ok"

    result = _call_with_retries(
        rate_limited_once,
        trace=trace,
        event_name="model_request_retry",
        max_retries=2,
        base_delay=0,
        sleeper=lambda delay: None,
    )

    assert result == "ok"
    assert attempts["count"] == 2
    assert "model_request_retry" in trace.path.read_text(encoding="utf-8")


def test_call_with_retries_survives_extended_provider_outage(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    attempts = {"count": 0}
    sleeps: list[float] = []

    def unavailable_four_times() -> str:
        attempts["count"] += 1
        if attempts["count"] <= 4:
            raise RuntimeError("503 service unavailable")
        return "ok"

    result = _call_with_retries(
        unavailable_four_times,
        trace=trace,
        event_name="model_request_retry",
        max_retries=4,
        base_delay=0.5,
        sleeper=sleeps.append,
    )

    events = [
        json.loads(line)
        for line in trace.path.read_text(encoding="utf-8").splitlines()
    ]

    assert result == "ok"
    assert attempts["count"] == 5
    assert sleeps == [0.5, 1.0, 2.0, 4.0]
    assert len(events) == 4
    assert all(event["data"]["max_retries"] == 4 for event in events)


def test_response_usage_extracts_token_counts() -> None:
    class Usage:
        input_tokens = 12
        output_tokens = 5

    class Response:
        usage = Usage()

    assert _response_usage(Response()) == {
        "input_tokens": 12,
        "output_tokens": 5,
    }


def test_failed_tool_result_gets_retry_plan_context(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("old old\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    result = registry.call("edit_file", path="sample.txt", old_text="old", new_text="new")

    content = _augment_failed_tool_result("edit_file", result, registry)

    assert not result.ok
    assert "Automatic retry plan" in content
    assert "read_file -> edit_file" in content
    assert "agent_retry_plan_injected" in trace.path.read_text(encoding="utf-8")


def test_retry_plan_result_is_not_recursively_augmented(tmp_path: Path) -> None:
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    result = ToolResult(False, "retry plan failed")

    content = _augment_failed_tool_result("retry_plan", result, registry)

    assert content == "retry plan failed"


def test_compact_on_max_turns_returns_context_summary(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    registry.call(
        "todo_write",
        todos=[{"task": "Read README", "status": "in_progress"}],
    )
    registry.call("read_file", path="README.md")

    summary = _compact_on_max_turns(registry)

    assert "# Context Summary" in summary
    assert "README.md" in summary
    assert "agent_max_turns_context" in trace.path.read_text(encoding="utf-8")


def test_run_agent_supports_injected_client_tool_loop(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse(
            "tool_use",
            [
                FakeBlock(
                    "tool_use",
                    id="toolu_1",
                    name="todo_write",
                    input={"todos": [{"task": "Read README", "status": "in_progress"}]},
                )
            ],
        ),
        FakeResponse(
            "tool_use",
            [
                FakeBlock(
                    "tool_use",
                    id="toolu_2",
                    name="read_file",
                    input={"path": "README.md"},
                )
            ],
        ),
        FakeResponse("end_turn", [FakeBlock("text", text="Read README.md with read_file.")]),
    ])

    answer = run_agent("inspect README", registry, client=client, model="fake-model")

    assert answer == "Read README.md with read_file."
    assert len(client.messages.calls) == 3
    assert client.messages.calls[0]["model"] == "fake-model"
    assert any(tool["name"] == "read_file" for tool in client.messages.calls[0]["tools"])
    trace_text = trace.path.read_text(encoding="utf-8")
    assert "agent_start" in trace_text
    assert "todo_state" in trace_text
    assert "evidence_check" in trace_text


def test_run_agent_preloads_retrieve_then_read_evidence(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "def invoice_total(items):\n"
        "    return round(sum(item.price for item in items), 2)\n",
        encoding="utf-8",
    )
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse(
            "end_turn",
            [FakeBlock("text", text="Used retrieve_then_read evidence from billing.py.")],
        )
    ])

    answer = run_agent("inspect invoice total rounding", registry, client=client, model="fake-model")

    first_message = client.messages.calls[0]["messages"][0]["content"]
    trace_text = trace.path.read_text(encoding="utf-8")
    assert answer == "Used retrieve_then_read evidence from billing.py."
    assert "Preloaded retrieval evidence from `retrieve_then_read`" in first_message
    assert "invoice_total" in first_message
    assert "billing.py" in first_message
    assert "agent_retrieval_preflight" in trace_text
    events = [json.loads(line) for line in trace_text.splitlines()]
    preflight = next(event for event in events if event["event"] == "agent_retrieval_preflight")
    assert preflight["data"]["injected_chars"] <= 2400
    assert preflight["data"]["budget"]["limit"] == 2
    assert preflight["data"]["budget"]["max_chars"] == 2400


def test_run_agent_preflight_uses_explicit_retrieval_query(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "def invoice_total(items):\n"
        "    return round(sum(item.price for item in items), 2)\n",
        encoding="utf-8",
    )
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse("end_turn", [FakeBlock("text", text="Used billing.py evidence.")])
    ])

    run_agent(
        "Support prompt with workflow memories and broad tool instructions.\n\nTask: inspect invoice total rounding",
        registry,
        client=client,
        model="fake-model",
        retrieval_query="invoice total rounding",
    )

    events = [
        json.loads(line)
        for line in trace.path.read_text(encoding="utf-8").splitlines()
    ]
    preflight = [
        event for event in events
        if event["event"] == "agent_retrieval_preflight"
    ][0]
    assert preflight["data"]["query"] == "invoice total rounding"


def test_run_agent_caps_preflight_evidence_and_records_metrics(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "\n".join(
            f"def invoice_total_{index}(items): return round(sum(items), 2)  # invoice total rounding"
            for index in range(120)
        ),
        encoding="utf-8",
    )
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse("end_turn", [FakeBlock("text", text="Used billing.py evidence.")])
    ])

    run_agent(
        "inspect invoice total rounding",
        registry,
        client=client,
        model="fake-model",
        retrieval_preflight_budget=RetrievalPreflightBudget(
            limit=2,
            chunk_lines=30,
            read_window=4,
            max_chars_per_read=1000,
            max_chars=500,
        ),
    )

    events = [
        json.loads(line)
        for line in trace.path.read_text(encoding="utf-8").splitlines()
    ]
    preflight = next(event for event in events if event["event"] == "agent_retrieval_preflight")
    first_message = client.messages.calls[0]["messages"][0]["content"]
    assert preflight["data"]["raw_evidence_chars"] > 500
    assert preflight["data"]["injected_chars"] <= 500
    assert preflight["data"]["truncated"] is True
    assert preflight["data"]["merged_read_count"] >= 1
    assert "... [evidence truncated]" in first_message


def test_retrieval_preflight_budget_reads_bounded_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RETRIEVAL_PREFLIGHT_LIMIT", "5")
    monkeypatch.setenv("AGENT_RETRIEVAL_PREFLIGHT_CHUNK_LINES", "64")
    monkeypatch.setenv("AGENT_RETRIEVAL_PREFLIGHT_READ_WINDOW", "12")
    monkeypatch.setenv("AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS_PER_READ", "1800")
    monkeypatch.setenv("AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS", "3200")

    budget = RetrievalPreflightBudget.from_env()

    assert budget == RetrievalPreflightBudget(
        limit=5,
        chunk_lines=64,
        read_window=12,
        max_chars_per_read=1800,
        max_chars=3200,
    )


def test_build_preflight_evidence_enforces_total_budget_across_many_reads() -> None:
    metadata = {
        "reads": [
            {
                "ok": True,
                "read_file_args": {
                    "path": f"service_{index}.py",
                    "start_line": 1,
                    "end_line": 20,
                },
                "text": f"def service_{index}():\n" + ("    return 'context'\n" * 30),
            }
            for index in range(5)
        ]
    }

    output, metrics = _build_preflight_evidence(metadata, 700)

    assert len(output) <= 700
    assert metrics["injected_chars"] == len(output)
    assert metrics["raw_evidence_chars"] > len(output)
    assert metrics["omitted_read_count"] >= 1
    assert metrics["truncated"] is True


def test_run_agent_can_disable_retrieval_preflight(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "def invoice_total(items):\n"
        "    return round(sum(item.price for item in items), 2)\n",
        encoding="utf-8",
    )
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse("end_turn", [FakeBlock("text", text="No preload used.")])
    ])

    answer = run_agent(
        "inspect invoice total rounding",
        registry,
        client=client,
        model="fake-model",
        retrieval_preflight=False,
    )

    first_message = client.messages.calls[0]["messages"][0]["content"]
    trace_text = trace.path.read_text(encoding="utf-8")
    assert answer == "No preload used."
    assert "Preloaded retrieval evidence" not in first_message
    assert "agent_retrieval_preflight_skipped" in trace_text


def test_run_agent_injects_retry_plan_after_failed_tool(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("old old\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse(
            "tool_use",
            [
                FakeBlock(
                    "tool_use",
                    id="toolu_1",
                    name="edit_file",
                    input={"path": "sample.txt", "old_text": "old", "new_text": "new"},
                )
            ],
        ),
        FakeResponse("end_turn", [FakeBlock("text", text="Saw retry_plan guidance for edit_file.")]),
    ])

    answer = run_agent("fix sample", registry, client=client, model="fake-model")

    second_call_messages = client.messages.calls[1]["messages"]
    tool_result_message = [
        item for item in second_call_messages if item["role"] == "user"
    ][-1]
    tool_result_content = tool_result_message["content"][0]["content"]
    assert answer == "Saw retry_plan guidance for edit_file."
    assert "Automatic retry plan" in tool_result_content
    assert "read_file -> edit_file" in tool_result_content
    assert "agent_retry_plan_injected" in trace.path.read_text(encoding="utf-8")


def test_run_agent_returns_context_summary_on_max_turns(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    trace = TraceLogger(tmp_path / "trace.jsonl")
    registry = build_registry(tmp_path, trace, allow_write=True)
    client = FakeClient([
        FakeResponse(
            "tool_use",
            [
                FakeBlock(
                    "tool_use",
                    id="toolu_1",
                    name="todo_write",
                    input={"todos": [{"task": "Read README", "status": "in_progress"}]},
                )
            ],
        )
    ])

    answer = run_agent("inspect README", registry, max_turns=1, client=client, model="fake-model")

    assert answer.startswith("Stopped: max_turns reached.")
    assert "Context summary:" in answer
    assert "Read README" in answer
