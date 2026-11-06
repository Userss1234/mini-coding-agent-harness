# Coding Agent Progress and Strengthening Review

Follow-up: the user subsequently approved the bounded local P0-P3 implementation. See
[implementation evidence](../reports/RELIABLE_MAINTENANCE_20261103.md) and the current
project-strengthening Skill. The review below preserves its original decision context;
optional P4/P5 work, remote publishing and paid comparisons are still separate decisions.

Reviewed: 2026-11-03. This is a research/recommendation document, not authorization to implement
every item. No runtime code, resume, commits, pushes or paid model evaluations changed in this review.

## Scope and Source Provenance

Inspected local core modules, current skills, verification reports and Git status. External
comparison used public first-party documentation plus selected source modules, not complete
audits or local benchmark runs of the comparison products.

The local parent workspace README identifies Learn Claude Code and its LICENSE names shareAI Lab
under MIT. The public shareAI repository describes an educational Claude-Code-like harness.
These observations do not establish that this project incorporates leaked official Claude Code
source. Avoid that claim without identifying and verifying the exact source and provenance.
If implementation was copied, retain applicable upstream notices and explain the boundary between
upstream learning material, adapted code and project-specific engineering. Do not claim that every
line was independently invented. No license-compliance audit was performed here.

Suggested positioning: a lightweight coding-agent harness for repository maintenance, developed
from public agent-harness learning material and extended with recoverable execution, permission
governance, source-grounded retrieval and reproducible verification.

## Latest Verified State

The latest complete verification was on 2026-11-02, not rerun as part of today's document review.

| Area | Present capability | Evidence / implementation |
| --- | --- | --- |
| Agent loop and tools | JSON Schema contracts, stable failures, conservative parallel local reads | harness/agent.py; harness/tools.py |
| Durable execution | SQLite run/checkpoint/tool-call ledger, result reuse, unknown-outcome reconciliation | harness/run_store.py; harness/run_session.py |
| Context | Actual bounded history replacement and checkpointed summaries | harness/context_window.py |
| Workspace governance | Separate copies, reviewed patches, conflict checks and recovery journals | harness/workspace.py |
| Docker | Actual non-root/no-network execution, copy-only modification and timeout cleanup | reports/QDRANT_DOCKER_BOUNDARY_20261102.md; reports/QDRANT_RETRIEVAL_20261102.md |
| MCP | Official SDK server transports, external stdio/HTTP tools, explicit policy and deadlines | harness/mcp_client.py; harness/mcp_sdk.py; harness/mcp_sdk_http.py |
| Code RAG | Lexical/local hybrid, Python AST candidates, local source hashes and line evidence | harness/retrieval.py; harness/code_symbols.py |
| Vector persistence | Optional Qdrant, incremental upserts/deletions, repository/config collections | harness/qdrant_retrieval.py |
| Observability | Redacted JSONL, stored execution state, trace HTML and evaluation reports | harness/trace.py; harness/trace_viewer.py |

Final gates: 364 tests passed, one optional Windows symlink skip, 83.59% branch-enabled coverage,
Ruff/mypy/compile/dependency checks passed, 40/40 existing scripted tasks passed.
The 40 tasks are not 40 autonomous Qdrant-backed model completions.

Qdrant's fixed 28-query / 24-file development fixture reports MRR 0.9762 and Recall@5 1.0,
matching the prior local hybrid result. Actual restart reuse covered 37 stored vectors and a
real MiniLM/official MCP stdio evidence call. This is not a scale or latency benchmark.
Historical raw 9/12 public challenge runs and the exception-contract ambiguity remain unchanged.

Git status contains uncommitted core/Qdrant changes and local commits ahead of the recorded
origin/main reference. Local evidence must not be described as already published remote CI.

## What Public Agents Suggest

| Reference | Inspected mechanism | Relevant gap / adaptation |
| --- | --- | --- |
| Aider | RepoMap uses symbol extraction, reference relationships and a context budget; base coder integrates edit/lint/test feedback | Add an actual bounded diagnostic-repair loop; later add a compact repository map rather than relying only on vector similarity |
| SWE-agent | Agent-computer interface treats tool/observation design as a first-class component | Return structured diagnostics, precise edit failures and bounded useful observations, not merely more tools |
| OpenCode | Official LSP documentation describes language-server diagnostics fed to the agent | Start with Python diagnostics and definition/reference navigation through a proven language server; do not call suffix matching semantic resolution |
| OpenHands SDK | LocalConversation coordinates events, cancellation and stuck detection | Extend existing max-turn/context limits with persisted run-wide budgets, explicit cancellation and no-progress stops |
| Claude Code public docs | Lifecycle hooks and permission-limited subagents with separate contexts | Prefer deterministic trusted policy/verification hooks first; add bounded read-only subagents only after the single-agent loop is reliable |

These are architecture inspirations, not head-to-head performance conclusions. No claim that the
project matches these products, implements their full security model, or benefits by copying all
their features is supported by this review.

## Recommended Order

### P0: Publishable, Reproducible Baseline

Necessity: high; bounded housekeeping, not another framework feature.

- Record source provenance and contribution boundaries without the unsupported leaked-code claim.
- Review the existing local batch, retain separate evidence categories, and obtain user approval
  before commits/pushes. Then actually run the remote quality/Qdrant CI jobs.
- Keep deterministic compatibility, real-model maintenance and retrieval-quality scores separate.
- Version any future challenge-contract clarification; never silently rescore raw 9/12 reports.

Done when: a reviewer can reach a specific revision, reproduce the local Docker/Qdrant example,
and distinguish original work, reused material, measured results and limitations.

### P1: Structured Diagnostics and Bounded Repair

