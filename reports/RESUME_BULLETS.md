# Resume Bullets

Use these as source-backed resume bullet options. Pick 2-3 depending on resume space and keep the evidence files available for interview follow-up.

## Strong Options

- Implemented a lightweight Coding Agent Harness for repository maintenance, including an agent loop with retrieval preflight, permission-checked tool registry, todo planning, context compaction, workflow memory, semantic retry planning, execution traces, and interactive self-contained trace reports.
  Evidence: `README.md`, `reports/DEMO_python_bugfix.md`, `reports/DEMO_python_bugfix_TRACE.html`, `reports/MCP_SMOKE.md`.

- Built a deterministic 40-task code-maintenance benchmark covering Python bug fixes, test generation, nested packages, cross-file contracts, dependency/config interactions, plugin discovery, security checks, local RAG retrieval planning, agent-loop retrieve-then-read preflight, memory ranking, and MCP smoke validation; integrated it into GitHub Actions CI.
  Evidence: `README.md`, `.github/workflows/ci.yml`, `reports/MCP_SMOKE.md`.

- Ran and analyzed DeepSeek `deepseek-chat` real-agent evaluations, improving an initial 20-task pass rate from 18/20 to 20/20, validating 36-task full-suite runs at 36/36 and 35/36, then fixing the unstable `error_recovery` prompt path and restoring the post-fix full-suite run to 36/36.
  Evidence: `reports/AGENT_EVAL_36_TASKS.md`, `reports/AGENT_EVAL_36_TASKS_RUN2.md`, `reports/AGENT_EVAL_36_TASKS_RUN3.md`, `reports/ERROR_RECOVERY_AGENT_FIX.md`, `reports/AGENT_EVAL_20_TASKS.md`, `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/EVAL_STABILITY.md`.

- Ran two complete 40-task DeepSeek real-agent evaluations at 39/40 and 40/40, traced the sole first-run interruption to provider HTTP 503, increased transient request retries from 2 to 4, and measured repeated-run stability with 39 stable-pass tasks and one provider-affected fail-to-pass task.
  Evidence: `reports/AGENT_EVAL_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_RUN2.md`, `reports/EVAL_STABILITY_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`, `harness/agent.py`, `harness/evaluation.py`, `tests/test_agent.py`, `tests/test_evaluation.py`.

- Added evaluation-analysis CLIs (`analyze-eval`, `eval-history`, `eval-failures`, `eval-stability`, `retrieval-stability`) that preserve per-task comparison results and convert JSON outputs into trend, failure-mode, repeated-run, aggregate retrieval, and task-level paired-variance evidence for debugging agent behavior beyond pass rate.
  Evidence: `README.md`, `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/EVAL_STABILITY.md`.

- Implemented explainable conditional retrieval gating with bounded evidence, merged read ranges, configurable thresholds, and schema suppression; across two order-varied paired 8-task DeepSeek runs, kept all four auto/off rows at 8/8, activated retrieval on 4/8 tasks, and reduced tool calls by 7.41%-17.73% and direct reads by 14.29%-15.38%.
  Evidence: `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS.md`, `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_OFF_FIRST.md`, `reports/RETRIEVAL_GATING_STABILITY.md`, `reports/RETRIEVAL_GATING_8_TASKS_ANALYSIS.md`, `harness/agent.py`, `harness/evaluation.py`.

- Built a relevance-judged 10-query code retrieval benchmark and an optional local MiniLM hybrid backend with lexical/semantic fusion plus incremental embedding caching; improved project-specific MRR from 0.8000 to 0.9000 and Recall@3/5 from 0.80 to 1.00, recovering both retained semantic cases at rank 2 without a model API.
  Evidence: `benchmarks/retrieval/judgments.json`, `harness/hybrid_retrieval.py`, `harness/retrieval_benchmark.py`, `tests/test_hybrid_retrieval.py`, `reports/RETRIEVAL_QUALITY_BASELINE.md`, `reports/RETRIEVAL_QUALITY_HYBRID.md`.

