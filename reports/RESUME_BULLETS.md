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

- Added evaluation-analysis CLIs (`analyze-eval`, `eval-history`, `eval-failures`, `eval-stability`) that convert JSON eval outputs into comparison, trend, failure-mode, and repeated-run stability dashboards for debugging agent behavior beyond pass rate.
  Evidence: `README.md`, `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/EVAL_STABILITY.md`.

- Optimized retrieval preflight with merged read ranges, deduplication, configurable per-read/total evidence caps, and trace metrics; on the repeated paired 8-task DeepSeek evaluation, preserved 8/8 in both conditions while narrowing retrieval's input-token premium from 34.38% to 13.48% and estimated-cost premium from 28.65% to 11.53%.
  Evidence: `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.md`, `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.md`, `reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md`, `harness/agent.py`, `harness/retrieval.py`.

- Exposed the harness through a minimal MCP stdio server with permission-checked tools, safe read-only resources, prompt templates, workspace resource guards, and a committed protocol smoke transcript.
  Evidence: `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md`.

## Short Version

- Built a lightweight Coding Agent Harness for codebase maintenance, integrating a permission-checked tool registry, RAG retrieval preflight, task planning, context compaction, workflow memory, semantic retry planning, error recovery, interactive execution tracing, MCP resources/prompts, and a 40-task deterministic benchmark validated by a complete 40/40 real-agent run.

## Evidence Map

| Claim area | Evidence files |
| --- | --- |
| Agent loop and local demo | `reports/DEMO_python_bugfix.md`, `reports/DEMO_python_bugfix_TRACE.html`, `harness/agent.py`, `harness/tools.py` |
| Deterministic benchmark and CI | `README.md`, `.github/workflows/ci.yml`, `harness/evaluation.py`, `tests/test_evaluation.py` |
| Real-agent evaluation | `reports/AGENT_EVAL_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_RUN2.md`, `reports/EVAL_STABILITY_40_TASKS.md`, `reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`, `reports/AGENT_EVAL_40_TASKS_PROVIDER_RETRY.md`, `reports/AGENT_EVAL_36_TASKS.md`, `reports/AGENT_EVAL_36_TASKS_RUN2.md`, `reports/AGENT_EVAL_36_TASKS_RUN3.md`, `reports/ERROR_RECOVERY_AGENT_FIX.md`, `reports/AGENT_EVAL_20_TASKS.md` |
| Prompt-contract improvement | `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md` |
| Evaluation analysis tooling | `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/EVAL_STABILITY.md`, `reports/EVAL_STABILITY_40_TASKS.md` |
| Retrieval ablation | `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.md`, `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.md`, `reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md` |
| MCP integration | `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md` |

## Claims To Avoid

- Do not call it a full autonomous software engineer.
- Do not claim broad benchmark superiority from this project-specific 40-task suite.
- Do not claim embedding-based retrieval; current retrieval and memory ranking are lexical.
- Do not claim OS-level sandboxing; the project implements harness-level permission controls.
