from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .agent import run_agent
from .evidence_metrics import summarize_evidence_use
from .execution import DockerExecutionConfig, DockerExecutor, HostExecutor
from .run_store import SQLiteRunStore
from .tools import build_registry
from .trace import TraceLogger
from .trace_viewer import load_trace_events


def _hashes(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Challenge inputs cannot contain links")
        if path.is_file() and not {"__pycache__", ".pytest_cache"}.intersection(path.parts):
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def load_suite(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 1 or not spec.get("tasks"):
        raise ValueError("Invalid challenge suite")
    ids = set()
    root = path.resolve().parent
    for task in spec["tasks"]:
        name = task["id"]
        if name in ids or not name.replace("_", "").isalnum():
            raise ValueError("Invalid or duplicate challenge ID")
        ids.add(name)
        if type(task.get("expected_tests")) is not int or task["expected_tests"] <= 0:
            raise ValueError("Expected acceptance test count must be positive")
        for relative in task["editable"]:
            if Path(relative).name != relative or not relative.endswith(".py"):
                raise ValueError("Editable challenge files must be top-level Python files")
            if not (root / "workspaces" / name / relative).is_file():
                raise ValueError("Missing challenge source")
        if not (root / "acceptance" / (name + ".py")).is_file():
            raise ValueError("Missing external acceptance")
    _hashes(root)
    return spec


class AcceptanceDockerExecutor(DockerExecutor):
    def __init__(self, workspace: Path, acceptance: Path):
        super().__init__(workspace, DockerExecutionConfig.from_env())
        self.acceptance = acceptance.resolve()
        if (self.config.network != "none" or int(self.config.user.split(":")[0]) == 0
                or not self.config.read_only_root or self.config.fallback_to_host):
            raise ValueError("Acceptance requires restricted Docker without host fallback")

    def docker_argv(self, argv: Sequence[str], env: Mapping[str, str] | None = None,
                    container_name: str | None = None) -> list[str]:
        command = super().docker_argv(argv, env, container_name)
        if "," in str(self.acceptance):
            raise ValueError("Acceptance mount cannot contain a comma")
        position = len(command) - len(argv) - 1
        command[position:position] = ["--mount", f"type=bind,source={self.acceptance},target=/acceptance,readonly"]
        return command


def verify_submission(root: Path, task: dict[str, Any], candidate: Path, *, backend: str) -> dict[str, Any]:
    if backend not in {"host", "docker"}:
        raise ValueError("Unknown acceptance backend")
    if set(_hashes(candidate)) != set(task["editable"]):
        return {"passed": False, "reason": "submission contains missing or unauthorized files"}
    protected = _hashes(root / "acceptance")
    with tempfile.TemporaryDirectory(prefix="mini-agent-acceptance-") as folder:
        submission = Path(folder)
        results = submission / "results"
        results.mkdir()
        for name in task["editable"]:
            shutil.copyfile(candidate / name, submission / name)
        if backend == "docker":
            submission.chmod(0o755)
            results.chmod(0o777)
            for name in task["editable"]:
                (submission / name).chmod(0o644)
        executor = (AcceptanceDockerExecutor(submission, root / "acceptance")
                    if backend == "docker" else HostExecutor(submission))
        acceptance = "/acceptance" if backend == "docker" else str(root / "acceptance")
        target = executor.workspace_path.replace("\\", "/")
        wrapper = ("import os,runpy;os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';"
                   "os.environ['PYTEST_ADDOPTS']='';runpy.run_module('pytest',run_name='__main__')")
        result = executor.run([
            executor.python_executable, "-I", "-c", wrapper, "-c", acceptance + "/pytest.ini",
            "--confcutdir=" + acceptance, "-p", "no:cacheprovider", "-o", "pythonpath=" + target,
            "--junitxml=" + target + "/results/result.xml", acceptance + "/" + task["id"] + ".py",
        ], timeout=60, env={"PYTHONDONTWRITEBYTECODE": "1"})
        cases = []
        try:
            cases = list(ET.parse(results / "result.xml").iter("testcase"))
        except (OSError, ET.ParseError):
            pass
        clean = all(not list(case) for case in cases)
        unchanged = protected == _hashes(root / "acceptance")
        passed = result.returncode == 0 and len(cases) == task["expected_tests"] and clean and unchanged
        return {"passed": passed, "returncode": result.returncode, "test_cases": len(cases),
                "acceptance_unchanged": unchanged, "timed_out": result.timed_out,
                "output": result.output[-6000:], "backend": backend}


def run_challenges(suite_path: Path, output: Path, *, mode: str = "validate",
                   backend: str = "host", compare_backends: bool = False,
                   max_turns: int = 12) -> dict[str, Any]:
    spec = load_suite(suite_path)
    root = suite_path.resolve().parent
    if mode not in {"validate", "agent"}:
        raise ValueError("Challenge mode must be validate or agent")
    if mode == "agent" and (backend != "docker" or shutil.which("docker") is None):
        raise ValueError("Model-driven challenges require Docker; host mode is trusted validation only")
    if compare_backends and mode != "agent":
        raise ValueError("Backend comparison requires actual agent mode")
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("Challenge output must be outside the suite")
    output.mkdir(parents=True, exist_ok=False)
    protected = _hashes(root)
    rows = []
    order = ["lexical", "hybrid", "hybrid", "lexical"] if compare_backends else ["lexical"]
    for trial, retrieval in enumerate(order):
        for task in spec["tasks"]:
            folder = output / f"{trial}-{retrieval}" / task["id"]
            candidate = folder / "workspace"
            shutil.copytree(root / "workspaces" / task["id"], candidate,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            baseline = verify_submission(root, task, candidate, backend=backend)
            if (baseline.get("returncode") != 1 or baseline.get("test_cases") != task["expected_tests"]
                    or not baseline.get("acceptance_unchanged")):
                raise ValueError("Baseline acceptance did not execute correctly; no model request is allowed")
            if mode == "validate":
                for name in task["editable"]:
                    shutil.copyfile(root / "reference" / task["id"] / name, candidate / name)
            else:
                trace = TraceLogger(folder / "trace.jsonl")
                executor = DockerExecutor(candidate)
                policy = executor.describe()
                if (policy["network"] != "none" or int(str(policy["user"]).split(":")[0]) == 0
                        or policy["fallback_to_host"] or not policy["read_only_root"]):
                    raise ValueError("Agent requires restricted Docker")
                registry = build_registry(candidate, trace, allow_write=True,
                                          retrieval_backend=retrieval, executor=executor)
                prompt = (task["prompt"] + "\nSubmission scope: only these files may remain: "
                          + ", ".join(task["editable"]) + ". External acceptance is not available in this workspace.")
                run_agent(prompt, registry, max_turns=max_turns,
                          run_store=SQLiteRunStore(folder / "runs.sqlite3"))
            verdict = verify_submission(root, task, candidate, backend=backend)
            row = {"task_id": task["id"], "trial": trial, "retrieval_backend": retrieval,
                   "baseline": baseline, "verdict": verdict}
            if mode == "agent":
                events, _ = load_trace_events(folder / "trace.jsonl")
                row["evidence_use"] = summarize_evidence_use(events)
            rows.append(row)
    unchanged = protected == _hashes(root)
    result = {"schema_version": 1, "mode": mode, "split": spec["split"], "backend": backend,
              "execution_order": order, "protected_inputs_unchanged": unchanged,
              "rows": rows, "passed": sum(bool(row["verdict"]["passed"]) for row in rows),
              "interpretation": ("Reference validation, not an agent score" if mode == "validate"
                                 else "Public author-known challenge performance; not blind generalization")}
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not unchanged:
        raise ValueError("Protected challenge inputs changed")
    return result
