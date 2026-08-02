class OrderRepository:
    def persist_status(self, order_id: str, status: str) -> None:
        """Persist an order status transition in storage."""
        raise NotImplementedError
