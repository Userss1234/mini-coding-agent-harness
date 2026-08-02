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

The retrieval layer is local lexical retrieval over safe workspace text chunks. It indexes allowed text files, skips sensitive/generated paths and workflow memories under `skills/`, ranks chunks by query terms, turns matches into read plans, and can load the planned line ranges as evidence.

Evidence:

- `harness/retrieval.py`
- `retrieve_then_read`, `rag_search`, and `rag_explain` in `harness/tools.py`
- `tests/test_retrieval.py`
- `reports/AGENT_EVAL_36_TASKS.md`

## 8. Is the RAG embedding-based?

No. Current retrieval is lexical, not vector-based and not embedding-based. The project is honest about this limitation. The current goal is explainable local retrieval with path and line metadata, not semantic vector search.

Evidence:

- `README.md` Current Limitations
- `harness/retrieval.py`

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

MCP exposes the same permission-checked tool registry through a stdio server. It also exposes selected read-only resources, workspace resource templates, and prompt templates. This lets an MCP client inspect the same tools and evidence without bypassing the harness policy.

Evidence:

- `harness/mcp_server.py`
- `MCP.md`
- `tests/test_mcp_server.py`
- `reports/MCP_SMOKE.md`

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

The current system is not a full autonomous software engineer. It has harness-level permission controls, not OS sandboxing. Retrieval is lexical, not embedding-based. MCP is stdio-only. The two complete expanded-suite runs passed 39/40 and 40/40; 39 tasks were stable passes, while `shell_no_shell_execution` remains a fail-to-pass stability case because its first run stopped on a provider HTTP 503 before verification.

Evidence:

- `README.md` Current Limitations
- `reports/EVAL_STABILITY_40_TASKS.md`

## 17. What would you improve next?

Conditional gating and the first order-varied stability check are complete. Two prompt-aligned 8-task pairs ran in opposite orders; all four configuration rows passed 8/8, auto activated retrieval on 4/8 tasks in both runs, tool calls stayed 7.41%-17.73% lower, and direct reads stayed 14.29%-15.38% lower. Input-token and cost direction changed between runs, so the project does not claim stable cost savings. Next, preserve per-task comparison rows and time-box task-level paired variance. Docker execution isolation is implemented; the following major stages are retrieval-dependent fixtures plus optional hybrid reranking, then MCP Streamable HTTP and one final cross-feature validation.

Evidence:

- `README.md` Next Steps
- `reports/RETRIEVAL_GATING_8_TASKS_ANALYSIS.md`
- `reports/RETRIEVAL_GATING_STABILITY.md`

## 18. How should you summarize this on a resume?

Use a claim that stays grounded:

Implemented a lightweight Coding Agent Harness for repository maintenance with a permission-checked tool registry, retrieval preflight, task planning, context compaction, workflow memory, semantic retry planning, interactive execution-trace reports, MCP resources/prompts, and a 40-task deterministic suite; ran two complete DeepSeek real-agent evaluations at 39/40 and 40/40, traced the sole first-run interruption to provider HTTP 503, and verified the retry hardening in the full second run.

Evidence:

- `reports/RESUME_BULLETS.md`
- `reports/AGENT_EVAL_40_TASKS_RUN2.md`
- `reports/EVAL_STABILITY_40_TASKS.md`
- `reports/MCP_SMOKE.md`
