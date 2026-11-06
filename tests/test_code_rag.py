import os

from harness.code_symbols import search_code_symbols
from harness.retrieval import build_workspace_index, search_workspace


def test_chunk_cache_invalidates_same_size_same_timestamp_edits_and_deletions(tmp_path):
    path = tmp_path / "module.py"
    path.write_text("def alpha():\n    return 1\n")
    old_stat = path.stat()
    first = build_workspace_index(tmp_path)
    warm = build_workspace_index(tmp_path)
    assert first.chunk_cache_misses == 1 and warm.chunk_cache_hits == 1
    old_hash = first.chunks[0].source_sha256
    path.write_text("def bravo():\n    return 2\n")
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    changed = build_workspace_index(tmp_path)
    assert changed.chunk_cache_misses == 1 and changed.chunks[0].source_sha256 != old_hash
    assert "bravo" in changed.chunks[0].text
    match = search_workspace(tmp_path, "bravo")["matches"][0]
    assert match["indexed_source_sha256"] == changed.chunks[0].source_sha256
    path.unlink()
    assert build_workspace_index(tmp_path).chunks_indexed == 0


def test_symbol_relationships_keep_source_evidence_and_exclude_nested_calls(tmp_path):
    (tmp_path / "module.py").write_text(
        "def helper():\n    return 1\n\ndef caller():\n    return helper()\n\n"
        "class Service:\n    def run(self):\n        return helper()\n\n"
        "def outer():\n    def nested():\n        return helper()\n    return 0\n")
    (tmp_path / ".env").write_text("SECRET=hidden")
    (tmp_path / "broken.py").write_text("def broken(:")
    result = search_code_symbols(tmp_path, "helper")
    assert result["definitions"][0]["symbol"] == "helper"
    callers = {item["symbol"] for item in result["possible_callers"]}
    assert callers == {"caller", "Service.run", "outer.nested"}
    assert result["files_skipped_parse"] == 1
    for item in result["definitions"] + result["possible_callers"]:
        assert len(item["indexed_source_sha256"]) == 64
        assert item["path"] == "module.py" and item["start_line"] <= item["end_line"]
    assert search_code_symbols(tmp_path, "caller")["possible_callees"][0]["symbol"] == "helper"
