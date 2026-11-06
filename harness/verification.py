from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .execution import DockerExecutor, ReadOnlyDockerExecutor
from .workspace import _scan

SYNTAX_SCRIPT = """import json,sys,tokenize
errors=[]
for name in sys.argv[1:]:
    try:
        with tokenize.open(name) as f: compile(f.read(),name,'exec')
    except SyntaxError as e:
        errors.append(dict(tool='syntax',file=name,line=e.lineno,column=e.offset,
                           severity='error',code=type(e).__name__,message=e.msg))
    except Exception as e:
        errors.append(dict(tool='syntax',file=name,severity='error',code=type(e).__name__,
                           message=str(e)))
print(json.dumps(errors));sys.exit(bool(errors))
"""
PYTEST_SCRIPT = ("import os,sys;os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';"
                 "sys.path.insert(0,os.getcwd());import pytest;"
                 "sys.exit(pytest.main(sys.argv[1:]))")


@dataclass(frozen=True)
class VerificationConfig:
    checks: tuple[str, ...] = ("syntax",)
    test_target: str = "tests"
    timeout: int = 30
    max_repairs: int = 2

    def __post_init__(self) -> None:
        if (not self.checks or len(set(self.checks)) != len(self.checks)
                or any(c not in {"syntax", "ruff", "pytest"} for c in self.checks)):
            raise ValueError("Verification checks must be unique syntax/ruff/pytest names")
        if (type(self.timeout) is not int or not 1 <= self.timeout <= 60
                or type(self.max_repairs) is not int or not 0 <= self.max_repairs <= 3):
            raise ValueError("Verification timeout 1..60 and max_repairs 0..3 required")
        path = Path(self.test_target)
        if (not self.test_target or path.is_absolute() or ".." in path.parts
                or self.test_target.startswith("-") or "\\" in self.test_target
                or ":" in self.test_target or any(ord(c) < 32 for c in self.test_target)):
            raise ValueError("Verification test target must be a workspace-relative path")

    @classmethod
    def load(cls, path: Path, workspace: Path) -> VerificationConfig:
        path = path.resolve()
        if path.is_relative_to(workspace.resolve()):
            raise ValueError("Verification configuration must be outside the Agent workspace")
        if path.stat().st_size > 8192:
            raise ValueError("Verification configuration exceeds 8 KiB")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.pop("version", None) != 1:
            raise ValueError("Verification configuration requires version 1")
        if set(data) - {"checks", "test_target", "timeout", "max_repairs"}:
            raise ValueError("Unknown verification configuration field")
        checks = data.pop("checks", ["syntax"])
        if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
            raise ValueError("Verification checks must be a list of names")
        return cls(checks=tuple(checks), **data)


