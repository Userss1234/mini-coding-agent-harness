# Requirement Checks and Turn Budgets

Opt-in code-changing tasks receive generic requirement-to-check guidance. No challenge-specific
solutions, extra model turns, acceptance relaxations or automatic retries were added.

Set `HARNESS_VERIFICATION_GUIDANCE=on` before starting a new run to enable the experiment.
Default is off: the first actual comparison retained 9/12 acceptance and exposed larger-plan
context stops and unfinished helper-file cleanup. Optional todo fields remain available in both
modes. Resume uses the persisted mode, not a changed environment variable.

Follow-up fixes are documented in [scope-safe verification](SCOPE_SAFE_VERIFICATION.md).
Historical summaries now account for full plans separately under the same total input cap.
Restricted Docker registries offer `run_python_check` for inline assertions without helper scripts.

## Plan Contract

Existing `todo_write` items still accept only `task` and `status`. Three optional string fields
(at most 600 characters each) make verification intent and observations visible:

```json
{
  "todos": [{
    "task": "Verify boundary behavior",
    "status": "pending",
    "requirement": "Reject values outside the documented range",
    "check": "Exercise an in-range value, each exact boundary and a value outside each boundary",
    "evidence": "not run yet"
  }]
}
```

Plan entries should follow actual task clauses, including scope qualifiers, invalid inputs and
non-mutation requirements. Checks must not be derived only from the proposed implementation.
The tool returns a self-reported coverage summary: requirement-bearing items, missing check
descriptions, completed items with no evidence text and open requirement items. Invalid field
types/lengths fail without replacing the current plan. Legacy string/list plans still work.

These are model-authored text fields. Any nonempty evidence, including "not run", fills the
field; neither the status nor text attests a successful execution. The harness does not infer
all requirements from free text, inspect arbitrary test semantics or block a final answer based
on this count. External tests and human review remain necessary. A zero missing count is not
proof of complete requirement coverage.

The mapping is included in normal tool metadata/trace, SQLite todos and structured context
summaries. It follows the existing redaction and context-size boundaries. Large current plans
may still exceed the context budget and stop rather than being silently discarded.

## Runtime Budget Guidance

Before each new model turn the harness appends remaining-turn and coverage counts to a fresh
system prompt. At two turns or fewer it prioritizes targeted checks and final reporting over
broad exploration or cosmetic work. It does not forbid a needed repair, execute a check on the
model's behalf or guarantee that the model follows the advice.

The exact augmented prompt is passed to the context-window estimator before the request.
Guidance is not appended repeatedly to conversation history and creates no additional provider
turn. It includes only counts, not unbounded task/evidence text. Retries retain the same logical
turn's prompt; this is a turn allowance, not an API-cost or wall-clock limit.

Resume continues the existing policy: `max_turns` grants an additional loop allowance. A pending
tool batch is reconciled through the durable ledger before another model request; this change
does not replay completed tools. New runs preserve requirement fields on pause/resume. Adding
optional fields changes the tool-schema hash, so older durable runs whose schemas differ are
rejected by the existing compatibility guard; they are not silently migrated or rewritten.

`agent_turn_budget` records the remaining allowance and the self-reported mapping counters.
Normal and max-turn `agent_end` events also include the counters. `stopped=max_turns` remains distinct from a normal final
response and from external final-submission acceptance. No turn-limit increase is implied.

## Verification

Focused tests cover legacy plans, mapping preservation, invalid-input atomicity, self-report
limitations, bounded prompts, countdown, the actual prompt passed to context accounting, no
extra model call and SQLite recovery. Final stage results and the separate real-agent comparison
are recorded in `reports/VERIFICATION_GUIDANCE_20261029.md`.
