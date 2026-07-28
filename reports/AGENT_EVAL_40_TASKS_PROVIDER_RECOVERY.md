# 40-Task Agent Eval Provider Recovery

Generated: 2026-07-28

## Outcome

- The first DeepSeek `deepseek-chat` run over the expanded 40-task suite passed **39/40**.
- All 39 completed verifiers passed. The only failed task, `shell_no_shell_execution`, stopped before verification after the model endpoint returned HTTP 503 through the original retry budget.
- The agent request retry budget was increased from 2 retries to 4 retries, preserving exponential backoff.
- A focused regression test now proves recovery after four consecutive transient 503 failures.
- A targeted model-backed rerun of `shell_no_shell_execution` passed **1/1**.

This is not presented as a single-run 40/40 result. The committed evidence is one full 39/40 run plus a successful targeted provider-recovery rerun.

## Full-Run Evidence

Source: `reports/AGENT_EVAL_40_TASKS.md` and `reports/AGENT_EVAL_40_TASKS.json`

- Tasks: **40**
- Passed: **39**
- Success rate: **97.50%**
- Input tokens: **1,510,966**
- Output tokens: **44,294**
- Estimated model cost: **$5.197308**
- Average duration: **101.21s**

The failed task trace is:

`artifacts/agent_eval_40_tasks_runs/agent/shell_no_shell_execution.jsonl`

Its final model-request sequence records two `model_request_retry` events followed by a terminal `agent_error` for `HTTP Error 503: Service Temporarily Unavailable`.

## Hardening

Code changes:

- `harness.agent.run_agent(..., max_retries=4)` now permits up to five total attempts for transient model failures.
- `_call_with_retries(...)` keeps exponential delays of 0.5s, 1s, 2s, and 4s.
- `trace_metrics(...)` now classifies a terminal `agent_error` as `model_request_failed`.
- Unit coverage simulates four consecutive 503 responses and verifies recovery on the fifth attempt.

The retry policy still does not retry non-transient request errors.

## Targeted Rerun Evidence

Source: `reports/AGENT_EVAL_40_TASKS_PROVIDER_RETRY.md` and `reports/AGENT_EVAL_40_TASKS_PROVIDER_RETRY.json`

- Task: `shell_no_shell_execution`
- Passed: **1/1**
- Input tokens: **85,198**
- Output tokens: **1,178**
- Estimated model cost: **$0.273264**
- Duration: **137.46s**
- Terminal model errors: **0**

## Interpretation

The full run demonstrates that all expanded-suite task verifiers except the provider-interrupted task passed. The targeted rerun demonstrates that the task itself remains solvable after the provider recovered. A second complete 40-task run is still required before claiming a single-run 40/40 result with the hardened retry policy.
