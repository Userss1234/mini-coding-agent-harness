from __future__ import annotations

import shlex
import sys
from pathlib import Path

SHELL_OPERATOR_MARKERS = ["&&", "||", ";", "|", ">", "<", "\n", "\r"]

ALLOWED_SHELL_COMMANDS = {
    "cat",
    "dir",
    "echo",
    "findstr",
    "get-childitem",
    "ls",
    "pwd",
    "python",
    "python.exe",
    "py",
    "py.exe",
    "pytest",
    "pytest.exe",
    "type",
    Path(sys.executable).name.lower(),
}

READ_ONLY_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "rev-parse",
    "show",
    "status",
    "ls-files",
}


def safe_path(workspace: Path, path: str | Path) -> Path:
    candidate = (workspace / path).resolve()
    if not candidate.is_relative_to(workspace):
        raise ValueError(f"Path escapes workspace: {path}")
    return candidate


def is_transient_exception(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    transient_markers = [
        "timeout",
        "temporarily",
        "connection",
        "rate limit",
        "ratelimit",
        "overloaded",
        "service unavailable",
        "502",
        "503",
        "504",
    ]
    return any(marker in name or marker in text for marker in transient_markers)


def shell_permission_decision(command: str) -> str:
    tokens = parse_shell_tokens(command)
    if not tokens:
        return "blocked_empty_shell"
    lowered = command.lower()
    if any(marker in lowered for marker in SHELL_OPERATOR_MARKERS):
        return "blocked_shell_operator"
    if any(token.lower() in {"--force", "-f", "/f"} for token in tokens):
        return "blocked_force_flag"

    executable = Path(tokens[0]).name.lower()
    if executable == "git":
        return git_shell_permission_decision(tokens)

    if executable not in ALLOWED_SHELL_COMMANDS:
        return "blocked_shell_not_allowlisted"
    return "allow"


def parse_shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


def git_shell_permission_decision(tokens: list[str]) -> str:
    if len(tokens) < 2:
        return "blocked_git_missing_subcommand"
    if any(token.lower().startswith("--force") for token in tokens):
        return "blocked_force_flag"

    subcommand = tokens[1].lower()
    if subcommand not in READ_ONLY_GIT_SUBCOMMANDS:
        return "blocked_git_not_allowlisted"
    if subcommand == "branch" and any(token.startswith("-") for token in tokens[2:]):
        return "blocked_git_branch_mutation"
    return "allow"
