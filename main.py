from __future__ import annotations

import argparse
from pathlib import Path

from harness.agent import run_agent
from harness.demo import run_demo
from harness.eval_analysis import analyze_eval_reports, build_eval_history
from harness.evaluation import run_evaluation
from harness.mcp_server import build_mcp_server, serve_stdio
from harness.mcp_smoke import run_mcp_smoke
from harness.review import inspect_repo
from harness.tools import build_registry
from harness.trace import TraceLogger
from harness.trace_viewer import build_trace_report


def make_registry(
    workspace: Path,
    trace_path: Path,
    fresh_trace: bool = False,
    allow_write: bool = False,
):
    if fresh_trace and trace_path.exists():
        trace_path.unlink()
    trace = TraceLogger(trace_path)
    trace.log("session_start", workspace=str(workspace.resolve()), allow_write=allow_write)
    return build_registry(workspace.resolve(), trace, allow_write=allow_write)


def cmd_tools(args) -> None:
    registry = make_registry(Path(args.workspace), Path(args.trace), args.fresh_trace, args.allow_write)
    print("\n".join(registry.names()))


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
    registry = make_registry(Path(args.workspace), Path(args.trace), args.fresh_trace, args.allow_write)
    print(run_agent(args.prompt, registry))
    print(f"Trace written to {Path(args.trace).resolve()}")


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
        retrieval_enabled=args.retrieval == "on",
        compare=args.compare,
        compare_retrieval=args.compare_retrieval,
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


def cmd_trace_report(args) -> None:
    html = build_trace_report(Path(args.input), Path(args.output))
    print(f"Trace report written to {Path(args.output).resolve()}")
    print(f"Report size: {len(html)} chars")


def cmd_demo(args) -> None:
    result = run_demo(args.task, Path(args.output_dir), fresh=not args.keep_existing)
    print(result.report)
    print(f"Demo report written to {result.report_path.resolve()}")
    print(f"Trace report written to {result.html_path.resolve()}")


def cmd_mcp_server(args) -> None:
    server = build_mcp_server(
        Path(args.workspace),
        Path(args.trace),
        allow_write=args.allow_write,
        fresh_trace=args.fresh_trace,
    )
    serve_stdio(server)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mini Coding Agent Harness")
    parser.add_argument("--workspace", default=".", help="Repository workspace to inspect")
    parser.add_argument("--trace", default="trace.jsonl", help="JSONL trace output path")
    parser.add_argument("--fresh-trace", action="store_true", help="Delete the trace file before running")
    parser.add_argument("--allow-write", action="store_true", help="Allow tools to overwrite existing files")

    sub = parser.add_subparsers(dest="command", required=True)

    tools = sub.add_parser("tools", help="List registered tools")
    tools.set_defaults(func=cmd_tools)

    manual = sub.add_parser("manual", help="Manually call basic tools")
    manual.set_defaults(func=cmd_manual)

    inspect = sub.add_parser("inspect", help="Inspect the repository and write REVIEW.md")
    inspect.add_argument("--output", default="REVIEW.md", help="Review report path")
    inspect.set_defaults(func=cmd_inspect)

    trace_report = sub.add_parser("trace-report", help="Render a JSONL trace as a static HTML report")
    trace_report.add_argument("--input", default="trace.jsonl", help="Input JSONL trace path")
    trace_report.add_argument("--output", default="TRACE.html", help="Output HTML report path")
    trace_report.set_defaults(func=cmd_trace_report)

    demo = sub.add_parser("demo", help="Run a local portfolio demo without requiring a model API key")
    demo.add_argument("--task", default="python_bugfix", help="Demo task id")
    demo.add_argument("--output-dir", default="artifacts/demo", help="Directory for demo workspace and reports")
    demo.add_argument("--keep-existing", action="store_true", help="Reuse the existing demo workspace instead of resetting it")
    demo.set_defaults(func=cmd_demo)

    mcp_server = sub.add_parser("mcp-server", help="Expose registered tools over MCP stdio")
    mcp_server.set_defaults(func=cmd_mcp_server)

    mcp_smoke = sub.add_parser("mcp-smoke", help="Run an in-process MCP protocol smoke test and write a report")
    mcp_smoke.add_argument("--output", default="reports/MCP_SMOKE.md", help="Smoke report path")
    mcp_smoke.set_defaults(func=cmd_mcp_smoke)

    ask = sub.add_parser("ask", help="Run the model-driven agent loop")
    ask.add_argument("prompt")
    ask.set_defaults(func=cmd_ask)

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
        choices=["on", "off"],
        default="on",
        help="Enable or disable context-pack retrieval support for evaluation reporting and agent runs",
    )
    eval_cmd.add_argument(
        "--compare",
        action="store_true",
        help="Run four memory/context configurations using the selected retrieval setting and write a comparison report",
    )
    eval_cmd.add_argument(
        "--compare-retrieval",
        action="store_true",
        help="Run retrieval-on and retrieval-off configurations using the selected memory/context settings",
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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
