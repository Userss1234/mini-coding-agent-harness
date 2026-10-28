# Priority 4: Evaluation and Retrieval Credibility

Status: **local engineering complete; live Docker/hybrid/agent evidence remains outstanding**

Historical stage status above is retained. Follow-up actual local Docker, hybrid reverse-order,
MCP and paid agent ABBA results are in [LIVE_VALIDATION_20261028.md](LIVE_VALIDATION_20261028.md).
The agent submissions pass 9/12, not 12/12; seven attempts reach their turn limit.

## Delivered Evidence

- Three separate public, author-known maintenance challenges with behavioral prompts, fresh
  submission verification, external acceptance, expected JUnit case counts and protected hashes.
- Reference validation rejects all three buggy baselines and accepts all three references across
  17 cases. This is not a model 3/3 score. See `CHALLENGE_VALIDATION.json`.
- Docker-only actual agent entry, read-only external acceptance mount, and fresh ABBA trials.
  Tests exercise the ordering with an injected fixture controller, not actual models.
- Optional Python AST boundaries with decorator/blank-line/line-number preservation, line-window
  fallback and bounds. The legacy 10-query lexical MRR remains 0.8000.
- New 24-file, 28-query public retrieval development fixture and preserved semantic misses.
- Full-call first/repeated latency observations plus explicit missing-hybrid metadata.
- Temporal retrieved-path/read/edit follow-up reports, with a clearly scripted trace example.

## Ranking Results

| Same 28-query corpus | Line windows | Python boundaries |
|---|---:|---:|
| Lexical MRR | 0.9107 | 0.9286 |
| Recall@5 | 0.9286 | 0.9286 |
| Zero-result queries | 1 | 1 |

Only one judged query changes first-relevant rank from 2 to 1. The two semantic misses remain;
this is a small local ranking observation, not an agent success, token, cost or generalization
gain. The corpus was constructed and inspected by the author, including adding four stress
paraphrases after initial saturation. Gates were not lowered; this is not blind held-out evidence.
See `RETRIEVAL_V2_LINES.md/.json` and `RETRIEVAL_V2_PYTHON.md/.json` for all cases.

## Local Gates

Windows / Python 3.12.2; no paid model calls, push or remote CI in this stage.

| Gate | Result |
|---|---|
| Focused challenge/credibility tests | 19 passed |
| Ruff / mypy | pass; mypy 33 source files |
| Full tests / coverage | 295 passed, 1 optional symlink skip; 82.78% |
| 40-task legacy scripted regression | 40/40 passed on final source |
| Reference acceptance | 3 baselines rejected, 3 references accepted, 17 cases |

Final compatibility artifacts remain local in `artifacts/priority4-verified-EVAL.md`, `.json`
and `priority4-verified-eval-runs/`. Focused tests also cover non-root verification result
directory setup; POSIX permission assertions require a POSIX host and are not Linux runtime
proof from this Windows run.

`RETRIEVAL_V2_STUDY.json` records first/repeated full-call timings. These are document-cache
observations, not OS/model cold start or guaranteed latency. Lexical has no prepared-index cache
in this path. Sentence Transformers is not installed locally, so hybrid is explicitly unavailable
and the real paired forward/reverse retrieval study is not complete. No optional dependencies
were installed or model files downloaded for this stage.

Docker is unavailable locally. Read-only mounts and policy contracts are tested, not newly
verified in a live container. New real-agent ABBA attempts were not run. Existing 8-task real
backend evidence remains lexical-first and does not establish hybrid agent superiority. These
remaining live checks require Docker/dependencies and separate API-run authorization.

The four priorities are engineering/local-evidence work, not a production-readiness or external-
benchmark certification. Detailed usage, limitations and next live checks are in
`docs/EVALUATION_CREDIBILITY.md`. Resume changes remain a separate user-authorized step after
this priority is reported; unsupported live results must not enter resume claims.
