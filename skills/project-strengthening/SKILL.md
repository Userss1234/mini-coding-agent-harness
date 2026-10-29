---
name: project-strengthening
description: Follow the agreed strengthening priorities for mini-coding-agent-harness and stop after each completed priority.
---

# Project Strengthening

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

Complete only the current priority in one user-authorized stage. Run focused tests, the full
unit suite and the 40-task scripted regression, update docs and evidence, and make a local
commit. Then STOP and report the result. Wait for the user before starting the next priority.
Do not push commits or trigger remote CI: the user will push all accumulated commits together.
Do not edit resume content until all four priorities have finished. Do not add a vector DB,
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
Guidance remains off by default. Preserve all three 9/12 reports. STOP and report.
Next authorized priority: audit task/API/acceptance contract consistency, freeze and version any
explicit contract correction before comparing again; no task-specific agent hints or weakened
submission scope. Then address Windows MCP teardown. Further paid runs, resume edits and pushing
await user continuation. No new technology merely to grow the roadmap.
