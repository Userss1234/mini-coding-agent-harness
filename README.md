# Mini Coding Agent Harness

A lightweight coding-agent harness for repository maintenance experiments.

This project is not a chatbot and not a thin LLM wrapper. It is a small agent infrastructure project: the model decides what to do, while the harness provides tools, permissions, execution traces, context summaries, memory, recovery guidance, and evaluation reports.

Chinese documentation: [README.zh-CN.md](README.zh-CN.md)

License: [MIT](LICENSE)

## Quick Start

```powershell
python -m pip install -r requirements.txt
python -m pytest
python main.py eval --mode scripted
python main.py demo --task python_bugfix
```

For a model-backed smoke run, copy `.env.example` to `.env`, set a DeepSeek/OpenAI-compatible or Anthropic-compatible API key, then run:

```powershell
python main.py eval --mode agent --task python_bugfix --task python_add_tests --task multi_file_service_fix
```

## Project Snapshot

- **Scripted benchmark:** 31 deterministic repository-maintenance tasks, 31/31 passing in the committed snapshot.
- **Real-agent eval:** DeepSeek `deepseek-chat` report over 10 representative tasks, 10/10 passing; expanded 20-task run, 20/20 passing.
- **Ablations:** Memory/context comparison over 2 tasks and retrieval-on/off comparison for `context_pack_retrieval`.
- **CI:** `.github/workflows/ci.yml` runs tests, syntax checks, scripted benchmark, trace rendering, and MCP smoke validation.
- **Reports:** Start with [`reports/AGENT_EVAL_20_TASKS.md`](reports/AGENT_EVAL_20_TASKS.md), [`reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md`](reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md), [`reports/AGENT_EVAL_10_TASKS.md`](reports/AGENT_EVAL_10_TASKS.md), [`reports/AGENT_COMPARE_2_TASKS.md`](reports/AGENT_COMPARE_2_TASKS.md), and [`reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md`](reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md).

## What It Does

The harness supports repository-maintenance workflows such as:

```text
task -> todo plan -> tool calls -> file/test/git operations -> trace.jsonl -> REVIEW.md / EVAL.md
```

Current capabilities:

- Tool registry for file, shell, Git, test, memory, and report tools
- Permission checks for writes plus allowlisted Shell/Git operations executed with `shell=False`
- Confirmed file deletion with audit metadata
- Targeted file edits with exact-once replacement
- Pytest execution with return code, duration, target, and timeout metadata
- Git diff inspection with clear non-Git-repository handling
- Todo planning and basic todo quality checks
- Injectable model client for deterministic agent-loop tests
- JSONL execution tracing for every tool call
- Retry/backoff for transient model requests and non-write tool handler failures
- Semantic retry planning from failed trace events
- Automatic retry-plan context injected into the model loop after failed tools
- Context compaction from long traces and max-turn stops
- Query-ranked repository context retrieval with file snippets and line ranges
- Query-ranked workflow memory stored in `skills/*.md`
- Error recovery suggestions for failed tool calls
- Evidence-backed repository review generation
- Static HTML trace report generation
- MCP stdio server exposing the same permission-checked tool registry, selected resources, and prompt templates
- Deterministic Markdown/JSON evaluation reports with per-task traces
- GitHub Actions CI for tests, compilation, benchmark, trace-report artifacts, and MCP protocol smoke checks
- Machine-readable permission policy reports for workspace, shell, Git, and sandbox boundaries

## Architecture

```text
main.py
  -> harness.agent.run_agent()        model-driven tool loop
  -> harness.review.inspect_repo()    deterministic repository inspection
  -> harness.evaluation.run_evaluation() benchmark runner

harness.tools.ToolRegistry
  -> permission checks
  -> tool dispatch
  -> trace logging

harness.trace.TraceLogger
  -> append-only JSONL events
```

The model-facing tools are registered in `harness/tools.py`. Each tool returns a `ToolResult` with `ok`, `output`, and optional metadata. `ToolRegistry.call(...)` applies permission policy before dispatching the tool and records the result in trace JSONL.

## Tools