Necessity: highest functional priority; strongest immediate Tool Calling improvement.

Current: tools can run tests/compilation, but model-selected checks and self-reported todo evidence
are not a guaranteed verification controller. A non-tool model response currently ends the run.

- Capture files changed by actual successful mutations, and bind checks to the changed-file state.
- Produce diagnostics with tool, file, range, severity, code, message and exit status.
- Run an operator-selected syntax/lint/test profile inside the existing isolated execution policy.
- Return failures for a bounded repair attempt; detect repeated identical failures/no source change.
- Distinguish verified, failed and unverified completion. A nonzero exit cannot become success
  because the model says the task is done. Do not treat model-authored tests as external acceptance.
- Prevent hooks/configurations writable by the model from granting permissions or disabling checks.

Done when: the edit -> diagnosed failure -> bounded repair -> successful recheck path has durable
trace evidence, and timeout/unavailable-check/no-progress paths stop honestly. Validate check
profiles against explicit task contracts before conducting a small versioned real-model comparison.

Resume value: a reproducible repair/verification controller, not a generic claim of autonomous coding.

### P2: Repository Map and Semantic Code Navigation

Necessity: high for code-RAG depth; start with Python, not a multi-language platform.

Current: AST symbol lookup returns syntax-based caller/callee candidates. Qdrant similarity is not
import resolution, type checking or reference resolution.

- Add a token-bounded repository map containing modules, public signatures and dependency hints.
- Connect one established Python language server for definitions, references and diagnostics.
- Use symbol/navigation results to select source ranges; use Qdrant for semantic discovery where
  symbol names are unknown. Preserve source/version evidence and handle outdated documents.
- Bound server lifetime, allowed roots, executable configuration and request deadlines. Do not
  automatically install or launch language servers selected by untrusted workspace content.

Done when: alias/import and same-name-symbol cases are handled better than current suffix matching,
with navigation tests and a fixed multi-file study measuring useful evidence and retrieval overhead.
No blind-holdout, exact-call-graph or token-saving claim without supporting evidence.

Resume value: complementary structural/semantic retrieval, rather than merely integrating a vector DB.

### P3: Run Controls and Trusted Policy Hooks

Necessity: medium-high; reliability and cost-control depth.

- Keep existing max-turn and context limits; additionally account for cumulative provider-reported
  usage, wall time, tool budget and bounded repeated-failure/no-progress patterns.
- Persist consumed budgets across resume. Missing provider usage must remain unknown, not zero cost.
- Add cooperative cancellation and safe stop points; retain unknown-outcome handling for interrupted
  external writes. Cancellation does not prove a remote action was rolled back.
- Introduce only the lifecycle hooks needed for deterministic policy and verification. They may
  tighten existing permissions, not bypass them. Reuse existing MCP allowlists and fingerprints.

Done when: budget/cancel/stuck stops are distinct, testable, durable and do not blindly retry writes.
Do not claim exact billing caps when token usage or provider prices are unavailable.

Resume value: recoverable, budget-aware execution with explicit failure semantics.

### P4: Bounded Read-Only Delegation (Optional)

Necessity: optional; after P1-P3, not the next immediate expansion.

Start with one explorer/reviewer subagent, separate context, parent-linked run record and a strict
tool/permission subset. No recursive spawning, independent patch application or extra provider API
is required. Reuse the same provider with explicit total/concurrency budgets and cancellation.
Return source-grounded findings rather than unlimited transcripts. A reviewer is not an independent
correctness oracle, and delegation does not automatically improve quality or reduce total cost.

Done when: parent/child trace, permission inheritance, failure/cancel behavior and bounded result
merging work on selected cross-file tasks. No team mailbox/autonomous swarm infrastructure.

### P5: Measured Index Lifecycle Scaling (Conditional)

Necessity: conditional on actual retrieval overhead or multi-repository needs.

Current Qdrant queries rescan sources and scroll IDs. Separate explicit synchronization/status from
querying only after measuring this overhead. Consider a persistent manifest, index generations and
incremental updates; preserve stale/deleted evidence rejection and index-version migration.
Measure corpus size, first/repeated indexing, p50/p95 latency and error behavior before choosing
targets. No PostgreSQL, second vector database, Kafka or distributed worker pool is justified now.

## Stopping Rule for Resume Readiness

The current project already supports a source-backed Agent infrastructure project entry. P1 and P2
would add substantial technical depth; P3 strengthens operational credibility. Completing P0-P3
with one compact reproducible demonstration is a reasonable target, not matching every commercial
agent feature. P4/P5 are optional choices, not prerequisites to applying for internships.
Do not defer the resume indefinitely while adding technologies. Rewrite it only after the chosen
bounded implementation scope and its evidence are finalized, as the user previously requested.

## Primary References (Accessed 2026-11-03)

- Learn Claude Code: https://github.com/shareAI-lab/learn-claude-code
- Claude Code public repository: https://github.com/anthropics/claude-code
- Hooks: https://code.claude.com/docs/en/hooks
- Subagents: https://code.claude.com/docs/en/sub-agents
- Aider repository map: https://aider.chat/docs/repomap.html
- Aider lint/test: https://aider.chat/docs/usage/lint-test.html
- Aider source: https://github.com/Aider-AI/aider/blob/main/aider/repomap.py
- Aider edit/feedback source: https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py
- SWE-agent ACI: https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/aci.md
- OpenCode LSP: https://opencode.ai/docs/lsp/
- OpenHands SDK: https://github.com/OpenHands/software-agent-sdk
- OpenHands conversation source: https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py

External links refer to mutable upstream branches/pages. Pin an upstream revision and review its
license if adapting implementation code; this comparison does not vendor any external source.
