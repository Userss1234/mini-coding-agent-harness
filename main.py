from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path

from harness.agent import run_agent
from harness.challenge_eval import run_challenges
from harness.context_window import ContextConfig
from harness.cross_feature_smoke import run_cross_feature_smoke
from harness.demo import run_demo
from harness.docker_smoke import run_docker_smoke
from harness.eval_analysis import (
    analyze_eval_reports,
    build_eval_history,
    build_failure_dashboard,
    build_retrieval_stability_report,
    build_stability_report,
)
from harness.evaluation import run_evaluation
from harness.evidence_metrics import summarize_evidence_use
from harness.mcp_http_smoke import run_mcp_http_smoke
from harness.mcp_sdk import build_mcp_sdk_server, serve_mcp_sdk_stdio
from harness.mcp_sdk_http import build_mcp_sdk_http_server, serve_mcp_sdk_http
from harness.mcp_smoke import run_mcp_smoke
from harness.retrieval_benchmark import (
    run_retrieval_benchmark,
    write_retrieval_benchmark_outputs,
)
from harness.retrieval_study import run_retrieval_study
from harness.review import inspect_repo
from harness.run_store import SQLiteRunStore
from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.trace_viewer import build_trace_report, load_trace_events
from harness.workspace import WorkspaceSession


def make_registry(
    workspace: Path,
    trace_path: Path,
    fresh_trace: bool = False,
    allow_write: bool = False,
    enable_context_pack: bool = True,
    retrieval_backend: str | None = None,
):
    if fresh_trace and trace_path.exists():
        trace_path.unlink()
    trace = TraceLogger(trace_path)
    trace.log("session_start", workspace=str(workspace.resolve()), allow_write=allow_write)
    return build_registry(
        workspace.resolve(),
        trace,
        allow_write=allow_write,
        enable_context_pack=enable_context_pack,
        retrieval_backend=retrieval_backend,
    )


def cmd_tools(args) -> None:
    registry = make_registry(Path(args.workspace), Path(args.trace), args.fresh_trace, args.allow_write)
    print("\n".join(registry.names()))


def cmd_challenges(args) -> None:
    result = run_challenges(Path(args.suite), Path(args.output_dir), mode=args.mode,
                            backend=args.backend, compare_backends=args.compare_backends,
                            max_turns=args.max_turns)
    for row in result["rows"]:
        row["baseline"].pop("output", None)
        row["verdict"].pop("output", None)
    if args.json_output:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not all(not row["baseline"]["passed"] and row["baseline"]["returncode"] == 1
               and row["verdict"]["passed"] for row in result["rows"]):
        raise SystemExit("Challenge acceptance failed")


def cmd_retrieval_study(args) -> None:
    if args.include_hybrid:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    result = run_retrieval_study(Path(args.judgments), include_hybrid=args.include_hybrid,
                                 chunk_strategy=args.chunk_strategy, repeats=args.repeats)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Study: {output.resolve()}; unavailable backends: {result['unavailable_backends']}")


def cmd_evidence_report(args) -> None:
    rows = []
    for trace in args.trace_input:
        events, errors = load_trace_events(Path(trace))
        rows.append({"trace": Path(trace).name, "parse_errors": errors,
                     **summarize_evidence_use(events)})
    result = {"schema_version": 1, "source_label": args.label, "rows": rows,
              "claim_boundary": "Observed path follow-up only; source label is operator supplied, not authenticated provenance."}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence report: {output.resolve()}")


def cmd_manual(args) -> None:
    registry = make_registry(Path(args.workspace), Path(args.trace), args.fresh_trace, args.allow_write)
    print("== Python files ==")
    print(registry.call("list_python_files").output)
    print("\n== Syntax check ==")
    print(registry.call("run_py_compile").output)


def cmd_inspect(args) -> None:
    registry = make_registry(Path(args.workspace), Path(args.trace), args.fresh_trace, args.allow_write)
    result = inspect_repo(registry, args.output)
    print(result)
    print(f"Trace written to {Path(args.trace).resolve()}")


