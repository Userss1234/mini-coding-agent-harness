# Core Agent Stack Strengthening

Date: 2026-10-29. Working tree based on `576aecd`; changes are deliberately uncommitted under
the user's latest instruction. No push, remote CI, resume rewrite or expanded task suite.
This pass continuously implements Tool Calling, external MCP client integration and code RAG.

## Delivered

### Tool Calling

- One advertised/executed JSON Schema contract, stable error codes and rejection before handler
  execution. Undeclared local arguments, excessive schemas and external schema references fail.
- Invalid JSON/non-object arguments are retained as invalid data, never converted into an empty
  object that might execute a zero-argument action. Empty/duplicate provider IDs fail before use.
- Optional 1-4-worker batches only for the three explicitly allowed local file-read tools;
  mixed/mutating/remote batches stay serial. Results retain order and durable ledger writes stay
  on the controller. Default remains serial. Trace writes are synchronized on the logger instance.
- External writes with uncertain transport outcomes stop the agent, leave the call `started`
  and require existing operator reconciliation before resume. No silent retry/reconnect.

### External MCP

- Official SDK v2 client for persistent stdio and authenticated Streamable HTTP connections.
- Explicit local tool allowlists/risk mapping, namespacing, write permission checks, schema and
  configuration identity guards. Operator config must be outside the model's writable workspace.
- CLI `ask/resume --mcp-config`; policy is checked before launching external servers on resume.
  Credentials use explicit environment references and opaque fingerprints, not saved raw values.
- Bounded discovery/deadlines, error-result mapping, close-on-transport-failure and same-task
  SDK context teardown. Unknown writes are not treated as safely repeatable failures.
- HTTP listener shutdown now waits for serving-loop completion before socket close; Windows
  HTTP uses its own socket Selector loop, without changing subprocess-client loop policy.

### Code RAG

- `rag_symbols`: AST definitions, possible syntactic callers/callees, paths, line ranges, snippets
  and indexed-source hashes. Results and displayed call names are bounded and marked if clipped.
- Shared 128-entry content-fingerprint chunk/tokenization LRU for lexical and hybrid paths.
  Queries still reread eligible text and rebuild query scoring. Same-size/same-mtime edits
  invalidate cached chunks, deletions cannot return stale files, and sensitive/path filters remain.
- Source hashes accompany matches. These hash the normalized indexed prefix, not an attestation
  of a complete raw file, model understanding or actual runtime call relationships.

Usage, configuration and limits: [CORE_AGENT_STACK.md](../docs/CORE_AGENT_STACK.md).
Template: [mcp-client.example.json](../examples/mcp-client.example.json).

## Final Verification

Windows / Python 3.12.2, installed MCP SDK 2.2.0. This is local evidence, not a new remote
Python-version matrix or certification of arbitrary third-party MCP providers.

| Check | Result |
|---|---|
| Full tests | 340 passed; 1 optional Windows symlink skip |
| Branch-enabled coverage | 83.16%; gate 75% |
| Strict thread-error handling | pass with PytestUnhandledThreadExceptionWarning treated as error |
| Ruff / mypy | pass; mypy 35 source files |
| Compilation / dependency consistency | pass |
| Existing scripted regression | 40/40 |
| Original 10-query lexical MRR | 0.8000; unchanged |
| Fixed 28-query hybrid/Python MRR / Recall@5 | 0.9762 / 1.0000; preserved |

Tests use real SDK stdio processes and authenticated localhost HTTP sessions for discovery,
read calls, local write rejection, remote error mapping, deadline/connection poisoning, thread
cleanup, policy changes rejected before launch, and the Agent/durable-ledger bridge. Parallel
read overlap is checked with a barrier, not an ungrounded speedup estimate. Unknown-write
reconciliation is tested with an injected uncertain result; no destructive production remote
mutation was performed. The remaining original client/server protocol tests also pass.

Actual Windows shutdown tests and the live run below no longer show the earlier WinError
995/10038 listener failures. This is not an exhaustive socket/load test. The live MiniLM
dependency still emits its unrelated `resume_download` FutureWarning; it is not suppressed.

Existing runtime package versions were not upgraded. `httpx2` and `jsonschema`, already pinned
in both locks, are now explicit direct requirements; lock provenance comments reflect that.

## Actual Model Tool Usage

A single bounded DeepSeek `deepseek-chat` read-only smoke used the real CLI, an external stdio
MCP server and local symbol RAG. The allowance was 8 turns; it ended normally after 4 model
responses. The original fixture source was unchanged and no project helper file was created.

| Observed tool | Calls |
|---|---:|
| Retrieval preflight `retrieve_then_read` | 1 |
| `todo_write` | 2 |
| External `mcp__fixture__read_file` | 1 |
| Local `rag_symbols` | 1 |

The final answer identifies `reserve(stock, items)` in `service.py` and the possible dependency
`catalog.valid_quantity`, distinguishing syntactic evidence from runtime resolution. Reported
usage: 14621 input tokens and 1029 output tokens. These are provider counters, not an invoice.
Run ID: `ff0d7aedb0a046a6829a1b8d5b703d5e`. Local trace/database:
`artifacts/core-agent-mcp-rag-20261029.jsonl` and `.sqlite3`.

This is actual tool-selection/integration evidence, not a maintenance success-rate comparison.
The later malformed-input/uncertain-write/teardown hardening branches were validated by tests;
no second paid suite was run to fabricate a stronger model-quality claim.

## Actual Docker / Hybrid / MCP Runtime

- [Docker probe](CORE_STACK_DOCKER_20261029.md): non-root UID 10001, mounted workspace,
  network blocked, no host fallback.
- [Authenticated HTTP hybrid call](CORE_STACK_CROSS_FEATURE_20261029.md): initialize 200,
  initialized 202, tool 200, actual cached 384-dimensional MiniLM model, expected implementation
  path in the top three and no tool/request error. Serving loop and listener close normally.

Embeddings remain on the host and command execution uses Docker. This combines explicit
evidence paths; it does not claim that the embedding model ran inside the execution container.
External-client interoperability here is verified with the project's SDK server and controlled
fixtures, not every hosted OAuth/multimodal MCP service.

## Reproduction and Scope

Local artifacts: `artifacts/core-stack-20261029-EVAL.md/.json`, its trace directory,
`core-retrieval-baseline-20261029.md/.json`, and `core-rag-v2-hybrid-20261029.md/.json`.
The source/tests and documented CLI reproduce the mechanisms; generated working data
and raw run databases remain ignored.

All three core work items are handled together. No automatic commit or push was made. The
previous three raw 9/12 reports and exception-contract ambiguity are retained; this pass does
not silently rescore them, invent generalization gains, install a vector DB or edit the resume.
