# Reliable Maintenance Controls

This optional P0-P3 extension builds on the existing Tool Calling/MCP/RAG/Docker/SQLite stack.
It adds trusted completion checks, a Python repository map and language server, and durable
run controls. It does not enable multi-agent orchestration or a distributed vector-index service.

## P0: Provenance and Reproducibility

See [source notices](../THIRD_PARTY_NOTICES.md). The educational starting point is Learn Claude
Code; this project does not claim to authenticate leaked official Claude Code source.
The repository retains its project license and separately preserves the upstream MIT notice.
This is not a completed line-by-line provenance/license-compliance audit.

Base dependencies and local backends remain unchanged. Install optional semantic navigation with:

```powershell
python -m pip install -r requirements-dev.lock -r requirements-codeintel.lock
docker build -f docker/sandbox/Dockerfile -t mini-coding-agent-harness-sandbox:latest .
docker build -f docker/verification/Dockerfile -t mini-coding-agent-harness-verification:latest .
```

The verification image extends the existing sandbox with Ruff 0.16.7 and returns to UID 10001.
Actual checks still enforce non-root/no-network/read-only-root/read-only-workspace/no-fallback.
CI has new optional-language-server and actual Docker-check jobs/steps; definition in the local
working tree is not proof of a remote passing run. Commits/pushes require user approval.

## P1: Completion Verification and Bounded Repair

Use an operator-owned JSON configuration **outside the target Agent workspace**. The example
in this harness's `examples/verification.example.json` is valid when maintaining a different repo;
it is not valid as a self-maintenance policy when the whole harness directory is the Agent workspace.

```json
{"version": 1, "checks": ["syntax", "ruff", "pytest"],
 "test_target": "tests", "timeout": 30, "max_repairs": 2}
```

```powershell
$env:HARNESS_DOCKER_IMAGE = "mini-coding-agent-harness-verification:latest"
python main.py --workspace D:/projects/example --execution-backend docker --allow-write `
  ask "Repair the issue and verify the changed code" --isolate D:/agent-sessions/example-01 `
  --verification-config examples/verification.example.json --max-turns 12
```

The controller takes a raw-source hash baseline and compares the safe bounded workspace when the
model proposes a final answer. It is not run after every intermediate edit. Existing generated/
private-file exclusions and workspace scan limits apply; deleted paths are detected.

- Syntax checks compile changed existing Python source without executing it.
- Ruff uses isolated fixed E4/E7/E9/F rules and no cache; model-editable Ruff settings are ignored.
- Pytest runs the operator-selected relative target with plugin autoload disabled, no cache,
  an explicit root and `/dev/null` configuration. Workspace `pytest.ini` addopts cannot skip checks.
  Conftest and test code still execute as repository code inside the Docker boundary.
- Diagnostics contain tool/file/position/severity/code/message, status and exit code where available.
- Source hashes are compared again after checks; concurrent changes invalidate the result.
- A passing profile allows completion. Failure injects observed diagnostics for at most 0..3
  configured repair rounds, subject also to the model-turn/run budgets. Identical failures on an
  unchanged snapshot stop early. Missing tools/targets, timeouts, invalid diagnostic output or no
  applicable check produce `verification_unverified`, not a passing result.
- Failed/unverified completion is paused, not completed. Baseline, observations and consumed repair
  allowance persist; resuming does not reset them. A profile change is rejected by run-policy checks.

Syntax success alone is not behavioral correctness. Repository tests may be model-authored or
incomplete. `passed` means only that the selected checks passed for the observed source snapshot;
it is not independent task acceptance or a correctness proof. Protected challenge acceptance
remains separate. Markdown-only edits under a syntax-only profile can be unverified.

## P2: Structural and Semantic Retrieval

`repo_map` is available with built-in retrieval. It returns a query-ranked, 500..12000-character
Python module/signature/import map with source hashes. It is AST syntax structure, not resolved
dependencies. Sensitive/generated paths reuse existing retrieval filters; large source files use
the existing 200,000-character indexed prefix.

Opt into semantic navigation explicitly:

```powershell
$env:HARNESS_PYTHON_LSP = "on"
$env:HARNESS_PYTHON_LSP_TIMEOUT = "10"
```

`python_navigate(path, line, column=1, operation="definition")` supports definitions, references
and diagnostics. Inputs are 1-based Unicode-code-point positions; returned columns are 1-based
UTF-16 positions and include the raw LSP range. Definitions/references come from the installed
Python LSP Server/Jedi, not AST name-suffix matching. Diagnostics use Pyflakes.

