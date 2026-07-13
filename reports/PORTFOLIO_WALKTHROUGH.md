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
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

## Talk Track

1. Start with `reports/DEMO_python_bugfix.md`.
   Explain that the harness turns a maintenance task into a todo plan, tool calls, file edits, tests, and a final diff. The important point is that every action is recorded as evidence, not hidden inside a model response.

2. Open `reports/AGENT_EVAL_36_TASKS.md`.
   Explain that the project has a real model-backed evaluation path, not only scripted fixtures. The committed full-suite DeepSeek `deepseek-chat` run reached 36/36, and each task has tool-call counts, duration, token cost, and trace paths.

3. Open `reports/EVAL_HISTORY.md`.
   Explain the engineering loop: an earlier 20-task run passed 18/20, trace review drove a prompt-contract improvement to 20/20, and the final full-suite run reached 36/36. Point to the success-rate change, tool-call mix, and task outcome changes.

4. Open `reports/FAILURE_MODES.md`.
   Explain that the project does not stop at pass rate. It classifies failed tasks into patterns such as `max_turns`, `no_file_change`, `over_exploration`, `verification_failed`, and `tool_failures`, so the next harness change can be targeted.

5. Open `reports/MCP_SMOKE.md`.
   Explain that the same harness is exposed through a minimal MCP stdio server. It lists tools, resources, and prompts, including report resources such as `harness://reports/eval-history`, `harness://reports/failure-modes`, and `harness://reports/eval-stability`.

6. Open `reports/EVAL_STABILITY.md`.
   Explain that the repeated same-model runs quantify variance without needing another provider API: run 1 passed 36/36, run 2 passed 35/36 with `error_recovery` failing, and the post-fix run 3 returned to 36/36.

## Key Architecture Points

- `main.py` wires the CLI commands to the agent loop, evaluation runner, report analyzers, trace renderer, and MCP server.
- `harness/tools.py` owns the permission-checked tool registry for file, shell, Git, test, memory, and reporting tools.
- `harness/agent.py` preloads `retrieve_then_read` evidence before the first model turn when retrieval tools are enabled.
- `harness/evaluation.py` owns deterministic and model-backed benchmark execution.
- `harness/eval_analysis.py` turns JSON eval reports into comparison, history, failure-mode, and stability dashboards.
- `harness/mcp_server.py` exposes selected tools, read-only resources, and prompts through MCP.

## Claims To Make

- Built a coding-agent infrastructure project with retrieval preflight, tool calling, permission governance, planning, context compaction, memory, error recovery, traces, and evaluation.
- Added a 36-task deterministic benchmark and a full 36-task real-agent evaluation artifact.
- Improved real-agent evaluation from an 18/20 baseline to 20/20, then validated the expanded 36-task run at 36/36 using trace-backed failure analysis.
- Added a stability-report CLI so repeated same-model runs can be compared when only one model API is available.
- Exposed evaluation artifacts through MCP resources so external clients can inspect the same evidence.

## Claims To Avoid

- Do not claim this is a full autonomous software engineer.
- Do not claim broad benchmark superiority from a single 36-task run.
- Do not claim embedding-based retrieval; current retrieval and memory ranking are lexical.
- Do not claim OS-level sandboxing; the project implements harness-level permission controls.
