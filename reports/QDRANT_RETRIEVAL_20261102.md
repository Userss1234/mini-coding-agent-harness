# Optional Qdrant Retrieval: Implementation and Live Validation

Date: 2026-11-02. Local Windows / Python 3.12.2 / Docker Linux engine 29.9.2.
Changes remain uncommitted and unpushed at the user's request. No resume edits or paid model runs.

## Delivered

- Optional `qdrant` selection behind the existing Agent/preflight/MCP retrieval tools and
  retrieval-quality CLI. Local lexical remains the default and local hybrid remains available.
- Qdrant REST adapter with bounded response size, authentication, request deadlines, no redirects,
  no environment proxy, explicit remote-HTTPS opt-in and no automatic fallback/retry.
- Separate collections for workspace/model/dimension/index-version/chunk settings. A model cannot
  activate the service through tool arguments without operator backend selection.
- Content-addressed point IDs, incremental missing-vector embedding/upsert, stale-vector deletion,
  batched mutations and single-host synchronization locking. Query glob filtering never deletes
  unrelated files from the complete corpus index.
- Semantic and lexical candidate-union fusion; source snippets and line/hash evidence are loaded
  from safe local chunks and revalidated before output, not trusted from remote payload text.
- Run policy binds service, credential digest, model, weights and index version for resume.
- Pinned Docker Compose service, localhost-only published REST port, required API key, persistent
  volumes, resource limits and an actual-service CI job. CI has not run remotely for these changes.

Implementation: `harness/qdrant_retrieval.py`; operations/limits: `docs/QDRANT_RETRIEVAL.md`.
SQLite continues to store Agent runs/checkpoints/tool-call records; it is not replaced by Qdrant.

## Final Quality Gates

| Check | Result |
| --- | --- |
| Complete pytest suite, actual Qdrant enabled | 364 passed, 1 optional Windows symlink skip |
| Branch-enabled coverage | 83.59% (75% required) |
| Focused Qdrant/MCP/report compatibility | 51 passed |
| Ruff | pass |
| mypy | pass, 36 source files |
| compileall / pip dependency check | pass |
| Strict unhandled-thread-exception gate | pass |
| Existing scripted compatibility benchmark | 40/40 pass |

Raw compatibility artifacts: `artifacts/QDRANT_COMPAT_20261102.md`, `.json`, and
`artifacts/qdrant-compat-20261102-runs/`. This uses the original lexical scripted mode and
does not claim 40 autonomous Qdrant-backed model completions.

The first full pass exposed one outdated MCP-schema assertion that listed only two retrieval
backends. It was updated to the new three-backend contract; the final complete run above passed.
No acceptance verifier was weakened, and historical reports were not rescored.

## Actual Docker Service

Tested image: `qdrant/qdrant:v1.16.3`.
Pulled digest: `sha256:0425e3e03e7fd9b3dc95c4214546afe19de2eb2e28ca621441a56663ac6e1f46`.
Service: `mini-agent-retrieval-qdrant-1`; host endpoint `127.0.0.1:6333`.
Credential is generated locally and retained only in process/container configuration, not reports.
Named volumes preserve storage and snapshots. The service remains running for local use.

Live deterministic tests cover first indexing/reuse, changed-file invalidation, deleted-file
cleanup, narrow globs, empty-corpus cleanup, repository/model/chunk separation, registry dispatch,
resume configuration rejection and official SDK MCP evidence reads. Additional controlled tests
cover authentication, refused redirects, unavailable service, partial-upsert reconciliation and
source mutation during queries. Live tests remove only the collections they create.

The read-only root produces a nonfatal startup warning when Qdrant tries to write the optional
`.qdrant-initialized` indicator. Actual storage writes and restart reuse pass; no warning is hidden.
Cached model loading emits the existing Hugging Face `resume_download` deprecation warning.

## Real Model, Persistence and MCP

See `QDRANT_PERSISTENCE_MCP_20261102.json`:

- Actual cached `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, no embedding API.
- Docker container restart followed by the same query: all 37 vectors reused, zero upserts or
  deletions, identical returned path ordering. This proves restart persistence for the fixture.
- Incorrect database API key rejected by the actual server.
- Official MCP SDK stdio client launches the actual `main.py mcp-server` child with explicit
  Qdrant environment. `retrieve_then_read` returns `inventory.py` first and two source reads;
  all 37 stored vectors are reused. No FakeClient or fake embedder in this smoke.

See `QDRANT_QUALITY_20261102.md` / `.json` for the unchanged 28-query, 24-file development corpus:

| Metric | Qdrant / real MiniLM |
| --- | --- |
| MRR | 0.9762 |
| Recall@5 | 1.0000 |
| Zero-result queries | 0 |
| Quality gate | pass |

These metrics match the previous same-corpus local hybrid metrics, not an improvement from adding
a database. The final warm report counts 1,036 vector-reuse observations (28 x 37), not 1,036
distinct vectors. Earlier first indexing and live tests establish insertion separately.

## Execution Isolation Is Separate

The actual execution-sandbox recheck is `QDRANT_DOCKER_BOUNDARY_20261102.md`: UID 10001,
workspace mount and blocked network pass under the existing resource/read-only-root policy.
An actual `WorkspaceSession` copy was modified in Docker, generated one review entry and left
the fixture source hashes unchanged; a sleeping container timed out and was removed.
Qdrant connectivity is host-side retrieval and does not relax the code sandbox's `network none`.
Container isolation is not a VM or a proven hostile multi-tenant security boundary.

## Claim Boundaries

This is a single-host, development-scale backend, not a distributed index coordinator. Queries
still reread safe sources and scroll IDs; locks require a common local cache directory. The
candidate union is bounded and may differ from exhaustive fusion at larger sizes. Namespace
separation is not independent database authorization. Old configuration collections require
operator cleanup, and the model name alone does not attest immutable weights: use a fixed model
directory and bump index version after changing weights under the same identifier.
No 50k-chunk capacity, lower latency, higher Agent completion rate or new model-quality claim.
Historical raw 9/12 Agent reports and their acceptance-contract ambiguity remain unchanged.
