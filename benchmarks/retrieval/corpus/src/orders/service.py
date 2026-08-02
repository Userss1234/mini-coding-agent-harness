from .repository import OrderRepository


def transition_order_status(order_id: str, status: str, repository: OrderRepository) -> None:
    """Validate an order status transition before asking the repository to persist it."""
    if status not in {"paid", "shipped", "cancelled"}:
        raise ValueError("unsupported order status")
    repository.persist_status(order_id, status)
