# Interview Q&A

Use this file to practice explaining the project out loud. Keep answers evidence-backed: point to code, reports, and traces instead of making broad claims.

## 1. What is this project?

This is a lightweight coding-agent harness for repository maintenance. The model decides the next action, while the harness provides the tool registry, permission checks, retrieval context, todo planning, trace logging, memory, error recovery, MCP exposure, and evaluation reports.

Evidence:

- `harness/agent.py`
- `harness/tools.py`
- `harness/evaluation.py`
- `reports/AGENT_EVAL_36_TASKS.md`

## 2. How is it different from a chatbot or a thin LLM wrapper?

A chatbot mainly returns text. This harness turns a maintenance request into tool calls against a workspace: read files, edit files, run tests, inspect traces, apply permission policy, and produce evidence. The LLM is one component inside a controlled execution loop, not the whole product.

Evidence:

- `harness.agent.run_agent()`
- `ToolRegistry.call(...)` in `harness/tools.py`
- JSONL traces under eval reports

## 3. What is the runtime flow?

The flow is: task prompt -> optional retrieval preflight -> model response -> tool call execution -> trace logging -> retry/context feedback -> final answer -> eval verifier. For benchmark tasks, each run writes a per-task JSONL trace and a Markdown/JSON summary.

Evidence:

- `harness/agent.py`
- `harness/trace.py`
- `reports/AGENT_EVAL_36_TASKS.md`

## 4. What tools does the harness expose?

The main tools include file reads/writes, exact text edits, grep, pytest, Python compilation, Git diff, shell commands, todo planning, memory, recovery, local RAG search, retrieve-then-read, trace compaction, and permission-policy reporting.

Evidence:

- `harness/tools.py`
- `README.md` tool table
- `reports/MCP_SMOKE.md` tool list

## 5. How does permission control work?

All tool calls go through `ToolRegistry.call(...)`. Reads are allowed inside the workspace. Writes require configured write access and produce diff metadata. Delete requires explicit confirmation. Shell and Git commands are constrained by allowlists and shell operators are blocked.

Evidence:

- `ToolRegistry` in `harness/tools.py`
- `permission_policy` tool output
- `tests/test_tools.py`
- `reports/MCP_SMOKE.md`

## 6. Is this a real sandbox?

The default host backend is still a harness-level permission system, not an OS sandbox. The optional Docker backend adds a real container boundary for shell, pytest, and compilation: non-root execution, disabled networking, dropped capabilities, a read-only root filesystem, resource limits, and timeout cleanup. It is still not a VM or absolute security boundary, and the writable workspace mount remains accessible inside the container.

Evidence:

- `README.md` Current Limitations
- `permission_policy` tool output
- `harness/execution.py`
- `docs/DOCKER_SANDBOX.md`
- `tests/test_execution.py`
- `reports/DOCKER_SANDBOX_SMOKE.md`

## 7. How does RAG work in this project?

The retrieval layer builds one safe local workspace chunk index. It skips sensitive/generated paths and workflow memories under `skills/`, returns path/line evidence, turns matches into read plans, and loads bounded line ranges. The default backend ranks chunks lexically. An optional local hybrid backend combines normalized lexical scores with MiniLM cosine similarity and incrementally caches document embeddings. On the same 10-query judgments, lexical reaches 0.8000 MRR and 0.70/0.80/0.80 Recall@1/3/5; hybrid reaches 0.9000 MRR and 0.70/1.00/1.00. A separate lexical-first 8-task agent comparison found no workflow-efficiency gain and exposed a lexical-only verifier assumption, which was fixed and validated in a targeted 1/1 pair.

Evidence:

- `harness/retrieval.py`
- `harness/hybrid_retrieval.py`
- `retrieve_then_read`, `rag_search`, and `rag_explain` in `harness/tools.py`
- `tests/test_retrieval.py`
- `tests/test_hybrid_retrieval.py`
- `benchmarks/retrieval/judgments.json`
- `reports/RETRIEVAL_QUALITY_BASELINE.md`
- `reports/RETRIEVAL_QUALITY_HYBRID.md`
- `reports/RETRIEVAL_BACKEND_8_TASKS_ANALYSIS.md`
- `reports/AGENT_EVAL_36_TASKS.md`

