# Retrieval Quality Baseline

## Summary

- Backend: **lexical**
- Cases: **10**
- Ranking unit: **deduplicated path**
- Mean reciprocal rank: **0.8000**
- Zero-result queries: **0**
- Quality gate: **pass**

| Metric | Value |
|---|---:|
| MRR | 0.8000 |
| Recall@1 | 70.00% |
| Hit Rate@1 | 80.00% |
| Recall@3 | 80.00% |
| Hit Rate@3 | 80.00% |
| Recall@5 | 80.00% |
| Hit Rate@5 | 80.00% |

## Quality Gate

| Metric | Actual | Minimum | Status |
|---|---:|---:|---|
| `mrr` | 0.8000 | 0.8000 | pass |
| `recall_at_5` | 0.8000 | 0.8000 | pass |

## Cases

`R@K` is the fraction of judged relevant paths found in the first K deduplicated paths. `P/O` means the first relevant path rank, or `none` when no relevant path appears.

| Case | Relevant | Top 5 Paths | P/O | R@1 | R@3 | R@5 |
|---|---|---|---:|---:|---:|---:|
| `invoice_rounding` | `src/billing/totals.py` | 1. `src/billing/totals.py`<br>2. `docs/invoice_copy.md` | 1 | 100.00% | 100.00% | 100.00% |
| `secret_redaction` | `src/security/redaction.py` | 1. `src/security/redaction.py`<br>2. `src/auth/tokens.py`<br>3. `src/auth/middleware.py` | 1 | 100.00% | 100.00% | 100.00% |
| `plugin_discovery` | `src/plugins/discovery.py` | 1. `src/plugins/discovery.py`<br>2. `docs/plugin_authoring.md` | 1 | 100.00% | 100.00% | 100.00% |
| `order_status_persistence` | `src/orders/service.py`<br>`src/orders/repository.py` | 1. `src/orders/service.py`<br>2. `src/orders/repository.py` | 1 | 50.00% | 100.00% | 100.00% |
| `payment_duplicate_semantic` | `src/payments/idempotency.py` | 1. `docs/card_support.md` | none | 0.00% | 0.00% | 0.00% |
| `timezone_formatting` | `src/timezone/formatter.py` | 1. `src/timezone/formatter.py` | 1 | 100.00% | 100.00% | 100.00% |
| `provider_retry` | `src/retry/policy.py` | 1. `src/retry/policy.py` | 1 | 100.00% | 100.00% | 100.00% |
| `config_precedence` | `src/config/precedence.py` | 1. `src/config/precedence.py`<br>2. `docs/traffic_guide.md` | 1 | 100.00% | 100.00% | 100.00% |
| `auth_validation_flow` | `src/auth/middleware.py`<br>`src/auth/tokens.py` | 1. `src/auth/middleware.py`<br>2. `src/auth/tokens.py`<br>3. `src/security/redaction.py` | 1 | 50.00% | 100.00% | 100.00% |
| `request_coalescing_semantic` | `src/cache/coalescing.py` | 1. `docs/traffic_guide.md` | none | 0.00% | 0.00% | 0.00% |

## Misses At 5

- `payment_duplicate_semantic`: missing `src/payments/idempotency.py`; query `stop charging a card twice`
- `request_coalescing_semantic`: missing `src/cache/coalescing.py`; query `combine simultaneous identical requests`

## Interpretation

This is an offline lexical retrieval baseline over committed relevance judgments. It measures ranking quality independently from the agent loop and does not claim embedding or semantic retrieval. Misses are retained as targets for the optional hybrid backend; future backends must run against the same corpus and judgments.
