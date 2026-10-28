from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


def summarize_evidence_use(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Observe retrieved evidence followed by reads/edits, not model reasoning or causality."""
    retrieved: set[str] = set()
    reads: set[str] = set()
    edits: set[str] = set()
    preflight: set[str] = set()
    in_verifier = False

    def normalized(value: Any) -> str:
        text = str(value or "").replace("\\", "/")
        return str(PurePosixPath(text)) if text else ""

    for event in events:
        name = event.get("event")
        data = event.get("data") or {}
        if name == "eval_agent_verifier_start":
            in_verifier = True
        elif name == "eval_agent_verifier_end":
            in_verifier = False
        if in_verifier:
            continue
        if name == "agent_retrieval_preflight" and data.get("ok"):
            paths = {normalized(path) for path in data.get("paths", [])} - {""}
            preflight.update(paths)
            retrieved.update(paths)
        elif name == "tool_call" and data.get("ok"):
            tool = data.get("tool")
            metadata = data.get("metadata") or {}
            if tool in {"rag_search", "context_pack", "retrieve_then_read"}:
                retrieved.update(normalized(item.get("path")) for item in metadata.get("matches", []))
                retrieved.discard("")
            path = normalized((data.get("args") or {}).get("path"))
            if path and path in retrieved:
                if tool == "read_file":
                    reads.add(path)
                elif tool in {"edit_file", "write_file"}:
                    edits.add(path)
    used = reads | edits
    return {
        "retrieved_paths": sorted(retrieved), "preflight_injected_paths": sorted(preflight),
        "subsequently_read_paths": sorted(reads), "subsequently_edited_paths": sorted(edits),
        "path_followup_ratio": len(used) / len(retrieved) if retrieved else None,
        "interpretation": "Temporal path follow-up proxy; not proof of semantic use, correctness or causality.",
    }
