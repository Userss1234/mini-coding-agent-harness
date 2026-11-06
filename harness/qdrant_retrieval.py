from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import NAMESPACE_URL, uuid5

from .hybrid_retrieval import (
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
    get_sentence_transformer_embedder,
)
from .retrieval import build_workspace_index, search_retrieval_index, tokenize_query
from .run_store import SQLiteRunStore


@dataclass(frozen=True)
class QdrantConfig:
    url: str = "http://127.0.0.1:6333"
    api_key: str = ""
    timeout: float = 10
    allow_remote: bool = False
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    lexical_weight: float = 0.35
    semantic_weight: float = 0.65
    index_version: str = "1"

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}
                or (not local and (not self.allow_remote or parsed.scheme != "https"))):
            raise ValueError("Qdrant requires loopback HTTP(S), or explicitly allowed remote HTTPS")
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 60:
            raise ValueError("Qdrant timeout must be within (0, 60] seconds")
        if (not self.embedding_model.strip() or not self.index_version.strip()
                or not all(math.isfinite(w) and w >= 0
                           for w in (self.lexical_weight, self.semantic_weight))
                or abs(self.lexical_weight + self.semantic_weight - 1) > 1e-6):
            raise ValueError("Qdrant requires a model and normalized nonnegative weights")

    @classmethod
    def from_env(cls) -> QdrantConfig:
        return cls(
            url=os.getenv("HARNESS_QDRANT_URL", "http://127.0.0.1:6333").rstrip("/"),
            api_key=os.getenv("HARNESS_QDRANT_API_KEY", ""),
            timeout=float(os.getenv("HARNESS_QDRANT_TIMEOUT", "10")),
            allow_remote=os.getenv("HARNESS_QDRANT_ALLOW_REMOTE", "").lower() == "true",
            embedding_model=os.getenv("HARNESS_RETRIEVAL_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            lexical_weight=float(os.getenv("HARNESS_RETRIEVAL_LEXICAL_WEIGHT", "0.35")),
            semantic_weight=float(os.getenv("HARNESS_RETRIEVAL_SEMANTIC_WEIGHT", "0.65")),
            index_version=os.getenv("HARNESS_QDRANT_INDEX_VERSION", "1"),
        )

    def policy(self) -> dict[str, Any]:
        return {"url": self.url, "timeout": self.timeout, "allow_remote": self.allow_remote,
                "authentication_fingerprint": hashlib.sha256(self.api_key.encode()).hexdigest(),
                "embedding_model": self.embedding_model, "lexical_weight": self.lexical_weight,
                "semantic_weight": self.semantic_weight, "index_version": self.index_version}


class QdrantRequestError(RuntimeError):
    retryable = False


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class QdrantREST:
    """Small bounded adapter for Qdrant's documented JSON REST API; no implicit retries."""

    def __init__(self, config: QdrantConfig):
        self.config = config
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def request(self, method: str, path: str, body: Any = None,
                *, missing_ok: bool = False) -> Any:
        data = json.dumps(body, allow_nan=False).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["api-key"] = self.config.api_key
        req = Request(self.config.url.rstrip("/") + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.config.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise QdrantRequestError("Qdrant response exceeds 16 MiB")
            payload = json.loads(raw)
            if payload.get("status") != "ok":
                raise QdrantRequestError("Qdrant returned unsuccessful status")
            return payload["result"]
        except HTTPError as exc:
            if missing_ok and exc.code == 404:
                return None
            raise QdrantRequestError(f"Qdrant HTTP {exc.code}; no fallback or automatic retry") from None
        except (URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            # Do not include URL credentials, response bodies, or transport exception text.
            raise QdrantRequestError(
                f"Qdrant request failed ({type(exc).__name__}); no fallback") from None


def _vector(values: Any, dimension: int | None = None) -> list[float]:
    result = [float(value) for value in values]
    norm = math.sqrt(sum(value * value for value in result))
    if (not result or not math.isfinite(norm) or norm == 0
            or (dimension is not None and len(result) != dimension)):
        raise ValueError("Embedding must be finite, nonzero and dimension-consistent")
    return [value / norm for value in result]


def search_workspace_qdrant(
    workspace: Path, query: str, *, glob_pattern: str = "*", limit: int = 5,
    chunk_lines: int = 80, overlap: int = 10, max_chars_per_chunk: int = 1200,
    embedder: EmbeddingProvider | None = None, embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path | None = None, lexical_weight: float = 0.35, semantic_weight: float = 0.65,
    chunk_strategy: str | None = None, config: QdrantConfig | None = None,
) -> dict[str, Any]:
    if (not all(math.isfinite(w) and w >= 0 for w in (lexical_weight, semantic_weight))
            or abs(lexical_weight + semantic_weight - 1) > 1e-6):
        raise ValueError("Retrieval weights must be nonnegative and sum to one")
    root = workspace.resolve()
    # Always synchronize the complete safe corpus, not the query glob: a narrow query must
    # never delete other files from the shared persistent index.
    index = build_workspace_index(root, chunk_lines=chunk_lines, overlap=overlap,
                                  chunk_strategy=chunk_strategy)
    selected = build_workspace_index(root, glob_pattern=glob_pattern, chunk_lines=chunk_lines,
                                     overlap=overlap, chunk_strategy=chunk_strategy)
    output: dict[str, Any] = {"query": str(query).strip(), "tokens": tokenize_query(query),
                              "matches": [], "index": selected.metadata(),
                              "retrieval": "qdrant_hybrid_scoring"}
    if not output["tokens"] or limit <= 0:
        return output
    active = embedder or get_sentence_transformer_embedder(embedding_model)
    model = str(active.model_name)
    query_vector = _vector(active.encode_query(query))
    active_config = config or QdrantConfig.from_env()
    identity = json.dumps(["v1", active_config.index_version, str(root), model,
                           len(query_vector), chunk_lines, overlap,
                           index.chunk_strategy], separators=(",", ":"))
    collection = "mini_agent_" + hashlib.sha256(identity.encode()).hexdigest()[:40]
    client = QdrantREST(active_config)
    base = "/collections/" + collection
    chunks = {str(uuid5(NAMESPACE_URL, json.dumps(
        [identity, c.path, c.start_line, c.end_line, c.text, c.source_sha256]
    ))): c for c in index.chunks}
    # This is a local single-host synchronization lock, not a distributed lease.
    lock_root = cache_dir or Path(os.getenv("HARNESS_RETRIEVAL_CACHE_DIR",
                                          str(Path.home() / ".cache/mini-coding-agent-harness")))
    locks = SQLiteRunStore(Path(lock_root) / "qdrant-sync.sqlite3")
    with locks.lock(collection):
        info = client.request("GET", base, missing_ok=True)
        if info is None:
            client.request("PUT", base, {"vectors": {"size": len(query_vector),
                                                     "distance": "Cosine"}})
        else:
            vectors = info["config"]["params"]["vectors"]
            if vectors.get("size") != len(query_vector) or vectors.get("distance") != "Cosine":
                raise ValueError("Existing Qdrant collection has incompatible vector configuration")
        existing: set[str] = set()
        offset = None
        for _ in range(1000):
            page = client.request("POST", base + "/points/scroll", {
                "limit": 256, "offset": offset, "with_payload": False, "with_vector": False})
            existing.update(str(point["id"]) for point in page["points"])
            following = page.get("next_page_offset")
            if following is None:
                break
            if following == offset:
                raise RuntimeError("Qdrant scroll did not advance")
            offset = following
        else:
            raise RuntimeError("Qdrant collection exceeds bounded scroll limit")
        missing = sorted(chunks.keys() - existing)
        for start in range(0, len(missing), 64):
            ids = missing[start:start + 64]
            encoded = list(active.encode_documents([
                f"Path: {chunks[pid].path}\n{chunks[pid].text}" for pid in ids]))
            if len(encoded) != len(ids):
                raise ValueError("Embedding provider returned an incorrect batch size")
            points = []
            for pid, values in zip(ids, encoded):
                chunk = chunks[pid]
                points.append({"id": pid, "vector": _vector(values, len(query_vector)), "payload": {
                    "path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line,
                    "source_sha256": chunk.source_sha256, "model": model}})
            client.request("PUT", base + "/points?wait=true", {"points": points})
        stale = sorted(existing - chunks.keys())
        for start in range(0, len(stale), 256):
            client.request("POST", base + "/points/delete?wait=true",
                           {"points": stale[start:start + 256]})
        selected_chunks = set(selected.chunks)
        selected_ids = [pid for pid, chunk in chunks.items() if chunk in selected_chunks]
        lexical = search_retrieval_index(selected, query, limit=len(selected.chunks),
                                         max_chars_per_chunk=max_chars_per_chunk)["matches"]
        lexical_scores = {(m["path"], m["start_line"], m["end_line"]): float(m["score"])
                          for m in lexical}
        max_lexical = max(lexical_scores.values(), default=0.0)
        candidates = min(max(int(limit) * 4, 40), 1000)

        def nearest(ids: list[str], count: int) -> list[dict[str, Any]]:
            if not ids:
                return []
            return client.request("POST", base + "/points/query", {
                "query": query_vector, "filter": {"must": [{"has_id": ids}]},
                "limit": count, "with_payload": False, "with_vector": False})["points"]

        semantic = nearest(selected_ids, candidates)
        lexical_ids = sorted(selected_ids, key=lambda pid: -lexical_scores.get(
            (chunks[pid].path, chunks[pid].start_line, chunks[pid].end_line), 0))[:candidates]
        combined = {str(p["id"]): p for p in semantic + nearest(lexical_ids, candidates)}
        # Re-enumeration also rechecks sensitive paths, deletions and links. Remote payloads
        # never supply evidence text: only still-current local chunks may be returned.
        current = build_workspace_index(root, glob_pattern=glob_pattern, chunk_lines=chunk_lines,
                                        overlap=overlap, chunk_strategy=chunk_strategy)
        valid = set(current.chunks)
        scored: list[dict[str, Any]] = []
        for pid, point in combined.items():
            evidence = chunks.get(pid)
            if evidence is None or pid not in selected_ids or evidence not in valid:
                continue
            cosine = float(point["score"])
            if not math.isfinite(cosine):
                raise RuntimeError("Qdrant returned nonfinite similarity")
            raw = lexical_scores.get((evidence.path, evidence.start_line, evidence.end_line), 0.0)
            lex = raw / max_lexical if max_lexical else 0.0
            sem = max(0.0, min((cosine + 1) / 2, 1.0))
            scored.append({"path": evidence.path, "start_line": evidence.start_line,
                           "end_line": evidence.end_line, "snippet": evidence.text[:max_chars_per_chunk],
                           "indexed_source_sha256": evidence.source_sha256,
                           "score": round(lexical_weight * lex + semantic_weight * sem, 6),
                           "lexical_score": raw, "lexical_normalized": lex,
                           "semantic_score": cosine, "semantic_normalized": sem})
        scored.sort(key=lambda m: (-m["score"], -m["semantic_score"], m["path"], m["start_line"]))
        output["matches"] = scored[:int(limit)]
        output["hybrid"] = {"embedding_model": model, "embedding_dimension": len(query_vector),
                            "lexical_weight": lexical_weight, "semantic_weight": semantic_weight}
        output["qdrant"] = {"collection": collection, "upserted": len(missing),
                            "deleted": len(stale), "reused": len(chunks) - len(missing),
                            "candidate_limit": candidates, "candidates_scored": len(scored)}
    return output
