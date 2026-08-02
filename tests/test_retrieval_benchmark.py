from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.retrieval_benchmark import (
    build_retrieval_benchmark_report,
    load_retrieval_judgments,
    run_retrieval_benchmark,
    write_retrieval_benchmark_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_fixture(tmp_path: Path, *, quality_gate: dict | None = None) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.py").write_text("def alpha():\n    pass\n", encoding="utf-8")
    (corpus / "b.py").write_text("def beta():\n    pass\n", encoding="utf-8")
    (corpus / "c.py").write_text("def gamma():\n    pass\n", encoding="utf-8")
    judgments = {
        "schema_version": 1,
        "corpus_root": "corpus",
        "k_values": [1, 3],
        "quality_gate": quality_gate or {},
        "cases": [
            {
                "case_id": "multi",
                "query": "alpha beta",
                "relevant_paths": ["a.py", "b.py"],
            },
            {
                "case_id": "miss",
                "query": "gamma",
                "relevant_paths": ["c.py"],
            },
        ],
    }
    path = tmp_path / "judgments.json"
    path.write_text(json.dumps(judgments), encoding="utf-8")
    return path


def _fake_search(_workspace: Path, query: str, **_kwargs):
    if query == "alpha beta":
        return {"matches": [
            {"path": "a.py"},
            {"path": "a.py"},
            {"path": "b.py"},
        ]}
    return {"matches": [{"path": "b.py"}]}


def test_benchmark_deduplicates_paths_and_calculates_metrics(tmp_path: Path) -> None:
    result = run_retrieval_benchmark(_write_fixture(tmp_path), search_fn=_fake_search)

    assert result["summary"]["mrr"] == pytest.approx(0.5)
    assert result["summary"]["recall_at_k"] == {"1": 0.25, "3": 0.5}
    assert result["summary"]["hit_rate_at_k"] == {"1": 0.5, "3": 0.5}
    assert result["cases"][0]["ranked_paths"] == ["a.py", "b.py"]
    assert result["cases"][0]["recall_at_k"] == {"1": 0.5, "3": 1.0}
    assert result["cases"][1]["first_relevant_rank"] is None


def test_benchmark_reports_failed_quality_gate(tmp_path: Path) -> None:
    path = _write_fixture(tmp_path, quality_gate={"mrr": 0.6, "recall_at_3": 0.5})
    result = run_retrieval_benchmark(path, search_fn=_fake_search)

    assert result["summary"]["quality_gate_passed"] is False
    assert [check["passed"] for check in result["summary"]["quality_gate_checks"]] == [False, True]


@pytest.mark.parametrize("k_values", [[1.5], [True], [0], []])
def test_judgments_reject_invalid_k_values(tmp_path: Path, k_values: list) -> None:
    path = _write_fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["k_values"] = k_values
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="k_values"):
        load_retrieval_judgments(path)


def test_judgments_reject_paths_outside_corpus(tmp_path: Path) -> None:
    path = _write_fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cases"][0]["relevant_paths"] = ["../outside.py"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="escapes retrieval corpus"):
        load_retrieval_judgments(path)


def test_report_outputs_markdown_and_json(tmp_path: Path) -> None:
    result = run_retrieval_benchmark(_write_fixture(tmp_path), search_fn=_fake_search)
    output = tmp_path / "report.md"
    json_output = tmp_path / "report.json"

    report = write_retrieval_benchmark_outputs(
        result,
        output_path=output,
        json_output_path=json_output,
    )

    assert report == build_retrieval_benchmark_report(result)
    assert "# Retrieval Quality Baseline" in output.read_text(encoding="utf-8")
    assert json.loads(json_output.read_text(encoding="utf-8"))["summary"]["mrr"] == 0.5


def test_committed_lexical_baseline_passes_quality_gate() -> None:
    result = run_retrieval_benchmark(
        REPO_ROOT / "benchmarks" / "retrieval" / "judgments.json"
    )

    assert result["summary"]["case_count"] == 10
    assert result["summary"]["mrr"] == pytest.approx(0.8)
    assert result["summary"]["recall_at_k"]["5"] == pytest.approx(0.8)
    assert result["summary"]["quality_gate_passed"] is True
    semantic_case = next(
        case for case in result["cases"]
        if case["case_id"] == "payment_duplicate_semantic"
    )
    assert semantic_case["first_relevant_rank"] is None
