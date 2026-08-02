from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Protocol, Sequence

from .retrieval import (
    RetrievalChunk,
    RetrievalIndex,
    build_workspace_index,
    search_retrieval_index,
    tokenize_query,
)


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_LEXICAL_WEIGHT = 0.35
DEFAULT_SEMANTIC_WEIGHT = 0.65


class EmbeddingProvider(Protocol):
    model_name: str

    def encode_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...

    def encode_query(self, text: str) -> Sequence[float]:
        ...


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        model_cache_dir: Path | None = None,
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.model_cache_dir = model_cache_dir
        self.device = device
        self._model: Any = None

    def encode_documents(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load_model()
        method = getattr(model, "encode_document", None) or model.encode
        return _as_vectors(method(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ))

    def encode_query(self, text: str) -> list[float]:
        model = self._load_model()
        method = getattr(model, "encode_query", None) or model.encode
        vectors = _as_vectors(method(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ))
        return vectors[0]

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Hybrid retrieval requires the optional local dependency. "
                "Install it with: python -m pip install -e \".[retrieval]\""
            ) from exc
        self._model = SentenceTransformer(
            self.model_name,
            cache_folder=str(self.model_cache_dir) if self.model_cache_dir else None,
            device=self.device,
        )
        return self._model


@dataclass(frozen=True)
class EmbeddingCacheStats:
    path: Path
    hits: int
    misses: int
    entries: int
    written: bool

    def metadata(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "hits": self.hits,
            "misses": self.misses,
            "entries": self.entries,
            "written": self.written,
        }


def search_workspace_hybrid(
    workspace: Path,
    query: str,
    *,
    glob_pattern: str = "*",
    limit: int = 5,
    chunk_lines: int = 80,
    overlap: int = 10,
    max_chars_per_chunk: int = 1200,
    embedder: EmbeddingProvider | None = None,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path | None = None,
    lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
) -> dict[str, Any]:
    query_text = str(query).strip()
    tokens = tokenize_query(query_text)
    _validate_weights(lexical_weight, semantic_weight)
    root = workspace.resolve()
    index = build_workspace_index(
        root,
        glob_pattern=glob_pattern,
        chunk_lines=chunk_lines,
        overlap=overlap,
    )
    if not query_text or not tokens or limit <= 0:
        return {
            "query": query_text,
            "tokens": tokens,
            "matches": [],
            "index": index.metadata(),
            "retrieval": "local_chunk_hybrid_scoring",
        }
    if not index.chunks:
        return {
            "query": query_text,
            "tokens": tokenize_query(query_text),
            "matches": [],
            "index": index.metadata(),
            "retrieval": "local_chunk_hybrid_scoring",
        }

    active_embedder = embedder or get_sentence_transformer_embedder(embedding_model)
    model_name = str(getattr(active_embedder, "model_name", embedding_model))
    query_vector = _normalize_vector(active_embedder.encode_query(query_text))
    document_vectors, cache_stats = _document_embeddings(
        root,
        index,
        active_embedder,
        model_name=model_name,
        cache_dir=cache_dir,
        expected_dimension=len(query_vector),
    )
    lexical_result = search_retrieval_index(
        index,
        query_text,
        limit=len(index.chunks),
        max_chars_per_chunk=max_chars_per_chunk,
    )
    lexical_matches = {
        _match_key(item): item
        for item in lexical_result.get("matches") or []
    }
    max_lexical = max(
        (float(item.get("score", 0.0)) for item in lexical_matches.values()),
        default=0.0,
    )

    scored = []
    for chunk, document_vector in zip(index.chunks, document_vectors):
        key = _chunk_identity(chunk)
        lexical = lexical_matches.get(key) or {}
        lexical_score = float(lexical.get("score", 0.0))
        lexical_normalized = lexical_score / max_lexical if max_lexical > 0 else 0.0
        cosine = _dot(query_vector, _normalize_vector(document_vector))
        semantic_normalized = max(0.0, min((cosine + 1.0) / 2.0, 1.0))
        fused_score = (
            lexical_weight * lexical_normalized
            + semantic_weight * semantic_normalized
        )
        snippet = chunk.text
        if len(snippet) > max_chars_per_chunk:
            snippet = snippet[:max_chars_per_chunk] + (
                f"\n... ({len(snippet) - max_chars_per_chunk} more chars)"
            )
        scored.append({
            "path": chunk.path,
            "score": round(fused_score, 6),
            "lexical_score": round(lexical_score, 6),
            "lexical_normalized": round(lexical_normalized, 6),
            "semantic_score": round(cosine, 6),
            "semantic_normalized": round(semantic_normalized, 6),
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "snippet": snippet,
        })

    scored.sort(
        key=lambda item: (
            -float(item["score"]),
            -float(item["semantic_score"]),
            str(item["path"]),
            int(item["start_line"]),
        )
    )
    return {
        "query": query_text,
        "tokens": tokens,
        "matches": scored[:max(int(limit), 0)],
        "index": index.metadata(),
        "retrieval": "local_chunk_hybrid_scoring",
        "hybrid": {
            "embedding_model": model_name,
            "embedding_dimension": len(query_vector),
            "lexical_weight": lexical_weight,
            "semantic_weight": semantic_weight,
            "cache": cache_stats.metadata(),
        },
    }


