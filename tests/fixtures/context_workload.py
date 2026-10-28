from __future__ import annotations

import argparse
import json
import re
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from harness.agent import run_agent
from harness.context_window import ContextConfig
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger

STEPS = 12
TASK = "Complete step_1 through step_12 in progress.txt. Preserve PROJECT_SENTINEL."
CONFIG = ContextConfig(max_input_tokens=12000, summary_tokens=1800, keep_recent_turns=1)


def registry_for(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    evidence = root / "evidence.txt"
    if not evidence.exists():
        evidence.write_text("Historical source detail.\n" * 80, encoding="utf-8")
    return build_registry(root, TraceLogger(root / "trace.jsonl"), allow_write=True)


class ContextClient:
    def __init__(self, root: Path, *, interrupt: bool = False):
        self.root = root
        self.interrupt = interrupt
        self.messages = SimpleNamespace(create=self.create)

    def create(self, *, system, tools, messages, **_kwargs):
        assert "PROJECT_SENTINEL" in messages[0]["content"]
        if self.interrupt and len(messages) > 1 and "Historical execution summary" in str(messages[1]):
            (self.root / "ready").write_text("checkpoint saved", encoding="utf-8")
            time.sleep(45)
            raise RuntimeError("Crash test parent did not terminate child")
        progress = 0
        for message in messages:
            if not isinstance(message["content"], list):
                continue
            for block in message["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    if str(block.get("tool_use_id", "")).endswith("_progress"):
                        numbers = re.findall(r"step_(\d+)", str(block["content"]))
                        progress = max([progress, *[int(number) for number in numbers]])
        if progress == STEPS:
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(
                type="text", text="Completed 12 steps in progress.txt; PROJECT_SENTINEL preserved.",
            )])
        step = progress + 1
        blocks = [
            SimpleNamespace(type="tool_use", id=f"{step}_write", name="write_file", input={
                "path": "progress.txt", "content": "\n".join(f"step_{i}" for i in range(1, step + 1)),
            }),
            SimpleNamespace(type="tool_use", id=f"{step}_evidence", name="read_file", input={
                "path": "evidence.txt",
            }),
            SimpleNamespace(type="tool_use", id=f"{step}_progress", name="read_file", input={
                "path": "progress.txt",
            }),
        ]
        return SimpleNamespace(stop_reason="tool_use", content=blocks)


def run_workload(root: Path, config: ContextConfig | None = CONFIG, *, resume_id=None, interrupt=False):
    registry = registry_for(root)
    store = SQLiteRunStore(root / "runs.sqlite3")
    answer = run_agent(
        TASK, registry, client=ContextClient(root, interrupt=interrupt), model="fixture",
        max_turns=20, retrieval_preflight=False, run_store=store, resume_run_id=resume_id,
        context_config=config,
    )
    run_id = resume_id or store.list_runs()[0]["id"]
    state = store.load(run_id)
    events = [json.loads(line) for line in (root / "trace.jsonl").read_text().splitlines()]
    requests = [event["data"] for event in events if event["event"] == "context_request"]
    assert "Completed 12 steps" in answer
    assert (root / "progress.txt").read_text().splitlines() == [f"step_{i}" for i in range(1, 13)]
    assert len(store.calls(run_id)) == STEPS * 3
    return {
        "completed": True, "steps": STEPS, "model_requests": len(requests),
        "tool_calls": len(store.calls(run_id)),
        "compactions": state.get("context_state", {}).get("revision", 0),
        "peak_estimated_input_tokens": max(item["after_estimated_tokens"] for item in requests),
        "total_estimated_input_tokens": sum(item["after_estimated_tokens"] for item in requests),
        "estimator": "utf8_bytes_v1", "state": state,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--interrupt-workspace", type=Path)
    args = parser.parse_args()
    if args.interrupt_workspace:
        run_workload(args.interrupt_workspace, interrupt=True)
        return
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        managed = run_workload(root / "managed")
        baseline = run_workload(root / "baseline", ContextConfig(enabled=False))
    result = {
        "managed": {key: value for key, value in managed.items() if key != "state"},
        "baseline": {key: value for key, value in baseline.items() if key != "state"},
        "claim_boundary": "Deterministic local workload; byte estimates, not provider tokens or cost.",
    }
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
