def retry_delay(attempt, base, cap):
    """Bound exponential job retry backoff by the declared maximum delay."""
    return min(base * 2 ** attempt, cap)


def before_deadline(now, delay, deadline):
    """Do not schedule another retry when it would exceed the job deadline."""
    return now + delay <= deadline


def enqueue_once(queue, idempotency_key, payload):
    """Repeated job submission with the same idempotency key reuses the first payload."""
    return queue.setdefault(idempotency_key, payload)