class VerificationController:
    def __init__(self, workspace: Path, executor: DockerExecutor, config: VerificationConfig):
        if not isinstance(executor, DockerExecutor):
            raise ValueError("Completion verification requires restricted Docker; no host fallback")
        self.workspace = workspace.resolve()
        self.executor = ReadOnlyDockerExecutor(workspace, executor.config, executor.docker_executable)
        self.config = config
        self.state: dict[str, Any] = {}

    def policy(self) -> dict[str, Any]:
        return json.loads(json.dumps(asdict(self.config)))

    def snapshot(self) -> dict[str, str]:
        return {name: item["sha256"] for name, item in _scan(self.workspace, source=True).items()}

    def start(self, saved: dict[str, Any] | None = None) -> None:
        self.state = saved if saved is not None else {
            "baseline": [{"path": name, "sha256": digest}
                         for name, digest in self.snapshot().items()],
            "repairs": 0, "last_failure": None, "last_report": None,
        }

    def check(self) -> dict[str, Any]:
        try:
            before = self.snapshot()
            baseline = {item["path"]: item["sha256"] for item in self.state["baseline"]}
            changed = sorted(name for name in baseline.keys() | before.keys()
                             if baseline.get(name) != before.get(name))
            python = [name for name in changed if name.endswith(".py") and name in before]
            checks: list[dict[str, Any]] = []
            for name in self.config.checks:
                if name in {"syntax", "ruff"} and not python:
                    continue
                if name == "syntax":
                    argv = ["python", "-I", "-B", "-c", SYNTAX_SCRIPT, *["./" + p for p in python]]
                elif name == "ruff":
                    argv = ["python", "-I", "-B", "-m", "ruff", "check", "--no-cache",
                            "--isolated", "--select", "E4,E7,E9,F", "--output-format", "json",
                            "--", *["./" + p for p in python]]
                else:
                    target = (self.workspace / self.config.test_target).resolve()
                    if not target.is_relative_to(self.workspace) or not target.exists():
                        checks.append({"tool": name, "status": "unverified", "exit_status": None,
                                       "diagnostics": [{"code": "missing_test_target",
                                                        "message": "Configured test target is absent"}]})
                        continue
                    argv = ["python", "-I", "-B", "-c", PYTEST_SCRIPT, "-q",
                            "-c", "/dev/null", "--rootdir", self.executor.workspace_path,
                            "-p", "no:cacheprovider", "--basetemp=/tmp/harness-verify-tests",
                            "./" + self.config.test_target]
                result = self.executor.run(argv, timeout=self.config.timeout,
                                           env={"PYTHONDONTWRITEBYTECODE": "1"})
                unavailable = (result.timed_out or result.error is not None
                               or "No module named" in result.output
                               or (name == "pytest" and result.returncode in {4, 5}))
                status = "unverified" if unavailable else ("passed" if result.returncode == 0 else "failed")
                diagnostics: list[dict[str, Any]] = []
                if name in {"syntax", "ruff"} and not unavailable:
                    try:
                        parsed = json.loads(result.stdout)
                        if not isinstance(parsed, list):
                            raise ValueError("Expected diagnostic list")
                        for item in parsed[:100]:
                            filename = item.get("file", item.get("filename"))
                            if isinstance(filename, str):
                                filename = filename.removeprefix(self.executor.workspace_path + "/").removeprefix("./")
                            diagnostics.append({
                                "tool": name, "file": filename,
                                "line": item.get("line", (item.get("location") or {}).get("row")),
                                "column": item.get("column", (item.get("location") or {}).get("column")),
                                "severity": "error", "code": item.get("code", "diagnostic"),
                                "message": str(item.get("message", ""))[:1000],
                            })
                    except (ValueError, TypeError, AttributeError):
                        status = "unverified"
                if not diagnostics and status != "passed":
                    diagnostics = [{"tool": name, "severity": "error", "code": status,
                                    "message": result.output[:4000] or "Check unavailable or failed"}]
                checks.append({"tool": name, "status": status, "exit_status": result.returncode,
                               "timed_out": result.timed_out, "diagnostics": diagnostics})
            after = self.snapshot()
            stable = before == after
            status = ("unverified" if not stable or not checks or
                      any(c["status"] == "unverified" for c in checks) else
                      "failed" if any(c["status"] == "failed" for c in checks) else "passed")
            report = {"status": status, "changed_files": changed, "checks": checks,
                      "source_stable": stable,
                      "scope": "Operator-selected checks only; not external task acceptance",
                      "source_digest": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()}
        except (OSError, ValueError, RuntimeError) as exc:
            report = {"status": "unverified", "checks": [], "changed_files": [],
                      "reason": type(exc).__name__ + ": " + str(exc)[:1000]}
        self.state["last_report"] = report
        return report

    def repair_allowed(self, report: dict[str, Any]) -> bool:
        digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
        allowed = (report["status"] == "failed" and self.state["repairs"] < self.config.max_repairs
                   and digest != self.state["last_failure"])
        if allowed:
            self.state["repairs"] += 1
        self.state["last_failure"] = digest
        return allowed
