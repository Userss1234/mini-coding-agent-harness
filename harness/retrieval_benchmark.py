from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .retrieval import search_workspace


SearchFunction = Callable[..., Mapping[str, Any]]


def run_retrieval_benchmark(
    judgments_path: Path,
    *,
    backend: str = "lexical",
    search_fn: SearchFunction | None = None,
) -> dict[str, Any]:
    judgments_path = judgments_path.resolve()
    spec = load_retrieval_judgments(judgments_path)
    corpus_root = _resolve_corpus_root(judgments_path, str(spec["corpus_root"]))
    k_values = _normalize_k_values(spec.get("k_values", [1, 3, 5]))
    cases = list(spec["cases"])
    active_search = search_fn or _search_backend(backend)
    max_k = max(k_values)
    case_results = []

    for case in cases:
        search_result = active_search(
            corpus_root,
            str(case["query"]),
            glob_pattern=str(case.get("glob") or spec.get("glob") or "*"),
            limit=max(50, max_k * 10),
            chunk_lines=int(case.get("chunk_lines") or spec.get("chunk_lines") or 40),
            overlap=int(case.get("overlap") or spec.get("overlap") or 5),
            max_chars_per_chunk=int(spec.get("max_chars_per_chunk") or 1200),
        )
        ranked_paths = _dedupe_ranked_paths(search_result.get("matches") or [])
        relevant_paths = [str(path).replace("\\", "/") for path in case["relevant_paths"]]
        relevant_set = set(relevant_paths)
        first_relevant_rank = next(
            (rank for rank, path in enumerate(ranked_paths, start=1) if path in relevant_set),
            None,
        )
        recall_at_k = {
            str(k): _recall_at_k(ranked_paths, relevant_set, k)
            for k in k_values
        }
        hit_at_k = {
            str(k): any(path in relevant_set for path in ranked_paths[:k])
            for k in k_values
        }
        case_results.append({
            "case_id": str(case["case_id"]),
            "query": str(case["query"]),
            "rationale": str(case.get("rationale") or ""),
            "relevant_paths": relevant_paths,
            "ranked_paths": ranked_paths[:max_k],
            "first_relevant_rank": first_relevant_rank,
            "reciprocal_rank": (1.0 / first_relevant_rank if first_relevant_rank else 0.0),
            "recall_at_k": recall_at_k,
            "hit_at_k": hit_at_k,
            "missing_relevant_at_max_k": sorted(
                relevant_set - set(ranked_paths[:max_k])
            ),
        })

    summary = _summarize_cases(case_results, k_values)
    quality_gate = _evaluate_quality_gate(summary, spec.get("quality_gate") or {})
    summary["quality_gate_passed"] = quality_gate["passed"]
    summary["quality_gate_checks"] = quality_gate["checks"]
    return {
        "schema_version": 1,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "backend": backend,
        "judgments": _display_path(judgments_path),
        "corpus_root": _display_path(corpus_root),
        "configuration": {
            "glob": str(spec.get("glob") or "*"),
            "chunk_lines": int(spec.get("chunk_lines") or 40),
            "overlap": int(spec.get("overlap") or 5),
            "k_values": k_values,
            "ranking_unit": "deduplicated_path",
        },
        "summary": summary,
        "cases": case_results,
    }


