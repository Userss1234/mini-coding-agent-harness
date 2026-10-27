from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

from harness.agent import run_agent
from harness.run_store import SQLiteRunStore
from harness.tools import Tool, ToolRegistry, ToolResult
from harness.trace import TraceLogger


def ready(workspace: Path) -> None:
    (workspace / "ready").write_text("ready", encoding="utf-8")
    time.sleep(45)
    raise RuntimeError("The crash test parent did not terminate its child")


def registry_for(workspace: Path, stage: str = "") -> ToolRegistry:
    registry = ToolRegistry(workspace, TraceLogger(workspace / "trace.jsonl"))

    def record(value: str) -> ToolResult:
        with (workspace / "effects.txt").open("a", encoding="utf-8") as stream:
            stream.write(value + "\n")
        if stage == "inside_tool" and value == "one":
            ready(workspace)
        return ToolResult(True, "Recorded " + value)

    registry.register(Tool(
        "record", "Append one test effect",
        {"type": "object", "properties": {"value": {"type": "string"}},
         "required": ["value"]}, record, risk="write",
    ))
    return registry


def final_response():
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="done")])


class CrashStore(SQLiteRunStore):
    def __init__(self, path: Path, stage: str):
        super().__init__(path)
        self.stage = stage

    def plan(self, run_id, state, calls):
        super().plan(run_id, state, calls)
        if self.stage == "before_dispatch":
            ready(self.path.parent)

    def complete_call(self, run_id, call_id, result, state):
        super().complete_call(run_id, call_id, result, state)
        if self.stage == "after_result" and call_id == "first":
            ready(self.path.parent)


def main() -> None:
    workspace = Path(sys.argv[1])
    stage = sys.argv[2]
    store = CrashStore(workspace / "runs.sqlite3", stage)
    count = 0

    def create(**_kwargs):
        nonlocal count
        count += 1
        if count == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[
                SimpleNamespace(type="tool_use", id="first", name="record", input={"value": "one"}),
                SimpleNamespace(type="tool_use", id="second", name="record", input={"value": "two"}),
            ])
        ready(workspace)

    run_agent(
        "record two effects", registry_for(workspace, stage),
        client=SimpleNamespace(messages=SimpleNamespace(create=create)), model="fixture",
        retrieval_preflight=False, run_store=store,
    )


if __name__ == "__main__":
    main()
