class PaymentDeduplicator:
    """Prevent duplicate payment authorization with an idempotency key."""

    def reserve(self, idempotency_key: str) -> bool:
        raise NotImplementedError
