# Retrieval Quality Benchmark

## Summary

- Backend: **hybrid**
- Cases: **10**
- Ranking unit: **deduplicated path**
- Mean reciprocal rank: **0.9000**
- Zero-result queries: **0**
- Quality gate: **pass**
- Embedding model: **sentence-transformers/all-MiniLM-L6-v2**
- Embedding dimension: **384**
- Fusion weights (lexical/semantic): **0.35/0.65**
- Document embedding cache (hits/misses/writes): **144/16/1**


| Metric | Value |
|---|---:|
| MRR | 0.9000 |
| Recall@1 | 70.00% |
| Hit Rate@1 | 80.00% |
| Recall@3 | 100.00% |
| Hit Rate@3 | 100.00% |
| Recall@5 | 100.00% |
| Hit Rate@5 | 100.00% |

## Quality Gate

| Metric | Actual | Minimum | Status |
|---|---:|---:|---|
| `mrr` | 0.9000 | 0.9000 | pass |
| `recall_at_3` | 1.0000 | 1.0000 | pass |
| `recall_at_5` | 1.0000 | 1.0000 | pass |

## Cases

`R@K` is the fraction of judged relevant paths found in the first K deduplicated paths. `P/O` means the first relevant path rank, or `none` when no relevant path appears.

| Case | Relevant | Top 5 Paths | P/O | R@1 | R@3 | R@5 |
|---|---|---|---:|---:|---:|---:|
| `invoice_rounding` | `src/billing/totals.py` | 1. `src/billing/totals.py`<br>2. `docs/invoice_copy.md`<br>3. `docs/traffic_guide.md`<br>4. `src/payments/idempotency.py`<br>5. `src/retry/policy.py` | 1 | 100.00% | 100.00% | 100.00% |
| `secret_redaction` | `src/security/redaction.py` | 1. `src/security/redaction.py`<br>2. `src/auth/tokens.py`<br>3. `src/auth/middleware.py`<br>4. `docs/plugin_authoring.md`<br>5. `docs/card_support.md` | 1 | 100.00% | 100.00% | 100.00% |
| `plugin_discovery` | `src/plugins/discovery.py` | 1. `src/plugins/discovery.py`<br>2. `docs/plugin_authoring.md`<br>3. `docs/traffic_guide.md`<br>4. `src/config/precedence.py`<br>5. `src/payments/idempotency.py` | 1 | 100.00% | 100.00% | 100.00% |
| `order_status_persistence` | `src/orders/service.py`<br>`src/orders/repository.py` | 1. `src/orders/service.py`<br>2. `src/orders/repository.py`<br>3. `src/retry/policy.py`<br>4. `src/payments/idempotency.py`<br>5. `docs/traffic_guide.md` | 1 | 50.00% | 100.00% | 100.00% |
| `payment_duplicate_semantic` | `src/payments/idempotency.py` | 1. `docs/card_support.md`<br>2. `src/payments/idempotency.py`<br>3. `src/retry/policy.py`<br>4. `docs/traffic_guide.md`<br>5. `docs/invoice_copy.md` | 2 | 0.00% | 100.00% | 100.00% |
| `timezone_formatting` | `src/timezone/formatter.py` | 1. `src/timezone/formatter.py`<br>2. `src/config/precedence.py`<br>3. `docs/invoice_copy.md`<br>4. `src/billing/totals.py`<br>5. `src/security/redaction.py` | 1 | 100.00% | 100.00% | 100.00% |
| `provider_retry` | `src/retry/policy.py` | 1. `src/retry/policy.py`<br>2. `docs/card_support.md`<br>3. `src/orders/service.py`<br>4. `src/orders/repository.py`<br>5. `src/payments/idempotency.py` | 1 | 100.00% | 100.00% | 100.00% |
| `config_precedence` | `src/config/precedence.py` | 1. `src/config/precedence.py`<br>2. `src/timezone/formatter.py`<br>3. `docs/plugin_authoring.md`<br>4. `src/plugins/discovery.py`<br>5. `src/auth/tokens.py` | 1 | 100.00% | 100.00% | 100.00% |
| `auth_validation_flow` | `src/auth/middleware.py`<br>`src/auth/tokens.py` | 1. `src/auth/middleware.py`<br>2. `src/auth/tokens.py`<br>3. `src/security/redaction.py`<br>4. `src/payments/idempotency.py`<br>5. `src/orders/service.py` | 1 | 50.00% | 100.00% | 100.00% |
| `request_coalescing_semantic` | `src/cache/coalescing.py` | 1. `docs/traffic_guide.md`<br>2. `src/cache/coalescing.py`<br>3. `docs/card_support.md`<br>4. `src/payments/idempotency.py`<br>5. `src/retry/policy.py` | 2 | 0.00% | 100.00% | 100.00% |

## Misses At 5

- None.

## Interpretation

This is a local hybrid run over the same committed corpus and relevance judgments as the lexical baseline. It fuses normalized lexical scores with Sentence Transformers cosine similarity, uses no model API, and records document-embedding cache behavior. Its gains are project-fixture evidence, not a broad retrieval benchmark claim.
