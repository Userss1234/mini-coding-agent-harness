# Optional Qdrant Retrieval

SQLite remains the durable Agent run/checkpoint/tool ledger. Qdrant is a separate optional
vector store for derived code indexes, not a replacement for SQLite or a web framework.
The default backend is still `lexical`; `hybrid` still works without a vector service.
No new Python runtime dependency is required for the documented Qdrant REST adapter.
Embeddings still require the existing optional `.[retrieval]` dependencies and a local model.

## Start Locally (PowerShell)

```powershell
python -m pip install -e ".[retrieval]"
$env:HARNESS_QDRANT_API_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
docker compose -f compose.qdrant.yaml up -d
$env:HARNESS_RETRIEVAL_BACKEND = "qdrant"
python main.py --workspace path/to/repository ask "Find the reservation validation logic"
```

Keep the same key in the requesting process and service. Do not commit it or paste it into
prompts. A new terminal must obtain it from your local secret manager; for an already-running
local development container, this sets it without printing the value:

```powershell
$container = docker inspect mini-agent-retrieval-qdrant-1 | ConvertFrom-Json
$env:HARNESS_QDRANT_API_KEY = ($container.Config.Env | Where-Object {
  $_.StartsWith('QDRANT__SERVICE__API_KEY=')
}).Substring('QDRANT__SERVICE__API_KEY='.Length)
$env:HARNESS_RETRIEVAL_BACKEND = "qdrant"
```

The same environment enables Qdrant for `mcp-server` and `mcp-http`, including
`rag_search`, `rag_explain`, `retrieve_then_read` and `context_pack`.
Alternatively use `ask --retrieval-backend qdrant`. A model cannot enable the remote backend
merely by passing `backend=qdrant` to a registry that the operator configured as lexical/hybrid.
`index_workspace` and `rag_symbols` remain local tools.

The Compose service pins the tested Qdrant `v1.16.3` image, binds REST only to `127.0.0.1`,
requires an API key, disables telemetry, drops capabilities, sets resource limits and uses named
storage/snapshot volumes. No host gRPC port is published. `docker compose stop` preserves data;
do not run `down --volumes` unless intentionally deleting the vector indexes.
The tested read-only root configuration emits a startup warning for the nonessential
`.qdrant-initialized` marker; storage is writable through the named volume.

## Index Lifecycle

1. Every nonempty query scans the complete safe workspace corpus; query globs only filter retrieval.
2. A collection identity hashes resolved workspace path, schema/index version, embedding model
   identifier, dimension and chunk settings. Different repositories cannot share a collection
   accidentally. This is namespace separation, not database-user authorization.
3. Content-addressed UUIDs include path, line range, chunk text and indexed-source SHA-256.
4. Scroll reads existing IDs. Only missing points are embedded and upserted in batches of 64.
   Stale IDs are deleted in batches of 256 after upserts succeed; all mutations use `wait=true`.
5. A single-host SQLite process lock serializes synchronizers using the same cache directory.
6. Semantic candidates and top lexical candidates are scored by Qdrant and fused using the
   existing default 0.35 lexical / 0.65 semantic weights. Candidate budget is
   `min(max(4 * limit, 40), 1000)` per branch, not a full-corpus exact hybrid ranking guarantee.
7. A final safe local scan discards changed/deleted evidence. Snippets, paths and hashes come
   from current local chunks, never from untrusted database payload text.

The collection stores vectors and path/line/hash/model metadata, not source snippets or
provider credentials. Vectors themselves are derived sensitive data; protect the volumes.
An edit changes all chunk IDs for that file because the source hash is file-prefix scoped.
Existing private/generated-file exclusions and the 200,000-character indexed-file cap apply.
Hashes represent normalized indexed text, not a full raw-file approval digest.

## Configuration

| Variable | Default / meaning |
| --- | --- |
| `HARNESS_QDRANT_URL` | `http://127.0.0.1:6333` |
| `HARNESS_QDRANT_PORT` | Compose host port, default `6333`; also update URL for a different port |
| `HARNESS_QDRANT_API_KEY` | Service credential; Compose requires a nonempty value |
| `HARNESS_QDRANT_TIMEOUT` | Per-request timeout, default 10 seconds, maximum 60 |
| `HARNESS_QDRANT_ALLOW_REMOTE` | Explicit `true` required for non-loopback HTTPS |
| `HARNESS_QDRANT_INDEX_VERSION` | `1`; bump after changing model weights/revision under the same model name |
| `HARNESS_RETRIEVAL_EMBEDDING_MODEL` | Existing MiniLM default; prefer an immutable local model directory |
| `HARNESS_RETRIEVAL_CACHE_DIR` | Local sync-lock directory; keep consistent across processes |

URLs cannot contain credentials, query strings, fragments or path prefixes. Redirects and
environment proxies are disabled. Remote HTTP is rejected. Loopback HTTP is development-only.
Remote HTTPS opt-in can transmit code-derived embeddings and metadata outside this computer.
Response bodies and transport errors do not leak API keys in error messages.
Endpoint, credential digest, model, weights and index version are captured in the Qdrant run
policy. Resume rejects changes rather than silently switching service or model.

## Failures and Limits

There is no automatic local fallback or request retry. Service/authentication/timeout errors
surface as failed tools. Upserts/deletes are idempotent derived-index operations: if a response
is lost, the next explicit query rescans the service and reconciles IDs. Never translate this
into retry permission for arbitrary external write tools.

This is a single-host, development-scale synchronizer: source is reread on queries, IDs are
scrolled, and current-ID filters are sent to the server. It is not a distributed index service,
transactional filesystem snapshot, tenant security boundary or demonstrated 50k-chunk solution.
Collection settings/model changes create new collections; older collections require explicit
operator cleanup. No background collection deletion or arbitrary collection-name override exists.

The vector service runs separately from code-execution sandboxes. Do not attach the Docker
socket to Agent workspaces or open their `--network none` policy to reach Qdrant. The host-side
retrieval adapter communicates with the service; isolated execution only mounts the copy.

## Verification

```powershell
$env:HARNESS_QDRANT_TEST_URL = $env:HARNESS_QDRANT_URL
# If URL is unset, use http://127.0.0.1:6333 explicitly.
python -m pytest tests/test_qdrant_retrieval.py -q
python main.py retrieval-benchmark --backend qdrant --chunk-strategy python `
  --judgments benchmarks/retrieval-v2/judgments.json `
  --output artifacts/QDRANT_QUALITY.md --json-output artifacts/QDRANT_QUALITY.json
```

Tests use a deterministic synthetic embedder and both an in-memory REST double and real Qdrant
when the test URL is set. The real model benchmark is separate; no model API payment is needed.
CI includes an actual Qdrant service job, but local results do not imply remote CI has run.
See [implementation and live evidence](../reports/QDRANT_RETRIEVAL_20261102.md).

API references: [query points](https://api.qdrant.tech/api-reference/search/query-points),
[scroll](https://api.qdrant.tech/api-reference/points/scroll-points),
[local deployment](https://qdrant.tech/documentation/quickstart/).
