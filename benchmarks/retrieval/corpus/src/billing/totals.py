from decimal import Decimal, ROUND_HALF_UP


def invoice_total(subtotal: Decimal, tax_rate: Decimal) -> Decimal:
    """Calculate invoice tax and round the total to currency precision."""
    tax = subtotal * tax_rate
    return (subtotal + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
