from __future__ import annotations

from pathlib import Path

import pytest

from harness.evidence_metrics import summarize_evidence_use
from harness.retrieval import build_workspace_index, search_workspace
from harness.retrieval_benchmark import run_retrieval_benchmark
from harness.retrieval_study import run_retrieval_study

ROOT = Path(__file__).resolve().parents[1]
JUDGMENTS = ROOT / 'benchmarks/retrieval-v2/judgments.json'


def test_ast_chunks_preserve_decorators_methods_and_source_line_ranges(tmp_path):
    text = 'import os\n\n@decorate\ndef first():\n    return 1\n\nclass Client:\n    @property\n    def value(self):\n        return 2\n\nasync def last():\n    return 3\n'
    (tmp_path / 'sample.py').write_text(text)
    index = build_workspace_index(tmp_path, chunk_strategy='python', chunk_lines=20)
    assert len(index.chunks) == 5
    assert index.chunks[1].start_line == 3 and index.chunks[1].text.startswith('@decorate')
    assert index.chunks[3].text.startswith('    @property')
    assert '\n'.join(chunk.text for chunk in index.chunks).splitlines() == text.splitlines()
    for chunk in index.chunks:
        assert chunk.text == '\n'.join(text.splitlines()[chunk.start_line - 1:chunk.end_line])


def test_ast_fallback_and_long_function_bounds(tmp_path):
    (tmp_path / 'broken.py').write_text('def bad(:\n    pass\n')
    assert build_workspace_index(tmp_path, chunk_strategy='python').chunks
    (tmp_path / 'long.py').write_text('def long():\n' + '    pass\n' * 30)
    index = build_workspace_index(tmp_path, chunk_strategy='python', chunk_lines=5, overlap=1)
    assert all(chunk.end_line - chunk.start_line + 1 <= 5 for chunk in index.chunks)
    with pytest.raises(ValueError, match='chunk_strategy'):
        build_workspace_index(tmp_path, chunk_strategy='unknown')


def test_legacy_baseline_is_unchanged_and_v2_has_more_judgments():
    legacy = run_retrieval_benchmark(ROOT / 'benchmarks/retrieval/judgments.json')
    assert legacy['summary']['mrr'] == pytest.approx(0.8)
    result = run_retrieval_benchmark(JUDGMENTS, backend_options={'chunk_strategy': 'python'})
    assert result['summary']['case_count'] == 28
    assert result['summary']['quality_gate_passed']
    stress = next(case for case in result['cases'] if case['case_id'] == 'semantic_spreadsheet')
    assert stress['first_relevant_rank'] is None


def test_environment_can_enable_ast_without_changing_tool_schemas(tmp_path, monkeypatch):
    monkeypatch.setenv('HARNESS_RETRIEVAL_CHUNK_STRATEGY', 'python')
    (tmp_path / 'a.py').write_text('def alpha():\n    return 1\n')
    assert search_workspace(tmp_path, 'alpha')['index']['chunk_strategy'] == 'python'


def test_evidence_proxy_is_temporal_ignores_failures_and_verifier_reads():
    def event(tool, path, ok=True):
        return {'event': 'tool_call', 'data': {'tool': tool, 'args': {'path': path}, 'ok': ok}}
    events = [event('read_file', 'a.py'),
              {'event': 'agent_retrieval_preflight', 'data': {'ok': True, 'paths': ['a.py', 'b.py']}},
              event('read_file', 'a.py', False), event('edit_file', 'b.py'),
              {'event': 'eval_agent_verifier_start'}, event('read_file', 'a.py'),
              {'event': 'eval_agent_verifier_end'}]
    result = summarize_evidence_use(events)
    assert result['subsequently_read_paths'] == []
    assert result['subsequently_edited_paths'] == ['b.py']
    assert result['path_followup_ratio'] == 0.5
    assert summarize_evidence_use([])['path_followup_ratio'] is None


def test_study_runs_both_orders_with_fresh_cache_and_records_timing(tmp_path):
    calls = []

    def fake(workspace, query, **kwargs):
        calls.append(query)
        return {'matches': [{'path': 'inventory.py'}]}

    result = run_retrieval_study(JUDGMENTS, include_hybrid=True, repeats=1,
                                 search_functions={'lexical': fake, 'hybrid': fake})
    assert result['execution_orders'] == [['lexical', 'hybrid'], ['hybrid', 'lexical']]
    assert result['counterbalanced_complete'] and len(result['rows']) == 4
    assert all(row['cold_median_ms'] >= 0 and row['warm_median_ms'] >= 0 for row in result['rows'])
    # Fake ranking is explicitly a unit test, not a committed hybrid result.
    assert len(calls) == 28 * 3 * 4


def test_study_reports_missing_optional_hybrid_without_inventing_results(monkeypatch):
    monkeypatch.setattr('harness.retrieval_study.importlib.util.find_spec', lambda _: None)
    result = run_retrieval_study(JUDGMENTS, include_hybrid=True, repeats=1)
    assert result['unavailable_backends'] == ['hybrid']
    assert not result['counterbalanced_complete']
    assert [row['backend'] for row in result['rows']] == ['lexical']
    with pytest.raises(ValueError):
        run_retrieval_study(JUDGMENTS, repeats=0)
