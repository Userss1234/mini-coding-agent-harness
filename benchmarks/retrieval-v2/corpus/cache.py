def cache_expired(entry, now):
    """Cached HTTP responses expire independently of worker ownership."""
    return entry['expires'] <= now