| Tool | Purpose |
|---|---|
| `todo_write` | Create/update a task plan and record todo quality metadata. |
| `list_python_files` | List Python files while ignoring caches and evaluation workspaces. |
| `read_file` | Read workspace files with optional line ranges, line/character limits, and read-cache metadata. |
| `context_pack` | Retrieve task-relevant workspace snippets with lexical path and line scoring. |
| `write_file` | Write files and record diff metadata. |
| `edit_file` | Replace an exact text block that appears exactly once. |
| `delete_file` | Delete one file only with explicit confirmation; directories are refused. |
| `grep` | Search files by substring. |
| `permission_policy` | Report write, shell, Git, and sandbox permission boundaries. |
| `shell` | Run allowlisted commands with `shell=False`, blocking operators, force flags, and mutating Git commands. |
| `run_py_compile` | Check Python syntax. |
| `run_tests` | Run pytest, defaulting to `tests/` only when it contains pytest files, otherwise the workspace root. |
| `git_diff` | Run `git diff -- .` inside a Git worktree. |
| `compact_context` | Summarize trace state into goal, files, errors, and next step. |
| `recover_errors` | Classify failed tool calls and suggest recovery steps. |
| `retry_plan` | Convert failed trace events into an ordered next-step plan with suggested tools. |
| `save_memory` | Save reusable workflows into `skills/*.md`. |
| `list_memories` | List saved workflow memories, optionally ranked by query relevance. |
| `read_memory` | Read a saved workflow memory. |
| `cache_stats` | Report read-cache hit/miss metrics. |

## Run

From this directory:

Optional editable install:

```powershell
python -m pip install -e ".[dev]"
mini-agent tools
```

```powershell
python main.py tools
python main.py manual
python main.py demo --task python_bugfix
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
python main.py --allow-write --fresh-trace inspect
python main.py trace-report --input trace.jsonl --output TRACE.html
python main.py eval --mode scripted
python main.py eval --mode scripted --json-output EVAL.json
python main.py eval --mode scripted --compare --task syntax_check
python main.py eval --mode scripted --compare-retrieval --task syntax_check
python main.py eval --mode agent --retrieval off --task python_bugfix
python main.py eval --mode scripted --category multi_file
python main.py analyze-eval --before artifacts/AGENT_EVAL_BEFORE.json --after reports/AGENT_EVAL_20_TASKS.json --output artifacts/AGENT_EVAL_ANALYSIS.md --trace-root .
python main.py eval-history --run baseline=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run current=reports/AGENT_EVAL_20_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run baseline=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run current=reports/AGENT_EVAL_20_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
```

Local demo flow:

```text
1. todo_write creates a repair plan.
2. run_tests reproduces the failing calculator test.
3. read_file inspects calculator.py.
4. edit_file fixes the bug.
5. run_tests verifies the fix.
6. git_diff shows the final change.
7. trace-report renders the JSONL trace as HTML.
```

The demo writes generated output under `artifacts/demo/python_bugfix/`. Committed demo samples are available in `reports/DEMO_python_bugfix.md` and `reports/DEMO_python_bugfix_TRACE.html`.

Optional model-driven loop:

```powershell
python main.py --fresh-trace ask "List Python files, run tests, and summarize with sources."
python main.py eval --mode agent --memory on --context on --task python_bugfix
```

The model loop and `eval --mode agent` read these variables from `.env` when available. Use `.env.example` as the template. Anthropic-compatible and DeepSeek/OpenAI-compatible chat-completions clients are supported. Agent evaluation can call the model many times, so use `--task <task_id>` while tuning a single fixture.

```text
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AGENT_EVAL_MAX_TURNS=12

# Or Anthropic-compatible:
ANTHROPIC_API_KEY
ANTHROPIC_BASE_URL
MODEL_ID
```

Suggested first real-agent smoke run:

```powershell
python main.py eval --mode agent --output artifacts/AGENT_EVAL.md --json-output artifacts/AGENT_EVAL.json --trace-dir artifacts/agent_eval_runs --task python_bugfix --task python_add_tests --task python_import_fix --task config_default_fix --task multi_file_service_fix
python main.py trace-report --input artifacts/agent_eval_runs/agent/python_bugfix.jsonl --output artifacts/AGENT_TRACE_python_bugfix.html
```

Example memory/context ablation run:

```powershell
python main.py eval --mode agent --compare --output artifacts/AGENT_COMPARE_2_TASKS.md --json-output artifacts/AGENT_COMPARE_2_TASKS.json --trace-dir artifacts/agent_compare_runs --task python_bugfix --task multi_file_service_fix
```

Context retrieval ablation example:

```powershell
python main.py eval --mode agent --compare-retrieval --output artifacts/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md --json-output artifacts/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.json --trace-dir artifacts/agent_retrieval_context_task_runs --task context_pack_retrieval
python main.py eval --mode agent --retrieval on --output artifacts/AGENT_RETRIEVAL_ON.md --json-output artifacts/AGENT_RETRIEVAL_ON.json --trace-dir artifacts/agent_retrieval_on_runs --task python_bugfix
python main.py eval --mode agent --retrieval off --output artifacts/AGENT_RETRIEVAL_OFF.md --json-output artifacts/AGENT_RETRIEVAL_OFF.json --trace-dir artifacts/agent_retrieval_off_runs --task python_bugfix
```

Eval analysis example:

```powershell
python main.py analyze-eval --before artifacts/AGENT_EVAL_BEFORE.json --after reports/AGENT_EVAL_20_TASKS.json --output artifacts/AGENT_EVAL_ANALYSIS.md --trace-root .
python main.py eval-history --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
```

## Reports

- `REVIEW.md` is generated by `python main.py --allow-write --fresh-trace inspect`.
- `TRACE.html` is generated by `python main.py trace-report`.
- `EVAL.md` is generated by `python main.py eval`.
- `EVAL.json` can be generated with `python main.py eval --json-output EVAL.json`.
- `artifacts/AGENT_EVAL.md` and `artifacts/AGENT_EVAL.json` can be generated by the selected real-agent smoke command above.
- `artifacts/AGENT_TRACE_<task>.html` can be generated from any per-task agent trace with `trace-report`.
- `reports/DEMO_python_bugfix.md` and `reports/DEMO_python_bugfix_TRACE.html` are committed local demo artifacts.
- `reports/AGENT_EVAL.md` is a committed DeepSeek `deepseek-chat` report over 10 representative agent-mode tasks.
- `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md` is generated with `python main.py analyze-eval` to compare two JSON eval reports and classify failed-task patterns.
- `reports/EVAL_HISTORY.md` is generated with `python main.py eval-history` to track eval metrics and task outcome changes across runs.
- `reports/FAILURE_MODES.md` is generated with `python main.py eval-failures` to aggregate failed tasks by failure mode.
- `reports/AGENT_COMPARE_2_TASKS.md` is a committed memory/context ablation report over 2 representative agent-mode tasks.
- `reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md` is a committed retrieval-on/off ablation report for the `context_pack_retrieval` task.
- `reports/AGENT_TRACE_python_add_tests.html` and `reports/AGENT_TRACE_multi_file_service_fix.html` are committed sample trace viewer outputs from that real-agent run.
- `reports/AGENT_TRACE_retrieval_on_context_pack.html` and `reports/AGENT_TRACE_retrieval_off_context_pack.html` show the successful and disabled-retrieval paths for the retrieval ablation.
- `reports/README.md` explains the committed demo and real-agent evaluation artifacts.
- `trace.jsonl` records the current inspect/ask run.
- `eval_runs/*.jsonl` records per-task evaluation traces.

`REVIEW.md`, `TRACE.html`, `EVAL.json`, `COMPARE.json`, `trace.jsonl`, `eval_runs/`, and `artifacts/` are generated artifacts and are ignored by Git. `EVAL.md` is kept as the latest benchmark snapshot.

## MCP Server

The harness exposes the same permission-checked `ToolRegistry` through a minimal MCP stdio server:

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

Use `--allow-write` before `mcp-server` when the client should be allowed to edit existing files:

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl --allow-write mcp-server
```

Supported MCP methods: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `resources/templates/list`, `prompts/list`, and `prompts/get`. See `MCP.md` for message examples and boundaries.

The server also supports `resources/templates/list` for safe workspace text resources such as `harness://workspace/README.md`. Committed report resources include `harness://reports/eval-history` and `harness://reports/failure-modes`. Sensitive paths such as `.env`, `.git`, `artifacts`, and `eval_runs` are blocked. A committed protocol transcript is available in `reports/MCP_SMOKE.md`.

For client integration, copy `examples/mcp_config.example.json` and replace `/absolute/path/to/mini-coding-agent-harness` with your local checkout path.

## CI

`.github/workflows/ci.yml` runs the reproducibility checks used for the project snapshot:

- install dependencies from `requirements.txt`
- compile `main.py`, `harness/`, and `tests/`
- run `python -m pytest`
- run the full scripted benchmark into Markdown and JSON artifacts
- render one sample trace as `TRACE.html`
- run an MCP protocol smoke check and upload `MCP_SMOKE.md`

## Evaluation

The current benchmark has **31 tasks** and is fully deterministic. It includes harness checks, an injected-client agent-loop simulation, isolated code-maintenance fixtures, line-range file reading, query-ranked context retrieval, static trace HTML rendering, no-shell command execution, permission policy reporting, multi-file contract fixes, semantic retry planning, memory relevance ranking, and a package-structured `src/` fixture.

