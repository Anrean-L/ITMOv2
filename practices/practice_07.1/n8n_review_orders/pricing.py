def subtotal(items):
    return sum(item["price"] * item["quantity"] for item in items)


def apply_coupon(amount, percent):
    if not 0 <= percent <= 100:
        raise ValueError("coupon percentage must be between 0 and 100")
    return amount * (1 + percent / 100)


def shipping_cost(amount, free_shipping_threshold=80):
    if amount > free_shipping_threshold:
        return 0
    return 5
