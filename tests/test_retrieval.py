from __future__ import annotations

from pathlib import Path

from harness.retrieval import build_workspace_index, search_workspace, tokenize_query


def test_tokenize_query_keeps_searchable_terms() -> None:
    assert tokenize_query("Fix invoice_total rounding in billing.py!") == [
        "fix",
        "invoice",
        "total",
        "rounding",
        "in",
        "billing",
        "py",
    ]


def test_build_workspace_index_chunks_text_and_skips_sensitive_paths(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "billing.py").write_text(
        "\n".join(f"line {index}" for index in range(1, 8)),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("SECRET_TOKEN=hidden\n", encoding="utf-8")
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "trace.py").write_text("secret generated context\n", encoding="utf-8")

    index = build_workspace_index(tmp_path, glob_pattern="*.py", chunk_lines=3, overlap=1)

    assert index.files_indexed == 1
    assert index.chunks_indexed == 3
    assert index.chunks[0].path == "src/billing.py"
    assert index.chunks[0].start_line == 1
    assert index.chunks[1].start_line == 3
    indexed_text = "\n".join(chunk.text for chunk in index.chunks)
    assert "SECRET_TOKEN" not in indexed_text
    assert "secret generated context" not in indexed_text


def test_search_workspace_ranks_symbol_chunk_across_distractors(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "class BillingService:\n"
        "    def invoice_total(self, items):\n"
        "        subtotal = sum(item.price for item in items)\n"
        "        return round(subtotal, 2)\n",
        encoding="utf-8",
    )
    (tmp_path / "invoice_notes.md").write_text(
        "Invoice copy and customer-facing billing notes.\n",
        encoding="utf-8",
    )
    (tmp_path / "weather.py").write_text(
        "def forecast(city):\n"
        "    return f'sunny in {city}'\n",
        encoding="utf-8",
    )

    result = search_workspace(tmp_path, "invoice total rounding", glob_pattern="*.py,*.md", limit=2, chunk_lines=4)

    assert result["matches"][0]["path"] == "billing.py"
    assert result["matches"][0]["start_line"] == 1
    assert "invoice_total" in result["matches"][0]["snippet"]
    assert result["index"]["files_indexed"] == 3
    assert result["retrieval"] == "local_chunk_lexical_scoring"
