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

5. Open `reports/MCP_SMOKE.md`.
   Explain that the same harness is exposed through a minimal MCP stdio server. It lists tools, resources, and prompts, including report resources such as `harness://reports/eval-history`, `harness://reports/failure-modes`, and `harness://reports/eval-stability`.

6. Open `reports/EVAL_STABILITY_40_TASKS.md`.
   Explain that repeated same-model runs quantify variance without needing another provider API: the two complete expanded-suite runs passed 39/40 and 40/40, with 39 stable-pass tasks and one provider-affected fail-to-pass task.

7. Open `reports/AGENT_RETRIEVAL_ABLATION_8_TASKS_ANALYSIS.md`.
   Explain the measured retrieval tradeoff: both conditions passed 8/8, retrieval reduced tool exploration and direct reads, but the preloaded evidence increased input tokens and cost. The next engineering target is a smaller evidence budget, not an unsupported success-rate claim.

## Key Architecture Points

- `main.py` wires the CLI commands to the agent loop, evaluation runner, report analyzers, trace renderer, and MCP server.
- `harness/tools.py` owns the permission-checked tool registry for file, shell, Git, test, memory, and reporting tools.
- `harness/agent.py` preloads `retrieve_then_read` evidence before the first model turn when retrieval tools are enabled.
- `harness/evaluation.py` owns deterministic and model-backed benchmark execution.
- `harness/eval_analysis.py` turns JSON eval reports into comparison, history, failure-mode, and stability dashboards.
- `harness/mcp_server.py` exposes selected tools, read-only resources, and prompts through MCP.

## Claims To Make

- Built a coding-agent infrastructure project with retrieval preflight, tool calling, permission governance, planning, context compaction, memory, error recovery, traces, and evaluation.
- Expanded the deterministic benchmark from 36 to 40 tasks with nested-package, cross-file, plugin-registry, and dependency/config fixtures.
- Improved real-agent evaluation from an 18/20 baseline to 20/20, validated the earlier 36-task suite at 36/36, then ran the expanded suite twice at 39/40 and 40/40; traced the only first-run interruption to provider HTTP 503 and verified recovery in a complete hardened run.
- Added a stability-report CLI so repeated same-model runs can be compared when only one model API is available.
- Measured retrieval on eight ordinary maintenance tasks and identified a concrete exploration-versus-context-cost tradeoff.
- Exposed evaluation artifacts through MCP resources so external clients can inspect the same evidence.

## Claims To Avoid

- Do not claim this is a full autonomous software engineer.
- Do not claim broad benchmark superiority from this project-specific 40-task suite.
- Do not claim embedding-based retrieval; current retrieval and memory ranking are lexical.
- Do not claim OS-level sandboxing; the project implements harness-level permission controls.
