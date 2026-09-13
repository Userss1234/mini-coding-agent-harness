from pathlib import Path

import pytest

from harness.permissions import (
    git_shell_permission_decision,
    is_transient_exception,
    safe_path,
    shell_permission_decision,
)


def test_safe_path_accepts_workspace_child_and_blocks_escape(tmp_path: Path) -> None:
    assert safe_path(tmp_path, "src/main.py") == tmp_path / "src" / "main.py"

    with pytest.raises(ValueError, match="Path escapes workspace"):
        safe_path(tmp_path, "../outside.txt")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("slow"), True),
        (RuntimeError("service unavailable"), True),
        (ValueError("invalid input"), False),
    ],
)
def test_transient_exception_classification(error: Exception, expected: bool) -> None:
    assert is_transient_exception(error) is expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python -V", "allow"),
        ("git status", "allow"),
        ("git push origin main", "blocked_git_not_allowlisted"),
        ("echo hello > output.txt", "blocked_shell_operator"),
        ('python -c "unterminated', "blocked_empty_shell"),
    ],
)
def test_shell_permission_decisions(command: str, expected: str) -> None:
    assert shell_permission_decision(command) == expected


def test_git_branch_flags_are_treated_as_mutation() -> None:
    assert git_shell_permission_decision(["git", "branch", "-d", "old"]) == (
        "blocked_git_branch_mutation"
    )