def _document_embeddings(
    workspace: Path,
    index: RetrievalIndex,
    embedder: EmbeddingProvider,
    *,
    model_name: str,
    cache_dir: Path | None,
    expected_dimension: int,
) -> tuple[list[list[float]], EmbeddingCacheStats]:
    cache_path = _embedding_cache_path(workspace, model_name, cache_dir)
    cached = _load_cache(cache_path, model_name)
    active_entries: dict[str, list[float]] = {}
    missing_chunks: list[RetrievalChunk] = []
    hits = 0

    for chunk in index.chunks:
        key = _cache_key(chunk)
        vector = cached.get(key)
        if vector and len(vector) == expected_dimension:
            active_entries[key] = vector
            hits += 1
        else:
            missing_chunks.append(chunk)

    if missing_chunks:
        encoded = _as_vectors(embedder.encode_documents([
            _embedding_document(chunk)
            for chunk in missing_chunks
        ]))
        if len(encoded) != len(missing_chunks):
            raise RuntimeError("Embedding provider returned the wrong number of document vectors.")
        for chunk, vector in zip(missing_chunks, encoded):
            if len(vector) != expected_dimension:
                raise RuntimeError("Embedding provider returned inconsistent vector dimensions.")
            active_entries[_cache_key(chunk)] = _normalize_vector(vector)

    vectors = [active_entries[_cache_key(chunk)] for chunk in index.chunks]
    written = bool(missing_chunks) or len(active_entries) != len(cached)
    if written:
        _write_cache(cache_path, model_name, active_entries)
    return vectors, EmbeddingCacheStats(
        path=cache_path,
        hits=hits,
        misses=len(missing_chunks),
        entries=len(active_entries),
        written=written,
    )


@lru_cache(maxsize=4)
def get_sentence_transformer_embedder(model_name: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(model_name)


def _embedding_cache_path(
    workspace: Path,
    model_name: str,
    cache_dir: Path | None,
) -> Path:
    base = cache_dir or Path(os.getenv(
        "HARNESS_RETRIEVAL_CACHE_DIR",
        Path.home() / ".cache" / "mini-coding-agent-harness" / "retrieval",
    ))
    workspace_key = hashlib.sha256(str(workspace).lower().encode("utf-8")).hexdigest()[:16]
    model_key = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:12]
    return Path(base).expanduser().resolve() / f"{workspace_key}-{model_key}.json"


def _load_cache(path: Path, model_name: str) -> dict[str, list[float]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return {}
    if payload.get("model") != model_name or not isinstance(payload.get("entries"), dict):
        return {}
    entries = {}
    for key, vector in payload["entries"].items():
        if isinstance(key, str) and isinstance(vector, list) and vector:
            try:
                entries[key] = [float(value) for value in vector]
            except (TypeError, ValueError):
                continue
    return entries


def _write_cache(path: Path, model_name: str, entries: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "model": model_name,
        "entries": entries,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def _embedding_document(chunk: RetrievalChunk) -> str:
    return f"Path: {chunk.path}\n{chunk.text}"


def _cache_key(chunk: RetrievalChunk) -> str:
    value = f"{chunk.path}\0{chunk.start_line}\0{chunk.end_line}\0{chunk.text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _chunk_identity(chunk: RetrievalChunk) -> tuple[str, int, int]:
    return chunk.path, chunk.start_line, chunk.end_line


def _match_key(item: dict[str, Any]) -> tuple[str, int, int]:
    return str(item["path"]), int(item["start_line"]), int(item["end_line"])


def _validate_weights(lexical_weight: float, semantic_weight: float) -> None:
    if not math.isfinite(lexical_weight) or not math.isfinite(semantic_weight):
        raise ValueError("Hybrid retrieval weights must be finite.")
    if lexical_weight < 0 or semantic_weight < 0:
        raise ValueError("Hybrid retrieval weights must be non-negative.")
    if lexical_weight + semantic_weight <= 0:
        raise ValueError("At least one hybrid retrieval weight must be positive.")


def _as_vectors(values: Any) -> list[list[float]]:
    if hasattr(values, "tolist"):
        values = values.tolist()
    return [[float(value) for value in vector] for vector in values]


def _normalize_vector(values: Sequence[float]) -> list[float]:
    vector = [float(value) for value in values]
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 0:
        return vector
    return [value / magnitude for value in vector]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise RuntimeError("Query and document embedding dimensions do not match.")
    return sum(a * b for a, b in zip(left, right))
