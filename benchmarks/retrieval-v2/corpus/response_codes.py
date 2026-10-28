def retryable_status(status):
    """HTTP transport classification; job backoff is owned by the scheduler."""
    return status in {429, 502, 503, 504}
