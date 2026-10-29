# Context-Window Management

The agent checks its input budget before each new model request. When the current input is
over budget, it replaces eligible old history with a bounded structured summary and continues
the same task. This differs from the existing `compact_context` tool, which produces an
execution-trace summary without replacing model messages.

## Controls

```powershell
python main.py --workspace . --allow-write ask "Fix the failing test" --context-budget 24000 --context-summary-budget 1800 --context-recent-turns 2
python main.py --workspace . --allow-write resume RUN_ID
python main.py --workspace . --allow-write resume RUN_ID --context-budget 32000
python main.py ask "Inspect the repository" --no-context-management
python main.py --workspace . resume RUN_ID --context-management
```

| Setting | Default | Meaning |
|---|---:|---|
| `--context-budget` | 24000 | Estimated input budget including system prompt, tool schemas and messages |
| `--context-summary-budget` | 1800 | Maximum historical-summary estimate; the complete current plan separately consumes the same total input budget |
| `--context-recent-turns` | 2 | Minimum complete recent interaction groups retained verbatim |
| `--context-management` / `--no-context-management` | enabled | Enable or disable future compaction |

Resume inherits saved settings unless explicitly overridden. An existing Priority 1 checkpoint
without context settings uses the defaults. Disabling management does not reconstruct history
that was already summarized. The library API accepts `ContextConfig` as `run_agent(context_config=...)`.

## What Is Retained

The original task message, including its planning instructions and initial retrieval evidence,
is kept verbatim. Recent interactions are grouped atomically: an assistant message containing
tool calls and its user tool-result message must stay together, including every call in a
multi-tool batch. Orphan, partial and mismatched tool IDs are rejected before the model call.

The manager does not compact an unfinished tool batch. Priority 1 first recovers its completed
results and executes remaining pending calls. Budget management runs only at the next complete
model-request boundary.

## Structured Summary

Old complete groups are summarized using deterministic extraction, with no extra model call:

- cumulative tool-call counts;
- bounded paths read and changed;
- recent failure records and outcome flags;
- bounded excerpts from tool outputs and assistant notes;
- the current todo list, rendered as a separately accounted complete plan;
- a count showing that historical details were omitted.

The original task remains outside this summary. In schema v2 the historical block is bounded
by the summary allowance; the complete current plan is rendered alongside it without charging
that plan to the historical allowance. Both blocks, all system/tool definitions, the original
task and recent groups still count against the unchanged total input ceiling. This is an
allocation change, not a larger input limit or silent plan truncation. An oversized complete
plan still stops before model execution. Current todos are kept intact; historical
details can be trimmed to meet the history budget. Repeated compaction merges the existing
summary with newly retired groups, avoiding duplicate counts. Excerpts are marked as historical
observations rather than instructions or approval. Exact source content should be reread.

Schema v1 saved messages keep their original rendering until a new compaction upgrades them.
Schema v2 refreshes the current plan from live registry state even when no further compaction
is needed. Exact requirement/check/evidence fields stay in the checkpoint and request; completed
plan entries are not silently dropped. This addresses richer plans exhausting the old combined
summary allowance. It does not guarantee semantic understanding of the retained text.

If the original task, system/tool definitions, minimum recent groups or summary essentials
cannot fit, the agent returns `Stopped: context budget exceeded` before calling the model.
It preserves the checkpoint and pauses the durable run. Increase the budget or explicitly
reduce the retained-turn setting and resume; the manager does not silently remove a protected
tool result or truncate the original task.

## Estimation and Metrics

`utf8_bytes_v1` counts UTF-8 bytes of the normalized JSON input envelope and adds a small
fixed overhead. One byte is treated as one estimated token, deliberately conservative for
ordinary text. This is not a provider tokenizer or a guarantee about a provider's wire format.
It includes system text and tool schemas, not just conversation text. The configured budget
is a local estimated input limit, not an advertised model context capacity.

The existing model request separately caps output at 4000 tokens. Configure an input budget
that leaves suitable output and provider overhead space for the actual model in use.

Each model request emits `context_request` metrics: estimator, configured budget, message
counts before/after, estimated input before/after, revision and retired-group count.
For compacted history, `history_summary_estimated_tokens` and `current_plan_estimated_tokens`
show the separate byte-based allocations. They are not provider token counts. Real
provider usage, when present, remains in `agent_response.usage`; estimated values must not be
presented as measured provider tokens or monetary savings.

## Checkpoints and Recovery

Before contacting the model, a durable run atomically saves the replacement messages,
structured summary, revision, context settings and last metrics in a SQLite checkpoint.
After a process exit, `resume` restores that exact summary and recent history. It does not
repeat retrieval preflight or regenerate the retired conversation. The saved summary is
checked against its message representation before continuing.

The tool-call ledger and older checkpoints remain available for inspection. Request compaction
does not prune the audit database or guarantee bounded disk usage. In-memory runs have no
durable old-message archive; their JSONL trace may contain only output previews.

## Evidence and Limits

Reproduce the local comparison without API credentials:

```powershell
python -m tests.fixtures.context_workload --output artifacts/context-window-comparison.json
python -m pytest tests/test_context_window.py tests/test_run_cli.py
```

The fixture client chooses each next step from the history actually supplied to it, performs
12 real file-update steps and 36 tool calls, and checks the preserved task requirement.
Managed and disabled runs must both complete. A separate child-process test stops immediately
after a compacted checkpoint is saved and verifies continuation after restart.

See `reports/CONTEXT_WINDOW_COMPARISON.json` and `reports/CONTEXT_WINDOW.md`. These are local
deterministic context-budget results. Semantic retention, task quality and actual token/cost
effects with a real model remain unmeasured for this stage.