The host launches a fixed `python -I -m pylsp` module, not a model-selected command or shell.
Provider credentials/PYTHONPATH are not forwarded. Cwd, user configuration and caches are placed
in a request-scoped temporary directory. Root URI is explicit, result paths are restricted to
current safe indexed Python sources, and hashes are rechecked. No automatic server download.
Shutdown/exit, bounded waiting and process cleanup run on success and timeout. Package versions
and request deadline are captured in the run policy when navigation is enabled.

This trusted local language-server process is **not** a Docker sandbox. Installed server/plugins
must be trusted. Static analysis cannot fully resolve dynamic Python dispatch. Returned diagnostic
messages/code snippets are untrusted content, not permission grants. Each call starts a process;
no persistent language-server lifecycle or lower-latency claim is made.

Use Qdrant for semantic discovery, repository maps for a bounded overview and LSP for symbol
navigation. `rag_symbols` still reports syntax-only candidate callers/callees. Retrieval `off`
suppresses all these built-in retrieval tools; external MCP tool permissions remain separate.
The default registry exposes seven built-in retrieval tools, or eight with Python LSP enabled.

## P3: Durable Run Controls

All run controls are opt-in; existing turn and context budgets remain in place:

| CLI option | Meaning |
| --- | --- |
| `--max-tools N` | Cumulative model-tool dispatch count, not handler retry count |
| `--max-seconds S` | Cumulative active-run wall time, excluding time while stopped between resumes |
| `--max-tokens N` | Stop threshold on cumulative provider-reported input + output usage |
| `--repeat-limit N` | Stop after N consecutive identical tool/argument/result observations |
| `--cancel-file PATH` | Cooperative operator cancellation signal outside the Agent workspace |

Consumed limits and repeated-observation state are checkpointed. Resume restores the original
limits and rejects overrides rather than resetting the allowance. Completed cached tool results
are reused without counting another dispatch. Budget/cancellation checks run before marking new
calls started; a blocked dispatch remains pending, not an unknown executed action.

Token-limited runs stop when usage is missing/invalid, including interrupted model requests with
unknown usage. Missing usage is not zero. Automatic provider retries are disabled under a token
limit because failed-request billing is not observable. Numeric token counters/limits survive
redaction; actual credential strings remain redacted. Qdrant authentication identity now uses a
non-secret fingerprint field that also survives redaction.

Checks occur at model/tool/completion boundaries. They do not preempt a synchronous in-flight
model/tool call. One request may exceed the token/time stop threshold before its usage/time is
known, so these are **not exact billing caps or hard deadlines**. Verification checks count in
elapsed time but are not model-tool dispatches. Controlled runs serialize tool dispatch to honor
per-call stops; default uncontrolled safe-read batching is unchanged.
Elapsed accounting is checkpoint-based; a hard process termination can leave its last interval
unrecorded. It is not an audited time/billing meter or a hard process-lifetime enforcement mechanism.

Cancellation does not prove rollback. Existing external-write unknown-outcome reconciliation still
takes precedence after an uncertain execution. Repeated identical observations are only a heuristic;
the opt-in threshold can stop legitimate repetitive work. No opaque LLM stuck-classifier is used.

These controller gates are narrowly scoped trusted lifecycle/policy boundaries, not an arbitrary
workspace hook/plugin runner. They can refuse dispatch or completion, never grant extra authority.

## Resume and Evidence Boundaries

Verification configuration, optional language-server settings, provider identity, permissions and
tool schemas must still match on resume. Old checkpoints with different schemas or the earlier
redacted Qdrant credential fingerprint are intentionally not silently migrated: create a new run
rather than bypassing policy identity checks. Token/cancel/budget stops do not authorize limit resets.

Reproduce the real Docker repair boundary with a deterministic model driver (no paid model API):

```powershell
$env:HARNESS_LIVE_DOCKER = "1"
$env:HARNESS_VERIFICATION_REPORT = "artifacts/RELIABILITY_SMOKE.json"
python -m pytest tests/test_verification_controller.py -k actual_docker -q
python -m pytest tests/test_code_intelligence.py tests/test_run_controls.py -q
```

The actual repair smoke proves tool/execution/controller integration, not model coding accuracy.
Real language-server tests prove alias/reference/diagnostic behavior on controlled fixtures.
Historical model evaluation and retrieval results are retained unchanged. See the dated reliability
report for current gates; further paid model comparisons and remote publication remain pending.