def load_retrieval_judgments(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Retrieval judgments file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid retrieval judgments JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Retrieval judgments must be a JSON object.")
    if int(payload.get("schema_version", 0) or 0) != 1:
        raise ValueError("Retrieval judgments schema_version must be 1.")
    corpus_value = str(payload.get("corpus_root") or "").strip()
    if not corpus_value:
        raise ValueError("Retrieval judgments must define corpus_root.")
    corpus_root = _resolve_corpus_root(path, corpus_value)
    if not corpus_root.is_dir():
        raise ValueError(f"Retrieval corpus directory not found: {corpus_root}")
    _normalize_k_values(payload.get("k_values", [1, 3, 5]))
    quality_gate = payload.get("quality_gate", {})
    if not isinstance(quality_gate, dict):
        raise ValueError("Retrieval quality_gate must be an object.")
    for metric, minimum in quality_gate.items():
        if not isinstance(metric, str) or not metric:
            raise ValueError("Retrieval quality gate metric names must be non-empty strings.")
        try:
            value = float(minimum)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Retrieval quality gate minimum must be numeric: {metric}") from exc
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Retrieval quality gate minimum must be between 0 and 1: {metric}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Retrieval judgments must contain at least one case.")
    seen_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each retrieval judgment case must be an object.")
        case_id = str(case.get("case_id") or "").strip()
        query = str(case.get("query") or "").strip()
        relevant_paths = case.get("relevant_paths")
        if not case_id or case_id in seen_ids:
            raise ValueError(f"Retrieval case_id must be non-empty and unique: {case_id!r}")
        if not query:
            raise ValueError(f"Retrieval case {case_id} must define a query.")
        if not isinstance(relevant_paths, list) or not relevant_paths:
            raise ValueError(f"Retrieval case {case_id} must define relevant_paths.")
        if any(not isinstance(value, str) or not value.strip() for value in relevant_paths):
            raise ValueError(f"Retrieval case {case_id} relevant_paths must contain non-empty strings.")
        normalized_paths = [value.replace("\\", "/") for value in relevant_paths]
        if len(set(normalized_paths)) != len(normalized_paths):
            raise ValueError(f"Retrieval case {case_id} contains duplicate relevant_paths.")
        seen_ids.add(case_id)
        for relevant_path in relevant_paths:
            target = _safe_corpus_path(corpus_root, str(relevant_path))
            if not target.is_file():
                raise ValueError(
                    f"Relevant path for retrieval case {case_id} does not exist: {relevant_path}"
                )
    return payload


def build_retrieval_benchmark_report(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    k_values = [int(value) for value in result["configuration"]["k_values"]]
    metric_rows = "\n".join(
        "| Recall@{k} | {recall:.2%} |\n| Hit Rate@{k} | {hit_rate:.2%} |".format(
            k=k,
            recall=float(summary["recall_at_k"][str(k)]),
            hit_rate=float(summary["hit_rate_at_k"][str(k)]),
        )
        for k in k_values
    )
    gate_rows = "\n".join(
        "| `{metric}` | {actual:.4f} | {minimum:.4f} | {status} |".format(
            metric=check["metric"],
            actual=float(check["actual"]),
            minimum=float(check["minimum"]),
            status="pass" if check["passed"] else "fail",
        )
        for check in summary["quality_gate_checks"]
    ) or "| (none) | n/a | n/a | pass |"
    max_k = max(k_values)
    case_rows = "\n".join(
        _case_report_row(case, k_values, max_k)
        for case in result["cases"]
    )
    failures = [
        case for case in result["cases"]
        if case["missing_relevant_at_max_k"]
    ]
    failure_rows = "\n".join(
        "- `{case_id}`: missing {missing}; query `{query}`".format(
            case_id=case["case_id"],
            missing=", ".join(f"`{path}`" for path in case["missing_relevant_at_max_k"]),
            query=case["query"],
        )
        for case in failures
    ) or "- None."
    return f"""# Retrieval Quality Baseline

## Summary

- Backend: **{result['backend']}**
- Cases: **{summary['case_count']}**
- Ranking unit: **deduplicated path**
- Mean reciprocal rank: **{float(summary['mrr']):.4f}**
- Zero-result queries: **{summary['zero_result_queries']}**
- Quality gate: **{'pass' if summary['quality_gate_passed'] else 'fail'}**

| Metric | Value |
|---|---:|
| MRR | {float(summary['mrr']):.4f} |
{metric_rows}

## Quality Gate

| Metric | Actual | Minimum | Status |
|---|---:|---:|---|
{gate_rows}

## Cases

`R@K` is the fraction of judged relevant paths found in the first K deduplicated paths. `P/O` means the first relevant path rank, or `none` when no relevant path appears.

| Case | Relevant | Top {max_k} Paths | P/O | {' | '.join(f'R@{k}' for k in k_values)} |
|---|---|---|---:|{'|'.join('---:' for _ in k_values)}|
{case_rows}

## Misses At {max_k}

{failure_rows}

## Interpretation

This is an offline lexical retrieval baseline over committed relevance judgments. It measures ranking quality independently from the agent loop and does not claim embedding or semantic retrieval. Misses are retained as targets for the optional hybrid backend; future backends must run against the same corpus and judgments.
"""


def write_retrieval_benchmark_outputs(
    result: Mapping[str, Any],
    *,
    output_path: Path,
    json_output_path: Path | None = None,
) -> str:
    report = build_retrieval_benchmark_report(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    if json_output_path is not None:
        json_output_path.parent.mkdir(parents=True, exist_ok=True)
        json_output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return report


def _search_backend(name: str) -> SearchFunction:
    if name == "lexical":
        return search_workspace
    raise ValueError(f"Unsupported retrieval benchmark backend: {name}")


def _resolve_corpus_root(judgments_path: Path, corpus_value: str) -> Path:
    base = judgments_path.resolve().parent
    root = (base / corpus_value).resolve()
    if not root.is_relative_to(base):
        raise ValueError("Retrieval corpus_root must stay inside the judgments directory.")
    return root


def _safe_corpus_path(corpus_root: Path, value: str) -> Path:
    normalized = value.replace("\\", "/").lstrip("/")
    target = (corpus_root / normalized).resolve()
    if not target.is_relative_to(corpus_root):
        raise ValueError(f"Relevant path escapes retrieval corpus: {value}")
    return target


def _normalize_k_values(values: Any) -> list[int]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError("k_values must be a list of positive integers.")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("k_values must be a list of positive integers.")
    normalized = sorted(set(values))
    if not normalized or normalized[0] <= 0:
        raise ValueError("k_values must contain positive integers.")
    return normalized


def _dedupe_ranked_paths(matches: Sequence[Mapping[str, Any]]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in matches:
        path = str(match.get("path") or "").replace("\\", "/")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def _recall_at_k(ranked_paths: Sequence[str], relevant_paths: set[str], k: int) -> float:
    if not relevant_paths:
        return 0.0
    return len(relevant_paths & set(ranked_paths[:k])) / len(relevant_paths)


def _summarize_cases(cases: Sequence[Mapping[str, Any]], k_values: Sequence[int]) -> dict[str, Any]:
    count = len(cases)
    return {
        "case_count": count,
        "mrr": sum(float(case["reciprocal_rank"]) for case in cases) / count if count else 0.0,
        "recall_at_k": {
            str(k): sum(float(case["recall_at_k"][str(k)]) for case in cases) / count if count else 0.0
            for k in k_values
        },
        "hit_rate_at_k": {
            str(k): sum(1 for case in cases if case["hit_at_k"][str(k)]) / count if count else 0.0
            for k in k_values
        },
        "zero_result_queries": sum(1 for case in cases if not case["ranked_paths"]),
    }


def _evaluate_quality_gate(
    summary: Mapping[str, Any],
    quality_gate: Mapping[str, Any],
) -> dict[str, Any]:
    checks = []
    for metric, minimum_value in quality_gate.items():
        if metric == "mrr":
            actual = float(summary["mrr"])
        elif metric.startswith("recall_at_"):
            k = metric.removeprefix("recall_at_")
            if k not in summary["recall_at_k"]:
                raise ValueError(f"Quality gate references unconfigured metric: {metric}")
            actual = float(summary["recall_at_k"][k])
        elif metric.startswith("hit_rate_at_"):
            k = metric.removeprefix("hit_rate_at_")
            if k not in summary["hit_rate_at_k"]:
                raise ValueError(f"Quality gate references unconfigured metric: {metric}")
            actual = float(summary["hit_rate_at_k"][k])
        else:
            raise ValueError(f"Unsupported retrieval quality gate metric: {metric}")
        minimum = float(minimum_value)
        checks.append({
            "metric": metric,
            "actual": actual,
            "minimum": minimum,
            "passed": actual + 1e-12 >= minimum,
        })
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _case_report_row(
    case: Mapping[str, Any],
    k_values: Sequence[int],
    max_k: int,
) -> str:
    relevant = "<br>".join(f"`{path}`" for path in case["relevant_paths"])
    ranked = "<br>".join(f"{index}. `{path}`" for index, path in enumerate(case["ranked_paths"][:max_k], start=1)) or "none"
    rank = case["first_relevant_rank"] if case["first_relevant_rank"] is not None else "none"
    recalls = " | ".join(f"{float(case['recall_at_k'][str(k)]):.2%}" for k in k_values)
    return f"| `{case['case_id']}` | {relevant} | {ranked} | {rank} | {recalls} |"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)
