# Architecture

This project is a small coding-agent harness for repository maintenance. The model chooses actions; the harness owns tools, context loading, permissions, execution, traces, and evaluation.

## System Overview

```mermaid
flowchart TD
    U["User or eval task"] --> CLI["main.py CLI"]
    CLI --> Agent["harness.agent.run_agent"]
    CLI --> Scripted["harness.evaluation scripted runners"]
    CLI --> MCP["harness.mcp_server stdio server"]

    Agent --> Preflight["Retrieval preflight"]
    Preflight --> RTR["retrieve_then_read"]
    RTR --> RAG["Local lexical retrieval index"]
    RAG --> Evidence["Line-range evidence pack"]
    Evidence --> Model["Model turn"]

    Agent --> Model
    Model --> ToolUse["Tool request"]
    ToolUse --> Registry["ToolRegistry.call"]
    Registry --> Policy["Permission policy"]
    Policy --> Tools["File, shell, Git, tests, memory, RAG, reports"]
    Tools --> Trace["TraceLogger JSONL"]
    Trace --> Agent

    Trace --> Compact["compact_context"]
    Trace --> Retry["recover_errors / retry_plan"]
    Compact --> Model
    Retry --> Model

    Agent --> Answer["Final answer"]
    Scripted --> EvalReport["Markdown and JSON eval reports"]
    Agent --> EvalReport
    EvalReport --> Analysis["analyze-eval / eval-history / eval-failures / eval-stability"]
```

## Runtime Flow

1. A user command or eval task enters through `main.py`.
2. Agent mode builds a `ToolRegistry` and starts `harness.agent.run_agent()`.
3. If retrieval is enabled, the agent preloads a `retrieve_then_read` evidence pack before the first model turn.
4. The model returns either text or a tool request.
5. Every tool request goes through `ToolRegistry.call(...)`, which applies permission policy before dispatching.
6. Tool results are written to append-only JSONL through `TraceLogger`.
7. Failed tools can trigger `retry_plan` feedback; long traces can be summarized with `compact_context`.
8. Eval runs verify the final workspace state and write Markdown/JSON reports.
9. Analysis CLIs convert JSON reports into trend, failure, and stability dashboards.

## Main Modules

| Module | Role |
|---|---|
| `main.py` | CLI entry point for agent runs, evals, report analysis, trace rendering, demos, and MCP. |
| `harness/agent.py` | Model-driven loop, retrieval preflight, tool-result feedback, max-turn context compaction. |
| `harness/tools.py` | Permission-checked tool registry and tool implementations. |
| `harness/retrieval.py` | Local lexical chunk retrieval, read-plan generation, safe path filtering. |
| `harness/evaluation.py` | Scripted and real-agent benchmark runners, task fixtures, verifiers, report generation. |
| `harness/eval_analysis.py` | Eval comparison, trend history, failure dashboard, and repeated-run stability reports. |
| `harness/mcp_server.py` | MCP stdio server exposing selected tools, resources, templates, and prompts. |
| `harness/trace.py` | Append-only JSONL trace writer. |
| `harness/trace_viewer.py` | Static HTML trace rendering. |

## Tool Registry Boundary

All tool execution goes through `ToolRegistry.call(...)`.

```mermaid
flowchart LR
    Request["Tool call request"] --> Scope["Workspace path scope"]
    Scope --> Risk["Risk classification"]
    Risk --> Policy["Permission policy"]
    Policy --> Dispatch["Tool handler"]
    Dispatch --> Metadata["ToolResult metadata"]
    Metadata --> Trace["JSONL trace event"]
```

The important design choice is that the model cannot directly touch the filesystem, shell, Git, tests, memory, or reports. It can only request registered tools. The harness then decides whether and how to execute the request.

## Retrieval Boundary

Retrieval is local and lexical. It is not embedding-based and does not use a vector database.

```mermaid
flowchart TD
    Query["Task query"] --> Index["Index safe text files"]
    Index --> Filter["Skip .env, .git, artifacts, eval_runs, skills"]
    Filter --> Score["Lexical chunk scoring"]
    Score --> Plan["rag_explain read plan"]
    Plan --> Read["read_file line ranges"]
    Read --> Pack["retrieve_then_read evidence pack"]
```

This makes retrieval explainable: reports and traces show which paths and line ranges were selected.

## Evaluation Pipeline

```mermaid
flowchart TD
    Tasks["36 eval tasks"] --> Mode{"Mode"}
    Mode --> Scripted["Scripted deterministic runner"]
    Mode --> AgentMode["Real model-backed agent loop"]
    Scripted --> Verify["Task verifier"]
    AgentMode --> Verify
    Verify --> Report["Markdown report"]
    Verify --> JSON["Machine-readable JSON"]
    JSON --> History["eval-history"]
    JSON --> Failures["eval-failures"]
    JSON --> Stability["eval-stability"]
```

The committed reports show the project as an evaluated system, not only an implementation. The most important artifacts are:

- `reports/AGENT_EVAL_36_TASKS.md`
- `reports/EVAL_HISTORY.md`
- `reports/FAILURE_MODES.md`
- `reports/EVAL_STABILITY.md`
- `reports/MCP_SMOKE.md`

## MCP Surface

The MCP server does not bypass the harness. MCP `tools/call` delegates to the same `ToolRegistry.call(...)` path as the CLI and agent loop.

```mermaid
flowchart LR
    Client["MCP client"] --> Server["harness.mcp_server"]
    Server --> Registry["ToolRegistry.call"]
    Server --> Resources["Selected read-only resources"]
    Server --> Prompts["Prompt templates"]
    Registry --> Policy["Same permission policy"]
```

MCP exposes selected project documents and reports, including evaluation history, failure modes, stability, and MCP smoke evidence.

## What To Emphasize In Interviews

- The model makes decisions, but the harness controls execution.
- Every action is traceable through JSONL.
- Permission policy is centralized in the tool registry.
- Retrieval is explainable because it returns paths and line ranges.
- Evaluation includes task verifiers, per-task traces, cost/tool metrics, failure analysis, and stability reporting.

## Current Limits

- Permission checks are harness-level, not OS-level sandboxing.
- Retrieval is lexical, not embedding-based.
- MCP is stdio-only.
- The committed full-suite real-agent results now include three same-model DeepSeek runs: 36/36, 35/36, and post-fix 36/36. `eval-stability` records `error_recovery` as the historical variance case.