Task coverage:

- Python syntax check
- Pytest suite execution
- Injected-client agent-loop simulation
- Context compaction
- Line-range file reading
- Query-ranked context pack retrieval
- Static HTML trace report generation
- Error recovery
- Semantic retry planning
- Workflow memory listing
- Workflow memory relevance ranking
- Python bug fix
- Adding missing tests
- README update
- Import/name mismatch fix
- Configuration default fix
- JSON configuration update
- CLI argument validation fix
- Environment default fix
- CSV parsing edge-case fix
- Date formatting fix
- Pagination off-by-one fix
- Secret redaction fix
- No-shell allowlisted command execution and permission policy reporting
- Path normalization fix
- Dependency pin update
- Mutable default argument fix
- Multi-file service/repository contract fix
- Multi-file API handler/response contract fix
- Package-structured order/pricing fix under `src/`

The latest evaluation report tracks:

- Evaluation mode
- Memory and context-compaction settings
- Context retrieval setting
- Success rate
- Average tool calls
- Tool-call mix, including `context_pack` and `read_file`
- Average duration
- Input/output tokens
- Estimated model cost
- Optional machine-readable JSON output
- Failed tool calls
- Failure categories
- Per-task trace paths

Use `--compare` to run the same selected tasks across four configurations:

```text
memory-on_context-on
memory-off_context-on
memory-on_context-off
memory-off_context-off
```

Use `--retrieval on|off` to expose or hide `context_pack` during evaluation. This supports retrieval ablation without changing the rest of the harness.

Use `--compare-retrieval` to generate a two-row retrieval-on/retrieval-off comparison report under the same memory/context settings.
Comparison reports include average `context_pack` and `read_file` calls so retrieval changes can be inspected beyond pass rate.

Use `--task <task_id>` or `--category <category>` to run a targeted subset while tuning a fixture or agent behavior. Categories currently include `agent_loop`, `code_maintenance`, `code_quality`, `configuration`, `documentation`, `memory`, `multi_file`, `recovery`, `security`, `tests`, and `trace`.

Current honest status: this is a 31-task deterministic benchmark with query-ranked context retrieval, memory/context ablation reporting, an injected-client agent-loop smoke test, static trace HTML rendering, no-shell command execution, permission policy reporting, CI validation, and a DeepSeek/OpenAI-compatible client path for real API-backed `eval --mode agent`. A committed DeepSeek `deepseek-chat` report currently covers 10 representative agent-mode tasks with 10/10 passing, plus a 2-task memory/context ablation with all four configurations passing. A committed retrieval ablation on `context_pack_retrieval` shows retrieval-on passing with a real `context_pack` call and retrieval-off failing without the tool exposed. Full 31-task real API comparison data still needs larger runs and analysis before claiming broad autonomous benchmark performance.

## Git Baseline

This project is intended to run inside a Git worktree. `git_diff` uses:

```powershell
git diff -- .
```

After the initial baseline commit, future tool changes and generated report changes can be inspected through `git_diff`.

## Current Limitations

- The stable benchmark snapshot is scripted and includes an injected-client agent-loop smoke test; real API-backed model evaluation is supported and has a 10-task report, a 2-task memory/context ablation, and a focused retrieval-on/off ablation, but still needs full-suite comparison runs and broader retrieval tuning.
- Workflow memory can be ranked and injected into agent evaluation prompts, but ranking is still lexical rather than embedding-based.
- Context compaction is generated for max-turn stops, but automatic resume from that summary is not implemented yet.
- Retry/backoff handles transient model/API and non-write tool handler failures; retry_plan is injected back into the model loop after failed tools, but it does not execute repairs automatically.
- Shell/Git permission checks use an allowlist and `shell=False`, including through MCP, but they are not a real OS sandbox.
- MCP support is stdio-only and does not yet implement HTTP/SSE transport, OAuth, or resource subscriptions.
- Workflow memory is not full RAG: it ranks local Markdown memories lexically rather than using embeddings or a vector database.

## Next Steps

1. Run and tune real API-backed `eval --mode agent` against the 31 tasks, then compare it with scripted mode.
2. Add more realistic repository fixtures with nested packages, cross-file tests, and dependency/config interactions.
3. Add optional MCP HTTP/SSE transport and richer resource subscriptions.
4. Add optional OS-level sandboxing for shell execution.
5. Track whether injected retry plans improve `eval --mode agent` success rate and tool-call count.