def cmd_ask(args) -> None:
    workspace, trace_path = Path(args.workspace), Path(args.trace)
    isolated = None
    if args.isolate:
        if args.no_persist:
            raise SystemExit("Isolated runs require persistence")
        isolated = WorkspaceSession.create(workspace, Path(args.isolate))
        workspace, trace_path = isolated.workspace, isolated.path / "trace.jsonl"
        args.run_db = str(isolated.path / "runs.sqlite3")
        os.environ["HARNESS_EXECUTION_BACKEND"] = (
            args.execution_backend or os.getenv("HARNESS_EXECUTION_BACKEND") or "docker"
        )
    registry = make_registry(
        workspace,
        trace_path,
        args.fresh_trace,
        args.allow_write,
        enable_context_pack=args.retrieval != "off",
        retrieval_backend=args.retrieval_backend,
    )
    if isolated:
        registry.baseline_workspace = isolated.baseline
        _check_isolated_policy(registry)
    store = SQLiteRunStore(Path(args.run_db)) if not args.no_persist else None
    existing_ids = {run["id"] for run in store.list_runs()} if store else set()
    with isolated.operations.lock("workspace") if isolated else nullcontext():
        print(run_agent(
            args.prompt, registry, retrieval_mode=args.retrieval,
            max_turns=args.max_turns, run_store=store,
            context_config=_context_config(args),
        ))
    if store:
        print(f"Run database: {store.path}")
        for run in store.list_runs():
            if run["id"] not in existing_ids:
                print(f"Run ID: {run['id']}")
    print(f"Trace written to {trace_path.resolve()}")
    if isolated:
        print(f"Isolated session: {isolated.path}; changes staged in copy. Run workspace-review next.")


def cmd_resume(args) -> None:
    if args.fresh_trace:
        raise SystemExit("Resume cannot delete the original trace; omit --fresh-trace")
    isolated = WorkspaceSession(Path(args.isolate)) if args.isolate else None
    if isolated:
        args.run_db = str(isolated.path / "runs.sqlite3")
    store = SQLiteRunStore(Path(args.run_db))
    saved = store.load(args.run_id)
    policy = saved["policy"]
    if args.execution_backend and args.execution_backend != policy["execution_backend"]:
        raise SystemExit("Resume requires the original execution backend")
    os.environ["HARNESS_EXECUTION_BACKEND"] = policy["execution_backend"]
    registry = make_registry(
        isolated.workspace if isolated else Path(args.workspace), Path(saved["artifacts"]["trace"]),
        allow_write=args.allow_write,
        enable_context_pack="context_pack" in policy["tool_names"],
        retrieval_backend=policy["retrieval_backend"],
    )
    if isolated:
        registry.baseline_workspace = isolated.baseline
        _check_isolated_policy(registry)
    with isolated.operations.lock("workspace") if isolated else nullcontext():
        if isolated:
            isolated.ensure_available()
        print(run_agent("", registry, max_turns=args.max_turns, run_store=store,
                        resume_run_id=args.run_id,
                        context_config=_context_config(args, saved.get("context_config"))))


def _check_isolated_policy(registry) -> None:
    policy = registry.execution_policy
    if registry.execution_backend == "host":
        print("Warning: host execution is not a security sandbox; use Docker for untrusted code.")
    elif (
        policy.get("network") != "none" or not policy.get("read_only_root")
        or policy.get("fallback_to_host") or int(str(policy.get("user", "0")).split(":")[0]) == 0
    ):
        raise SystemExit("Isolated Docker runs require no network, non-root, read-only root and no host fallback")


def _approve_workspace(review_id: str) -> bool:
    if not sys.stdin.isatty():
        raise SystemExit("Human approval requires an interactive terminal; piping/--yes is not supported")
    return input(f"Type APPLY {review_id} to authorize this exact operation: ").strip() == f"APPLY {review_id}"


def cmd_workspace(args) -> None:
    if args.command == "workspace-create":
        session = WorkspaceSession.create(Path(args.workspace), Path(args.session))
        print(f"Workspace: {session.workspace}")
        return
    session = WorkspaceSession(Path(args.session))
    if args.command == "workspace-review":
        review = session.review()
        print(f"Review: {session.path / 'review.patch'}")
        print(f"Review ID: {review['id']}; changed files: {len(review['entries'])}")
    elif args.command == "workspace-apply":
        print((session.path / "review.patch").read_text(encoding="utf-8"))
        session.apply(args.review, _approve_workspace)
        print("Reviewed changes applied to source. Session retained for audit.")
    else:
        print("Recovery restores the original pre-application files; it does not finish applying changes.")
        session.recover(_approve_workspace)
        print("Interrupted application rolled back; review again before applying.")