## 8. Is the RAG embedding-based?

The default backend is not embedding-based: it remains dependency-free lexical retrieval. The optional hybrid backend is embedding-based and runs `sentence-transformers/all-MiniLM-L6-v2` locally, then fuses semantic and lexical scores. It is not a vector database and does not call a model API. The judged corpus deliberately retained two lexical semantic misses; hybrid recovers both relevant paths at rank 2. That result is project-specific rather than evidence of general retrieval superiority.

Evidence:

- `docs/HYBRID_RETRIEVAL.md`
- `harness/retrieval.py`
- `harness/hybrid_retrieval.py`
- `reports/RETRIEVAL_QUALITY_BASELINE.md`
- `reports/RETRIEVAL_QUALITY_HYBRID.md`

## 9. What is retrieval preflight?

Before the first model turn, retrieval can run in `on`, `auto`, or `off` mode. Auto scores explainable task-complexity signals and either suppresses all five retrieval schemas plus preflight or runs the bounded `retrieve_then_read` path. Active preflight merges overlapping ranges, removes exact duplicates, and caps per-read and total evidence. Traces expose the gate decision, schema counts, evidence metrics, and budget.

Evidence:

- `harness/agent.py`
- `tests/test_agent.py`
- `reports/RETRIEVAL_GATING_8_TASKS_ANALYSIS.md`

## 10. What is context compaction?

Context compaction summarizes the trace into the current goal, files read, files changed, key errors, tool counts, latest todos, and a suggested next step. The agent can call it explicitly, and the loop also uses it when max turns are reached.

Evidence:

- `compact_context` in `harness/tools.py`
- `tests/test_tools.py`
- `reports/EVAL_STABILITY.md`

## 11. How does memory work?

Memory is stored as Markdown workflow notes under `skills/*.md`. The harness can list memories, rank them lexically by query relevance, and read a selected memory into the agent workflow. It is useful for reusable patterns, but it is not full long-term vector memory.

Evidence:

- `list_memories`, `read_memory`, and `save_memory` in `harness/tools.py`
- `skills/tool-implementation-verification-workflow.md`
- `tests/test_tools.py`

## 12. How does error recovery work?

Failed tool calls are classified into categories such as edit-match failure, permission block, missing file, timeout, no tests collected, missing dependency, and Git repo missing. `retry_plan` turns those failures into ordered next steps and can be injected back into the agent loop after a failed tool call.

Evidence:

- `recover_errors` and `retry_plan` in `harness/tools.py`
- `_augment_failed_tool_result` in `harness/agent.py`
- `tests/test_agent.py`
- `tests/test_tools.py`

## 13. What does MCP add?

MCP exposes the same permission-checked tool registry through stdio and a `2025-11-25`-compatible Streamable HTTP transport. HTTP adds localhost-safe binding, exact Origin validation, static Bearer authentication, cryptographically random expiring sessions, and DELETE termination. It returns JSON for POST and 405 for GET, while both transports reuse `MCPToolServer` and `ToolRegistry.call(...)` instead of duplicating business logic.

Evidence:

- `harness/mcp_server.py`
- `harness/mcp_http.py`
- `MCP.md`
- `tests/test_mcp_server.py`
- `tests/test_mcp_http.py`
- `reports/MCP_SMOKE.md`
- `reports/MCP_HTTP_SMOKE.md`

## 14. What did the benchmark validate?

The committed deterministic benchmark has 40 tasks covering code quality, pytest, trace behavior, local retrieval, MCP RAG search, recovery, memory ranking, code maintenance, configuration fixes, documentation, security checks, nested packages, dependency interactions, and multi-file repairs. The expanded full real-agent DeepSeek runs passed 39/40 and then 40/40 after transient request retry hardening. Earlier 36-task repeats remain committed as historical stability evidence.

