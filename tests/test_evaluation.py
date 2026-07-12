from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.evaluation import EvalTask, _agent_eval_max_turns, build_agent_eval_prompt, run_evaluation


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
    assert "Tasks: **35**" in report
    assert "Success rate: **100.00%**" in report
    assert "Average tool calls:" in report
    assert "Input tokens: **0**" in report
    assert "Output tokens: **0**" in report
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
    assert (tmp_path / "EVAL.md").exists()
    assert (tmp_path / "eval_runs" / "syntax_check.jsonl").exists()
    assert (tmp_path / "eval_runs" / "read_file_line_range.jsonl").exists()
    assert (tmp_path / "eval_runs" / "context_pack_retrieval.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_symbol_retrieval.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_sensitive_path_filter.jsonl").exists()
    assert (tmp_path / "eval_runs" / "rag_read_plan_generation.jsonl").exists()
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
    assert copied_memory.exists()
    eval_json = json.loads((tmp_path / "EVAL.json").read_text(encoding="utf-8"))
    assert eval_json["summary"]["task_count"] == 35
    assert eval_json["summary"]["passed"] == 35
    assert eval_json["summary"]["retrieval_enabled"] is True
    assert "tool_counts" in eval_json["summary"]
    assert eval_json["tasks"][0]["task_id"] == "syntax_check"
    assert eval_json["tasks"][0]["retrieval_enabled"] is True
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


def test_build_agent_eval_prompt_constrains_tool_exploration() -> None:
    task = EvalTask(
        "python_add_tests",
        "code_maintenance",
        "Add missing pytest coverage for an existing Python helper.",
        lambda registry: True,
    )

    prompt = build_agent_eval_prompt(task, "Support details.")

    assert "Start with `todo_write`" in prompt
    assert "Avoid broad shell or Git exploration" in prompt
    assert "make the first file change by turn 6" in prompt
    assert "create a focused `tests/test_*.py` file" in prompt
    assert "Support details." in prompt


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
    assert "reread the changed document" in prompt


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
    assert "Tasks: **3**" in report
    assert "multi_file_service_fix" in report
    assert "multi_file_api_contract_fix" in report
    assert "package_order_total_fix" in report
    assert "python_bugfix" not in report
    assert (tmp_path / "eval_runs" / "multi_file_service_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "multi_file_api_contract_fix.jsonl").exists()
    assert (tmp_path / "eval_runs" / "package_order_total_fix.jsonl").exists()
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
    assert "Avg context_pack" in report
    assert "Avg read_file" in report
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
    assert "average_context_pack_calls" in compare_json["comparison"][0]
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
    assert "Avg context_pack" in report
    assert "Avg read_file" in report
    assert "retrieval-on" in report
    assert "retrieval-off" in report
    assert (tmp_path / "eval_runs" / "compare_retrieval" / "retrieval-on" / "syntax_check.jsonl").exists()
    assert (tmp_path / "eval_runs" / "compare_retrieval" / "retrieval-off" / "syntax_check.jsonl").exists()
    compare_json = json.loads((tmp_path / "RETRIEVAL_COMPARE.json").read_text(encoding="utf-8"))
    assert len(compare_json["comparison"]) == 2
    assert compare_json["comparison"][0]["retrieval_enabled"] is True
    assert compare_json["comparison"][1]["retrieval_enabled"] is False


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
