from catalog import valid_quantity


def reserve(stock, items):
    for product, quantity in items:
        if not valid_quantity(quantity) or product not in stock or stock[product] < quantity:
            return False
        stock[product] -= quantity
    return True
