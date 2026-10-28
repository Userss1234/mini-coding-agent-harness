from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.workspace import WorkspaceSession


def run_workflow() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="mini-agent-workspace-smoke-") as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        original = b"def add(a, b):\n    return a - b\n"
        (source / "sample.py").write_bytes(original)
        (source / "test_sample.py").write_text(
            "from sample import add\ndef test_add(): assert add(2, 3) == 5\n", encoding="utf-8"
        )
        session = WorkspaceSession.create(source, root / "session")
        registry = build_registry(session.workspace, TraceLogger(session.path / "trace.jsonl"),
                                  allow_write=True, execution_backend="host")
        registry.baseline_workspace = session.baseline
        failing = registry.call("run_tests", timeout=30)
        edited = registry.call("edit_file", path="sample.py", old_text="a - b", new_text="a + b")
        passing = registry.call("run_tests", timeout=30)
        reviewed_content = (session.workspace / "sample.py").read_bytes()
        unchanged = (source / "sample.py").read_bytes() == original
        review = session.review()
        try:
            session.apply(review["id"], lambda _: False)
        except ValueError as exc:
            declined = "declined" in str(exc)
        else:
            declined = False
        approval_ids = []
        session.apply(review["id"], lambda digest: approval_ids.append(digest) or True)
        applied = (source / "sample.py").read_bytes() == reviewed_content and (
            (source / "sample.py").read_text() == "def add(a, b):\n    return a + b\n"
        )
        result = {
            "schema_version": 1, "backend": "host", "model_calls": 0,
            "baseline_test_failed": not failing.ok, "copy_edit_succeeded": edited.ok,
            "copy_test_passed": passing.ok, "source_unchanged_before_approval": unchanged,
            "declined_application_blocked": declined, "reviewed_files": len(review["entries"]),
            "exact_review_id_approved": approval_ids == [review["id"]],
            "source_matches_review_after_apply": applied,
            "approval_source": "deterministic fixture callback, not a human terminal session",
            "claim_boundary": "Local copy/review/apply behavior; no OS sandbox or Docker runtime claim.",
        }
        if not all(result[key] is True for key in (
            "baseline_test_failed", "copy_edit_succeeded", "copy_test_passed",
            "source_unchanged_before_approval", "declined_application_blocked",
            "exact_review_id_approved", "source_matches_review_after_apply",
        )):
            raise AssertionError(result)
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_workflow()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
