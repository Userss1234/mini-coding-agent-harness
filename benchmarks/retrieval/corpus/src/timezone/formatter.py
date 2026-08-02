from datetime import datetime, timezone


def format_utc_timestamp(value: datetime) -> str:
    """Normalize a timezone-aware timestamp to UTC formatting."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
