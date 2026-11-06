---
name: project-strengthening
description: Follow the user's current core-agent priorities, execution mode and evidence boundaries for mini-coding-agent-harness.
---

# Project Strengthening

## Active Reliability Scope (2026-11-03)

The user approved the recommendations in docs/AGENT_STRENGTHENING_REVIEW_20261103.md.
Execute P0 local provenance/reproducibility, P1 structured diagnostics and bounded repair,
P2 Python repository map/semantic navigation, and P3 durable budgets/cancellation/no-progress
controls continuously. No stage-by-stage stops or automatic commits/pushes. Remote publication
and paid model comparisons require separate approval; leave these clearly pending, not passed.
P4 delegation and P5 index-scale infrastructure remain optional and are not authorized by this
bounded P0-P3 pass. Resume changes remain deferred until the chosen scope is verified.

Keep defaults/backward compatibility conservative. Verification must bind actual workspace state,
report verified/failed/unverified honestly, and run only operator-selected checks under existing
execution policy. Model-editable configuration cannot grant permissions or disable checks.
Reuse a proven Python language server for semantic navigation; do not relabel AST suffix matches.
Persist run-wide usage/elapsed/tool budgets across resume, preserve unknown usage, and do not
confuse cooperative cancellation with rollback of remote writes. Never weaken historical acceptance
or silently rescore 9/12. Finish focused/full tests, existing compatibility checks, docs and evidence.

P0-P3 are now implemented and verified locally: 391 tests passed, one optional symlink skip,
83.77% branch coverage, mypy 39 modules, 40/40 scripted compatibility. Actual Docker completion
checks reject a failing proposal and pass a corrected version without changing original source;
actual Python LSP resolves cross-file definitions/references and diagnostics. Durable dispatch,
usage/elapsed budgets and cancellation/no-progress gates have explicit cooperative limits.
Evidence: reports/RELIABLE_MAINTENANCE_20261103.md; usage: docs/RELIABLE_MAINTENANCE.md.
Remote publication/CI and paid model comparisons remain pending, not failed or silently complete.
Do not automatically start P4/P5 or rewrite the resume merely because local P0-P3 work is complete.

## User-Selected Vector Store (2026-11-02)

The user explicitly selected Qdrant after comparing it with Milvus. This supersedes the older
no-vector-database restriction for this scope only. Add an optional backend, preserve local
defaults and SQLite run recovery, and verify incremental upsert/deletion, repository/model/chunk
separation, source-grounded evidence, service errors, real Docker persistence and MCP integration.
Keep the vector service separate from no-network execution containers. No automatic commits,
pushes, resume edits or paid model benchmark expansion. Report the connected result at completion.
Do not claim speed, accuracy or distributed-scale gains without measurements.

This scope is complete locally: 364 tests passed, one optional symlink skip, 83.59% branch
coverage, 40/40 scripted compatibility, actual Qdrant restart reuse (37 vectors / zero upserts),
incorrect-key rejection and real MiniLM/MCP stdio evidence reads. Same fixed 28-query metrics:
MRR 0.9762, Recall@5 1.0, matching prior local hybrid results rather than improving them.
See reports/QDRANT_RETRIEVAL_20261102.md and docs/QDRANT_RETRIEVAL.md. Changes remain local,
uncommitted/unpushed; the localhost authenticated service is running. Old no-vector statements
below describe the earlier roadmap, not a reason to remove this user-authorized extension.

## Current Authorization (2026-10-29)

The user now prioritizes Tool Calling reliability, external MCP client integration and code RAG.
Work through all three continuously, verify the integrated result, and report once at completion.
Do not stop after each priority and do not automatically create per-stage commits or push.
Keep resume work and further benchmark expansion deferred. Preserve all historical raw scores;
the contract ambiguity remains documented, not silently rescored. Older stop/commit instructions
below describe historical stages and are superseded by this paragraph.

Core pass complete: schema/error contracts, safe read batching, external MCP stdio/HTTP sessions,
pre-launch resume policy checks, uncertain-write reconciliation, AST symbol evidence and bounded
content-invalidated chunks. Verified 340 tests (one optional skip), 83.16% coverage, 40/40 scripted,
real stdio/HTTP integration and one 4-response DeepSeek MCP/RAG smoke. Evidence:
reports/CORE_AGENT_STACK_20261029.md. Changes intentionally remain uncommitted/unpushed. Preserve
known limits: operator-trusted servers, syntax-only relationship candidates, no third-party OAuth
compatibility claim, no general success-rate gain. Do not resume benchmark expansion by default.