- Exposed the harness through a minimal MCP stdio server with permission-checked tools, safe read-only resources, prompt templates, workspace resource guards, and a committed protocol smoke transcript.
  Evidence: `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md`.

- Designed a pluggable command-execution layer for shell, pytest, and Python syntax checks, adding an opt-in Docker backend with non-root execution, default-deny networking, dropped capabilities, CPU/memory/PID limits, filtered environment forwarding, fail-closed startup, and forced timeout cleanup; validated the runtime boundary in GitHub Actions.
  Evidence: `harness/execution.py`, `harness/tools.py`, `docker/sandbox/Dockerfile`, `tests/test_execution.py`, `.github/workflows/ci.yml`, `reports/DOCKER_SANDBOX_SMOKE.md`.

## Short Version

- Built a lightweight Coding Agent Harness for codebase maintenance, integrating a permission-checked tool registry, optional Docker-isolated command execution, RAG retrieval preflight, task planning, context compaction, workflow memory, error recovery, interactive traces, MCP resources/prompts, and a 40-task benchmark validated by a complete 40/40 real-agent run.

## Evidence Map

| Claim area | Evidence files |
| --- | --- |
| Agent loop and local demo | `reports/DEMO_python_bugfix.md`, `reports/DEMO_python_bugfix_TRACE.html`, `harness/agent.py`, `harness/tools.py` |
| Deterministic benchmark and CI | `README.md`, `.github/workflows/ci.yml`, `harness/evaluation.py`, `tests/test_evaluation.py` |
| Real-agent evaluation | `reports/AGENT_EVAL_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_RUN2.md`, `reports/EVAL_STABILITY_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`, `reports/AGENT_EVAL_40_TASKS_PROVIDER_RETRY.md`, `reports/AGENT_EVAL_36_TASKS.md`, `reports/AGENT_EVAL_36_TASKS_RUN2.md`, `reports/AGENT_EVAL_36_TASKS_RUN3.md`, `reports/ERROR_RECOVERY_AGENT_FIX.md`, `reports/AGENT_EVAL_20_TASKS.md` |
| Prompt-contract improvement | `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md` |
| Evaluation analysis tooling | `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/EVAL_STABILITY.md`, `reports/EVAL_STABILITY_40_TASKS.md`, `reports/RETRIEVAL_GATING_STABILITY.md` |
| Retrieval ablation | `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.md`, `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.md`, `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS.md`, `reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_OFF_FIRST.md`, `reports/RETRIEVAL_GATING_8_TASKS_ANALYSIS.md`, `reports/RETRIEVAL_GATING_STABILITY.md` |
| Retrieval quality benchmark | `benchmarks/retrieval/judgments.json`, `harness/retrieval_benchmark.py`, `harness/hybrid_retrieval.py`, `tests/test_retrieval_benchmark.py`, `tests/test_hybrid_retrieval.py`, `reports/RETRIEVAL_QUALITY_BASELINE.md`, `reports/RETRIEVAL_QUALITY_HYBRID.md` |
| MCP integration | `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md` |
| Docker execution boundary | `harness/execution.py`, `harness/tools.py`, `docker/sandbox/Dockerfile`, `tests/test_execution.py`, `.github/workflows/ci.yml`, `reports/DOCKER_SANDBOX_SMOKE.md` |

## Claims To Avoid

- Do not call it a full autonomous software engineer.
- Do not claim broad benchmark superiority from this project-specific 40-task suite.
- Do not describe all retrieval as embedding-based: lexical remains the default and workflow memory ranking remains lexical. The optional hybrid backend uses local embeddings but not a vector database.
- Do not generalize the hybrid result beyond the committed 10-query project fixture or claim agent-level gains before the focused lexical/hybrid agent comparison is run.
- Do not claim stable token or cost savings from retrieval gating; the two order-varied pairs changed direction on those metrics.
- Do not describe Docker as a VM or absolute security sandbox. Host mode remains policy-only, and Docker mode intentionally retains a writable workspace mount.
