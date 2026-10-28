import hashlib


def audit_digest(previous_digest, record):
    """Link audit entries using a SHA256 hash chain over prior digest and record bytes."""
    return hashlib.sha256(previous_digest.encode() + record).hexdigest()


def verify_audit(previous_digest, record, expected):
    """Detect altered audit records by recomputing their chain digest."""
    return audit_digest(previous_digest, record) == expected
