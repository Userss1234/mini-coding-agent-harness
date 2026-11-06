# Tool Calling, External MCP and Code RAG

This document describes the 2026-10-29 core pass. The later user-selected
[Qdrant extension](QDRANT_RETRIEVAL.md) adds an optional vector database without replacing
the local default or SQLite run persistence; statements below about no new database refer
to the original core pass.

This pass strengthens the usable agent stack, not the benchmark task count. The existing raw
evaluation reports remain unchanged. No vector database, service orchestrator or new model API
is required.

## Tool Calling Contract

Tool arguments are checked against the advertised JSON Schema before a handler runs. Local
tools reject undeclared top-level arguments; external tools retain their declared schema.
Registration rejects name collisions, schemas over 64 KiB, nesting over 32 levels and external
`$ref`/dynamic/recursive references. Schema-resolution errors fail without executing a handler.
Schema validation is not a sandbox for malicious operator-selected services or complex regexes.

Malformed JSON and non-object arguments are not converted to `{}`. They become error results
with matching call IDs and durable ledger entries, so the model can correct them without an
accidental zero-argument execution. Empty or duplicate provider call IDs are rejected before
execution. `registry.call(tool_name, **arguments)` takes the tool name positionally, allowing an
external tool to legitimately have its own `name` parameter.

Failures expose `metadata.tool_error` with a stable `code` and `retryable=false` after the current
dispatch has failed. Codes include `unknown_tool`, `invalid_arguments`, `invalid_schema`,
`permission_denied`, `execution_failed`, `timeout` and MCP-specific error codes. Existing human-
readable output remains available. Local trusted read-handler exceptions retain the bounded
transient retry policy; writes, command execution and external tools are not automatically retried.

Set `HARNESS_TOOL_READ_WORKERS=2` (1-4; default 1) to parallelize a batch consisting entirely of
`read_file`, `grep`, `list_python_files`. Any mutation, planning operation, retrieval/embedding or
remote tool makes the batch serial. Results retain provider order. Durable calls are marked
started on the controlling thread and completed through the existing ledger; worker threads do
not write SQLite state. The trace logger serializes writes on its instance. This is bounded
read concurrency, not arbitrary thread cancellation or cross-process trace locking.

## External MCP Client

`ask` and `resume` accept `--mcp-config`. Configuration is operator-owned and must be outside
the agent's writable workspace. It can start trusted stdio programs or connect to Streamable
HTTP. It is not a model-facing launch-server tool or automatic plugin installer.

```powershell
python main.py --workspace D:/work/target ask "Inspect repository evidence" --mcp-config D:/config/agent-mcp.json
python main.py --workspace D:/work/target resume RUN_ID --mcp-config D:/config/agent-mcp.json
```

The template is `examples/mcp-client.example.json`; edit paths and use a Python environment
containing the locked dependencies. Relative `cwd` resolves against the configuration directory.
Activate the intended interpreter before using a bare `python` command, or specify an absolute
executable. Explicit configuration authorizes launching that host process; stdio servers do not
automatically run inside Docker.

Only locally allowlisted remote tools are imported. Names become `mcp__SERVER__TOOL`; server
names are at most 16 ASCII identifier characters and selected remote names at most 40 ASCII
letters/digits/underscore/hyphen. Unsupported names fail rather than being silently renamed.
Local risk is explicitly `read` or `write`; remote annotations do not grant authority. External
writes additionally require the harness `--allow-write` flag, and remote servers must enforce
their own filesystem/resource permissions. Results/descriptions can be untrusted prompt content.

HTTP examples can use `token_env` to name an already exported bearer-token variable. URL userinfo,
query and fragment credentials are rejected. Non-loopback services require HTTPS and explicit
`allow_remote=true`. Automatic redirects, OAuth enrollment and arbitrary discovery are not added.
Stdio `env` maps child-variable names to host-variable names, never inline token literals; the
SDK's small default environment plus those explicit values is used, not all provider credentials.

