# Portfolio Walkthrough

Use this script to present the project in a 2-3 minute interview walkthrough.

## Opening

This project is a lightweight coding-agent harness for repository maintenance. It is not a chatbot and not a thin LLM wrapper. The model decides the next action, while the harness provides tools, permission checks, task planning, context compaction, memory, error recovery, execution traces, and evaluation reports.

## Demo Route

Run these commands when demonstrating the project locally:

```powershell
python main.py demo --task python_bugfix
python main.py eval --mode scripted
python main.py eval-history --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --output reports/EVAL_HISTORY.md
python main.py eval-failures --run before-prompt-contract=reports/AGENT_EVAL_20_TASKS_BEFORE.json --run after-prompt-contract=reports/AGENT_EVAL_20_TASKS.json --output reports/FAILURE_MODES.md --trace-root .
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

## Talk Track

1. Start with `reports/DEMO_python_bugfix.md`.
   Explain that the harness turns a maintenance task into a todo plan, tool calls, file edits, tests, and a final diff. The important point is that every action is recorded as evidence, not hidden inside a model response.

2. Open `reports/AGENT_EVAL_20_TASKS.md`.
   Explain that the project has a real model-backed evaluation path, not only scripted fixtures. The committed 20-task DeepSeek `deepseek-chat` run reached 20/20, and each task has tool-call counts, duration, token cost, and trace paths.

3. Open `reports/EVAL_HISTORY.md`.
   Explain the engineering loop: an earlier 20-task run passed 18/20, then trace review drove a prompt-contract improvement, and the rerun reached 20/20. Point to the success-rate change, tool-call mix, and task outcome changes.

4. Open `reports/FAILURE_MODES.md`.
   Explain that the project does not stop at pass rate. It classifies failed tasks into patterns such as `max_turns`, `no_file_change`, `over_exploration`, `verification_failed`, and `tool_failures`, so the next harness change can be targeted.

5. Open `reports/MCP_SMOKE.md`.
   Explain that the same harness is exposed through a minimal MCP stdio server. It lists tools, resources, and prompts, including report resources such as `harness://reports/eval-history` and `harness://reports/failure-modes`.

## Key Architecture Points

- `main.py` wires the CLI commands to the agent loop, evaluation runner, report analyzers, trace renderer, and MCP server.
- `harness/tools.py` owns the permission-checked tool registry for file, shell, Git, test, memory, and reporting tools.
- `harness/evaluation.py` owns deterministic and model-backed benchmark execution.
- `harness/eval_analysis.py` turns JSON eval reports into comparison, history, and failure-mode dashboards.
- `harness/mcp_server.py` exposes selected tools, read-only resources, and prompts through MCP.

## Claims To Make

- Built a coding-agent infrastructure project with tool calling, permission governance, planning, context compaction, memory, error recovery, traces, and evaluation.
- Added a 34-task deterministic benchmark and a 20-task real-agent evaluation artifact.
- Improved a real-agent run from 18/20 to 20/20 using trace-backed failure analysis.
- Exposed evaluation artifacts through MCP resources so external clients can inspect the same evidence.

## Claims To Avoid

- Do not claim this is a full autonomous software engineer.
- Do not claim broad benchmark superiority from the 20-task run.
- Do not claim embedding-based retrieval; current retrieval and memory ranking are lexical.
- Do not claim OS-level sandboxing; the project implements harness-level permission controls.
