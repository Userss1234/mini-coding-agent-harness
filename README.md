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

- **Scripted benchmark:** 40 deterministic repository-maintenance tasks, 40/40 passing in the committed snapshot, including nested-package, cross-file, plugin-registry, and dependency/config fixtures.
- **Real-agent eval:** DeepSeek `deepseek-chat` passed 40/40 in the second complete expanded-suite run after transient request retries were increased from 2 to 4. The first run remains 39/40 because of one provider HTTP 503 before verification; 39/40 -> 40/40 stability evidence is committed without rewriting the original result.
- **Recovery fix:** tightened the `error_recovery` agent prompt after the second run; targeted and full-suite post-fix DeepSeek validations now pass with the expected `edit_match_failed` recovery path.
- **Ablations:** Memory/context comparison over 2 tasks plus original and budget-optimized paired 8-task retrieval studies. All four retrieval rows passed 8/8. The optimized rerun retained 6.82% fewer tool calls and 37.04% fewer direct reads while narrowing the input-token premium from 34.38% to 13.48% and the cost premium from 28.65% to 11.53%.
- **CI:** `.github/workflows/ci.yml` runs tests, syntax checks, scripted benchmark, trace rendering, and MCP smoke validation.
- **Reports:** Start with [`reports/AGENT_EVAL_40_TASKS_RUN2.md`](reports/AGENT_EVAL_40_TASKS_RUN2.md), [`reports/EVAL_STABILITY_40_TASKS.md`](reports/EVAL_STABILITY_40_TASKS.md), [`reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md`](reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md), [`reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`](reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md), and [`reports/EVAL_STABILITY.md`](reports/EVAL_STABILITY.md).

## Portfolio Walkthrough

Use this route when demonstrating the project in an interview:

