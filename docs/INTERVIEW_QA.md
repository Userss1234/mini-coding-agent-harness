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

No. It is a harness-level permission system, not an OS-level sandbox. That distinction matters: the project blocks dangerous operations through its own tool policy, but it does not isolate processes like a container, VM, or seccomp profile.

Evidence:

- `README.md` Current Limitations
- `permission_policy` tool output

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

Before the first model turn, the agent can call `retrieve_then_read` with a focused task query. The loaded evidence pack is injected into the model's initial context, and the preflight is recorded in the JSONL trace.

Evidence:

- `harness/agent.py`
- `tests/test_agent.py`
- `reports/AGENT_EVAL_36_TASKS.md`

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

The committed benchmark has 36 tasks covering code quality, pytest, trace behavior, local retrieval, MCP RAG search, recovery, memory ranking, code maintenance, configuration fixes, documentation, security checks, and multi-file repairs. The full real-agent DeepSeek run passed 36/36.

Evidence:

- `harness/evaluation.py`
- `reports/AGENT_EVAL_36_TASKS.md`
- `reports/AGENT_EVAL_36_TASKS.json`

## 15. How do you know improvements were real?

The project keeps machine-readable JSON reports, per-task traces, trend reports, failure-mode dashboards, and stability reports. Earlier real-agent runs had failures such as over-exploration and max-turn stops; prompt and eval-contract improvements moved those tasks to passing states.

Evidence:

- `reports/EVAL_HISTORY.md`
- `reports/FAILURE_MODES.md`
- `reports/EVAL_STABILITY.md`
- `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`

## 16. What are the main limitations?

The current system is not a full autonomous software engineer. It has harness-level permission controls, not OS sandboxing. Retrieval is lexical, not embedding-based. MCP is stdio-only. The 36/36 real-agent result is currently a single committed full-suite run, so repeated-run variance still needs a second same-suite run.

Evidence:

- `README.md` Current Limitations
- `reports/EVAL_STABILITY.md`

## 17. What would you improve next?

The next best improvement is a second same-model 36-task run to measure repeated-run variance with `eval-stability`. After that, improve realism with larger multi-file fixtures, full-suite retrieval-off and memory/context ablations, optional MCP HTTP/SSE transport, and optional OS-level sandboxing.

Evidence:

- `README.md` Next Steps
- `reports/EVAL_STABILITY.md`

## 18. How should you summarize this on a resume?

Use a claim that stays grounded:

Implemented a lightweight Coding Agent Harness for repository maintenance with a permission-checked tool registry, retrieval preflight, task planning, context compaction, workflow memory, semantic retry planning, execution tracing, MCP resources/prompts, and a 36-task evaluation suite with committed real-agent reports.

Evidence:

- `reports/RESUME_BULLETS.md`
- `reports/AGENT_EVAL_36_TASKS.md`
- `reports/MCP_SMOKE.md`

