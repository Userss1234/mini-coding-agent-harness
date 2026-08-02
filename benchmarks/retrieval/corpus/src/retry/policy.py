def exponential_backoff(attempt: int) -> float:
    """Retry a transient provider failure with bounded exponential backoff."""
    return min(0.5 * (2 ** attempt), 8.0)
