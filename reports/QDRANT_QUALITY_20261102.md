# Retrieval Quality Benchmark

## Summary

- Backend: **qdrant**
- Cases: **28**
- Ranking unit: **deduplicated path**
- Mean reciprocal rank: **0.9762**
- Zero-result queries: **0**
- Quality gate: **pass**
- Embedding model: **sentence-transformers/all-MiniLM-L6-v2**
- Embedding dimension: **384**
- Fusion weights (lexical/semantic): **0.35/0.65**
- Qdrant sync totals (upserted/deleted/reused observations): **0/0/1036**
- Reuse totals count repeated observations, not unique stored vectors.


| Metric | Value |
|---|---:|
| MRR | 0.9762 |
| Recall@1 | 94.64% |
| Hit Rate@1 | 96.43% |
| Recall@3 | 100.00% |
| Hit Rate@3 | 100.00% |
| Recall@5 | 100.00% |
| Hit Rate@5 | 100.00% |

## Quality Gate

| Metric | Actual | Minimum | Status |
|---|---:|---:|---|
| `mrr` | 0.9762 | 0.6000 | pass |
| `recall_at_5` | 1.0000 | 0.8500 | pass |

## Cases

`R@K` is the fraction of judged relevant paths found in the first K deduplicated paths. `P/O` means the first relevant path rank, or `none` when no relevant path appears.

| Case | Relevant | Top 5 Paths | P/O | R@1 | R@3 | R@5 |
|---|---|---|---:|---:|---:|---:|
| `stock_atomic` | `inventory.py` | 1. `inventory.py`<br>2. `leases.py`<br>3. `retention.py`<br>4. `retry_jobs.py`<br>5. `response_codes.py` | 1 | 100.00% | 100.00% | 100.00% |
| `stock_available` | `inventory.py` | 1. `inventory.py`<br>2. `retention.py`<br>3. `leases.py`<br>4. `response_codes.py`<br>5. `retry_jobs.py` | 1 | 100.00% | 100.00% | 100.00% |
| `stock_duplicate` | `inventory.py` | 1. `inventory.py`<br>2. `billing.py`<br>3. `leases.py`<br>4. `retention.py`<br>5. `telemetry.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_project` | `retention.py` | 1. `retention.py`<br>2. `sorting.py`<br>3. `pagination.py`<br>4. `cleanup.py`<br>5. `cache.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_pins` | `retention.py` | 1. `retention.py`<br>2. `cleanup.py`<br>3. `leases.py`<br>4. `cache.py`<br>5. `retry_jobs.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_time` | `retention.py` | 1. `retention.py`<br>2. `cache.py`<br>3. `leases.py`<br>4. `retry_jobs.py`<br>5. `cleanup.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_sort` | `pagination.py` | 1. `pagination.py`<br>2. `sorting.py`<br>3. `retention.py`<br>4. `notifications.py`<br>5. `validation.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_end` | `pagination.py` | 1. `pagination.py`<br>2. `retention.py`<br>3. `sorting.py`<br>4. `retry_jobs.py`<br>5. `audit.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_bool` | `pagination.py` | 1. `pagination.py`<br>2. `inventory.py`<br>3. `audit.py`<br>4. `theme.py`<br>5. `leases.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_order` | `routing.py` | 1. `routing.py`<br>2. `versions.py`<br>3. `cleanup.py`<br>4. `leases.py`<br>5. `sorting.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_boundary` | `routing.py` | 1. `routing.py`<br>2. `auth.py`<br>3. `cleanup.py`<br>4. `audit.py`<br>5. `versions.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_symbol` | `routing.py` | 1. `routing.py`<br>2. `theme.py`<br>3. `response_codes.py`<br>4. `health.py`<br>5. `validation.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_renew` | `leases.py` | 1. `leases.py`<br>2. `cache.py`<br>3. `auth.py`<br>4. `retention.py`<br>5. `cleanup.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_fencing` | `leases.py` | 1. `leases.py`<br>2. `retention.py`<br>3. `inventory.py`<br>4. `validation.py`<br>5. `versions.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_deadline` | `leases.py` | 1. `leases.py`<br>2. `cache.py`<br>3. `retry_jobs.py`<br>4. `retention.py`<br>5. `cleanup.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_columns` | `exports.py` | 1. `exports.py`<br>2. `pagination.py`<br>3. `log_export.py`<br>4. `sorting.py`<br>5. `retention.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_private` | `exports.py` | 1. `exports.py`<br>2. `validation.py`<br>3. `retention.py`<br>4. `auth.py`<br>5. `log_export.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_symbol` | `exports.py` | 1. `exports.py`<br>2. `log_export.py`<br>3. `encoding.py`<br>4. `versions.py`<br>5. `transport.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_cap` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py`<br>3. `leases.py`<br>4. `cache.py`<br>5. `telemetry.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_deadline` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py`<br>3. `leases.py`<br>4. `retention.py`<br>5. `cache.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_duplicate` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py`<br>3. `retention.py`<br>4. `audit.py`<br>5. `telemetry.py` | 1 | 100.00% | 100.00% | 100.00% |
| `audit_chain` | `audit.py` | 1. `audit.py`<br>2. `retention.py`<br>3. `retry_jobs.py`<br>4. `inventory.py`<br>5. `cleanup.py` | 1 | 100.00% | 100.00% | 100.00% |
| `audit_changed` | `audit.py` | 1. `audit.py`<br>2. `retention.py`<br>3. `log_export.py`<br>4. `exports.py`<br>5. `retry_jobs.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cross_expiration` | `leases.py`<br>`retention.py` | 1. `retention.py`<br>2. `leases.py`<br>3. `cleanup.py`<br>4. `cache.py`<br>5. `inventory.py` | 1 | 50.00% | 100.00% | 100.00% |
| `semantic_owner` | `leases.py` | 1. `leases.py`<br>2. `retry_jobs.py`<br>3. `theme.py`<br>4. `response_codes.py`<br>5. `auth.py` | 1 | 100.00% | 100.00% | 100.00% |
| `semantic_freshest` | `retention.py` | 1. `retention.py`<br>2. `retry_jobs.py`<br>3. `cleanup.py`<br>4. `inventory.py`<br>5. `theme.py` | 1 | 100.00% | 100.00% | 100.00% |
| `semantic_spreadsheet` | `exports.py` | 1. `exports.py`<br>2. `log_export.py`<br>3. `versions.py`<br>4. `sorting.py`<br>5. `billing.py` | 1 | 100.00% | 100.00% | 100.00% |
| `semantic_duplicate` | `retry_jobs.py` | 1. `cache.py`<br>2. `auth.py`<br>3. `retry_jobs.py`<br>4. `theme.py`<br>5. `audit.py` | 3 | 0.00% | 100.00% | 100.00% |

## Misses At 5

- None.

## Interpretation

This run uses Qdrant semantic and lexical candidate fusion on the fixed development corpus, with local embeddings and no model API. Persistent-index synchronization statistics are not JSON embedding-cache metrics. Candidate truncation may differ from exhaustive local hybrid ranking. Scores do not establish general retrieval quality, latency, or Agent completion improvements.
