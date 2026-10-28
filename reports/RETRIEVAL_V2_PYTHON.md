# Retrieval Quality Baseline

## Summary

- Backend: **lexical**
- Cases: **28**
- Ranking unit: **deduplicated path**
- Mean reciprocal rank: **0.9286**
- Zero-result queries: **1**
- Quality gate: **pass**


| Metric | Value |
|---|---:|
| MRR | 0.9286 |
| Recall@1 | 91.07% |
| Hit Rate@1 | 92.86% |
| Recall@3 | 92.86% |
| Hit Rate@3 | 92.86% |
| Recall@5 | 92.86% |
| Hit Rate@5 | 92.86% |

## Quality Gate

| Metric | Actual | Minimum | Status |
|---|---:|---:|---|
| `mrr` | 0.9286 | 0.6000 | pass |
| `recall_at_5` | 0.9286 | 0.8500 | pass |

## Cases

`R@K` is the fraction of judged relevant paths found in the first K deduplicated paths. `P/O` means the first relevant path rank, or `none` when no relevant path appears.

| Case | Relevant | Top 5 Paths | P/O | R@1 | R@3 | R@5 |
|---|---|---|---:|---:|---:|---:|
| `stock_atomic` | `inventory.py` | 1. `inventory.py` | 1 | 100.00% | 100.00% | 100.00% |
| `stock_available` | `inventory.py` | 1. `inventory.py` | 1 | 100.00% | 100.00% | 100.00% |
| `stock_duplicate` | `inventory.py` | 1. `inventory.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_project` | `retention.py` | 1. `retention.py`<br>2. `sorting.py`<br>3. `pagination.py`<br>4. `cleanup.py`<br>5. `cache.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_pins` | `retention.py` | 1. `retention.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retention_time` | `retention.py` | 1. `retention.py`<br>2. `cache.py`<br>3. `leases.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_sort` | `pagination.py` | 1. `pagination.py`<br>2. `sorting.py`<br>3. `retention.py`<br>4. `validation.py`<br>5. `notifications.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_end` | `pagination.py` | 1. `pagination.py`<br>2. `retention.py`<br>3. `sorting.py`<br>4. `retry_jobs.py`<br>5. `audit.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cursor_bool` | `pagination.py` | 1. `pagination.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_order` | `routing.py` | 1. `routing.py`<br>2. `auth.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_boundary` | `routing.py` | 1. `routing.py` | 1 | 100.00% | 100.00% | 100.00% |
| `routing_symbol` | `routing.py` | 1. `routing.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_renew` | `leases.py` | 1. `leases.py`<br>2. `auth.py`<br>3. `cache.py`<br>4. `retention.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_fencing` | `leases.py` | 1. `leases.py` | 1 | 100.00% | 100.00% | 100.00% |
| `lease_deadline` | `leases.py` | 1. `leases.py`<br>2. `cache.py`<br>3. `retry_jobs.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_columns` | `exports.py` | 1. `exports.py`<br>2. `pagination.py`<br>3. `sorting.py`<br>4. `log_export.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_private` | `exports.py` | 1. `exports.py`<br>2. `validation.py`<br>3. `retention.py`<br>4. `pagination.py`<br>5. `sorting.py` | 1 | 100.00% | 100.00% | 100.00% |
| `csv_symbol` | `exports.py` | 1. `exports.py`<br>2. `log_export.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_cap` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_deadline` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py` | 1 | 100.00% | 100.00% | 100.00% |
| `retry_duplicate` | `retry_jobs.py` | 1. `retry_jobs.py`<br>2. `response_codes.py` | 1 | 100.00% | 100.00% | 100.00% |
| `audit_chain` | `audit.py` | 1. `audit.py` | 1 | 100.00% | 100.00% | 100.00% |
| `audit_changed` | `audit.py` | 1. `audit.py`<br>2. `retention.py`<br>3. `pagination.py`<br>4. `sorting.py`<br>5. `exports.py` | 1 | 100.00% | 100.00% | 100.00% |
| `cross_expiration` | `leases.py`<br>`retention.py` | 1. `retention.py`<br>2. `leases.py`<br>3. `cleanup.py`<br>4. `audit.py`<br>5. `cache.py` | 1 | 50.00% | 100.00% | 100.00% |
| `semantic_owner` | `leases.py` | 1. `leases.py`<br>2. `retry_jobs.py`<br>3. `theme.py`<br>4. `audit.py`<br>5. `auth.py` | 1 | 100.00% | 100.00% | 100.00% |
| `semantic_freshest` | `retention.py` | 1. `retention.py`<br>2. `retry_jobs.py`<br>3. `theme.py`<br>4. `inventory.py`<br>5. `cleanup.py` | 1 | 100.00% | 100.00% | 100.00% |
| `semantic_spreadsheet` | `exports.py` | none | none | 0.00% | 0.00% | 0.00% |
| `semantic_duplicate` | `retry_jobs.py` | 1. `auth.py`<br>2. `cache.py` | none | 0.00% | 0.00% | 0.00% |

## Misses At 5

- `semantic_spreadsheet`: missing `exports.py`; query `spreadsheet friendly comma separated download`
- `semantic_duplicate`: missing `retry_jobs.py`; query `avoid doing identical background work twice`

## Interpretation

This is an offline lexical retrieval baseline over committed relevance judgments. It measures ranking quality independently from the agent loop and does not claim embedding or semantic retrieval. Its retained misses are fixed comparison targets for the optional hybrid report; future backends must use the same corpus and judgments.