Evidence:

- `harness/evaluation.py`
- `reports/AGENT_EVAL_40_TASKS.md`
- `reports/AGENT_EVAL_40_TASKS_RUN2.md`
- `reports/EVAL_STABILITY_40_TASKS.md`
- `reports/AGENT_EVAL_36_TASKS.md`
- `reports/AGENT_EVAL_36_TASKS.json`
- `reports/AGENT_EVAL_36_TASKS_RUN2.md`
- `reports/AGENT_EVAL_36_TASKS_RUN2.json`
- `reports/AGENT_EVAL_36_TASKS_RUN3.md`
- `reports/AGENT_EVAL_36_TASKS_RUN3.json`

## 15. How do you know improvements were real?

The project keeps machine-readable JSON reports, per-task traces, trend reports, failure-mode dashboards, and stability reports. Earlier real-agent runs had failures such as over-exploration and max-turn stops; prompt and eval-contract improvements moved those tasks to passing states.

Evidence:

- `reports/EVAL_HISTORY.md`
- `reports/FAILURE_MODES.md`
- `reports/EVAL_STABILITY.md`
- `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`

## 16. What are the main limitations?

The current system is not a full autonomous software engineer. Host execution remains policy-only; optional Docker execution adds a container boundary but not a VM or absolute sandbox. Retrieval defaults to lexical; the optional embedding backend has a 10-query project-specific ranking benchmark, no vector database, and only one lexical-first focused agent pair. That pair found no hybrid efficiency gain and therefore does not support agent-level superiority claims. MCP HTTP uses static Bearer authentication rather than full OAuth and does not implement SSE replay or the newer `2026-07-28` protocol surface. The two complete expanded-suite runs passed 39/40 and 40/40; 39 tasks were stable passes, while `shell_no_shell_execution` remains a fail-to-pass stability case because its first run stopped on a provider HTTP 503 before verification.

Evidence:

- `README.md` Current Limitations
- `reports/EVAL_STABILITY_40_TASKS.md`

## 17. What would you improve next?

Conditional gating, Docker execution isolation, local hybrid RAG, focused backend agent evidence, MCP Streamable HTTP, and the cross-feature validation path are complete. The committed combined report uses real cached MiniLM retrieval over HTTP plus existing Docker CI runtime evidence; the immediate operational step is to trigger the manual CI job so Docker is rebuilt in the same workflow before the report artifact is generated. After that, the project is resume-ready at this scope. The next protocol step is optional official SDK v2 migration with parity proof, not more one-off feature expansion.

Evidence:

- `README.md` Next Steps
- `reports/RETRIEVAL_GATING_8_TASKS_ANALYSIS.md`
- `reports/RETRIEVAL_GATING_STABILITY.md`
- `tests/test_eval_analysis.py`
- `tests/test_evaluation.py`
- `reports/RETRIEVAL_QUALITY_BASELINE.md`
- `reports/CROSS_FEATURE_VALIDATION.md`

## 18. How should you summarize this on a resume?

Use a claim that stays grounded:

Implemented a lightweight Coding Agent Harness for repository maintenance with permission-checked tools, Docker-isolated command execution, lexical/local-hybrid RAG, paired agent evaluation, execution traces, and shared MCP stdio/Streamable HTTP exposure with Origin, Bearer, and session controls; validated a 40-task deterministic suite and a focused cross-feature path without claiming that embeddings run inside the container or improve agent efficiency.

Evidence:

- `reports/RESUME_BULLETS.md`
- `reports/AGENT_EVAL_40_TASKS_RUN2.md`
- `reports/EVAL_STABILITY_40_TASKS.md`
- `reports/MCP_SMOKE.md`
- `reports/MCP_HTTP_SMOKE.md`
- `reports/CROSS_FEATURE_VALIDATION.md`
