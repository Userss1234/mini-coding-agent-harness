# Local Runtime and Counterbalanced Validation

Date: 2026-10-28. Source revision: `e1a1c91`. Windows 10 22H2 / Python 3.12.2.
This follow-up supersedes the live-run gaps recorded at the end of Priority 4, not its
historical results. No source implementation, challenge prompt, acceptance test or gate was
changed during these runs. No push or remote CI was triggered.

## Docker Desktop

Docker Desktop 4.97.0 and WSL 2.7.14 are installed. The Linux engine responds as Docker
29.9.2. Login startup is enabled. Actual data disks exist under `D:\DockerDesktopData`:
`disk/docker_data.vhdx` and `main/ext4.vhdx`. These are Docker Desktop's WSL storage,
not a separate user-installed Linux desktop or dual-boot system.

The existing `docker/sandbox/Dockerfile` built successfully with locked runtime dependencies.
Image ID: `sha256:c3a7f8505912431d435698a83820e6332ab93aabd9e92c36f4ca0e22af55a821`.

- [Runtime smoke](LOCAL_DOCKER_SMOKE_20261028.md): UID 10001, workspace visible, outbound
  connection blocked, no host fallback.
- Additional live probes read cgroup limits: 536870912 bytes memory, `100000 100000` CPU
  quota/period, and 256 PIDs. `/proc/self/status` showed NoNewPrivs=1 and zero effective
  capabilities. A root-filesystem write failed with EROFS.
- Explicitly passing a non-secret `DEEPSEEK_API_KEY` sentinel to the executor did not forward
  the variable into the container. No real credential value is included in evidence.
- A 30-second sleep with a 2-second deadline returned `timeout`; cleanup succeeded and an
  independent Docker listing confirmed that named container no longer existed.
- Opening the external acceptance configuration for append failed with EROFS.
- [Docker reference validation](CHALLENGE_DOCKER_VALIDATION_20261028.json): all three buggy
  baselines rejected; all three references accepted across 17 external cases. Not an agent score.

The additional probes were operator-run Python snippets using the existing executors, not a new
automated security suite. Docker is not a hostile multi-tenant grading or VM boundary.

## Live MCP and Hybrid Retrieval

[Cross-feature report](LOCAL_CROSS_FEATURE_20261028.md): authenticated localhost MCP HTTP
initialization 200, initialized notification 202, tool request 200, session issued, actual
MiniLM hybrid retrieval, expected implementation path in the top three, no tool/request error.
Docker evidence was generated in this same local session. Embeddings run on the host, not in
the restricted execution container.

The process exited 0 but emitted a Windows asyncio accept-cancellation `WinError 995` warning
during server shutdown. The request checks passed; clean Windows server teardown remains a
follow-up. Do not describe this as warning-free runtime validation.

CPU-only optional environment: torch 2.15.0+cpu, sentence-transformers 5.7.0,
transformers 4.41.2. Existing cached all-MiniLM-L6-v2 weights produced 384-dimensional vectors
with Hugging Face/Transformers offline mode enabled. `pip check` passed. This is an observed
environment, not a newly locked optional dependency graph.

## Same-Corpus Retrieval Study

[Full observations](RETRIEVAL_V2_LIVE_STUDY_20261028.json): Python boundaries, 28 queries,
24 files, three repeated calls, lexical/hybrid then hybrid/lexical order. Both orders gave:

| Backend | MRR | Recall@5 | Zero-result queries |
|---|---:|---:|---:|
| Lexical | 0.9286 | 0.9286 | 1 |
| Hybrid | 0.9762 | 1.0000 | 0 |

Observed median first/repeated full calls were 29.08/28.94 ms and 31.03/31.03 ms for lexical;
584.34/69.73 ms and 580.06/71.59 ms for hybrid. First means empty document-embedding cache,
not cold OS/model. Other validation processes ran on the machine concurrently. These timings
are uncontrolled local observations, not isolated performance measurements or an SLA.
This inspected public development fixture does not establish agent superiority or generalization.

## Actual DeepSeek Agent ABBA

[Portable results](CHALLENGE_AGENT_ABBA_20261028.json): one complete sequence, same
`deepseek-chat` configuration, fresh task workspaces, Docker execution and external acceptance,
at most 12 turns per attempt. Normal line-window retrieval settings were retained; the separate
ranking study above uses Python boundaries and must not be treated as this run's agent ablation.

| Trial | Backend | Reservation | Retention | Cursor | Accepted |
|---|---|---|---|---|---:|
| 0 | lexical | pass | fail | pass | 2/3 |
| 1 | hybrid | pass | fail | pass | 2/3 |
| 2 | hybrid | pass | pass | pass | 3/3 |
| 3 | lexical | pass | fail | pass | 2/3 |

Total external acceptance: **9/12**; lexical **4/6**, hybrid **5/6**. Every baseline executed
the expected case count and failed before its model request. All protected inputs stayed unchanged.
The CLI exits 1 because some submissions fail acceptance, not because the suite was interrupted.
No failed attempt was removed or rerun.

All three failures apply the minimum-retention rule globally instead of separately per project.
The corresponding model self-checks did not exercise multiple projects. The one passing retention
attempt implements grouping. Evidence-path follow-up is 1.0 on every attempt, including failures:
it is not proof of requirement coverage or correct reasoning.

| Trace aggregate | Lexical | Hybrid |
|---|---:|---:|
| Model responses | 70 | 71 |
| Tool calls including preflight | 110 | 122 |
| Failed tool calls | 6 | 14 |
| Reported input tokens | 263803 | 277232 |
| Reported output tokens | 12921 | 14608 |
| Max-turn stops | 3 | 4 |

Totals: 141 model responses, 232 tool calls, 541035 input and 27529 output tokens. These are
provider-reported usage counters, not a reconciled bill or price estimate. Seven attempts stop
at the turn budget; acceptance can pass despite an unfinished conversational run. Therefore 9/12
is final-submission acceptance, not 9/12 normal autonomous completions. Twelve attempts on three
tiny author-known tasks are insufficient to claim a stable hybrid advantage; hybrid also uses
more tools/tokens in this sample.

Raw traces, candidates, external pytest outputs and per-attempt SQLite states remain ignored
under `artifacts/challenge-abba-20261028/`. Portable JSON retains verdicts and evidence paths,
not raw credentials or all model messages.

## Compatibility Gates and Next Work

- Full tests: 295 passed, one optional Windows symlink skip; 82.78% branch-enabled coverage.
- Ruff, mypy (33 source files), compileall and dependency consistency: pass.
- Existing scripted compatibility regression: 40/40, separate from the 9/12 agent challenges.
  Local artifacts: `artifacts/runtime-20261028-EVAL.md`, `.json` and matching trace directory.

Stop after this validation stage. A subsequent authorized improvement should address generic
requirement-to-check coverage and budget-aware verification, without hardcoding challenge
solutions or relaxing acceptance. Preserve this 9/12 baseline; any changed agent requires a new,
clearly labeled comparison rather than overwriting it. Also investigate the Windows MCP shutdown
warning. Resume wording and combined Git push remain separate user actions.
