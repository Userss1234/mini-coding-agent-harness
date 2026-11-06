from __future__ import annotations

import importlib.util
import json
import threading

import pytest

from harness.code_intelligence import navigate_python, repository_map
from harness.tools import build_registry
from harness.trace import TraceLogger


def test_repository_map_budget_and_source_filters(tmp_path):
    (tmp_path / "helpers.py").write_text("def compute(value: int):\n    return value+1\n")
    (tmp_path / "worker.py").write_text("from helpers import compute as selected\nresult=selected(3)\n")
    (tmp_path / ".env").write_text("SECRET=hidden\n")
    (tmp_path / "broken.py").write_text("def (\n")
    result = repository_map(tmp_path, "compute", 6000)
    assert result["files"][0]["path"] == "helpers.py"
    assert result["parse_skipped"] == 1
    assert result["files"][0]["symbols"][0]["signature"] == "compute(value: int)"
    assert len(json.dumps(repository_map(tmp_path, max_chars=500))) <= 500
    assert "SECRET" not in json.dumps(result)


@pytest.mark.skipif(importlib.util.find_spec("pylsp") is None, reason="Optional Python LSP not installed")
def test_real_language_server_resolves_aliases_references_and_diagnostics(tmp_path):
    (tmp_path / "helpers.py").write_text("def compute(value):\n    return value+1\n")
    (tmp_path / "worker.py").write_text("from helpers import compute as selected\nresult = selected(3)\n")
    (tmp_path / "other.py").write_text("def compute(value):\n    return 'unrelated'\n")
    result = navigate_python(tmp_path, "worker.py", 2, 10, timeout=20)
    assert [m["path"] for m in result["matches"]] == ["helpers.py"]
    refs = navigate_python(tmp_path, "helpers.py", 1, 5, "references", 20)
    assert "worker.py" in {m["path"] for m in refs["matches"]}
    assert "other.py" not in {m["path"] for m in refs["matches"]}
    (tmp_path / "bad.py").write_text("missing_name()\n")
    diagnostics = navigate_python(tmp_path, "bad.py", 1, 1, "diagnostics", 20)
    assert any("undefined name" in m["diagnostic"]["message"] for m in diagnostics["matches"])
    assert not any(t.name == "python-lsp-reader" for t in threading.enumerate())


def test_navigation_requires_safe_file_and_opt_in(tmp_path, monkeypatch):
    (tmp_path / "worker.py").write_text("value=1\n")
    with pytest.raises(ValueError):
        navigate_python(tmp_path, "../worker.py", 1)
    with pytest.raises(ValueError):
        navigate_python(tmp_path, "worker.py", 50)
    monkeypatch.delenv("HARNESS_PYTHON_LSP", raising=False)
    registry = build_registry(tmp_path, TraceLogger(tmp_path / "trace.jsonl"))
    assert "python_navigate" not in registry.names()
    monkeypatch.setenv("HARNESS_PYTHON_LSP", "on")
    enabled = build_registry(tmp_path, registry.trace)
    assert "python_navigate" in enabled.names() and "repo_map" in enabled.names()


@pytest.mark.skipif(importlib.util.find_spec("pylsp") is None, reason="Optional Python LSP not installed")
def test_language_server_timeout_closes_process_and_filters_provider_secrets(tmp_path, monkeypatch):
    from harness import code_intelligence as ci

    (tmp_path / "worker.py").write_text("value=1\n")
    spawned = []
    original = ci.subprocess.Popen
    monkeypatch.setenv("SYNTHETIC_PROVIDER_API_KEY", "must-not-reach-language-server")

    def popen(*args, **kwargs):
        assert "SYNTHETIC_PROVIDER_API_KEY" not in kwargs["env"]
        process = original(*args, **kwargs)
        spawned.append(process)
        return process

    monkeypatch.setattr(ci.subprocess, "Popen", popen)
    with pytest.raises(TimeoutError):
        navigate_python(tmp_path, "worker.py", 1, timeout=0.001)
    assert spawned and all(p.poll() is not None for p in spawned)
    assert not any(t.name == "python-lsp-reader" for t in threading.enumerate())
