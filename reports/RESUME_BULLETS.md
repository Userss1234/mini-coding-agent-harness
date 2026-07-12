# Resume Bullets

Use these as source-backed resume bullet options. Pick 2-3 depending on resume space and keep the evidence files available for interview follow-up.

## Strong Options

- Implemented a lightweight Coding Agent Harness for repository maintenance, including an agent loop with retrieval preflight, permission-checked tool registry, todo planning, context compaction, workflow memory, semantic retry planning, execution traces, and static trace reports.
  Evidence: `README.md`, `reports/DEMO_python_bugfix.md`, `reports/DEMO_python_bugfix_TRACE.html`, `reports/MCP_SMOKE.md`.

- Built a deterministic 36-task code-maintenance benchmark covering Python bug fixes, test generation, config updates, security checks, multi-file contract repairs, local RAG retrieval planning, agent-loop retrieve-then-read preflight, memory ranking, and MCP smoke validation; integrated it into GitHub Actions CI.
  Evidence: `README.md`, `.github/workflows/ci.yml`, `reports/MCP_SMOKE.md`.

- Ran and analyzed a 20-task DeepSeek `deepseek-chat` real-agent evaluation, improving pass rate from 18/20 to 20/20 through trace-backed prompt-contract changes while tracking tool calls, duration, token usage, cost, and failure patterns.
  Evidence: `reports/AGENT_EVAL_20_TASKS.md`, `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`, `reports/AGENT_EVAL_20_TASKS_BEFORE.json`, `reports/AGENT_EVAL_20_TASKS.json`.

- Added evaluation-analysis CLIs (`analyze-eval`, `eval-history`, `eval-failures`) that convert JSON eval outputs into comparison, trend, and failure-mode dashboards for debugging agent behavior beyond pass rate.
  Evidence: `README.md`, `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md`.

- Exposed the harness through a minimal MCP stdio server with permission-checked tools, safe read-only resources, prompt templates, workspace resource guards, and a committed protocol smoke transcript.
  Evidence: `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md`.

## Short Version

- Built a lightweight Coding Agent Harness for codebase maintenance, integrating a permission-checked tool registry, agent-loop retrieval preflight, task planning, context compaction, workflow memory, error recovery, execution tracing, MCP resources/prompts, and a 36-task deterministic benchmark plus 20-task model-backed evaluation artifacts.

## Evidence Map

| Claim area | Evidence files |
| --- | --- |
| Agent loop and local demo | `reports/DEMO_python_bugfix.md`, `reports/DEMO_python_bugfix_TRACE.html`, `harness/agent.py`, `harness/tools.py` |
| Deterministic benchmark and CI | `README.md`, `.github/workflows/ci.yml`, `harness/evaluation.py`, `tests/test_evaluation.py` |
| Real-agent evaluation | `reports/AGENT_EVAL_20_TASKS.md`, `reports/AGENT_EVAL_20_TASKS.json`, `reports/AGENT_EVAL_20_TASKS_BEFORE.json` |
| Prompt-contract improvement | `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md` |
| Evaluation analysis tooling | `harness/eval_analysis.py`, `tests/test_eval_analysis.py`, `reports/EVAL_HISTORY.md`, `reports/FAILURE_MODES.md` |
| MCP integration | `MCP.md`, `harness/mcp_server.py`, `tests/test_mcp_server.py`, `reports/MCP_SMOKE.md` |

## Claims To Avoid

- Do not call it a full autonomous software engineer.
- Do not claim broad benchmark superiority from the 20-task run.
- Do not claim embedding-based retrieval; current retrieval and memory ranking are lexical.
- Do not claim OS-level sandboxing; the project implements harness-level permission controls.
