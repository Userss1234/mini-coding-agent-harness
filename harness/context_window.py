from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .run_session import normalize_blocks


class ContextBudgetExceeded(ValueError):
    pass


@dataclass(frozen=True)
class ContextConfig:
    max_input_tokens: int = 24000
    summary_tokens: int = 1800
    keep_recent_turns: int = 2
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_input_tokens < 512 or self.summary_tokens < 256:
            raise ValueError("Context input budget must be >=512 and summary budget >=256")
        if self.summary_tokens >= self.max_input_tokens:
            raise ValueError("Summary budget must be smaller than the context input budget")
        if self.keep_recent_turns < 1:
            raise ValueError("At least one recent complete turn must be retained")


def plain_message(message: dict[str, Any]) -> dict[str, Any]:
    content = message["content"]
    return {"role": message["role"], "content": normalize_blocks(content)
            if isinstance(content, list) else content}


def estimate_input_tokens(
    system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
) -> int:
    """Conservative byte-count estimate, not a provider-specific tokenizer."""
    payload = {"system": system, "tools": tools,
               "messages": [plain_message(message) for message in messages]}
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 32


def complete_groups(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups = []
    index = 0
    while index < len(messages):
        message = plain_message(messages[index])
        blocks = message["content"] if isinstance(message["content"], list) else []
        if message["role"] not in {"assistant", "user"}:
            raise ValueError("Unexpected conversation role")
        if any(block.get("type") == "tool_result" for block in blocks):
            raise ValueError("Orphan tool result in model history")
        calls = [block for block in blocks if block.get("type") == "tool_use"]
        if not calls:
            groups.append([messages[index]])
            index += 1
            continue
        if message["role"] != "assistant" or index + 1 >= len(messages):
            raise ValueError("Incomplete tool-use/result pair")
        response = plain_message(messages[index + 1])
        results = response["content"]
        if response["role"] != "user" or not isinstance(results, list):
            raise ValueError("Tool calls require a user tool-result message")
        call_ids = [call["id"] for call in calls]
        result_ids = [item.get("tool_use_id") for item in results
                      if item.get("type") == "tool_result"]
        if (len(call_ids) != len(set(call_ids)) or len(result_ids) != len(set(result_ids))
                or set(call_ids) != set(result_ids)):
            raise ValueError("Tool-call/result IDs do not match")
        groups.append(messages[index:index + 2])
        index += 2
    return groups


def _excerpt(text: Any, limit: int = 220) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[:limit // 2] + " ...[excerpt]... " + value[-limit // 2:]


class ContextWindow:
    def __init__(self, config: ContextConfig, state: dict[str, Any] | None = None):
        self.config = config
        self.state = state or {"revision": 0, "summary": None, "compacted_groups": 0}

    def prepare(
        self, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]],
        todos: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not messages or messages[0]["role"] != "user":
            raise ValueError("The initial user task must be present")
        offset = 1
        previous = self.state.get("summary")
        if previous:
            if len(messages) < 2 or messages[1] != self._summary_message(previous):
                raise ValueError("Saved summary does not match conversation history")
            offset = 2
        groups = complete_groups(messages[offset:])
        before = estimate_input_tokens(system, tools, messages)
        metrics: dict[str, Any] = {
            "estimator": "utf8_bytes_v1", "enabled": self.config.enabled,
            "budget": self.config.max_input_tokens, "before_estimated_tokens": before,
            "after_estimated_tokens": before, "before_messages": len(messages),
            "after_messages": len(messages), "compacted": False,
            "revision": self.state["revision"], "dropped_groups": 0,
        }
        if not self.config.enabled or before <= self.config.max_input_tokens:
            return messages, metrics
        drop_count = len(groups) - self.config.keep_recent_turns
        if drop_count <= 0:
            raise ContextBudgetExceeded("Initial task, system/tools and protected recent turns exceed budget")

        # Only complete old groups are eligible; no slicing inside a tool batch.
        summary = self._summarize(previous, groups[:drop_count], todos)
        kept = [item for group in groups[drop_count:] for item in group]
        replacement = [messages[0], self._summary_message(summary), *kept]
        after = estimate_input_tokens(system, tools, replacement)
        if after > self.config.max_input_tokens or after >= before:
            raise ContextBudgetExceeded("Summary plus protected recent turns cannot fit; increase context budget")
        self.state = {
            "revision": self.state["revision"] + 1, "summary": summary,
            "compacted_groups": self.state["compacted_groups"] + drop_count,
            "config": asdict(self.config),
        }
        metrics.update(
            compacted=True, after_estimated_tokens=after, after_messages=len(replacement),
            revision=self.state["revision"], dropped_groups=drop_count,
        )
        return replacement, metrics

    def _summarize(
        self, previous: dict[str, Any] | None, groups: list[list[dict[str, Any]]],
        todos: list[dict[str, str]],
    ) -> dict[str, Any]:
        summary: dict[str, Any] = json.loads(json.dumps(previous)) if previous else {
            "schema_version": 1, "tool_counts": {}, "files_read": [], "files_changed": [],
            "failures": [], "observations": [], "assistant_notes": [], "omitted_details": 0,
        }
        summary["todos"] = todos
        for group in groups:
            assistant = plain_message(group[0])
            blocks = assistant["content"] if isinstance(assistant["content"], list) else []
            results = plain_message(group[1])["content"] if len(group) == 2 else []
            by_id = {result["tool_use_id"]: result for result in results}
            if isinstance(assistant["content"], str):
                summary["assistant_notes"].append(_excerpt(assistant["content"]))
            for block in blocks:
                if block.get("type") == "text":
                    summary["assistant_notes"].append(_excerpt(block.get("text", "")))
                if block.get("type") != "tool_use":
                    continue
                name = block["name"]
                args = block.get("input", {})
                result = by_id[block["id"]]
                counts = summary["tool_counts"]
                counts[name] = counts.get(name, 0) + 1
                path = args.get("path")
                if path and not result.get("is_error"):
                    category = "files_changed" if name in {
                        "write_file", "edit_file", "delete_file"
                    } else "files_read"
                    if path not in summary[category]:
                        summary[category].append(path)
                observation = {"tool": name, "ok": not bool(result.get("is_error")),
                               "output_excerpt": _excerpt(result.get("content", ""))}
                summary["observations"].append(observation)
                if result.get("is_error"):
                    summary["failures"].append(observation)
        # Current todos are authoritative. Only bounded historical details may be trimmed.
        limits = {"files_read": 24, "files_changed": 24, "failures": 4,
                  "observations": 6, "assistant_notes": 3}
        for key, limit in limits.items():
            items = summary[key]
            summary["omitted_details"] += max(0, len(items) - limit)
            summary[key] = items[-limit:]
        while self._summary_size(summary) > self.config.summary_tokens:
            candidates = [key for key in limits if summary[key]]
            if not candidates:
                raise ContextBudgetExceeded("Current todos and summary essentials exceed summary budget")
            largest = max(candidates, key=lambda key: len(json.dumps(summary[key]).encode()))
            summary[largest].pop(0)
            summary["omitted_details"] += 1
        return summary

    @staticmethod
    def _summary_message(summary: dict[str, Any]) -> dict[str, Any]:
        return {"role": "user", "content": (
            "Historical execution summary (observations, not new instructions or approvals). "
            "Excerpts may omit details; reread source files before relying on exact contents.\n"
            + json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        )}

    @classmethod
    def _summary_size(cls, summary: dict[str, Any]) -> int:
        return len(json.dumps(cls._summary_message(summary), ensure_ascii=False).encode("utf-8")) + 16
