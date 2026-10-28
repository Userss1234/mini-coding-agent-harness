def reserve_inventory(stock, items):
    """Validate product quantities before committing an atomic stock reservation."""
    combined = {}
    for product, quantity in items:
        if type(quantity) is not int or quantity <= 0:
            return False
        combined[product] = combined.get(product, 0) + quantity
    if any(stock.get(product, 0) < count for product, count in combined.items()):
        return False
    for product, count in combined.items():
        stock[product] -= count
    return True


def available_stock(stock, reserved):
    """Subtract outstanding reservations from warehouse inventory availability."""
    return {product: count - reserved.get(product, 0) for product, count in stock.items()}
