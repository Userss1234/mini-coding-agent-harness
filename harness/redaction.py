from __future__ import annotations

import os
import re
from typing import Any

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization|credential)")
_INLINE_SECRET = re.compile(
    r"(?i)((?:api[_-]?key|token|password|secret|authorization)"
    r"[\"']?\s*[=:]\s*[\"']?)[^\s,;\"'}]+"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_KNOWN_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL
)
_TOKEN_METRICS = {
    "max_tokens",
    "max_input_tokens", "summary_tokens", "before_estimated_tokens", "after_estimated_tokens",
    "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
    "prompt_tokens", "completion_tokens", "total_tokens",
}


def redact(value: Any) -> Any:
    """Best-effort output sanitization; never mutate live model/tool values."""
    if isinstance(value, dict):
        return {
            str(key): REDACTED if (
                _SECRET_KEY.search(str(key))
                and not (key in _TOKEN_METRICS and isinstance(item, int) and not isinstance(item, bool))
            ) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        for key, secret in os.environ.items():
            if _SECRET_KEY.search(key) and len(secret) >= 8:
                value = value.replace(secret, REDACTED)
        value = _PRIVATE_KEY.sub(REDACTED, value)
        value = _KNOWN_TOKEN.sub(REDACTED, value)
        value = _BEARER.sub("Bearer " + REDACTED, value)
        return _INLINE_SECRET.sub(lambda match: match[1] + REDACTED, value)
    return value
