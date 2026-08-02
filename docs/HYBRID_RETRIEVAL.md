# Hybrid Retrieval

The base installation keeps lexical retrieval as the deterministic offline default. The optional hybrid backend adds local dense embeddings and score fusion without requiring a model API key or vector database.

## Install And Run

```powershell
python -m pip install -e ".[retrieval]"
python main.py retrieval-benchmark --backend hybrid
```

The default model is [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), a 384-dimensional local sentence encoder. Its first use downloads model weights into the Hugging Face cache. Later runs reuse those files.

Select hybrid retrieval for actual agent and MCP tool calls with environment configuration:

```dotenv
HARNESS_RETRIEVAL_BACKEND=hybrid
HARNESS_RETRIEVAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
HARNESS_RETRIEVAL_LEXICAL_WEIGHT=0.35
HARNESS_RETRIEVAL_SEMANTIC_WEIGHT=0.65
```

Individual `context_pack`, `rag_search`, `rag_explain`, and `retrieve_then_read` calls can also pass `backend="hybrid"`. The environment default remains `lexical` so a base install never downloads a model unexpectedly.

## Ranking

1. Build the same safe, line-aware workspace chunk index used by lexical retrieval.
2. Normalize lexical chunk scores against the best lexical match.
3. Encode the query and each chunk locally, then calculate cosine similarity.
4. Normalize semantic similarity and fuse it with lexical scoring using configurable weights.
5. Sort fused chunk scores, then let the benchmark deduplicate ranked chunks to paths.

The committed weights are 0.35 lexical and 0.65 semantic. They are fixed for every query in the judged set.

## Incremental Cache

Document embeddings are stored outside the repository by default under `~/.cache/mini-coding-agent-harness/retrieval`. Set `HARNESS_RETRIEVAL_CACHE_DIR` to move the cache.

Each cache key includes the model name, relative path, line range, and chunk text. Repeated queries reuse unchanged document vectors. Editing one chunk invalidates only that chunk, while stale entries are removed on the next write. Cache files are written through a temporary file and atomically replaced.

## Evidence

| Backend | MRR | Recall@1 | Recall@3 | Recall@5 |
|---|---:|---:|---:|---:|
| Lexical | 0.8000 | 0.70 | 0.80 | 0.80 |
| Hybrid MiniLM | 0.9000 | 0.70 | 1.00 | 1.00 |

Both paraphrased semantic cases missed by lexical retrieval are rank 2 with hybrid retrieval. See `reports/RETRIEVAL_QUALITY_BASELINE.md` and `reports/RETRIEVAL_QUALITY_HYBRID.md` for per-query rankings.

## Boundaries

- The committed result covers a small project-specific 10-query fixture. It is regression evidence, not a broad code-retrieval benchmark.
- The first run needs network access to download the configured model. Encoding is local after download.
- The default implementation performs an in-memory scan over all indexed chunks. It is appropriate for small repositories, not a large-scale vector service.
- The JSON embedding cache is incremental storage, not a vector database.
