# Reports

This directory contains committed portfolio artifacts that can be reviewed without rerunning the model.

- `SCOPE_SAFE_VERIFICATION_20261029.md` and `CHALLENGE_SCOPE_SAFE_ABBA_20261029.json`: lossless current-plan accounting and Docker read-only inline checks; zero context/scope failures in one 12-attempt sequence, unchanged raw 9/12, explicit exception-contract ambiguity.

- `VERIFICATION_GUIDANCE_20261029.md` and `CHALLENGE_GUIDANCE_ABBA_20261029.json`: generic requirement/check mapping and budget-guidance experiment; unchanged 9/12 acceptance, fewer turn stops but three context stops and leftover helper files. Guidance remains opt-in, not a promoted default.

- `LIVE_VALIDATION_20261028.md`: actual local Docker/WSL, MCP/hybrid, same-corpus reverse-order retrieval and 12-attempt DeepSeek ABBA validation; 9/12 submission acceptance, seven turn-budget stops. Links to new dated portable artifacts; historical stage gaps below are retained as historical evidence.

- `PORTFOLIO_WALKTHROUGH.md`: short interview talk track tying the demo, eval, failure-analysis, and MCP artifacts together.
- `RESUME_BULLETS.md`: evidence-backed resume bullet options with claim-to-file mapping.

## CI Closure

- [GitHub Actions run 34760601827](https://github.com/Userss1234/mini-coding-agent-harness/actions/runs/34760601827): passing `validate` and `cross-feature` jobs for the official SDK HTTP path on commit `9da0a8b`.
- `ENGINEERING_QUALITY.md`: locked dependencies, Ruff/mypy gates, 75% branch coverage threshold, Python 3.10-3.12 CI matrix, and local 295-test/40-task verification (plus one optional symlink skip).
- `RUN_RECOVERY.md`: Priority 1 local SQLite durability, real process-termination recovery, tool-result reuse, unknown-outcome reconciliation and credential-redacted export evidence.
- `CONTEXT_WINDOW.md` and `CONTEXT_WINDOW_COMPARISON.json`: Priority 2 context-budget, complete tool-history and checkpoint continuation evidence, with a local deterministic 12-step comparison.
- `WORKSPACE_ISOLATION.md` and `WORKSPACE_ISOLATION_SMOKE.json`: Priority 3 copy/review/apply, host-conflict rejection, real process-interruption recovery and centralized trace redaction evidence; Docker runtime not rerun locally.
- `EVALUATION_CREDIBILITY.md`: Priority 4 separation of compatibility tests, public challenges and retrieval development fixtures; explicit live-run gaps.
- `CHALLENGE_VALIDATION.json`: three buggy baselines rejected and three references accepted over 17 external cases, not a model score.
- `RETRIEVAL_V2_LINES.md/.json`, `RETRIEVAL_V2_PYTHON.md/.json` and `RETRIEVAL_V2_STUDY.json`: 28-query/24-file rankings and local first/repeated timings; hybrid unavailable locally.
- `EVIDENCE_USE_EXAMPLE.json`: temporal path-follow-up proxy on explicitly scripted traces, not causal or model-quality evidence.

## Local Demo

- `DEMO_python_bugfix.md`: deterministic local demo report for `python main.py demo --task python_bugfix`.
- `DEMO_python_bugfix_TRACE.html`: self-contained interactive trace viewer output for the local demo.

## MCP

- `MCP_SMOKE.md`: in-process MCP protocol smoke report covering initialize, tools, resources, resource templates, prompts, and a permission-policy tool call.
- `MCP_HTTP_SMOKE.md`: localhost Streamable HTTP smoke report covering Bearer authentication, Origin rejection, session lifecycle, JSON/405 behavior, and stdio tool parity.
- `CROSS_FEATURE_VALIDATION.md`: passing Docker runtime markers plus a live cached MiniLM `rag_search` call through authenticated MCP HTTP.

## Execution Isolation

- `DOCKER_SANDBOX_SMOKE.md`: GitHub Actions runtime report proving non-root execution, workspace visibility, and blocked outbound networking for the configured Docker backend.

## Retrieval Quality

- `RETRIEVAL_QUALITY_BASELINE.md`: relevance-judged 10-query lexical baseline with path-level MRR, Recall@K, per-case rankings, and CI quality gates.
- `RETRIEVAL_QUALITY_BASELINE.json`: machine-readable copy used for future lexical-versus-hybrid comparisons.
- `RETRIEVAL_QUALITY_HYBRID.md`: optional local MiniLM hybrid result with fusion weights, cache metrics, backend-specific gates, and semantic-case rankings.
- `RETRIEVAL_QUALITY_HYBRID.json`: machine-readable hybrid result generated against the same judgments as the lexical baseline.
- `AGENT_RETRIEVAL_BACKEND_COMPARE_8_TASKS.md` / `.json`: lexical-first focused real-agent backend pair with complete task results, hybrid-minus-lexical pairs, and cache metrics.
- `AGENT_RETRIEVAL_BACKEND_RAG_SYMBOL_FIX.md` / `.json`: targeted post-fix pair for the backend-biased `rag_symbol_retrieval` verifier.
- `RETRIEVAL_BACKEND_8_TASKS_ANALYSIS.md`: honest interpretation separating ranking gains from the missing agent-workflow gain.

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
