from __future__ import annotations

from pathlib import Path

import pytest

from harness.hybrid_retrieval import (
    get_sentence_transformer_embedder,
    search_workspace_hybrid,
)


class SemanticFakeEmbedder:
    model_name = "semantic-fake-v1"

    def __init__(self) -> None:
        self.document_batches: list[list[str]] = []

    def encode_documents(self, texts):
        self.document_batches.append(list(texts))
        return [self._vector(text) for text in texts]

    def encode_query(self, text):
        return [1.0, 0.0]

    @staticmethod
    def _vector(text: str):
        if "singleflight" in text.lower() or "coalesce concurrent" in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]


def test_sentence_transformer_embedder_is_reused_per_process() -> None:
    get_sentence_transformer_embedder.cache_clear()

    first = get_sentence_transformer_embedder("local-test-model")
    second = get_sentence_transformer_embedder("local-test-model")

    assert first is second
    get_sentence_transformer_embedder.cache_clear()


def test_hybrid_zero_limit_returns_structured_result_without_loading_model(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("single flight\n", encoding="utf-8")

    result = search_workspace_hybrid(tmp_path, "combine requests", limit=0)

    assert result["matches"] == []
    assert result["index"]["chunks_indexed"] == 1
    assert result["retrieval"] == "local_chunk_hybrid_scoring"


def test_hybrid_search_recovers_semantic_match_over_lexical_distractor(tmp_path: Path) -> None:
    (tmp_path / "coalescing.py").write_text(
        "class SingleFlight:\n    # Coalesce concurrent work by operation key.\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "guide.md").write_text(
        "Combine simultaneous identical requests at the gateway.\n",
        encoding="utf-8",
    )
    embedder = SemanticFakeEmbedder()

    result = search_workspace_hybrid(
        tmp_path,
        "combine simultaneous identical requests",
        embedder=embedder,
        cache_dir=tmp_path / ".cache",
        lexical_weight=0.2,
        semantic_weight=0.8,
    )

    assert result["matches"][0]["path"] == "coalescing.py"
    assert result["matches"][0]["semantic_score"] == pytest.approx(1.0)
    assert result["retrieval"] == "local_chunk_hybrid_scoring"
    assert result["hybrid"]["embedding_dimension"] == 2


def test_embedding_cache_reuses_unchanged_chunks_and_invalidates_one_change(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("single flight operation\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("unrelated weather operation\n", encoding="utf-8")
    cache_dir = tmp_path / ".cache"
    embedder = SemanticFakeEmbedder()

    first = search_workspace_hybrid(
        tmp_path, "combine requests", embedder=embedder, cache_dir=cache_dir
    )
    second = search_workspace_hybrid(
        tmp_path, "combine requests", embedder=embedder, cache_dir=cache_dir
    )
    (tmp_path / "a.py").write_text("single flight operation changed\n", encoding="utf-8")
    third = search_workspace_hybrid(
        tmp_path, "combine requests", embedder=embedder, cache_dir=cache_dir
    )

    assert first["hybrid"]["cache"]["misses"] == 2
    assert second["hybrid"]["cache"]["hits"] == 2
    assert second["hybrid"]["cache"]["misses"] == 0
    assert third["hybrid"]["cache"]["hits"] == 1
    assert third["hybrid"]["cache"]["misses"] == 1
    assert [len(batch) for batch in embedder.document_batches] == [2, 1]


@pytest.mark.parametrize(
    ("lexical_weight", "semantic_weight"),
    [(-1.0, 1.0), (1.0, -1.0), (0.0, 0.0), (float("nan"), 1.0)],
)
def test_hybrid_search_rejects_invalid_weights(
    tmp_path: Path,
    lexical_weight: float,
    semantic_weight: float,
) -> None:
    (tmp_path / "sample.py").write_text("single flight\n", encoding="utf-8")

    with pytest.raises(ValueError, match="weights|weight"):
        search_workspace_hybrid(
            tmp_path,
            "combine requests",
            embedder=SemanticFakeEmbedder(),
            cache_dir=tmp_path / ".cache",
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
        )
