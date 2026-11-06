from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from harness import qdrant_retrieval as qr
from harness.run_session import RunSession
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger


class Embedder:
    model_name = "qdrant-test-v1"

    def __init__(self):
        self.encoded = 0

    def encode_query(self, text):
        return [1.0, 0.0]

    def encode_documents(self, texts):
        self.encoded += len(texts)
        return [[1.0, 0.0] if "coalesce" in text else [0.0, 1.0] for text in texts]


class MemoryREST:
    def __init__(self, config):
        self.collections = {}

    def request(self, method, path, body=None, *, missing_ok=False):
        collection = path.split("/")[2]
        current = self.collections.get(collection)
        if method == "GET":
            return None if current is None else {"config": {"params": {"vectors": current[0]}}}
        if method == "PUT" and "/points" not in path:
            self.collections[collection] = (body["vectors"], {})
            return True
        points = self.collections[collection][1]
        if path.endswith("/scroll"):
            ids = sorted(points)
            offset = body.get("offset")
            ids = [pid for pid in ids if offset is None or pid > offset]
            selected = ids[:2]  # Exercise actual pagination even on tiny fixtures.
            return {"points": [{"id": pid} for pid in selected],
                    "next_page_offset": selected[-1] if len(ids) > 2 else None}
        if path.endswith("/query"):
            allowed = body["filter"]["must"][0]["has_id"]
            hits = [{"id": pid, "score": sum(a*b for a, b in zip(body["query"], p["vector"]))}
                    for pid, p in points.items() if pid in allowed]
            return {"points": sorted(hits, key=lambda p: -p["score"])[:body["limit"]]}
        if "/delete" in path:
            for pid in body["points"]:
                points.pop(pid, None)
            return True
        if method == "PUT":
            points.update({p["id"]: p for p in body["points"]})
            return True
        raise AssertionError((method, path))


@pytest.fixture(params=["memory", "live"])
def backend(request, monkeypatch):
    if request.param == "live":
        url = os.getenv("HARNESS_QDRANT_TEST_URL")
        if not url:
            pytest.skip("Set HARNESS_QDRANT_TEST_URL to run real Qdrant integration")
        config = qr.QdrantConfig(url=url, api_key=os.getenv("HARNESS_QDRANT_API_KEY", ""))
        original = qr.QdrantREST
        created = set()

        class TrackedREST(original):
            def request(self, method, path, body=None, **kwargs):
                result = super().request(method, path, body, **kwargs)
                if method == "PUT" and "/points" not in path:
                    created.add(path)
                return result

        monkeypatch.setattr(qr, "QdrantREST", TrackedREST)
        yield config
        for path in created:
            original(config).request("DELETE", path)
        return
    memory = MemoryREST(qr.QdrantConfig())
    monkeypatch.setattr(qr, "QdrantREST", lambda config: memory)
    yield qr.QdrantConfig()


def test_incremental_sync_glob_deletion_and_workspace_isolation(tmp_path, backend):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "worker.py").write_text("# coalesce concurrent jobs\n")
    (a / "guide.md").write_text("job notes\n")
    (a / "extra.py").write_text("extra notes\n")
    (a / ".env").write_text("PRIVATE_VALUE=not-indexed\n")
    (b / "secret.py").write_text("# other repository only\n")
    embedder = Embedder()

    def search(root=a, **options):
        return qr.search_workspace_qdrant(root, "coalesce jobs", embedder=embedder,
                                          config=backend, cache_dir=tmp_path / "cache", **options)

    first = search()
    assert first["qdrant"]["upserted"] == 3
    assert first["matches"][0]["path"] == "worker.py"
    assert len(first["matches"][0]["indexed_source_sha256"]) == 64
    assert embedder.encoded == 3
    second = search(glob_pattern="*.py")
    assert second["qdrant"]["upserted"] == second["qdrant"]["deleted"] == 0
    assert all(m["path"].endswith(".py") for m in second["matches"])
    assert search()["qdrant"]["reused"] == 3  # glob did not evict guide.md
    (a / "worker.py").write_text("# coalesce updated jobs\n")
    changed = search()
    assert changed["qdrant"]["upserted"] == changed["qdrant"]["deleted"] == 1
    (a / "guide.md").unlink()
    removed = search()
    assert removed["qdrant"]["deleted"] == 1
    other = search(b)
    assert other["qdrant"]["collection"] != first["qdrant"]["collection"]
    assert [m["path"] for m in other["matches"]] == ["secret.py"]
    assert not any(m["path"] == "secret.py" for m in search()["matches"])
    (a / "worker.py").unlink()
    (a / "extra.py").unlink()
    assert search()["matches"] == []  # empty workspace still deletes stale vectors


