def total_with_discount(prices, discount_percent):
    """Return the total after applying the percentage discount."""
    total = sum(prices)
    return total + total * discount_percent / 100