def _context_config(args, saved: dict | None = None) -> ContextConfig:
    values = saved.copy() if saved else asdict(ContextConfig())
    for option, key in (
        ("context_budget", "max_input_tokens"),
        ("context_summary_budget", "summary_tokens"),
        ("context_recent_turns", "keep_recent_turns"),
    ):
        if getattr(args, option, None) is not None:
            values[key] = getattr(args, option)
    if args.context_management is not None:
        values["enabled"] = args.context_management
    return ContextConfig(**values)


def cmd_runs(args) -> None:
    store = SQLiteRunStore(Path(args.run_db))
    if args.export:
        if not args.run_id:
            raise SystemExit("--export requires --run-id")
        store.export(args.run_id, Path(args.export))
        print(f"Run exported to {args.export}")
    elif args.run_id:
        print(json.dumps({"state": store.load(args.run_id), "calls": store.calls(args.run_id)},
                         ensure_ascii=False, indent=2))
    else:
        print(json.dumps(store.list_runs(), indent=2))


def cmd_run_resolve(args) -> None:
    store = SQLiteRunStore(Path(args.run_db))
    store.reconcile(args.run_id, args.call_id, args.result, is_error=not args.succeeded)
    print("Recorded operator reconciliation; resume the run to continue.")


def cmd_eval(args) -> None:
    report = run_evaluation(
        workspace=Path(args.workspace),
        output_path=Path(args.output),
        trace_dir=Path(args.trace_dir),
        mode=args.mode,
        task_ids=args.task_ids,
        categories=args.categories,
        memory_enabled=args.memory == "on",
        context_enabled=args.context == "on",
        retrieval_enabled=args.retrieval != "off",
        retrieval_mode=args.retrieval,
        retrieval_backend=args.retrieval_backend,
        compare=args.compare,
        compare_retrieval=args.compare_retrieval,
        retrieval_compare_order=args.retrieval_compare_order,
        compare_retrieval_backends=args.compare_retrieval_backends,
        retrieval_backend_compare_order=args.retrieval_backend_compare_order,
        json_output_path=Path(args.json_output) if args.json_output else None,
    )
    print(report)
    print(f"Evaluation written to {Path(args.output).resolve()}")


def cmd_analyze_eval(args) -> None:
    report = analyze_eval_reports(
        before_path=Path(args.before),
        after_path=Path(args.after),
        output_path=Path(args.output) if args.output else None,
        trace_root=Path(args.trace_root) if args.trace_root else Path(args.workspace),
    )
    print(report)
    if args.output:
        print(f"Eval analysis written to {Path(args.output).resolve()}")


def cmd_eval_history(args) -> None:
    report = build_eval_history(
        run_specs=args.run,
        output_path=Path(args.output) if args.output else None,
    )
    print(report)
    if args.output:
        print(f"Eval history written to {Path(args.output).resolve()}")


def cmd_eval_failures(args) -> None:
    report = build_failure_dashboard(
        run_specs=args.run,
        output_path=Path(args.output) if args.output else None,
        trace_root=Path(args.trace_root) if args.trace_root else Path(args.workspace),
    )
    print(report)
    if args.output:
        print(f"Eval failure dashboard written to {Path(args.output).resolve()}")


def cmd_eval_stability(args) -> None:
    report = build_stability_report(
        run_specs=args.run,
        output_path=Path(args.output) if args.output else None,
    )
    print(report)
    if args.output:
        print(f"Eval stability report written to {Path(args.output).resolve()}")


def cmd_retrieval_stability(args) -> None:
    report = build_retrieval_stability_report(
        run_specs=args.run,
        output_path=Path(args.output) if args.output else None,
    )
    print(report)
    if args.output:
        print(f"Retrieval stability report written to {Path(args.output).resolve()}")