```powershell
python main.py demo --task python_bugfix
python main.py eval --mode scripted
python main.py eval-history --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
python main.py eval-stability --run full-36-v1=reports/AGENT_EVAL_36_TASKS.json --run full-36-v2=reports/AGENT_EVAL_36_TASKS_RUN2.json --run full-36-v3-postfix=reports/AGENT_EVAL_36_TASKS_RUN3.json --output reports/EVAL_STABILITY.md
python main.py eval-stability --run full-40-v1=reports/AGENT_EVAL_40_TASKS.json --run full-40-v2-hardened=reports/AGENT_EVAL_40_TASKS_RUN2.json --output reports/EVAL_STABILITY_40_TASKS.md
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

Show these committed artifacts while explaining the system:

- [`reports/PORTFOLIO_WALKTHROUGH.md`](reports/PORTFOLIO_WALKTHROUGH.md): 2-3 minute interview talk track.
- [`reports/RESUME_BULLETS.md`](reports/RESUME_BULLETS.md): evidence-backed resume bullet options.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): architecture diagrams and module boundaries.
- [`docs/INTERVIEW_QA.md`](docs/INTERVIEW_QA.md): source-backed interview questions and answers.
- [`reports/DEMO_python_bugfix.md`](reports/DEMO_python_bugfix.md): tool loop evidence for a deterministic local bugfix.
- [`reports/AGENT_EVAL_40_TASKS_RUN2.md`](reports/AGENT_EVAL_40_TASKS_RUN2.md): second complete expanded-suite run, 40/40 with hardened transient request retries.
- [`reports/EVAL_STABILITY_40_TASKS.md`](reports/EVAL_STABILITY_40_TASKS.md): two-run 40-task stability analysis, including the original provider interruption and the hardened full pass.
- [`reports/AGENT_EVAL_40_TASKS.md`](reports/AGENT_EVAL_40_TASKS.md): preserved first expanded full-suite run, 39/40 with one terminal provider HTTP 503 before verification.
- [`reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`](reports/AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md): retry hardening analysis and the failed task's targeted 1/1 recovery evidence.
- [`reports/AGENT_EVAL_36_TASKS.md`](reports/AGENT_EVAL_36_TASKS.md): full 36-task model-backed coding-agent evaluation result.
- [`reports/AGENT_EVAL_36_TASKS_RUN2.md`](reports/AGENT_EVAL_36_TASKS_RUN2.md): second same-model 36-task run that exposed `error_recovery` variance.
- [`reports/AGENT_EVAL_36_TASKS_RUN3.md`](reports/AGENT_EVAL_36_TASKS_RUN3.md): post-fix same-model 36-task run showing the suite back at 36/36.
- [`reports/ERROR_RECOVERY_AGENT_FIX.md`](reports/ERROR_RECOVERY_AGENT_FIX.md): targeted model-backed validation for the recovered `error_recovery` task.
- [`reports/AGENT_EVAL_20_TASKS.md`](reports/AGENT_EVAL_20_TASKS.md): earlier 20-task model-backed coding-agent evaluation result.
- [`reports/EVAL_HISTORY.md`](reports/EVAL_HISTORY.md): trend view showing 18/20 to 20/20 to 36/36.
- [`reports/FAILURE_MODES.md`](reports/FAILURE_MODES.md): failure-mode dashboard showing resolved agent failure patterns.
- [`reports/EVAL_STABILITY.md`](reports/EVAL_STABILITY.md): repeated-run stability report comparing three same-model 36-task runs.
- [`reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md`](reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md): before/after evidence-budget analysis with an offline replay and a new paired 8-task real-agent run.
- [`reports/MCP_SMOKE.md`](reports/MCP_SMOKE.md): MCP protocol transcript exposing tools, resources, and prompts.

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
- Budgeted agent-loop retrieval preflight that merges overlapping reads and caps injected evidence before the first model turn
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

When retrieval tools are enabled, `harness.agent.run_agent()` performs a retrieval preflight before the first model call. It calls `retrieve_then_read` with the task prompt, merges overlapping or adjacent line ranges, removes exact duplicate reads, and injects a bounded evidence pack into the initial model message. The JSONL trace records matched chunks, planned and merged reads, raw and injected evidence characters, omissions, truncation, and the active budget.

## Tools

| Tool | Purpose |
|---|---|
| `todo_write` | Create/update a task plan and record todo quality metadata. |
| `list_python_files` | List Python files while ignoring caches and evaluation workspaces. |
| `read_file` | Read workspace files with optional line ranges, line/character limits, and read-cache metadata. |
| `index_workspace` | Build a safe local retrieval index summary for workspace text chunks. |
| `rag_search` | Search code and docs using local chunked lexical retrieval with path and line metadata. |
| `rag_explain` | Convert RAG matches into a concrete `read_file` path and line-range plan. |
| `retrieve_then_read` | Run RAG, build a read plan, and return the loaded line-range evidence pack. |
| `context_pack` | Retrieve task-relevant workspace snippets using the same local retrieval layer. |
| `write_file` | Write files and record diff metadata. |
| `edit_file` | Replace an exact text block that appears exactly once. |
| `delete_file` | Delete one file only with explicit confirmation; directories are refused. |
| `grep` | Search files by substring. |
| `permission_policy` | Report write, shell, Git, and sandbox permission boundaries. |
| `audit_permissions` | Summarize trace permission decisions, blocked calls, risk classes, and failed allowed calls. |
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
python main.py eval-history --run baseline=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run baseline=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
python main.py eval-stability --run full-36-v1=reports/AGENT_EVAL_36_TASKS.json --run full-36-v2=reports/AGENT_EVAL_36_TASKS_RUN2.json --run full-36-v3-postfix=reports/AGENT_EVAL_36_TASKS_RUN3.json --output reports/EVAL_STABILITY.md
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
AGENT_RETRIEVAL_PREFLIGHT_LIMIT=2
AGENT_RETRIEVAL_PREFLIGHT_CHUNK_LINES=48
AGENT_RETRIEVAL_PREFLIGHT_READ_WINDOW=8
AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS_PER_READ=1400
AGENT_RETRIEVAL_PREFLIGHT_MAX_CHARS=2400

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
python main.py eval-history --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
python main.py eval-stability --run full-36-v1=reports/AGENT_EVAL_36_TASKS.json --run full-36-v2=reports/AGENT_EVAL_36_TASKS_RUN2.json --run full-36-v3-postfix=reports/AGENT_EVAL_36_TASKS_RUN3.json --output reports/EVAL_STABILITY.md
```

## Reports

