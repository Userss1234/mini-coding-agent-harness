from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from harness.challenge_eval import (
    AcceptanceDockerExecutor,
    load_suite,
    run_challenges,
    verify_submission,
)

SUITE = Path(__file__).resolve().parents[1] / 'benchmarks/challenges/suite.json'


def test_reference_validation_rejects_all_baselines_and_accepts_all_fixes(tmp_path):
    result = run_challenges(SUITE, tmp_path / 'run')
    assert result['passed'] == 3 and result['protected_inputs_unchanged']
    assert result['interpretation'] == 'Reference validation, not an agent score'
    assert sum(row['verdict']['test_cases'] for row in result['rows']) == 17
    for row in result['rows']:
        assert row['baseline']['returncode'] == 1 and not row['baseline']['passed']
        assert row['baseline']['test_cases'] == row['verdict']['test_cases']
        assert row['verdict']['acceptance_unchanged']
    assert not list((tmp_path / 'run').rglob('test_*.py'))


def test_submission_cannot_change_acceptance_or_add_configuration(tmp_path):
    root = SUITE.parent
    task = load_suite(SUITE)['tasks'][0]
    candidate = tmp_path / 'candidate'
    shutil.copytree(root / 'reference' / task['id'], candidate)
    (candidate / 'conftest.py').write_text('def pytest_collection_modifyitems(items): items.clear()')
    verdict = verify_submission(root, task, candidate, backend='host')
    assert not verdict['passed'] and 'unauthorized' in verdict['reason']


def test_early_success_exit_without_test_results_does_not_pass(tmp_path):
    task = load_suite(SUITE)['tasks'][2]
    candidate = tmp_path / 'candidate'
    candidate.mkdir()
    (candidate / 'pages.py').write_text('import os\nos._exit(0)\n')
    result = verify_submission(SUITE.parent, task, candidate, backend='host')
    assert result['returncode'] == 0 and not result['passed'] and result['test_cases'] == 0


def test_acceptance_docker_mount_is_read_only_and_not_in_agent_workspace(tmp_path):
    acceptance = SUITE.parent / 'acceptance'
    executor = AcceptanceDockerExecutor(tmp_path, acceptance)
    argv = executor.docker_argv(['python', '-m', 'pytest'])
    assert f'type=bind,source={acceptance},target=/acceptance,readonly' in argv
    assert argv[-4:] == [executor.config.image, 'python', '-m', 'pytest']
    assert '--read-only' in argv and argv[argv.index('--network') + 1] == 'none'


@pytest.mark.parametrize('kind', ['agent_host', 'compare_validation', 'nested', 'mode'])
def test_invalid_challenge_execution_fails_before_output_or_api(tmp_path, kind):
    kwargs = {}
    output = tmp_path / 'output'
    if kind == 'agent_host':
        kwargs['mode'] = 'agent'
    elif kind == 'compare_validation':
        kwargs['compare_backends'] = True
    elif kind == 'nested':
        output = SUITE.parent / 'forbidden-output'
    else:
        kwargs['mode'] = 'unknown'
    with pytest.raises(ValueError):
        run_challenges(SUITE, output, **kwargs)
    assert not output.exists()


def test_agent_comparison_has_fresh_abba_workspaces_and_no_reference_hints(tmp_path, monkeypatch):
    import harness.challenge_eval as module
    from harness.execution import HostExecutor

    captured = []
    monkeypatch.setattr(module.shutil, 'which', lambda _: 'docker')

    class FakeDocker(HostExecutor):
        def describe(self):
            return {**super().describe(), 'network': 'none', 'user': '10001',
                    'fallback_to_host': False, 'read_only_root': True}

    monkeypatch.setattr(module, 'DockerExecutor', FakeDocker)

    def fake_agent(prompt, registry, **kwargs):
        captured.append((prompt, registry.workspace, registry.retrieval_backend))
        task = next(task for task in load_suite(SUITE)['tasks'] if prompt.startswith(task['prompt']))
        assert set(path.name for path in registry.workspace.iterdir()) == set(task['editable'])
        registry.call('read_file', path=task['editable'][0])
        for name in task['editable']:
            shutil.copyfile(SUITE.parent / 'reference' / task['id'] / name, registry.workspace / name)

    monkeypatch.setattr(module, 'run_agent', fake_agent)
    real_verify = module.verify_submission
    monkeypatch.setattr(module, 'verify_submission', lambda root, task, candidate, **_: real_verify(
        root, task, candidate, backend='host'))
    result = run_challenges(SUITE, tmp_path / 'pair', mode='agent', backend='docker', compare_backends=True)
    assert result['execution_order'] == ['lexical', 'hybrid', 'hybrid', 'lexical']
    assert len({item[1] for item in captured}) == 12
    assert result['passed'] == 12
    assert all('old_text' not in prompt and 'new_text' not in prompt for prompt, _, _ in captured)


def test_suite_rejects_traversal_and_bad_test_counts(tmp_path):
    root = tmp_path / 'suite'
    shutil.copytree(SUITE.parent, root, ignore=shutil.ignore_patterns('__pycache__'))
    spec = json.loads((root / 'suite.json').read_text())
    spec['tasks'][0]['expected_tests'] = True
    (root / 'suite.json').write_text(json.dumps(spec))
    with pytest.raises(ValueError, match='test count'):
        load_suite(root / 'suite.json')


def test_environment_failure_stops_before_any_model_request(tmp_path, monkeypatch):
    import harness.challenge_eval as module

    monkeypatch.setattr(module.shutil, 'which', lambda _: 'docker')
    monkeypatch.setattr(module, 'verify_submission', lambda *_, **__: {
        'returncode': 2, 'test_cases': 0, 'acceptance_unchanged': True})
    monkeypatch.setattr(module, 'run_agent', lambda *_, **__: pytest.fail('must not call model'))
    with pytest.raises(ValueError, match='no model request'):
        run_challenges(SUITE, tmp_path / 'bad-runtime', mode='agent', backend='docker')


def test_docker_verifier_allows_non_root_result_output_without_opening_acceptance(tmp_path, monkeypatch):
    import harness.challenge_eval as module
    from harness.execution import ExecutionResult

    task = load_suite(SUITE)['tasks'][2]
    candidate = tmp_path / 'candidate'
    shutil.copytree(SUITE.parent / 'reference' / task['id'], candidate)

    class FakeExecutor:
        python_executable = 'python'
        workspace_path = '/workspace'

        def __init__(self, workspace, acceptance):
            self.workspace = workspace
            assert acceptance == SUITE.parent / 'acceptance'

        def run(self, argv, **kwargs):
            assert '--junitxml=/workspace/results/result.xml' in argv
            if os.name != 'nt':
                assert self.workspace.stat().st_mode & 0o777 == 0o755
                assert (self.workspace / 'results').stat().st_mode & 0o777 == 0o777
                assert (self.workspace / 'pages.py').stat().st_mode & 0o777 == 0o644
            xml = '<testsuite>' + '<testcase name="case"/>' * task['expected_tests'] + '</testsuite>'
            (self.workspace / 'results/result.xml').write_text(xml)
            return ExecutionResult(backend='docker', returncode=0)

    monkeypatch.setattr(module, 'AcceptanceDockerExecutor', FakeExecutor)
    assert verify_submission(SUITE.parent, task, candidate, backend='docker')['passed']