def cmd_retrieval_benchmark(args) -> None:
    backend_options = {"chunk_strategy": args.chunk_strategy}
    if args.backend == "hybrid":
        backend_options = {
            "chunk_strategy": args.chunk_strategy,
            "embedding_model": args.embedding_model,
            "cache_dir": args.cache_dir,
            "lexical_weight": args.lexical_weight,
            "semantic_weight": args.semantic_weight,
        }
    result = run_retrieval_benchmark(
        Path(args.judgments),
        backend=args.backend,
        backend_options=backend_options,
    )
    default_stem = (
        "RETRIEVAL_QUALITY_BASELINE"
        if args.backend == "lexical"
        else "RETRIEVAL_QUALITY_HYBRID"
    )
    output_path = Path(args.output or f"reports/{default_stem}.md")
    json_output_path = Path(args.json_output or f"reports/{default_stem}.json")
    report = write_retrieval_benchmark_outputs(
        result,
        output_path=output_path,
        json_output_path=json_output_path,
    )
    print(report)
    print(f"Retrieval benchmark written to {output_path.resolve()}")
    if not result["summary"]["quality_gate_passed"]:
        raise SystemExit("Retrieval quality gate failed.")


def cmd_trace_report(args) -> None:
    html = build_trace_report(Path(args.input), Path(args.output))
    print(f"Trace report written to {Path(args.output).resolve()}")
    print(f"Report size: {len(html)} chars")


def cmd_demo(args) -> None:
    result = run_demo(args.task, Path(args.output_dir), fresh=not args.keep_existing)
    print(result.report)
    print(f"Demo report written to {result.report_path.resolve()}")
    print(f"Trace report written to {result.html_path.resolve()}")


def cmd_docker_smoke(args) -> None:
    report = run_docker_smoke(
        Path(args.workspace),
        Path(args.output) if args.output else None,
    )
    print(report)
    if args.output:
        print(f"Docker smoke report written to {Path(args.output).resolve()}")


def cmd_mcp_server(args) -> None:
    server = build_mcp_sdk_server(
        Path(args.workspace),
        Path(args.trace),
        allow_write=args.allow_write,
        fresh_trace=args.fresh_trace,
        transport="mcp-sdk-v2-stdio",
    )
    serve_mcp_sdk_stdio(server)


def cmd_mcp_http(args) -> None:
    auth_token = None if args.no_auth else os.getenv(args.auth_token_env)
    if not auth_token and not args.no_auth:
        raise SystemExit(
            f"MCP HTTP requires a Bearer token in {args.auth_token_env}; "
            "use --no-auth only for explicit localhost development."
        )
    server = build_mcp_sdk_http_server(
        Path(args.workspace),
        Path(args.trace),
        allow_write=args.allow_write,
        fresh_trace=args.fresh_trace,
        host=args.host,
        port=args.port,
        endpoint=args.endpoint,
        auth_token=auth_token,
        allowed_origins=args.allow_origin,
        allow_remote=args.allow_remote,
        allow_unauthenticated=args.no_auth,
        session_ttl_seconds=args.session_ttl,
    )
    host, port = server.server_address[:2]
    host_text = host.decode() if isinstance(host, bytes) else str(host)
    print(
        f"MCP Streamable HTTP listening on http://{host_text}:{port}{server.config.endpoint}",
        flush=True,
    )
    print(
        "Authentication: "
        + (f"Bearer token from {args.auth_token_env}" if auth_token else "disabled for explicit localhost development"),
        flush=True,
    )
    serve_mcp_sdk_http(server)


def cmd_mcp_smoke(args) -> None:
    report = run_mcp_smoke(
        Path(args.workspace),
        Path(args.trace),
        Path(args.output),
        allow_write=args.allow_write,
        fresh_trace=args.fresh_trace,
    )
    print(report)
    print(f"MCP smoke report written to {Path(args.output).resolve()}")


def cmd_mcp_http_smoke(args) -> None:
    report = run_mcp_http_smoke(
        Path(args.workspace),
        Path(args.trace),
        Path(args.output),
        allow_write=args.allow_write,
        fresh_trace=args.fresh_trace,
    )
    print(report)
    print(f"MCP HTTP smoke report written to {Path(args.output).resolve()}")