- `REVIEW.md` is generated by `python main.py --allow-write --fresh-trace inspect`.
- `TRACE.html` is generated by `python main.py trace-report`.
- `EVAL.md` is generated by `python main.py eval`.
- `EVAL.json` can be generated with `python main.py eval --json-output EVAL.json`.
- `artifacts/AGENT_EVAL.md` and `artifacts/AGENT_EVAL.json` can be generated by the selected real-agent smoke command above.
- `artifacts/AGENT_TRACE_<task>.html` can be generated from any per-task agent trace with `trace-report`.
- `reports/DEMO_python_bugfix.md` and `reports/DEMO_python_bugfix_TRACE.html` are committed local demo artifacts.
- `reports/PORTFOLIO_WALKTHROUGH.md` is a short interview talk track that ties the demo, eval, failure analysis, and MCP reports together.
- `reports/AGENT_EVAL.md` is a committed DeepSeek `deepseek-chat` report over 10 representative agent-mode tasks.
- `reports/AGENT_EVAL_PROMPT_IMPROVEMENT.md` is generated with `python main.py analyze-eval` to compare two JSON eval reports and classify failed-task patterns.
- `reports/EVAL_HISTORY.md` is generated with `python main.py eval-history` to track eval metrics and task outcome changes across runs.
- `reports/FAILURE_MODES.md` is generated with `python main.py eval-failures` to aggregate failed tasks by failure mode.
- `reports/EVAL_STABILITY.md` is generated with `python main.py eval-stability` to measure repeated-run stability for same-suite agent reports.
- `reports/AGENT_COMPARE_2_TASKS.md` is a committed memory/context ablation report over 2 representative agent-mode tasks.
- `reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md` is a committed retrieval-on/off ablation report for the `context_pack_retrieval` task.
- `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS.md` and `reports/AGENT_RETRIEVAL_ABLATION_8_TASKS_ANALYSIS.md` compare retrieval preflight on eight ordinary maintenance tasks and document the measured exploration-versus-cost tradeoff.
- `reports/AGENT_RETRIEVAL_COMPARE_8_TASKS_OPTIMIZED.md` and `reports/RETRIEVAL_PREFLIGHT_BUDGET_OPTIMIZATION.md` validate the bounded preflight on the same eight tasks and compare it with the original result.
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

The server also supports `resources/templates/list` for safe workspace text resources such as `harness://workspace/README.md`. Committed report resources include `harness://reports/eval-history`, `harness://reports/failure-modes`, and `harness://reports/eval-stability`. Sensitive paths such as `.env`, `.git`, `artifacts`, and `eval_runs` are blocked. A committed protocol transcript is available in `reports/MCP_SMOKE.md`.

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

The current benchmark has **40 tasks** and is fully deterministic. It includes harness checks, an injected-client agent-loop simulation with retrieval preflight, isolated code-maintenance fixtures, line-range file reading, query-ranked context retrieval, local RAG symbol retrieval, RAG read-plan generation, retrieve-then-read evidence loading, sensitive-path retrieval filtering, MCP RAG search smoke validation, interactive self-contained trace HTML rendering, no-shell command execution, permission policy reporting, multi-file contract fixes, semantic retry planning, memory relevance ranking, nested `src/` packages, plugin discovery, and dependency/config interactions.

Task coverage:

- Python syntax check
- Pytest suite execution
- Injected-client agent-loop simulation with retrieval preflight
- Context compaction
- Line-range file reading
- Query-ranked context pack retrieval
- Local RAG symbol retrieval across distractor files
- RAG read-plan generation with concrete `read_file` arguments
- Retrieve-then-read evidence pack loading
- Sensitive-path filtering for RAG indexing/search
- MCP `rag_search` smoke validation
- Self-contained interactive HTML trace reports with event/tool/status/search filters, duration, model-turn, token, permission, and blocked-call summaries
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
- Nested package export and API payload contract fix
- Environment-over-file configuration precedence across modules
- Pyproject dependency/runtime compatibility alignment
- Nested plugin registry discovery and duplicate handling

The latest evaluation report tracks:

- Evaluation mode
- Memory and context-compaction settings
- Context retrieval setting
- Success rate
- Average tool calls
- Tool-call mix, including `retrieve_then_read`, `context_pack`, and `read_file`
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

