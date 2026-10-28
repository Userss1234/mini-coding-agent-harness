# Evaluation and Retrieval Evidence

## Separate the Questions

The existing 40-task scripted suite remains a compatibility/tool-contract regression. Its
historical real-agent reports remain unchanged; the new suite does not replace or inflate them.
`benchmarks/challenges` contains three separate public, author-known maintenance challenges:
atomic inventory reservations, per-project retention and ID-based cursor pagination.
These are not a secret blind holdout, an external benchmark or evidence of broad generalization.

The agent receives behavioral requirements and the allowed submission filenames. It receives
no reference implementation, replacement snippets or acceptance failures. Reference solutions
and 17 acceptance cases live outside the model-visible workspace. The input and acceptance
hashes are checked before/after evaluation. Only declared source files are copied to a fresh
verification directory; additional files, including conftest.py and pytest configuration, are
rejected. Generated Python/pytest caches are excluded from the submission file check.

## External Acceptance

The verifier selects a trusted external pytest configuration, disables third-party plugin
autoload and PYTEST_ADDOPTS, sets an explicit submission import path, and requires the declared
number of JUnit cases with no failures/errors/skips. A process exiting with code zero before
producing test results does not pass. A baseline must execute all expected tests and fail with
the test-failure exit code before any model request is allowed; missing Docker, import errors
or collection failures cannot be misreported as a valid failing baseline.

```powershell
python main.py challenge-eval --output-dir artifacts/challenge-validation-001 --json-output artifacts/challenge-validation.json
```

Default `validate` mode runs trusted baseline and reference code on the host. It uses no model
API. Its result is reference/acceptance validation, never an agent success rate.

Actual agent mode requires Docker. The coding container mounts only its candidate workspace;
acceptance is not mounted there. A separate verification container mounts acceptance at
`/acceptance` read-only and retains the existing no-network/non-root/read-only-root/resource/
timeout policies. Host agent mode is refused. These command and boundary contracts are locally
tested; Docker runtime is unavailable on the current verification machine.

Verification copies set explicit source-directory/file read permissions for the non-root UID
and a separate writable results directory. Acceptance files remain in the read-only mount.
POSIX permission assertions run only on POSIX hosts; this Windows run is not Linux runtime proof.

This is file-integrity and workflow protection, not a malicious-submission-proof grader.
Arbitrary Python executing inside the grading process can interfere with in-memory testing or
forge outputs. Read-only files, expected case counts and JUnit checks are not cryptographic
proof of correctness. Do not use this implementation as a hostile multi-tenant grading service.

## Counterbalanced Agent Trials

Completed local follow-up: [actual validation report](../reports/LIVE_VALIDATION_20261028.md)
and dated portable artifacts preserve all 12 attempts, including three failed submissions and
seven turn-budget stops. The original engineering-stage statements below are historical.

When Docker, dependencies and model credentials are available, explicitly run:

```powershell
python main.py challenge-eval --mode agent --backend docker --compare-backends --output-dir artifacts/challenge-abba-001
```

This runs lexical/hybrid/hybrid/lexical in fresh workspaces: 12 task attempts for three tasks,
up to 12 turns each by default. It makes paid API calls. No such calls were made for this stage.
There is no shared workflow memory or automatic application to the user's source repository.
Per-attempt SQLite run state and trace are retained outside each candidate. The aggregate CLI
requires a new output directory; it does not automatically resume an interrupted whole suite.
Individual durable runs can be inspected separately. Provider/model/OS caches and stochastic
variation remain confounders; order reversal alone is not a statistical superiority test.

## Code-Aware Retrieval

Line windows remain the default, preserving the old 10-query baseline. Optional Python AST
boundaries split top-level functions/classes and direct methods while retaining decorators,
blank lines and source line numbers. Oversized definitions still use bounded overlapping line
windows; syntax errors and non-Python text fall back to line windows. This is boundary-aware
chunking, not full semantic parsing or an unbreakable function-level unit.

```powershell
python main.py retrieval-benchmark --judgments benchmarks/retrieval-v2/judgments.json --chunk-strategy python --output artifacts/retrieval-python.md --json-output artifacts/retrieval-python.json
$env:HARNESS_RETRIEVAL_CHUNK_STRATEGY = 'python'
```

The environment variable selects the strategy for ordinary lexical/hybrid tools. Use the same
setting when comparing backends or resuming a study. It does not change model-facing tool
schemas. Retrieval skips symlink files and resolved paths outside the selected root.

The new corpus contains 24 small Python files and 28 judged queries, including multi-path and
four semantic stress cases. The first 24 direct queries saturated; four paraphrases were added
before freezing this development fixture. It is author-constructed, inspected and not a blind
test set. Two lexical misses are retained. Never compare its MRR directly with the old corpus
as if they were the same benchmark, or promote a small ranking difference into an agent gain.

## Timing and Evidence Follow-Up

```powershell
python main.py retrieval-study --include-hybrid --output artifacts/retrieval-study.json
python main.py evidence-report --trace-input TRACE.jsonl --label actual-source-mode --output artifacts/evidence.json
```

The study supports forward and reverse lexical/hybrid orders. It uses fresh document embedding
caches per case/order and repeated full retrieval calls; the preceding quality pass loads the
model before timing. "Cold" means document-cache cold, not OS/model cold. Lexical rebuilds its
index on both first and repeated calls. OS caches, CPU scheduling and machine load are not
controlled. Results are local observations, not latency SLAs. CLI hybrid studies are offline-only;
missing dependencies are recorded explicitly and no synthetic hybrid score is substituted.

Evidence reports distinguish injected paths from later successful explicit reads/edits, ignore
failed tools and verifier activity, and count only evidence retrieved before a follow-up. They
do not count an internal retrieve_then_read read as a separate downstream action. A zero ratio
does not prove evidence was unused, and a positive ratio does not prove semantic understanding,
causal benefit or task correctness. Source labels are operator-provided, not authenticated.
`reports/EVIDENCE_USE_EXAMPLE.json` is explicitly from scripted traces, not a real model run.
