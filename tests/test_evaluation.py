from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.evaluation import (
    EvalTask,
    _agent_eval_max_turns,
    build_agent_eval_prompt,
    build_agent_support_prompt,
    run_evaluation,
    trace_metrics,
)
from harness.tools import build_registry
from harness.trace import TraceLogger


def test_run_evaluation_writes_report_and_task_traces(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    (skill_dir / "fixture-workflow.md").write_text("# Fixture Workflow\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        json_output_path=tmp_path / "EVAL.json",
    )

    assert "# Evaluation Report" in report
    assert "Mode: **scripted**" in report
    assert "Memory: **enabled**" in report
    assert "Context compaction: **enabled**" in report
    assert "Context retrieval: **enabled**" in report
    assert "Categories: **agent_loop, code_maintenance, code_quality, configuration, documentation, memory, multi_file, recovery, retrieval, security, tests, trace**" in report
    assert "Tasks: **40**" in report
    assert "Success rate: **100.00%**" in report
    assert "Average tool calls:" in report
    assert "Input tokens: **0**" in report
    assert "Output tokens: **0**" in report
    assert "Average preflight evidence chars (raw -> injected):" in report
    assert "Estimated model cost: **$0.000000**" in report
    assert "Tool-call mix:" in report
    assert "edit_match_failed" in report
    assert "python_bugfix" in report
    assert "python_add_tests" in report
    assert "semantic_retry_plan" in report
    assert "read_file_line_range" in report
    assert "context_pack_retrieval" in report
    assert "rag_symbol_retrieval" in report
    assert "rag_sensitive_path_filter" in report
    assert "rag_read_plan_generation" in report
    assert "rag_retrieve_then_read" in report
    assert "mcp_rag_search_smoke" in report
    assert "trace_html_report" in report
    assert "agent_loop_simulation" in report
    assert "memory_relevance_ranking" in report
    assert "readme_update" in report
    assert "python_import_fix" in report
    assert "config_default_fix" in report
    assert "json_config_update" in report
    assert "cli_validation_fix" in report
    assert "env_default_fix" in report
    assert "csv_parser_fix" in report
    assert "date_format_fix" in report
    assert "pagination_off_by_one" in report
    assert "secret_redaction_fix" in report
    assert "shell_no_shell_execution" in report
    assert "permission_policy_report" in report
    assert "path_normalization_fix" in report
    assert "dependency_pin_update" in report
    assert "mutable_default_fix" in report
    assert "multi_file_service_fix" in report
    assert "multi_file_api_contract_fix" in report
    assert "package_order_total_fix" in report
    assert "nested_package_export_fix" in report
    assert "config_precedence_integration_fix" in report
    assert "dependency_compatibility_fix" in report
    assert "nested_plugin_registry_fix" in report
    assert (tmp_path / "EVAL.md").exists()
    assert (tmp_path / "eval_runs" / "syntax_check.jsonl").exists()
    assert (tmp_path / "eval_runs" / "read_file_line_range.jsonl").exists()
    assert (tmp_path / "eval_runs" / "context_pack_retrieval.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_symbol_retrieval.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_sensitive_path_filter.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_read_plan_generation.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_retrieve_then_read.jsonl").exists()
    assert (tmp_path / "eval_runs" / "mcp_rag_search_smoke.jsonl").exists()
    assert (tmp_path / "eval_runs" / "trace_html_report.jsonl").exists()
    assert (tmp_path / "eval_runs" / "agent_loop_simulation.jsonl").exists()
    assert (tmp_path / "eval_runs" / "error_recovery.jsonl").exists()
    assert (tmp_path / "eval_runs" / "semantic_retry_plan.jsonl").exists()
    assert (tmp_path / "eval_runs" / "memory_relevance_ranking.jsonl").exists()
    assert (tmp_path / "eval_runs" / "python_bugfix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "python_add_tests.jsonl").exists()
    assert (tmp_path / "eval_runs" / "readme_update.jsonl").exists()
    assert (tmp_path / "eval_runs" / "python_import_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "config_default_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "json_config_update.jsonl").exists()
    assert (tmp_path / "eval_runs" / "cli_validation_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "env_default_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "csv_parser_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "date_format_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "pagination_off_by_one.jsonl").exists()
    assert (tmp_path / "eval_runs" / "secret_redaction_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "shell_no_shell_execution.jsonl").exists()
    assert (tmp_path / "eval_runs" / "permission_policy_report.jsonl").exists()
    assert (tmp_path / "eval_runs" / "path_normalization_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "dependency_pin_update.jsonl").exists()
    assert (tmp_path / "eval_runs" / "mutable_default_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "multi_file_service_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "multi_file_api_contract_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "package_order_total_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "nested_package_export_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "config_precedence_integration_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "dependency_compatibility_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "nested_plugin_registry_fix.jsonl").exists()
    fixed_code = tmp_path / "eval_runs" / "workspaces" / "python_bugfix" / "calculator.py"
    added_test = tmp_path / "eval_runs" / "workspaces" / "python_add_tests" / "tests" / "test_string_utils.py"
    updated_readme = tmp_path / "eval_runs" / "workspaces" / "readme_update" / "README.md"
    fixed_import = tmp_path / "eval_runs" / "workspaces" / "python_import_fix" / "app.py"
    fixed_config = tmp_path / "eval_runs" / "workspaces" / "config_default_fix" / "settings.py"
    fixed_json = tmp_path / "eval_runs" / "workspaces" / "json_config_update" / "settings.json"
    fixed_cli = tmp_path / "eval_runs" / "workspaces" / "cli_validation_fix" / "cli.py"
    fixed_env = tmp_path / "eval_runs" / "workspaces" / "env_default_fix" / "env_config.py"
    fixed_csv = tmp_path / "eval_runs" / "workspaces" / "csv_parser_fix" / "csv_utils.py"
    fixed_date = tmp_path / "eval_runs" / "workspaces" / "date_format_fix" / "reporting.py"
    fixed_pagination = tmp_path / "eval_runs" / "workspaces" / "pagination_off_by_one" / "pagination.py"
    fixed_secret = tmp_path / "eval_runs" / "workspaces" / "secret_redaction_fix" / "log_filter.py"
    fixed_path = tmp_path / "eval_runs" / "workspaces" / "path_normalization_fix" / "path_utils.py"
    fixed_dependency = tmp_path / "eval_runs" / "workspaces" / "dependency_pin_update" / "requirements.txt"
    fixed_mutable_default = tmp_path / "eval_runs" / "workspaces" / "mutable_default_fix" / "collector.py"
    fixed_service = tmp_path / "eval_runs" / "workspaces" / "multi_file_service_fix" / "service.py"
    fixed_repository = tmp_path / "eval_runs" / "workspaces" / "multi_file_service_fix" / "repository.py"
    fixed_handler = tmp_path / "eval_runs" / "workspaces" / "multi_file_api_contract_fix" / "handlers.py"
    fixed_response = tmp_path / "eval_runs" / "workspaces" / "multi_file_api_contract_fix" / "responses.py"
    fixed_cart = tmp_path / "eval_runs" / "workspaces" / "package_order_total_fix" / "src" / "shop" / "cart.py"
    fixed_pricing = tmp_path / "eval_runs" / "workspaces" / "package_order_total_fix" / "src" / "shop" / "pricing.py"
    fixed_catalog_export = tmp_path / "eval_runs" / "workspaces" / "nested_package_export_fix" / "src" / "acme_store" / "catalog" / "__init__.py"
    fixed_catalog_api = tmp_path / "eval_runs" / "workspaces" / "nested_package_export_fix" / "src" / "acme_store" / "api.py"
    fixed_settings = tmp_path / "eval_runs" / "workspaces" / "config_precedence_integration_fix" / "src" / "jobrunner" / "settings.py"
    fixed_worker = tmp_path / "eval_runs" / "workspaces" / "config_precedence_integration_fix" / "src" / "jobrunner" / "worker.py"
    fixed_project = tmp_path / "eval_runs" / "workspaces" / "dependency_compatibility_fix" / "pyproject.toml"
    fixed_compat = tmp_path / "eval_runs" / "workspaces" / "dependency_compatibility_fix" / "src" / "gateway" / "compat.py"
    fixed_plugin_registry = tmp_path / "eval_runs" / "workspaces" / "nested_plugin_registry_fix" / "src" / "platform_app" / "plugins" / "registry.py"
    copied_memory = tmp_path / "eval_runs" / "workspaces" / "python_bugfix" / "skills" / "fixture-workflow.md"
    assert "return a + b" in fixed_code.read_text(encoding="utf-8")
    assert "test_normalize_title" in added_test.read_text(encoding="utf-8")
    assert "python -m pytest" in updated_readme.read_text(encoding="utf-8")
    assert "add_numbers" in fixed_import.read_text(encoding="utf-8")
    assert "DEBUG = False" in fixed_config.read_text(encoding="utf-8")
    assert '"mode": "prod"' in fixed_json.read_text(encoding="utf-8")
    assert "limit must be positive" in fixed_cli.read_text(encoding="utf-8")
    assert "https://api.example.com" in fixed_env.read_text(encoding="utf-8")
    assert "item.strip()" in fixed_csv.read_text(encoding="utf-8")
    assert "date.isoformat()" in fixed_date.read_text(encoding="utf-8")
    assert "page_size - 1" in fixed_pagination.read_text(encoding="utf-8")
    assert "[REDACTED]" in fixed_secret.read_text(encoding="utf-8")
    assert "strip('/')" in fixed_path.read_text(encoding="utf-8")
    assert "requests==2.32.0" in fixed_dependency.read_text(encoding="utf-8")
    assert "bucket is None" in fixed_mutable_default.read_text(encoding="utf-8")
    assert "inactive" in fixed_service.read_text(encoding="utf-8")
    assert "user not found" in fixed_repository.read_text(encoding="utf-8")
    assert "kind" in fixed_handler.read_text(encoding="utf-8")
    assert "status=400" in fixed_response.read_text(encoding="utf-8")
    assert "max(discounted_subtotal(items) - discount, 0)" in fixed_cart.read_text(encoding="utf-8")
    assert "item.get('quantity', 1)" in fixed_pricing.read_text(encoding="utf-8")
    assert "from .models import Product" in fixed_catalog_export.read_text(encoding="utf-8")
    assert "'available': product.is_available()" in fixed_catalog_api.read_text(encoding="utf-8")
    assert "env.get('JOB_TIMEOUT'" in fixed_settings.read_text(encoding="utf-8")
    assert "resolve_timeout(config, env)" in fixed_worker.read_text(encoding="utf-8")
    assert "httpx>=0.28,<0.29" in fixed_project.read_text(encoding="utf-8")
    assert "SUPPORTED_HTTPX_MINOR = 28" in fixed_compat.read_text(encoding="utf-8")
    assert "duplicate plugin slug" in fixed_plugin_registry.read_text(encoding="utf-8")
    assert copied_memory.exists()
    eval_json = json.loads((tmp_path / "EVAL.json").read_text(encoding="utf-8"))
    assert eval_json["summary"]["task_count"] == 40
    assert eval_json["summary"]["passed"] == 40
    assert eval_json["summary"]["retrieval_enabled"] is True
    assert eval_json["summary"]["average_preflight_raw_chars"] > 0
    assert eval_json["summary"]["average_preflight_injected_chars"] > 0
    assert "tool_counts" in eval_json["summary"]
    assert eval_json["tasks"][0]["task_id"] == "syntax_check"
    assert eval_json["tasks"][0]["retrieval_enabled"] is True
    assert eval_json["tasks"][0]["preflight_raw_chars"] == 0
    assert eval_json["tasks"][0]["preflight_injected_chars"] == 0
    assert eval_json["tasks"][0]["tool_counts"]["run_py_compile"] == 1
    assert eval_json["tasks"][0]["trace_path"].endswith("syntax_check.jsonl")


def test_agent_eval_max_turns_reads_environment(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_EVAL_MAX_TURNS", raising=False)
    assert _agent_eval_max_turns() == 12

    monkeypatch.setenv("AGENT_EVAL_MAX_TURNS", "16")
    assert _agent_eval_max_turns() == 16

    monkeypatch.setenv("AGENT_EVAL_MAX_TURNS", "invalid")
    assert _agent_eval_max_turns() == 12

    monkeypatch.setenv("AGENT_EVAL_MAX_TURNS", "0")
    assert _agent_eval_max_turns() == 1


def test_trace_metrics_classifies_terminal_model_request_failure(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        '{"event": "agent_response", "data": {"usage": {"input_tokens": 10, "output_tokens": 2}}}\n'
        '{"event": "model_request_retry", "data": {"attempt": 1, "max_retries": 4}}\n'
        '{"event": "agent_error", "data": {"error": "HTTPError: HTTP Error 503"}}\n',
        encoding="utf-8",
    )

    metrics = trace_metrics(trace_path)

    assert metrics["input_tokens"] == 10
    assert metrics["output_tokens"] == 2
    assert metrics["failure_categories"] == ["model_request_failed"]


def test_trace_metrics_collects_retrieval_preflight_evidence_chars(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        '{"event": "agent_retrieval_gate", "data": '
        '{"activated": true, "exposed_retrieval_schema_count": 5}}\n'
        '{"event": "agent_retrieval_preflight", "data": '
        '{"raw_evidence_chars": 3200, "injected_chars": 1200}}\n',
        encoding="utf-8",
    )

    metrics = trace_metrics(trace_path)

    assert metrics["preflight_raw_chars"] == 3200
    assert metrics["preflight_injected_chars"] == 1200
    assert metrics["retrieval_gate_evaluated"] is True
    assert metrics["retrieval_activated"] is True
    assert metrics["retrieval_schema_count"] == 5


def test_build_agent_eval_prompt_constrains_tool_exploration() -> None:
    task = EvalTask(
        "python_add_tests",
        "code_maintenance",
        "Add missing pytest coverage for an existing Python helper.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "Start with `todo_write`" in prompt
    assert "Prefer `retrieve_then_read`" in prompt
    assert "Avoid broad shell or Git exploration" in prompt
    assert "make the first file change by turn 6" in prompt
    assert "create a focused `tests/test_*.py` file" in prompt
    assert "Support details." in prompt


def test_auto_retrieval_support_prompt_matches_resolved_on_or_off_state(tmp_path: Path) -> None:
    registry = build_registry(
        tmp_path,
        TraceLogger(tmp_path / "trace.jsonl"),
        allow_write=True,
    )

    auto_off = build_agent_support_prompt(
        registry,
        memory_enabled=False,
        context_enabled=True,
        retrieval_enabled=True,
        retrieval_mode="auto",
        retrieval_active=False,
    )
    forced_off = build_agent_support_prompt(
        registry,
        memory_enabled=False,
        context_enabled=True,
        retrieval_enabled=False,
        retrieval_mode="off",
        retrieval_active=False,
    )
    auto_on = build_agent_support_prompt(
        registry,
        memory_enabled=False,
        context_enabled=True,
        retrieval_enabled=True,
        retrieval_mode="auto",
        retrieval_active=True,
    )
    forced_on = build_agent_support_prompt(
        registry,
        memory_enabled=False,
        context_enabled=True,
        retrieval_enabled=True,
        retrieval_mode="on",
        retrieval_active=True,
    )

    assert auto_off == forced_off
    assert auto_on == forced_on


def test_build_agent_eval_prompt_guides_readme_tasks_to_readme() -> None:
    task = EvalTask(
        "readme_update",
        "documentation",
        "Update a README placeholder with concrete pytest usage text.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "read `README.md` directly" in prompt
    assert "do not inspect Git history" in prompt
    assert "concrete executable command" in prompt
    assert "do not inspect tests, shell, Git, or memories" in prompt
    assert "replace exactly `Usage: TODO` with `Usage: run python -m pytest.`" in prompt
    assert "reread the changed document" in prompt


def test_build_agent_eval_prompt_guides_context_compaction_to_readme() -> None:
    task = EvalTask(
        "context_compaction",
        "trace",
        "Create todos, read README.md, and summarize the trace with compact_context.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "call `todo_write`, then `read_file` on `README.md`, then `compact_context`" in prompt
    assert "compacted summary mentions `README.md`" in prompt


def test_build_agent_eval_prompt_guides_retry_plan_failure() -> None:
    task = EvalTask(
        "semantic_retry_plan",
        "recovery",
        "Trigger edit_file on sample.txt with old_text=\"old\" so the repeated text fails, then produce an ordered retry_plan.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "call `edit_file` on `sample.txt` with `old_text=\"old\"` first" in prompt
    assert "classified as `edit_match_failed`" in prompt
    assert "Then call `retry_plan`" in prompt


def test_build_agent_eval_prompt_guides_error_recovery_directly() -> None:
    task = EvalTask(
        "error_recovery",
        "recovery",
        "Call edit_file on sample.txt with old_text=\"old\" so the repeated text fails, then classify the failure with recover_errors.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "do not explore with shell, Git, list_python_files, or path probes" in prompt
    assert "First call `edit_file` on `sample.txt` with `old_text=\"old\"` and `new_text=\"new\"`" in prompt
    assert "the edit must fail as `edit_match_failed`" in prompt
    assert "Then call `recover_errors`" in prompt


def test_pytest_ignores_generated_artifacts() -> None:
    pytest_ini = Path(__file__).parents[1] / "pytest.ini"
    text = pytest_ini.read_text(encoding="utf-8")

    assert "artifacts" in text


def test_run_evaluation_can_select_tasks(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
    )

    assert "Mode: **scripted**" in report
    assert "Tasks: **1**" in report
    assert "Input tokens: **0**" in report
    assert "syntax_check" in report
    assert "pytest_suite" not in report
    assert (tmp_path / "eval_runs" / "syntax_check.jsonl").exists()
    assert not (tmp_path / "eval_runs" / "pytest_suite.jsonl").exists()


def test_run_evaluation_can_select_categories(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        categories=["multi_file"],
    )

    assert "Categories: **multi_file**" in report
    assert "Tasks: **5**" in report
    assert "multi_file_service_fix" in report
    assert "multi_file_api_contract_fix" in report
    assert "package_order_total_fix" in report
    assert "nested_package_export_fix" in report
    assert "nested_plugin_registry_fix" in report
    assert "python_bugfix" not in report
    assert (tmp_path / "eval_runs" / "multi_file_service_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "multi_file_api_contract_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "package_order_total_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "nested_package_export_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "nested_plugin_registry_fix.jsonl").exists()
    assert not (tmp_path / "eval_runs" / "python_bugfix.jsonl").exists()


def test_run_evaluation_rejects_unknown_categories(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown eval category"):
        run_evaluation(
            workspace=tmp_path,
            output_path=tmp_path / "EVAL.md",
            trace_dir=tmp_path / "eval_runs",
            categories=["missing_category"],
        )


def test_run_evaluation_reports_memory_context_switches(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        memory_enabled=False,
        context_enabled=False,
        retrieval_enabled=False,
    )

    assert "Memory: **disabled**" in report
    assert "Context compaction: **disabled**" in report
    assert "Context retrieval: **disabled**" in report
    assert "Tasks: **1**" in report


def test_scripted_retrieval_off_keeps_context_pack_task_deterministic(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["context_pack_retrieval"],
        retrieval_enabled=False,
    )

    assert "Context retrieval: **disabled**" in report
    assert "Passed: **1**" in report
    assert "context_pack_retrieval | trace | pass" in report


def test_retrieval_mode_off_overrides_legacy_enabled_flag(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "EVAL.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        retrieval_enabled=True,
        retrieval_mode="off",
        json_output_path=tmp_path / "EVAL.json",
    )

    payload = json.loads((tmp_path / "EVAL.json").read_text(encoding="utf-8"))
    assert payload["summary"]["retrieval_enabled"] is False
    assert payload["summary"]["retrieval_mode"] == "off"


def test_run_evaluation_comparison_report(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "COMPARE.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        compare=True,
        retrieval_enabled=False,
        json_output_path=tmp_path / "COMPARE.json",
    )

    assert "# Evaluation Comparison Report" in report
    assert "Input Tokens" in report
    assert "Est. Cost" in report
    assert "Context Retrieval" in report
    assert "Avg retrieve_then_read" in report
    assert "Avg context_pack" in report
    assert "Avg read_file" in report
    assert "Avg Preflight Raw Chars" in report
    assert "Avg Preflight Injected Chars" in report
    assert "Retrieval Strategy" in report
    assert "Activation Rate" in report
    assert "Avg Retrieval Schemas" in report
    assert "disabled" in report
    assert "memory-on_context-on" in report
    assert "memory-off_context-on" in report
    assert "memory-on_context-off" in report
    assert "memory-off_context-off" in report
    assert "1/1" in report
    assert (tmp_path / "eval_runs" / "compare" / "memory-on_context-on" / "syntax_check.jsonl").exists()
    compare_json = json.loads((tmp_path / "COMPARE.json").read_text(encoding="utf-8"))
    assert len(compare_json["comparison"]) == 4
    assert compare_json["comparison"][0]["task_count"] == 1
    assert compare_json["comparison"][0]["retrieval_enabled"] is False
    assert "average_retrieve_then_read_calls" in compare_json["comparison"][0]
    assert "average_context_pack_calls" in compare_json["comparison"][0]
    assert "average_preflight_raw_chars" in compare_json["comparison"][0]
    assert "average_preflight_injected_chars" in compare_json["comparison"][0]
    assert "tool_counts" in compare_json["comparison"][0]


def test_run_retrieval_comparison_report(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "RETRIEVAL_COMPARE.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        compare_retrieval=True,
        json_output_path=tmp_path / "RETRIEVAL_COMPARE.json",
    )

    assert "# Evaluation Comparison Report" in report
    assert "Context Retrieval" in report
    assert "Avg retrieve_then_read" in report
    assert "Avg context_pack" in report
    assert "Avg read_file" in report
    assert "retrieval-on" in report
    assert "retrieval-off" in report
    assert (tmp_path / "eval_runs" / "compare_retrieval" / "retrieval-on" / "syntax_check.jsonl").exists()
    assert (tmp_path / "eval_runs" / "compare_retrieval" / "retrieval-off" / "syntax_check.jsonl").exists()
    compare_json = json.loads((tmp_path / "RETRIEVAL_COMPARE.json").read_text(encoding="utf-8"))
    assert compare_json["comparison_kind"] == "retrieval"
    assert compare_json["execution_order"] == ["retrieval-on", "retrieval-off"]
    assert compare_json["selected_retrieval_mode"] == "on"
    assert len(compare_json["comparison"]) == 2
    assert compare_json["comparison"][0]["retrieval_enabled"] is True
    assert compare_json["comparison"][0]["retrieval_mode"] == "on"
    assert compare_json["comparison"][1]["retrieval_enabled"] is False
    assert compare_json["comparison"][1]["retrieval_mode"] == "off"


def test_auto_retrieval_comparison_uses_auto_and_off_labels(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "RETRIEVAL_AUTO_COMPARE.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        retrieval_mode="auto",
        compare_retrieval=True,
        json_output_path=tmp_path / "RETRIEVAL_AUTO_COMPARE.json",
    )

    assert "retrieval-auto" in report
    assert "retrieval-off" in report
    compare_json = json.loads(
        (tmp_path / "RETRIEVAL_AUTO_COMPARE.json").read_text(encoding="utf-8")
    )
    assert compare_json["comparison"][0]["retrieval_mode"] == "auto"
    assert compare_json["comparison"][1]["retrieval_mode"] == "off"
    assert compare_json["execution_order"] == ["retrieval-auto", "retrieval-off"]


def test_retrieval_comparison_can_run_off_first(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    report = run_evaluation(
        workspace=tmp_path,
        output_path=tmp_path / "RETRIEVAL_AUTO_COMPARE.md",
        trace_dir=tmp_path / "eval_runs",
        task_ids=["syntax_check"],
        retrieval_mode="auto",
        compare_retrieval=True,
        retrieval_compare_order="off-first",
        json_output_path=tmp_path / "RETRIEVAL_AUTO_COMPARE.json",
    )

    assert "retrieval-auto" in report
    compare_json = json.loads(
        (tmp_path / "RETRIEVAL_AUTO_COMPARE.json").read_text(encoding="utf-8")
    )
    assert compare_json["execution_order"] == ["retrieval-off", "retrieval-auto"]
    assert compare_json["comparison"][0]["retrieval_mode"] == "off"
    assert compare_json["comparison"][1]["retrieval_mode"] == "auto"


def test_retrieval_comparison_rejects_unknown_execution_order(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="comparison order"):
        run_evaluation(
            workspace=tmp_path,
            output_path=tmp_path / "RETRIEVAL_AUTO_COMPARE.md",
            trace_dir=tmp_path / "eval_runs",
            task_ids=["syntax_check"],
            retrieval_mode="auto",
            compare_retrieval=True,
            retrieval_compare_order="random",
        )


def test_run_evaluation_rejects_two_comparison_modes(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    with pytest.raises(ValueError, match="compare"):
        run_evaluation(
            workspace=tmp_path,
            output_path=tmp_path / "COMPARE.md",
            trace_dir=tmp_path / "eval_runs",
            task_ids=["syntax_check"],
            compare=True,
            compare_retrieval=True,
        )