Use `--retrieval on|off` to expose or hide retrieval tools such as `context_pack`, `rag_search`, `rag_explain`, `retrieve_then_read`, and `index_workspace` during evaluation. In agent mode this also controls whether the loop can preload `retrieve_then_read` evidence before the first model turn.

Use `--compare-retrieval` to generate a two-row retrieval-on/retrieval-off comparison report under the same memory/context settings.
Comparison reports include average `retrieve_then_read`, `context_pack`, and `read_file` calls plus average raw/injected preflight evidence characters, so retrieval changes can be inspected beyond pass rate.

Use `--task <task_id>` or `--category <category>` to run a targeted subset while tuning a fixture or agent behavior. Categories currently include `agent_loop`, `code_maintenance`, `code_quality`, `configuration`, `documentation`, `memory`, `multi_file`, `recovery`, `retrieval`, `security`, `tests`, and `trace`.

Current honest status: this is a 40-task deterministic benchmark with query-ranked local code retrieval, memory/context ablation reporting, an injected-client agent-loop smoke test, interactive self-contained trace HTML rendering, no-shell command execution, permission policy reporting, CI validation, and a DeepSeek/OpenAI-compatible client path for real API-backed `eval --mode agent`. The retrieval layer chunks safe workspace text files, skips sensitive/generated paths and workflow memories under `skills/`, ranks chunks with local lexical scoring rather than embeddings, turns top matches into concrete `read_file` plans, merges overlapping ranges, and injects a character-capped evidence pack. The first expanded full-suite DeepSeek run passed 39/40 because `shell_no_shell_execution` stopped on a provider HTTP 503 before verification. After increasing transient request retries from 2 to 4, the task passed a targeted rerun and the second complete 40-task run passed 40/40 with no verifier or terminal provider failures. The second run used 1,590,593 input tokens and 44,750 output tokens, averaged 13.15 tool calls and 103.91 seconds per task, and cost an estimated $5.443029. The committed stability report records 39 stable-pass tasks and one provider-affected `fail -> pass` task. In the original paired 8-task retrieval ablation, both conditions passed 8/8 while retrieval reduced exploration but added 34.38% input tokens and 28.65% estimated cost. After evidence-budget optimization, the repeated paired run again passed 8/8 in both conditions, retained fewer tool calls and direct reads, and narrowed those premiums to 13.48% and 11.53%. Retrieval remains more expensive than retrieval-off on this sample, so no success-rate or cost-superiority claim is made.

## Git Baseline

This project is intended to run inside a Git worktree. `git_diff` uses:

```powershell
git diff -- .
```

After the initial baseline commit, future tool changes and generated report changes can be inspected through `git_diff`.

## Current Limitations

- The two same-model 40-task full runs are 39/40 and 40/40. Thirty-nine tasks are stable passes; `shell_no_shell_execution` is still classified as unstable because its first-run provider interruption became a second-run pass. More repeats or another provider/model would be needed for a stronger variance estimate.
- Workspace RAG is local chunked lexical retrieval with path/line metadata; it is not embedding-based and does not use a vector database.
- Workflow memory can be ranked and injected into agent evaluation prompts, but ranking is still lexical rather than embedding-based.
- Context compaction is generated for max-turn stops, but automatic resume from that summary is not implemented yet.
- Retry/backoff handles transient model/API failures with up to 4 retries and handles non-write tool handler failures; retry_plan is injected back into the model loop after failed tools, but it does not execute repairs automatically.
- Shell/Git permission checks use an allowlist and `shell=False`, including through MCP, but they are not a real OS sandbox.
- MCP support is stdio-only and does not yet implement HTTP/SSE transport, OAuth, or resource subscriptions.
- Workflow memory is not full RAG: it ranks local Markdown memories lexically rather than using embeddings or a vector database.

## Next Steps

1. Add conditional retrieval preflight and tool-schema exposure, then rerun the same paired 8-task ablation.
2. Expand memory/context ablation to a representative multi-file task set.
3. Add optional MCP HTTP/SSE transport and richer resource subscriptions.
4. Add optional OS-level sandboxing for shell execution.
5. Add a third hardened 40-task run or a second provider/model when another API becomes available.
