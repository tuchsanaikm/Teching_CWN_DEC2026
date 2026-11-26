def final_price(amount):
    """Return the price after discount.

    amount >= 1000: 10% off; amount >= 500: 5% off; otherwise no discount.
    Raises ValueError if amount is negative.
    """
    if amount < 0:
        raise ValueError("amount must not be negative")
    if amount >= 1000:
        return amount * 0.90
    if amount >= 500:
        return amount * 0.95
    return amount
