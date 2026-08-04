# Portfolio Walkthrough

Use this script to present the project in a 2-3 minute interview walkthrough.

## Opening

This project is a lightweight coding-agent harness for repository maintenance. It is not a chatbot and not a thin LLM wrapper. The model decides the next action, while the harness provides retrieval preflight, tools, permission checks, task planning, context compaction, memory, error recovery, execution traces, and evaluation reports.

## Demo Route

Run these commands when demonstrating the project locally:

```powershell
python main.py demo --task python_bugfix
python main.py eval --mode scripted
python main.py eval-history --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --run full-36-task=reports/AGENT_EVAL_36_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
python main.py eval-stability --run full-36-v1=reports/AGENT_EVAL_36_TASKS.json --run full-36-v2=reports/AGENT_EVAL_36_TASKS_RUN2.json --run full-36-v3-postfix=reports/AGENT_EVAL_36_TASKS_RUN3.json --output reports/EVAL_STABILITY.md
python main.py eval-stability --run full-40-v1=reports/AGENT_EVAL_40_TASKS.json --run full-40-v2-hardened=reports/AGENT_EVAL_40_TASKS_RUN2.json --output reports/EVAL_STABILITY_40_TASKS.md
python main.py retrieval-stability --run selected-first=reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS.json --run off-first=reports/AGENT_RETRIEVAL_AUTO_COMPARE_8_TASKS_OFF_FIRST.json --output reports/RETRIEVAL_GATING_STABILITY.md
python main.py retrieval-benchmark --backend hybrid
python main.py eval --mode agent --retrieval on --compare-retrieval-backends --task rag_symbol_retrieval
docker build --file docker/sandbox/Dockerfile --tag mini-coding-agent-harness-sandbox:latest .
python main.py docker-smoke --output artifacts/DOCKER_SANDBOX_SMOKE.md
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

## Talk Track

1. Start with `reports/DEMO_python_bugfix.md`.
   Explain that the harness turns a maintenance task into a todo plan, tool calls, file edits, tests, and a final diff. The important point is that every action is recorded as evidence, not hidden inside a model response.

2. Open `reports/AGENT_EVAL_40_TASKS_RUN2.md` and `reports/EVAL_STABILITY_40_TASKS.md`.
   Explain that the first expanded full-suite run passed 39/40 because of a provider HTTP 503 before verification. Show how the request retry budget was hardened, the original result was preserved, and the second complete run passed 40/40. The stability report records 39 stable-pass tasks and the provider-affected task as fail-to-pass.

3. Open `reports/EVAL_HISTORY.md`.
   Explain the engineering loop: an earlier 20-task run passed 18/20, trace review drove a prompt-contract improvement to 20/20, and the final full-suite run reached 36/36. Point to the success-rate change, tool-call mix, and task outcome changes.

4. Open `reports/FAILURE_MODES.md`.
   Explain that the project does not stop at pass rate. It classifies failed tasks into patterns such as `max_turns`, `no_file_change`, `over_exploration`, `verification_failed`, and `tool_failures`, so the next harness change can be targeted.

5. Open `reports/MCP_SMOKE.md` and `reports/MCP_HTTP_SMOKE.md`.
   Explain that stdio and Streamable HTTP reuse the same MCP protocol object and permission-checked registry. The HTTP evidence covers Bearer authentication, malicious-Origin rejection, secure session issuance/deletion, JSON responses, explicit GET 405 behavior, and 25/25 tool-name parity with stdio.

6. Open `reports/EVAL_STABILITY_40_TASKS.md`.
   Explain that repeated same-model runs quantify variance without needing another provider API: the two complete expanded-suite runs passed 39/40 and 40/40, with 39 stable-pass tasks and one provider-affected fail-to-pass task.

7. Open `reports/RETRIEVAL_GATING_STABILITY.md`.
   Explain the measured retrieval iteration: evidence budgeting came first, then an explainable gate suppressed preflight and five schemas for simple tasks. Two prompt-aligned pairs were run in opposite orders; all four rows passed 8/8, auto activated 4/8 tasks in both pairs, and tool calls/direct reads stayed lower. Input-token and cost direction changed, so the project reports stable exploration reduction but does not claim stable cost superiority. These historical JSON files contain aggregate rows only; current comparison JSON preserves `task_results` and `paired_tasks`, and the same CLI automatically adds task-level paired variance without rewriting old evidence.

8. Open `reports/DOCKER_SANDBOX_SMOKE.md`.
   Explain that shell, pytest, and syntax checks share one executor interface. The Docker backend fails closed, does not forward provider keys, and applies a non-root UID, disabled network, dropped capabilities, a read-only root filesystem, and resource limits. The committed CI report records `uid=10001 workspace=ok network=blocked`; Docker is still not presented as a VM or absolute security boundary.

9. Open `reports/RETRIEVAL_QUALITY_BASELINE.md` and `reports/RETRIEVAL_QUALITY_HYBRID.md`.
   Explain that both backends use the same safe chunks and 10-query judgments. The dependency-free lexical baseline reaches 0.8000 MRR and 0.80 Recall@3/5; optional local MiniLM fusion reaches 0.9000 MRR and 1.00 Recall@3/5, with both retained semantic cases at rank 2. Document embeddings are cached incrementally outside the repository. Keep the ranking claim scoped to this project fixture, then contrast it with the separate agent-level result.

10. Open `reports/RETRIEVAL_BACKEND_8_TASKS_ANALYSIS.md`.
   Explain that ranking gains were tested separately from agent workflow gains. The lexical-first 8-task pair did not show hybrid efficiency gains and exposed a verifier hardcoded to lexical metadata even though hybrid ranked the target first. The defect was fixed, a targeted pair passed on both backends, and the original report was preserved rather than rewritten.

## Key Architecture Points

- `main.py` wires the CLI commands to the agent loop, evaluation runner, report analyzers, trace renderer, and MCP server.
- `harness/tools.py` owns the permission-checked tool registry for file, shell, Git, test, memory, and reporting tools.
- `harness/agent.py` resolves `on/auto/off`, records the gate decision, filters model-facing schemas, and preloads bounded evidence only when active.
- `harness/evaluation.py` owns deterministic and model-backed benchmark execution, controllable retrieval comparison order, and per-configuration task-result retention.
- `harness/eval_analysis.py` turns JSON eval reports into comparison, history, failure-mode, repeated-run, aggregate retrieval, and task-level paired-variance evidence.
- `harness/execution.py` implements the host/Docker executor boundary, resource policy, environment filtering, and timeout cleanup.
- `harness/mcp_server.py` owns the shared MCP methods and stdio transport; `harness/mcp_http.py` adds the localhost-safe HTTP boundary without duplicating tool policy.

## Claims To Make

- Built a coding-agent infrastructure project with retrieval preflight, tool calling, permission governance, planning, context compaction, memory, error recovery, traces, and evaluation.
- Expanded the deterministic benchmark from 36 to 40 tasks with nested-package, cross-file, plugin-registry, and dependency/config fixtures.
- Improved real-agent evaluation from an 18/20 baseline to 20/20, validated the earlier 36-task suite at 36/36, then ran the expanded suite twice at 39/40 and 40/40; traced the only first-run interruption to provider HTTP 503 and verified recovery in a complete hardened run.
- Added stability-report CLIs so repeated same-model runs and order-varied retrieval pairs can be compared when only one model API is available.
- Preserved full per-task comparison results and compact selected/off task pairs so new repeated retrieval runs can identify task-level outcome and exploration variance.
- Measured retrieval on eight maintenance tasks across two opposite-order pairs; all four rows passed 8/8 while auto reduced tool calls by 7.41%-17.73% and direct reads by 14.29%-15.38%.
- Exposed evaluation artifacts through MCP resources so external clients can inspect the same evidence.
- Added a `2025-11-25`-compatible Streamable HTTP transport with exact Origin validation, static Bearer authentication, expiring sessions, explicit termination, and stdio parity evidence.
- Added an optional Docker command backend and CI runtime proof for non-root execution, workspace visibility, and blocked outbound networking while preserving the tool permission layer.
- Added optional local MiniLM hybrid retrieval with lexical/semantic fusion and incremental document-embedding caching; improved the same 10-query judged fixture from 0.8000 to 0.9000 MRR and recovered both retained semantic cases at rank 2.
- Added order-controlled lexical/hybrid agent comparison with task-level pairs and cache metrics, then used the first focused run to find and fix a backend-biased verifier without claiming unsupported agent-efficiency gains.

## Claims To Avoid

- Do not claim this is a full autonomous software engineer.
- Do not claim broad benchmark superiority from this project-specific 40-task suite.
- Do not describe all retrieval as embedding-based: lexical is the default, hybrid is optional, and memory ranking remains lexical.
- Do not claim general or agent-level hybrid superiority from the 10-query ranking fixture.
- Do not claim stable retrieval token or cost savings; those metrics changed direction across the two paired runs.
- Do not describe Docker as a VM or absolute security sandbox. Host mode remains policy-only, and the Docker workspace mount is writable by design.