def cmd_cross_feature_smoke(args) -> None:
    report = run_cross_feature_smoke(
        Path(args.workspace),
        Path(args.trace),
        Path(args.docker_report),
        Path(args.output),
        fresh_trace=args.fresh_trace,
        allow_model_download=args.allow_model_download,
    )
    print(report)
    print(f"Cross-feature report written to {Path(args.output).resolve()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mini Coding Agent Harness")
    parser.add_argument("--workspace", default=".", help="Repository workspace to inspect")
    parser.add_argument("--trace", default="trace.jsonl", help="JSONL trace output path")
    parser.add_argument("--fresh-trace", action="store_true", help="Delete the trace file before running")
    parser.add_argument("--allow-write", action="store_true", help="Allow tools to overwrite existing files")
    parser.add_argument(
        "--execution-backend",
        choices=["host", "docker"],
        help="Run shell, tests, and Python compilation on the host or in the configured Docker sandbox",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    challenge = sub.add_parser("challenge-eval", help="Separate public maintenance challenges with external acceptance")
    challenge.add_argument("--suite", default="benchmarks/challenges/suite.json")
    challenge.add_argument("--output-dir", required=True, help="New directory outside the suite")
    challenge.add_argument("--mode", choices=["validate", "agent"], default="validate")
    challenge.add_argument("--backend", choices=["host", "docker"], default="host")
    challenge.add_argument("--compare-backends", action="store_true", help="Actual agent ABBA lexical/hybrid order")
    challenge.add_argument("--max-turns", type=int, default=12)
    challenge.add_argument("--json-output", help="Portable result without raw pytest output")
    challenge.set_defaults(func=cmd_challenges)

    study = sub.add_parser("retrieval-study", help="Local ranking and document-cache cold/warm observations")
    study.add_argument("--judgments", default="benchmarks/retrieval-v2/judgments.json")
    study.add_argument("--include-hybrid", action="store_true", help="Offline-only paired forward/reverse orders")
    study.add_argument("--chunk-strategy", choices=["lines", "python"], default="python")
    study.add_argument("--repeats", type=int, default=3)
    study.add_argument("--output", default="artifacts/retrieval-study.json")
    study.set_defaults(func=cmd_retrieval_study)

    evidence = sub.add_parser("evidence-report", help="Measure temporal retrieval-to-read/edit path follow-up")
    evidence.add_argument("--trace-input", action="append", required=True)
    evidence.add_argument("--label", required=True, help="Explicit source and mode label")
    evidence.add_argument("--output", required=True)
    evidence.set_defaults(func=cmd_evidence_report)

    tools = sub.add_parser("tools", help="List registered tools")
    tools.set_defaults(func=cmd_tools)

    manual = sub.add_parser("manual", help="Manually call basic tools")
    manual.set_defaults(func=cmd_manual)

    inspect = sub.add_parser("inspect", help="Inspect the repository and write REVIEW.md")
    inspect.add_argument("--output", default="REVIEW.md", help="Review report path")
    inspect.set_defaults(func=cmd_inspect)

    trace_report = sub.add_parser("trace-report", help="Render a JSONL trace as an interactive self-contained HTML report")
    trace_report.add_argument("--input", default="trace.jsonl", help="Input JSONL trace path")
    trace_report.add_argument("--output", default="TRACE.html", help="Output HTML report path")
    trace_report.set_defaults(func=cmd_trace_report)

    demo = sub.add_parser("demo", help="Run a local portfolio demo without requiring a model API key")
    demo.add_argument("--task", default="python_bugfix", help="Demo task id")
    demo.add_argument("--output-dir", default="artifacts/demo", help="Directory for demo workspace and reports")
    demo.add_argument("--keep-existing", action="store_true", help="Reuse the existing demo workspace instead of resetting it")
    demo.set_defaults(func=cmd_demo)

    docker_smoke = sub.add_parser(
        "docker-smoke",
        help="Verify the configured Docker sandbox boundaries and write a report",
    )
    docker_smoke.add_argument(
        "--output",
        default="reports/DOCKER_SANDBOX_SMOKE.md",
        help="Docker smoke report path",
    )
    docker_smoke.set_defaults(func=cmd_docker_smoke)

    mcp_server = sub.add_parser("mcp-server", help="Expose registered tools over MCP stdio")
    mcp_server.set_defaults(func=cmd_mcp_server)

    mcp_http = sub.add_parser(
        "mcp-http",
        help="Expose registered tools over MCP Streamable HTTP with JSON responses",
    )
    mcp_http.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    mcp_http.add_argument("--port", type=int, default=8000, help="HTTP bind port")
    mcp_http.add_argument("--endpoint", default="/mcp", help="Single MCP HTTP endpoint path")
    mcp_http.add_argument(
        "--auth-token-env",
        default="HARNESS_MCP_AUTH_TOKEN",
        help="Environment variable containing the static Bearer token",
    )
    mcp_http.add_argument(
        "--allow-origin",
        action="append",
        help="Allowed browser Origin; repeat as needed (defaults to the bound localhost port)",
    )
    mcp_http.add_argument(
        "--session-ttl",
        type=int,
        default=3600,
        help="Idle session lifetime in seconds",
    )
    mcp_http.add_argument(
        "--allow-remote",
        action="store_true",
        help="Explicitly permit binding outside localhost; authentication remains required",
    )
    mcp_http.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable Bearer authentication for explicit localhost development only",
    )
    mcp_http.set_defaults(func=cmd_mcp_http)

    mcp_smoke = sub.add_parser("mcp-smoke", help="Run an in-process MCP protocol smoke test and write a report")
    mcp_smoke.add_argument("--output", default="reports/MCP_SMOKE.md", help="Smoke report path")
    mcp_smoke.set_defaults(func=cmd_mcp_smoke)

    mcp_http_smoke = sub.add_parser(
        "mcp-http-smoke",
        help="Run a localhost MCP Streamable HTTP security and parity smoke test",
    )
    mcp_http_smoke.add_argument(
        "--output",
        default="reports/MCP_HTTP_SMOKE.md",
        help="HTTP smoke report path",
    )
    mcp_http_smoke.set_defaults(func=cmd_mcp_http_smoke)

    cross_feature_smoke = sub.add_parser(
        "cross-feature-smoke",
        help="Validate Docker evidence plus a live hybrid retrieval call over MCP HTTP",
    )
    cross_feature_smoke.add_argument(
        "--docker-report",
        default="reports/DOCKER_SANDBOX_SMOKE.md",
        help="Passing Docker runtime report to inspect",
    )
    cross_feature_smoke.add_argument(
        "--output",
        default="reports/CROSS_FEATURE_VALIDATION.md",
        help="Combined validation report path",
    )
    cross_feature_smoke.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow the MiniLM preflight to download missing model files; default is cache-only",
    )
    cross_feature_smoke.set_defaults(func=cmd_cross_feature_smoke)

    ask = sub.add_parser("ask", help="Run the model-driven agent loop")
    ask.add_argument("prompt")
    ask.add_argument("--isolate", help="Create a new isolated session outside the source workspace")
    ask.add_argument("--run-db", default="artifacts/runs.sqlite3", help="Durable run database")
    ask.add_argument("--no-persist", action="store_true", help="Use an in-memory run only")
    ask.add_argument("--max-turns", type=int, default=8)
    _add_context_options(ask)
    ask.add_argument(
        "--retrieval",
        choices=["on", "auto", "off"],
        default="on",
        help="Always enable, conditionally gate, or disable retrieval preflight and model-facing schemas",
    )
    ask.add_argument(
        "--retrieval-backend",
        choices=["lexical", "hybrid"],
        default="lexical",
        help="Default ranking backend for retrieval tools and preflight",
    )
    ask.set_defaults(func=cmd_ask)

    resume = sub.add_parser("resume", help="Resume a durable run from its last checkpoint")
    resume.add_argument("run_id")
    resume.add_argument("--isolate", help="Resume using an existing isolated session")
    resume.add_argument("--run-db", default="artifacts/runs.sqlite3")
    resume.add_argument("--max-turns", type=int, default=8)
    _add_context_options(resume)
    resume.set_defaults(func=cmd_resume)

    for command, help_text in (
        ("workspace-create", "Copy a bounded source snapshot without model calls"),
        ("workspace-review", "Export an exact content-bound text review"),
        ("workspace-apply", "Interactively approve and apply an unchanged review"),
        ("workspace-recover", "Interactively roll back an interrupted application"),
    ):
        workspace_cmd = sub.add_parser(command, help=help_text)
        workspace_cmd.add_argument("session")
        if command == "workspace-apply":
            workspace_cmd.add_argument("--review", required=True, help="Full reviewed SHA-256 ID")
        workspace_cmd.set_defaults(func=cmd_workspace)

    runs = sub.add_parser("runs", help="List, inspect or export durable run records")
    runs.add_argument("--run-db", default="artifacts/runs.sqlite3")
    runs.add_argument("--run-id")
    runs.add_argument("--export", help="Write a portable JSONL run export")
    runs.set_defaults(func=cmd_runs)

    resolve = sub.add_parser("run-resolve", help="Record an inspected unknown tool outcome")
    resolve.add_argument("run_id")
    resolve.add_argument("call_id")
    resolve.add_argument("--run-db", default="artifacts/runs.sqlite3")
    resolve.add_argument("--result", required=True, help="Operator-verified outcome; never reexecutes")
    resolve.add_argument("--succeeded", action="store_true", help="Record a verified successful outcome")
    resolve.set_defaults(func=cmd_run_resolve)

    eval_cmd = sub.add_parser("eval", help="Run the harness evaluation suite")
    eval_cmd.add_argument("--output", default="EVAL.md", help="Evaluation report path")
    eval_cmd.add_argument("--json-output", help="Optional machine-readable JSON report path")
    eval_cmd.add_argument("--trace-dir", default="eval_runs", help="Directory for per-task traces")
    eval_cmd.add_argument(
        "--mode",
        choices=["scripted", "agent"],
        default="scripted",
        help="Evaluation mode: scripted deterministic runners or model-driven agent attempts",
    )
    eval_cmd.add_argument(
        "--task",
        dest="task_ids",
        action="append",
        help="Run one task id; repeat this option to run multiple selected tasks",
    )
    eval_cmd.add_argument(
        "--category",
        dest="categories",
        action="append",
        help="Run one task category; repeat this option to include multiple categories",
    )
    eval_cmd.add_argument(
        "--memory",
        choices=["on", "off"],
        default="on",
        help="Enable or disable workflow-memory support for evaluation reporting and agent runs",
    )
    eval_cmd.add_argument(
        "--context",
        choices=["on", "off"],
        default="on",
        help="Enable or disable context-compaction support for evaluation reporting and agent runs",
    )
    eval_cmd.add_argument(
        "--retrieval",
        choices=["on", "auto", "off"],
        default="on",
        help="Always enable, conditionally gate, or disable retrieval support for agent runs",
    )
    eval_cmd.add_argument(
        "--retrieval-backend",
        choices=["lexical", "hybrid"],
        default="lexical",
        help="Ranking backend used by retrieval tools and preflight",
    )
    eval_cmd.add_argument(
        "--compare",
        action="store_true",
        help="Run four memory/context configurations using the selected retrieval setting and write a comparison report",
    )
    eval_cmd.add_argument(
        "--compare-retrieval",
        action="store_true",
        help="Compare the selected on/auto retrieval strategy with retrieval-off using the same settings",
    )
    eval_cmd.add_argument(
        "--retrieval-compare-order",
        choices=["selected-first", "off-first"],
        default="selected-first",
        help="Execution order for paired retrieval comparisons",
    )
    eval_cmd.add_argument(
        "--compare-retrieval-backends",
        action="store_true",
        help="Compare lexical and hybrid ranking with the same retrieval strategy and tasks",
    )
    eval_cmd.add_argument(
        "--retrieval-backend-compare-order",
        choices=["lexical-first", "hybrid-first"],
        default="lexical-first",
        help="Execution order for paired lexical/hybrid comparisons",
    )
    eval_cmd.set_defaults(func=cmd_eval)

    analyze_eval = sub.add_parser("analyze-eval", help="Compare two JSON evaluation reports and summarize agent behavior changes")
    analyze_eval.add_argument("--before", required=True, help="Baseline JSON evaluation report path")
    analyze_eval.add_argument("--after", required=True, help="New JSON evaluation report path")
    analyze_eval.add_argument("--output", help="Optional Markdown analysis report path")
    analyze_eval.add_argument("--trace-root", help="Root used to resolve relative per-task trace paths")
    analyze_eval.set_defaults(func=cmd_analyze_eval)

    eval_history = sub.add_parser("eval-history", help="Build a Markdown trend report from multiple JSON evaluation reports")
    eval_history.add_argument(
        "--run",
        action="append",
        required=True,
        help="Evaluation JSON input, either PATH or LABEL=PATH; repeat in chronological order",
    )
    eval_history.add_argument("--output", help="Optional Markdown history report path")
    eval_history.set_defaults(func=cmd_eval_history)

    eval_failures = sub.add_parser("eval-failures", help="Aggregate failed eval tasks by failure mode")
    eval_failures.add_argument(
        "--run",
        action="append",
        required=True,
        help="Evaluation JSON input, either PATH or LABEL=PATH; repeat in chronological order",
    )
    eval_failures.add_argument("--output", help="Optional Markdown failure dashboard path")
    eval_failures.add_argument("--trace-root", help="Root used to resolve relative per-task trace paths")
    eval_failures.set_defaults(func=cmd_eval_failures)

    eval_stability = sub.add_parser("eval-stability", help="Measure repeated-run stability across JSON evaluation reports")
    eval_stability.add_argument(
        "--run",
        action="append",
        required=True,
        help="Evaluation JSON input, either PATH or LABEL=PATH; repeat for each same-suite run",
    )
    eval_stability.add_argument("--output", help="Optional Markdown stability report path")
    eval_stability.set_defaults(func=cmd_eval_stability)

    retrieval_stability = sub.add_parser(
        "retrieval-stability",
        help="Measure paired retrieval comparison stability across repeated JSON reports",
    )
    retrieval_stability.add_argument(
        "--run",
        action="append",
        required=True,
        help="Retrieval comparison JSON input, either PATH or LABEL=PATH; repeat for each paired run",
    )
    retrieval_stability.add_argument("--output", help="Optional Markdown stability report path")
    retrieval_stability.set_defaults(func=cmd_retrieval_stability)

    retrieval_benchmark = sub.add_parser(
        "retrieval-benchmark",
        help="Measure retrieval Recall@K and MRR over committed relevance judgments",
    )
    retrieval_benchmark.add_argument("--chunk-strategy", choices=["lines", "python"], default="lines")
    retrieval_benchmark.add_argument(
        "--judgments",
        default="benchmarks/retrieval/judgments.json",
        help="Retrieval corpus and relevance judgments JSON path",
    )
    retrieval_benchmark.add_argument(
        "--backend",
        choices=["lexical", "hybrid"],
        default="lexical",
        help="Retrieval backend to evaluate",
    )
    retrieval_benchmark.add_argument(
        "--output",
        help="Markdown benchmark report path; defaults by backend",
    )
    retrieval_benchmark.add_argument(
        "--json-output",
        help="Machine-readable benchmark report path; defaults by backend",
    )
    retrieval_benchmark.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Local Sentence Transformers model used by the hybrid backend",
    )
    retrieval_benchmark.add_argument(
        "--cache-dir",
        help="Optional document embedding cache directory",
    )
    retrieval_benchmark.add_argument(
        "--lexical-weight",
        type=float,
        default=0.35,
        help="Normalized lexical score weight for hybrid retrieval",
    )
    retrieval_benchmark.add_argument(
        "--semantic-weight",
        type=float,
        default=0.65,
        help="Normalized semantic score weight for hybrid retrieval",
    )
    retrieval_benchmark.set_defaults(func=cmd_retrieval_benchmark)

    return parser


def _add_context_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--context-budget", type=int, help="Estimated total input-token budget")
    parser.add_argument("--context-summary-budget", type=int, help="Estimated summary-token budget")
    parser.add_argument("--context-recent-turns", type=int, help="Complete recent turns to preserve")
    parser.add_argument(
        "--context-management", action=argparse.BooleanOptionalAction, default=None,
        help="Enable/disable budget compaction (resume inherits the saved choice)",
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.execution_backend:
        os.environ["HARNESS_EXECUTION_BACKEND"] = args.execution_backend
    args.func(args)


if __name__ == "__main__":
    main()
