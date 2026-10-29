# Requirement Mapping and Budget Guidance Experiment

Date: 2026-10-29. Engineering baseline: `7aaca50`; source changes are in this report's commit.
Status: implemented and measured; experimental guidance is **off by default** because the
experiment did not improve aggregate acceptance and exposed new context/cleanup failures.
No challenge prompt, reference, external acceptance or gate was changed. No push or remote CI.

## Delivered Mechanisms

- Existing `todo_write` accepts optional bounded `requirement`, `check`, `evidence` fields.
  They survive normal SQLite checkpoints and structured summaries; invalid values do not
  replace the existing plan. Legacy string/task/status items remain supported.
- The tool returns requirement-item, missing-check, completed-without-evidence and open-item
  counts. These are self-reports, not parsed task completeness, test execution attestation or
  correctness proof. Nonempty "not run" evidence is still only text, not a passed check.
- Opt-in guidance asks for clause-derived checks, scope/boundary awareness and concise planning.
  Every model turn receives remaining allowance; the last two prioritize checks and finalization.
  The actual augmented system prompt is counted by ContextWindow before the model request.
  No extra model turns or increased budget were introduced.
- `HARNESS_VERIFICATION_GUIDANCE=on` explicitly activates guidance for new runs. Default is off.
  New checkpoints persist the mode, so environment changes do not change it on resume.

Usage and limits: [VERIFICATION_GUIDANCE.md](../docs/VERIFICATION_GUIDANCE.md).

## Actual DeepSeek Comparison

[New complete result](CHALLENGE_GUIDANCE_ABBA_20261029.json), compared with the unchanged
[2026-10-28 baseline](CHALLENGE_AGENT_ABBA_20261028.json). Each is one fresh ABBA sequence:
lexical/hybrid/hybrid/lexical, three public author-known tasks, 12-turn allowance, Docker-only
execution and protected external acceptance. Same line-window retrieval and cached MiniLM
configuration; no new corpus, vector database or task-specific solution hints.

The 12 new attempts ran with the guidance active before adding the final default-off switch.
The final opt-in base system prompt was checked for exact equality with the measured saved
prompt. The switch adds mode selection/persistence, not a changed on-mode instruction. No second
paid suite was run. Raw experimental checkpoints predate the explicit mode field; keep them as
frozen study artifacts, not resumed replacement scores.

| Trial | Backend | Reservation | Retention | Cursor | Accepted |
|---|---|---|---|---|---:|
| 0 | lexical | fail: extra helper | pass | pass | 2/3 |
| 1 | hybrid | pass | fail: extra helper | pass | 2/3 |
| 2 | hybrid | fail: extra helper | pass | pass | 2/3 |
| 3 | lexical | pass | pass | pass | 3/3 |

All 12 baselines failed with the expected case counts before model execution. Protected suite
inputs stayed unchanged. The CLI exited 1 because three submissions failed, not because the
sequence was interrupted. All attempts are retained; none was automatically rerun.

| Observation | Prior baseline | Guidance experiment |
|---|---:|---:|
| Final-submission acceptance | 9/12 | 9/12 |
| Lexical acceptance | 4/6 | 5/6 |
| Hybrid acceptance | 5/6 | 4/6 |
| Normal conversational ends | 5 | 7 |
| Max-turn stops | 7 | 2 |
| Context-budget stops | 0 | 3 |
| Model responses | 141 | 117 |
| Tool calls including preflight | 232 | 213 |
| Failed tool calls | 20 | 31 |
| Reported input tokens | 541035 | 515260 |
| Reported output tokens | 27529 | 35721 |

The backend winner reverses; this does not demonstrate hybrid superiority. There is one small,
stochastic, inspected comparison per version with several simultaneous generic changes, not a
causal ablation or statistical significance test. Token counters are provider reports, not a bill.
Seven new normal ends all pass external acceptance; the other two accepted submissions stop at
budgets. Neither version's 9/12 means nine normal autonomous completions.

## Failure Analysis and Decision

The old three failures ignored per-project retention scope. In the new run, three retention
submissions pass; the fourth is rejected before behavioral grading because a helper file remains.
Do not claim the ungraded submission is correct.

The new three rejected submissions retain `_ephemeral_check.py`,
`check_retention_ephemeral.py` or `test_tmp_reserve.py`. Two are interrupted by context budgets;
one exhausts turns. Declaring a file "ephemeral" does not clean it up. The verifier correctly
rejects it. We did not delete the files after the fact or relax submission scope to raise scores.

Three runs stop because current todos plus summary essentials exceed the existing 1800-unit
byte-based summary estimate. Two fail submission scope; one already has an accepted final file
set. Plans with richer requirement/check/evidence text are larger even when individual fields
are within 600 characters. This is a real integration limitation, not a provider outage. The
default budget was not raised and current requirements were not silently truncated.

All attempts record requirement-bearing updates (25 updates total), but filling fields does
not establish that every task clause was covered or tested. More observations alone are not
reliable verification. As no aggregate gain was established, automatic guidance is not promoted
to the default. Optional plan fields and transparent counters remain available.

## Verification and Next Boundary

Focused tests cover legacy compatibility, mapping/limits, non-attestation, bounded countdown,
actual context-accounting input, unchanged model-call count, default-off behavior, new-mode
durability and environment-independent resume. After the final default-off integration:

- Full tests: 304 passed, one optional Windows symlink skip; 82.94% branch-enabled coverage.
- Ruff, mypy (33 source files), compileall and both roadmap-skill validators: pass.
- Final default-off scripted compatibility regression: 40/40. Local artifacts:
  `artifacts/guidance-final-20261029-EVAL.md`, `.json` and the matching trace directory.

Earlier development gates were 302 tests/82.87% and 40/40; they are not substituted for
the final-source results above.

Next authorized work should first make structured plans fit bounded summaries without dropping
requirements or inflating the total input ceiling, then support scope-safe verification without
leftover helper files. Preserve both 9/12 reports. Do not run another paid suite until the concrete
failure modes have focused coverage and the user authorizes the next stage. Windows MCP shutdown
WinError 995 remains separate outstanding work. Resume editing and Git push remain deferred.
