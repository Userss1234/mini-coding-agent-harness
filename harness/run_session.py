from __future__ import annotations

import hashlib
import json
from typing import Any

from .run_store import REDACTED, RunStore
from .tools import ToolRegistry


def normalize_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    result = []
    for block in blocks:
        if isinstance(block, dict):
            result.append(block)
        elif hasattr(block, "model_dump"):
            result.append(block.model_dump(mode="json"))
        else:
            result.append(vars(block))
    return result


class RunSession:
    def __init__(self, store: RunStore, run_id: str, registry: ToolRegistry, *, resume: bool):
        self.store = store
        self.run_id = run_id
        self.registry = registry
        self.state: dict[str, Any] = {}
        self.saved = store.load(run_id) if resume else None
        schema = json.dumps(registry.schemas(), sort_keys=True)
        self.policy = {
            "workspace": str(registry.workspace),
            "allow_write": registry.allow_write,
            "execution_backend": registry.execution_backend,
            "execution_policy": registry.execution_policy,
            "retrieval_backend": registry.retrieval_backend,
            "tool_schema_hash": hashlib.sha256(schema.encode()).hexdigest(),
            "tool_names": registry.names(),
        }
        if registry.baseline_workspace is not None:
            self.policy["baseline_workspace"] = str(registry.baseline_workspace)
        if registry.external_tool_policy:
            self.policy["external_tools"] = dict(registry.external_tool_policy)
        if registry.retrieval_policy:
            self.policy["retrieval_policy"] = dict(registry.retrieval_policy)
        if registry.verification_controller is not None:
            self.policy["verification"] = registry.verification_controller.policy()
        if registry.code_intelligence_policy:
            self.policy["code_intelligence"] = dict(registry.code_intelligence_policy)
        if registry.run_controls is not None:
            self.policy["run_controls"] = registry.run_controls.policy()
        if self.saved is not None:
            if self.saved["policy"] != self.policy:
                raise ValueError("Resume requires the original workspace, permissions, backend and tools")
            self.state = self.saved
            registry.todos = self.state["todos"]

    def initialize(self, **state: Any) -> None:
        self.state = {
            **state, "status": "running", "phase": "model", "turn": 0,
            "todos": self.registry.todos, "policy": self.policy,
            "artifacts": {"trace": str(self.registry.trace.path.resolve())},
        }
        self.store.create(self.run_id, self.state)
        self.registry.trace.log("run_created", run_id=self.run_id)

    def ensure_recoverable(self) -> None:
        for call in self.store.calls(self.run_id):
            if call["status"] == "started":
                self.save(status="blocked")
                raise RuntimeError(
                    f"Tool {call['id']} has an unknown outcome; inspect the workspace and use run-resolve"
                )

    def save(self, **updates: Any) -> None:
        self.state.update(updates)
        self.state["todos"] = self.registry.todos
        self.store.save(self.run_id, self.state)

    def plan(self, messages: list[dict[str, Any]], turn: int, blocks: list[Any]) -> None:
        calls = [block for block in normalize_blocks(blocks) if block.get("type") == "tool_use"]
        existing = {call["id"] for call in self.store.calls(self.run_id)}
        if len({call["id"] for call in calls}) != len(calls) or any(
            call["id"] in existing for call in calls
        ):
            raise ValueError("Duplicate tool-call IDs in a durable run")
        self.state.update(messages=messages, turn=turn, phase="tools", status="running")
        self.store.plan(self.run_id, self.state, calls)

    def result(self, call_id: str) -> dict[str, Any] | None:
        call = next(item for item in self.store.calls(self.run_id) if item["id"] == call_id)
        if call["status"] == "completed":
            return call["result"]
        if call["status"] == "started":
            self.save(status="blocked")
            raise RuntimeError(
                f"Tool {call_id} has an unknown outcome; inspect the workspace and use run-resolve"
            )
        if self.saved is not None and REDACTED in json.dumps(call["input"]):
            self.save(status="blocked")
            raise RuntimeError("Pending tool arguments were redacted; start a new run with fresh input")
        self.store.start_call(self.run_id, call_id)
        return None

    def complete(self, result: dict[str, Any], evidence_terms: set[str]) -> None:
        self.state.update(todos=self.registry.todos, evidence_terms=sorted(evidence_terms))
        self.store.complete_call(self.run_id, result["tool_use_id"], result, self.state)
