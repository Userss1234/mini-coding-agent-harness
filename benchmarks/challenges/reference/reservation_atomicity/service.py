from catalog import valid_quantity


def reserve(stock, items):
    requested = {}
    for product, quantity in items:
        if not valid_quantity(quantity) or product not in stock:
            return False
        requested[product] = requested.get(product, 0) + quantity
    if any(stock[product] < quantity for product, quantity in requested.items()):
        return False
    for product, quantity in requested.items():
        stock[product] -= quantity
    return True