This is the repository copy of the user's agreed roadmap, dated 2026-10-27.
The global mini-coding-agent-harness skill carries the same stage boundaries.

1. Durable run state and recovery: RunStore/SQLite, normalized messages, checkpoints,
   tool-call ledger, artifact references, JSONL export, secret redaction, local process
   exclusion, and actual process-termination tests. Reuse completed results and block unknown
   outcomes until operator reconciliation. No blind retries of interrupted writes.
2. Actual context-window management: replace old messages with structured summaries at a
   budget, preserve complete recent tool-use/result pairs, persist checkpoints, and validate
   long-running task continuation and context/token metrics.
3. Workspace isolation and change approval: temporary workspace/worktree, reviewed patch,
   conflict detection on host application, centralized trace redaction, existing Docker limits.
4. Evaluation and retrieval credibility: held-out tasks without solution hints, protected
   acceptance tests, a larger judged corpus, code-aware chunks, cold/warm latency,
   evidence-use measurement, and reversed lexical/hybrid execution order.

For a new user-selected scope, complete its connected core changes, focused tests, full suite,
40-task compatibility checks and documentation before final reporting. Do not automatically commit
or push; the user will decide Git operations. Resume editing remains separate. Do not add a vector DB,
PostgreSQL, a dashboard or multi-agent orchestration to increase the technology list.

Current stage: Priority 4 engineering/local acceptance complete (295 tests passed, one optional
symlink skip, 82.78% branch-enabled coverage, 40/40 legacy scripted regression). See
reports/EVALUATION_CREDIBILITY.md. Three public author-known challenges have external acceptance;
3/3 reference validation over 17 cases is NOT an agent score or blind holdout result. New 28-query,
24-file lexical MRR is 0.9107 for lines and 0.9286 for Python boundaries, with identical 0.9286
Recall@5 and two retained semantic misses. Do not compare those scores directly to the old corpus.
All four priorities are locally implemented. The user subsequently authorized installing Docker
Desktop and actual API validation. See reports/LIVE_VALIDATION_20261028.md: live Docker,
protected reference acceptance and MCP/hybrid pass; 28-query hybrid MRR 0.9762/Recall@5 1.0
versus lexical 0.9286/0.9286 in both orders. One 12-attempt DeepSeek ABBA sequence yields
9/12 submission acceptance (lexical 4/6, hybrid 5/6), with seven max-turn stops and three
per-project retention failures. Do not claim stable hybrid gains or normal autonomous completion.
Preserve this baseline and historical reports. Windows MCP teardown emitted WinError 995.
On 2026-10-29 requirement/check/evidence todo mapping and per-turn budget guidance were implemented.
See reports/VERIFICATION_GUIDANCE_20261029.md: new actual ABBA acceptance remains 9/12; normal
ends 5->7, max-turn stops 7->2, but context stops 0->3 and failed tools 20->31. Backend winner
reverses. Guidance is explicitly opt-in via HARNESS_VERIFICATION_GUIDANCE=on, default off;
new checkpoints preserve the mode. Do not claim an overall success-rate or stable backend gain.
Follow-up on 2026-10-29 implements v2 history/complete-plan accounting under the unchanged
24000 total ceiling and Docker-only read-only run_python_check. Three old failed checkpoints
replay losslessly within budget. New ABBA: 9/12 raw acceptance, zero context or submission-scope
failures, 9 normal ends and 3 turn stops; only 6 normal ends also pass acceptance. Three failures
raise TypeError where acceptance requires ValueError although the task does not specify the
exception class. Do not silently rescore or call these established algorithmic errors.
Evidence: reports/SCOPE_SAFE_VERIFICATION_20261029.md; 319 tests/83.01% coverage, 40/40 scripted.
Guidance remains off by default. Preserve all three 9/12 reports. The user subsequently deferred
contract-audit work to prioritize the completed core pass above. Windows HTTP teardown was fixed
in that pass. Any future evaluation correction must still be explicit/versioned, not silently
rescored. No task-specific hints, weaker submission scope or technology merely to grow the roadmap.
