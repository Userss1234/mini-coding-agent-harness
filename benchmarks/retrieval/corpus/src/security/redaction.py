import re


TOKEN_PATTERN = re.compile(r"(?i)(api[_-]?token=)[^&\s]+")


def redact_diagnostic_logs(message: str) -> str:
    """Redact an API token before diagnostic logs are emitted."""
    return TOKEN_PATTERN.sub(r"\1[REDACTED]", message)
