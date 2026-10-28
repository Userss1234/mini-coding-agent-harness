# Priority 2: Context-Window Management

Status: **complete; local verification and final scripted regression passed**

## Implemented Behavior

Input-envelope checks now run before new model requests. A configurable budget includes the
system prompt, tool schemas and conversation. Eligible old complete groups are replaced with
a bounded structured summary, while the original task and recent complete tool-use/result
batches remain intact. Repeated summaries merge historical counts and current todos.

An oversized protected task, batch or summary pauses execution before the model request.
Durable runs checkpoint the replacement messages, summary revision and config before dispatch.
Resume inherits those settings, with explicit CLI overrides for input budget, summary budget,
recent groups and the management switch. The legacy `compact_context` trace tool is unchanged.

## Local Verification

Environment: Windows, Python 3.12.2. No paid model calls, push or remote CI for this stage.

| Gate | Result |
|---|---|
| Full pytest suite | 237 passed |
| Branch-enabled total coverage | 81.59% (75% required) |
| Context-window module coverage | 93% |
| Ruff | pass |
| mypy | pass, 28 source files |
| 40-task scripted regression | 40/40 passed |

Tests cover repeated compaction, exact task preservation, complete multi-tool batches,
orphan/incomplete/mismatched tool IDs, large recent results, summary/todo budget stops,
system/schema/UTF-8 accounting, saved-summary consistency, CLI config inheritance and overrides,
and a genuine child-process termination after a compacted checkpoint commits.

Failed file operations remain failure observations and do not enter the successful read/change
path lists. The full-suite `pytest_suite` benchmark task and its verifier use a dedicated
300-second timeout because the expanded Windows regression suite exceeds the ordinary tool's
120-second default. The default `run_tests` timeout and smaller repair fixtures are unchanged.

## Deterministic Long-Task Comparison

Source: `CONTEXT_WINDOW_COMPARISON.json`.

```powershell
python -m tests.fixtures.context_workload --output artifacts/context-window-comparison.json
```

The fixture client selects the next step from the supplied history and uses real permission-
checked file tools. Both runs perform the same 12 file-update steps, 36 tool calls and 13 model
requests. Management uses an input budget of 12000, summary budget of 1800 and one protected
recent complete group. The baseline explicitly disables management.

| Metric | Disabled | Managed |
|---|---:|---:|
| Completed steps | 12/12 | 12/12 |
| Tool calls | 36 | 36 |
| Model requests | 13 | 13 |
| Compactions | 0 | 10 |
| Peak estimated input units | 40061 | 11211 |
| Cumulative estimated input units | 294624 | 125386 |

The managed fixture keeps every request under its declared 12000-unit budget. Peak estimated
input is 72.02% lower and cumulative estimated input is 57.44% lower on this fixture. A separate
restart test verifies the task completes using the saved compacted history with all 36 original
tool-call IDs represented once in the durable ledger.

## Estimation and Claim Boundary

`utf8_bytes_v1` uses normalized serialized UTF-8 input bytes plus fixed overhead as a
conservative estimate. These are not provider tokenizer counts, model context-capacity limits
or measured monetary savings. Real provider usage remains separately logged when available.

The summary is deterministic extraction, not an LLM semantic summary. It retains bounded
historical observations and excerpts and may omit older detail. Original task requirements and
current todos remain protected, and exact file content should be reread when needed. Previous
durable checkpoints and the tool ledger are retained; database retention is not addressed.

This stage verifies input bounding, conversation integrity and checkpoint continuation. It does
not establish real-model quality, success-rate or cost improvements. Resume content remains
deferred until all agreed priorities are complete.
