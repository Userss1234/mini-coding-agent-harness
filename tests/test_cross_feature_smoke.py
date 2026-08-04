from __future__ import annotations

from pathlib import Path

from harness.cross_feature_smoke import (
    EXPECTED_IMPLEMENTATION_PATH,
    inspect_docker_report,
    preflight_embedding_model,
    run_cross_feature_smoke,
)


def test_cross_feature_smoke_combines_docker_and_live_hybrid_mcp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    implementation = tmp_path / EXPECTED_IMPLEMENTATION_PATH
    implementation.parent.mkdir(parents=True)
    implementation.write_text("def validate_origin(): pass\n", encoding="utf-8")
    docker_report = tmp_path / "DOCKER_SANDBOX_SMOKE.md"
    docker_report.write_text(_passing_docker_report(), encoding="utf-8")

    def fake_hybrid(*_args, **_kwargs):
        return {
            "query": "Streamable HTTP Origin authentication session lifecycle",
            "tokens": ["streamable", "http", "origin", "session"],
            "matches": [{
                "path": EXPECTED_IMPLEMENTATION_PATH,
                "start_line": 1,
                "end_line": 1,
                "score": 0.99,
                "snippet": "def validate_origin(): pass",
            }],
            "index": {"files_indexed": 1, "chunks_indexed": 1},
            "retrieval": "local_chunk_hybrid_scoring",
            "hybrid": {
                "embedding_model": "fixture-embedder",
                "cache": {"hits": 2, "misses": 1, "written": True},
            },
        }

    monkeypatch.setattr(
        "harness.hybrid_retrieval.search_workspace_hybrid",
        fake_hybrid,
    )
    monkeypatch.setattr(
        "harness.cross_feature_smoke.get_sentence_transformer_embedder",
        lambda _model: type(
            "FixtureEmbedder",
            (),
            {"encode_query": staticmethod(lambda _query: [1.0, 0.0])},
        )(),
    )
    output = tmp_path / "CROSS_FEATURE_VALIDATION.md"

    report = run_cross_feature_smoke(
        tmp_path,
        tmp_path / "cross_feature_trace.jsonl",
        docker_report,
        output,
        fresh_trace=True,
    )

    assert "Status: **pass**" in report
    assert "local_chunk_hybrid_scoring" in report
    assert "fixture-embedder" in report
    assert EXPECTED_IMPLEMENTATION_PATH in report
    assert "2/1/1" in report
    assert output.read_text(encoding="utf-8") == report
    trace = (tmp_path / "cross_feature_trace.jsonl").read_text(encoding="utf-8")
    assert "cross-feature-local-token" not in trace


def test_inspect_docker_report_requires_runtime_and_no_fallback(tmp_path: Path) -> None:
    report = tmp_path / "DOCKER.md"
    report.write_text(
        _passing_docker_report().replace("network=blocked", "network=open"),
        encoding="utf-8",
    )

    result = inspect_docker_report(report)

    assert result["passed"] is False
    assert result["missing"] is False
    assert result["checks"]["network"] is False


def test_inspect_docker_report_marks_missing_evidence_blocked(tmp_path: Path) -> None:
    result = inspect_docker_report(tmp_path / "missing.md")

    assert result["passed"] is False
    assert result["missing"] is True


def test_embedding_preflight_defaults_offline_and_restores_environment(
    monkeypatch,
) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    observed: dict[str, str | None] = {}

    class FakeEmbedder:
        @staticmethod
        def encode_query(_query: str) -> list[float]:
            import os

            observed["hf"] = os.getenv("HF_HUB_OFFLINE")
            observed["transformers"] = os.getenv("TRANSFORMERS_OFFLINE")
            return [1.0]

    monkeypatch.setattr(
        "harness.cross_feature_smoke.get_sentence_transformer_embedder",
        lambda _model: FakeEmbedder(),
    )

    result = preflight_embedding_model(allow_model_download=False)

    assert result["passed"] is True
    assert observed == {"hf": "1", "transformers": "1"}
    import os

    assert os.getenv("HF_HUB_OFFLINE") is None
    assert os.getenv("TRANSFORMERS_OFFLINE") is None


def _passing_docker_report() -> str:
    return """# Docker Sandbox Smoke Report

- Status: **pass**
- Execution backend: **docker**

| Host fallback | `False` |

```text
uid=10001 workspace=ok network=blocked
```
"""
