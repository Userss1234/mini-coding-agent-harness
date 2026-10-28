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
All four priorities are locally implemented. STOP and report before further work. Docker runtime,
actual hybrid forward/reverse and new paid agent ABBA trials remain unrun; preserve these gaps.
Next user-authorized work may rewrite resume claims using only verified evidence. Do not push.