def test_model_and_chunk_configuration_use_separate_collections(tmp_path, backend):
    (tmp_path / "worker.py").write_text("# coalesce work\n")
    emb = Embedder()
    options = {"embedder": emb, "config": backend, "cache_dir": tmp_path / "cache"}
    one = qr.search_workspace_qdrant(tmp_path, "work", **options)
    two = qr.search_workspace_qdrant(tmp_path, "work", chunk_lines=20, overlap=0, **options)
    emb.model_name = "qdrant-test-v2"
    three = qr.search_workspace_qdrant(tmp_path, "work", **options)
    assert len({r["qdrant"]["collection"] for r in [one, two, three]}) == 3


def test_registry_and_resume_policy(tmp_path, monkeypatch, backend):
    monkeypatch.setenv("HARNESS_QDRANT_URL", backend.url)
    monkeypatch.setenv("HARNESS_QDRANT_API_KEY", backend.api_key)
    monkeypatch.setenv("HARNESS_RETRIEVAL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(qr, "get_sentence_transformer_embedder", lambda model: Embedder())
    (tmp_path / "worker.py").write_text("# coalesce work\n")
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"), retrieval_backend="qdrant")
    result = registry.call("rag_search", query="coalesce")
    assert result.ok, result.output
    assert result.metadata["retrieval"] == "qdrant_hybrid_scoring"
    assert result.metadata["qdrant"]["upserted"] == 1
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    session = RunSession(store, "qdrant", registry, resume=False)
    session.initialize()
    assert RunSession(store, "qdrant", registry, resume=True).saved is not None
    monkeypatch.setenv("HARNESS_QDRANT_URL", "http://127.0.0.1:1")
    changed = build_registry(tmp_path, registry.trace, retrieval_backend="qdrant")
    with pytest.raises(ValueError, match="Resume requires"):
        RunSession(store, "qdrant", changed, resume=True)


@pytest.mark.parametrize("url", ["http://example.com", "https://user:pass@localhost",
                                     "http://localhost/?key=x", "file:///tmp/qdrant",
                                     "http://localhost/path", "http://localhost/#fragment"])
def test_unsafe_endpoint_rejected(url):
    with pytest.raises(ValueError):
        qr.QdrantConfig(url=url)


def test_vectors_weights_and_zero_limit(tmp_path):
    for values in ([], [0.0], [float("nan")], [float("inf")]):
        with pytest.raises(ValueError):
            qr._vector(values)
    with pytest.raises(ValueError):
        qr._vector([1, 2], 3)
    with pytest.raises(ValueError):
        qr.search_workspace_qdrant(tmp_path, "work", lexical_weight=2)
    assert qr.search_workspace_qdrant(tmp_path, "work", limit=0)["matches"] == []


def test_service_failure_is_redacted_and_never_falls_back(tmp_path, monkeypatch):
    (tmp_path / "worker.py").write_text("# coalesce work\n")
    monkeypatch.setenv("HARNESS_QDRANT_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("HARNESS_QDRANT_API_KEY", "synthetic-sensitive-value")
    monkeypatch.setattr(qr, "get_sentence_transformer_embedder", lambda model: Embedder())
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"), retrieval_backend="qdrant")
    monkeypatch.setenv("HARNESS_RETRIEVAL_CACHE_DIR", str(tmp_path / "cache"))
    result = registry.call("rag_search", query="work")
    assert not result.ok
    assert "Qdrant" in result.output and "synthetic-sensitive-value" not in result.output


def test_mcp_sdk_returns_qdrant_evidence(tmp_path, monkeypatch, backend):
    from mcp import Client

    from harness.mcp_sdk import build_mcp_sdk_server

    monkeypatch.setenv("HARNESS_RETRIEVAL_BACKEND", "qdrant")
    monkeypatch.setenv("HARNESS_QDRANT_URL", backend.url)
    monkeypatch.setenv("HARNESS_QDRANT_API_KEY", backend.api_key)
    monkeypatch.setenv("HARNESS_RETRIEVAL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(qr, "get_sentence_transformer_embedder", lambda model: Embedder())
    (tmp_path / "worker.py").write_text("# coalesce concurrent jobs\n")
    server = build_mcp_sdk_server(tmp_path, tmp_path / "trace.jsonl")

    async def exercise():
        async with Client(server) as client:
            return await client.call_tool("retrieve_then_read", {"query": "coalesce jobs"})

    called = asyncio.run(exercise())
    assert not called.is_error
    metadata = called.structured_content["metadata"]
    assert metadata["retrieval"] == "qdrant_hybrid_scoring"
    assert "worker.py" in called.content[0].text


def test_changed_source_during_query_is_not_returned(tmp_path, monkeypatch):
    source = tmp_path / "worker.py"
    source.write_text("# coalesce original work\n")
    memory = MemoryREST(qr.QdrantConfig())
    original = memory.request

    def request(method, path, body=None, **kwargs):
        result = original(method, path, body, **kwargs)
        if path.endswith("/query"):
            source.write_text("# changed after indexing\n")
        return result

    memory.request = request
    monkeypatch.setattr(qr, "QdrantREST", lambda config: memory)
    result = qr.search_workspace_qdrant(tmp_path, "coalesce", embedder=Embedder(),
                                        cache_dir=tmp_path / "cache")
    assert result["matches"] == []


def test_partial_upsert_failure_reconciles_on_next_explicit_call(tmp_path, monkeypatch):
    (tmp_path / "worker.py").write_text("# coalesce original work\n")
    memory = MemoryREST(qr.QdrantConfig())
    original = memory.request
    failed = False

    def request(method, path, body=None, **kwargs):
        nonlocal failed
        result = original(method, path, body, **kwargs)
        if "/points?" in path and not failed:
            failed = True
            raise qr.QdrantRequestError("Qdrant HTTP 503")
        return result

    memory.request = request
    monkeypatch.setattr(qr, "QdrantREST", lambda config: memory)
    options = {"embedder": Embedder(), "cache_dir": tmp_path / "cache"}
    with pytest.raises(qr.QdrantRequestError):
        qr.search_workspace_qdrant(tmp_path, "coalesce", **options)
    assert qr.search_workspace_qdrant(tmp_path, "coalesce", **options)["qdrant"]["reused"] == 1


def test_remote_backend_requires_operator_opt_in_and_errors_disable_retries(tmp_path):
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    result = registry.call("rag_search", query="work", backend="qdrant")
    assert not result.ok and "explicitly" in result.output
    tool = registry._tools["rag_search"]
    assert not registry._should_retry_tool(tool, qr.QdrantRequestError("HTTP 503 timeout"), 0)


def test_qdrant_benchmark_reports_persistent_sync_not_json_cache(tmp_path, monkeypatch):
    from harness.retrieval_benchmark import (
        build_retrieval_benchmark_report,
        run_retrieval_benchmark,
    )

    memory = MemoryREST(qr.QdrantConfig())
    monkeypatch.setattr(qr, "QdrantREST", lambda config: memory)
    monkeypatch.setattr(qr, "get_sentence_transformer_embedder", lambda model: Embedder())
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "worker.py").write_text("# coalesce concurrent jobs\n")
    spec = tmp_path / "judgments.json"
    spec.write_text(json.dumps({"schema_version": 1, "corpus_root": "corpus", "cases": [
        {"case_id": "worker", "query": "coalesce", "relevant_paths": ["worker.py"]}]}))
    result = run_retrieval_benchmark(spec, backend="qdrant",
                                     backend_options={"cache_dir": tmp_path / "cache"})
    assert result["summary"]["mrr"] == 1
    assert result["configuration"]["qdrant_runtime"]["upserted"] == 1
    report = build_retrieval_benchmark_report(result)
    assert "Qdrant sync totals" in report and "Document embedding cache" not in report


@pytest.mark.parametrize("status", [200, 302, 401, 503])
def test_rest_auth_no_redirect_and_redacted_errors(status):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(self.headers.get("api-key"))
            self.send_response(status)
            self.send_header("Location", "/credential-leak")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "result": {"ready": True}}).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    try:
        client = qr.QdrantREST(qr.QdrantConfig(url=f"http://127.0.0.1:{server.server_port}",
                                             api_key="synthetic-api-key"))
        if status == 200:
            assert client.request("GET", "/collections")["ready"]
        else:
            with pytest.raises(qr.QdrantRequestError) as error:
                client.request("GET", "/collections")
            assert "synthetic-api-key" not in str(error.value)
        assert received == ["synthetic-api-key"]  # redirects/retries never forwarded the key
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
