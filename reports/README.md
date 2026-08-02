# Reports

This directory contains committed portfolio artifacts that can be reviewed without rerunning the model.

- `PORTFOLIO_WALKTHROUGH.md`: short interview talk track tying the demo, eval, failure-analysis, and MCP artifacts together.
- `RESUME_BULLETS.md`: evidence-backed resume bullet options with claim-to-file mapping.

## Local Demo

- `DEMO_python_bugfix.md`: deterministic local demo report for `python main.py demo --task python_bugfix`.
- `DEMO_python_bugfix_TRACE.html`: self-contained interactive trace viewer output for the local demo.

## MCP

- `MCP_SMOKE.md`: in-process MCP protocol smoke report covering initialize, tools, resources, resource templates, prompts, and a permission-policy tool call.

## Execution Isolation

- `DOCKER_SANDBOX_SMOKE.md`: GitHub Actions runtime report proving non-root execution, workspace visibility, and blocked outbound networking for the configured Docker backend.

## Retrieval Quality

- `RETRIEVAL_QUALITY_BASELINE.md`: relevance-judged 10-query lexical baseline with path-level MRR, Recall@K, per-case rankings, and CI quality gates.
- `RETRIEVAL_QUALITY_BASELINE.json`: machine-readable copy used for future lexical-versus-hybrid comparisons.

## Real Agent Eval

- `AGENT_EVAL_40_TASKS.md`: expanded full 40-task DeepSeek `deepseek-chat` run, 39/40 because one task hit a terminal provider HTTP 503 before verification.
- `AGENT_EVAL_40_TASKS.json`: machine-readable JSON copy of the expanded full-suite run.
- `AGENT_EVAL_40_TASKS_RUN2.md`: second complete 40-task DeepSeek `deepseek-chat` run, 40/40 with hardened transient request retries.
- `AGENT_EVAL_40_TASKS_RUN2.json`: machine-readable JSON copy of the second complete expanded-suite run.
- `AGENT_EVAL_40_TASKS_PROVIDER_RETRY.md`: targeted 1/1 rerun of the provider-interrupted task after retry hardening.
- `AGENT_EVAL_40_TASKS_PROVIDER_RETRY.json`: machine-readable JSON copy of the targeted rerun.
- `AGENT_EVAL_40_TASKS_PROVIDER_RECOVERY.md`: trace-backed analysis separating the original full-run result from the targeted recovery.
- `AGENT_EVAL.md`: earlier DeepSeek `deepseek-chat` report over 10 representative agent-mode tasks.
- `AGENT_EVAL_10_TASKS.md`: named copy of the 10-task real-agent evaluation report.
- `AGENT_EVAL_20_TASKS.md`: expanded 20-task DeepSeek `deepseek-chat` agent-mode evaluation report.
- `AGENT_EVAL_36_TASKS.md`: full 36-task DeepSeek `deepseek-chat` agent-mode evaluation report, 36/36 passing.
- `AGENT_EVAL_36_TASKS.json`: machine-readable JSON copy of the full 36-task agent-mode evaluation report.
- `AGENT_EVAL_36_TASKS_RUN2.md`: second same-model full 36-task DeepSeek `deepseek-chat` agent-mode evaluation report, 35/36 passing.
- `AGENT_EVAL_36_TASKS_RUN2.json`: machine-readable JSON copy of the second same-model full 36-task agent-mode evaluation report.
- `AGENT_EVAL_36_TASKS_RUN3.md`: post-fix same-model full 36-task DeepSeek `deepseek-chat` agent-mode evaluation report, 36/36 passing.
- `AGENT_EVAL_36_TASKS_RUN3.json`: machine-readable JSON copy of the post-fix same-model full 36-task agent-mode evaluation report.
- `ERROR_RECOVERY_AGENT_FIX.md`: targeted DeepSeek `deepseek-chat` agent-mode validation for the prompt fix that keeps `error_recovery` on the intended edit-failure recovery path.
- `ERROR_RECOVERY_AGENT_FIX.json`: machine-readable JSON copy of the targeted `error_recovery` fix validation.
- `AGENT_EVAL_20_TASKS_BEFORE.json`: machine-readable JSON copy of the 18/20 baseline run before the prompt-contract improvement.
- `AGENT_EVAL_20_TASKS.json`: machine-readable JSON copy of the expanded 20-task agent-mode evaluation report.
- `AGENT_EVAL_PROMPT_IMPROVEMENT.md`: `analyze-eval` generated comparison of the 18/20 run and the prompt-contract improvement that reached 20/20.
- `EVAL_HISTORY.md`: `eval-history` generated trend report comparing eval metrics and task outcomes across runs.
- `FAILURE_MODES.md`: `eval-failures` generated dashboard aggregating failed tasks by failure mode.
- `EVAL_STABILITY.md`: `eval-stability` generated repeated-run stability analysis across three same-model 36-task reports, including the post-fix rerun.
- `EVAL_STABILITY_40_TASKS.md`: repeated-run stability analysis across the two complete 40-task reports, showing 39 stable passes and one provider-affected fail-to-pass task.
- `AGENT_COMPARE_2_TASKS.md`: memory/context ablation report over 2 representative agent-mode tasks.
- `AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md`: retrieval-on/off ablation report for `context_pack_retrieval`.
- `AGENT_RETRIEVAL_COMPARE_8_TASKS.md`: paired retrieval-on/off real-agent comparison over 8 ordinary maintenance tasks.
- `AGENT_RETRIEVAL_COMPARE_8_TASKS.json`: machine-readable comparison metrics for the 8-task retrieval ablation.
- `AGENT_RETRIEVAL_ABLATION_8_TASKS_ANALYSIS.md`: evidence-backed interpretation of the ablation's tool-call, token, latency, and cost tradeoffs.
- `AGENT_TRACE_python_add_tests.html`: sample trace for a real agent task that adds pytest coverage.
- `AGENT_TRACE_multi_file_service_fix.html`: sample trace for a real agent task that fixes a multi-file service bug.
- `AGENT_TRACE_retrieval_on_context_pack.html`: trace where the model calls `context_pack` and passes the retrieval task.
- `AGENT_TRACE_retrieval_off_context_pack.html`: trace where `context_pack` is hidden and the retrieval task fails.

## Notes

- Generated working directories and raw JSONL traces live under `artifacts/` and are intentionally gitignored.
- These reports do not contain API keys.