An HTTP server entry can replace the stdio entry in the version-1 config:

```json
{
  "name": "reference",
  "transport": "http",
  "url": "http://127.0.0.1:8000/mcp",
  "token_env": "HARNESS_MCP_AUTH_TOKEN",
  "timeout": 15,
  "tools": {"read_file": "read", "rag_search": "read"}
}
```

The token must already be exported when the connection opens. A fingerprint checks configured
identity and privileges, not the integrity or honesty of the remote server implementation.

Connection options and resolved credential/environment digests form a policy fingerprint, without
persisting raw values. CLI resume checks it before launching any process or HTTP session. Tool
schema/permission changes are also checked by RunSession. Credential rotation intentionally needs
an explicit new configuration/run decision, not a silent privilege change. Direct library users
should pass saved `external_tools` as `ExternalMCPTools(..., expected_policy=...)` on resume.

Each connection owns one SDK session on one thread and one async task; context enter/exit occur
on that same task. Discovery is limited to 20 pages/1000 tools. Deadlines are 1-60 seconds.
Requests use SDK cancellation and close on transport failure, with no automatic reconnect/replay.
Cancellation is not proof that a remote side effect was rolled back. An uncertain external write
blocks the Agent and leaves the durable call `started` for `run-resolve` reconciliation before
resume. A nonpersistent run stops with the warning but has no durable reconciliation archive.

Text and structured JSON results are supported and clipped to 12000 returned characters. Images,
elicitation and other special result types are not a complete multimodal workflow; unsupported
result types fail explicitly. Remote `is_error` maps to a failed ToolResult, not a successful call.

Windows HTTP shutdown now waits for the serving loop to exit before closing its listener; its
socket-only Selector loop is local to that server, without changing subprocess clients' event-loop
policy. Close deadlines fail visibly rather than force-closing a socket still in use.

## Code RAG

`rag_symbols(symbol, limit=8)` returns Python definitions and possible syntactic callers/callees,
file/line ranges, snippets and indexed-source SHA-256. It parses source; it never imports it.
Qualified/suffix matching can be ambiguous and does not resolve dynamic dispatch, import aliases,
reflection or actual execution. Evidence is capped at 12000 characters, with truncation markers
and at most 30 displayed call names per record. Syntax errors and oversized/truncated sources
can omit relationships. The tool follows the same ignored/sensitive/path filters as retrieval and
is removed from model schemas when retrieval is off.
That switch controls built-in retrieval, not explicitly configured external tools whose semantics
are determined by the operator's MCP allowlist.

Both lexical and hybrid indexing share an in-memory, 128-entry LRU chunk/tokenization cache.
Every query re-enumerates paths and reads eligible source text; SHA-256 of that indexed text
invalidates changed chunks even for same-size/same-mtime edits. Deleted files cannot be returned.
Entries are scoped by resolved workspace, relative path and chunk options. No stat-only freshness
assumption, vector database or persisted plaintext index was added. Reads are not transactional
snapshots when an external editor changes files during a query.

Unchanged chunks reuse parse/tokenization work; query scoring is still rebuilt. File text remains
bounded by the existing 200000-character indexing cap. `indexed_source_sha256` hashes the decoded,
newline-normalized indexed prefix, not necessarily the entire raw file. Matches and symbol evidence
retain paths/lines/hashes for audit; those do not prove the model understood or used the evidence.

Retrieval-study timing descriptions now distinguish the shared chunk cache from document-vector
caches. Historical timings are preserved; no new latency SLA or agent-success gain is asserted.

## Verification

See `reports/CORE_AGENT_STACK_20261029.md` for final tests, real stdio/HTTP integration, actual
DeepSeek tool usage and current Docker/hybrid/MCP validation. The prior exception-contract ambiguity
is still documented and not silently fixed/rescored in this core-capability pass.
