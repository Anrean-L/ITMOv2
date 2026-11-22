from .pricing import apply_coupon, shipping_cost, subtotal
from .stock import reserve_items


def prepare_order(order_id, items, inventory, coupon_percent=0):
    if not items:
        raise ValueError("order must include at least one item")

    remaining = reserve_items(inventory, items)
    amount = apply_coupon(subtotal(items), coupon_percent)
    shipping = shipping_cost(amount)

    order = {
        "id": order_id,
        "items": list(items),
        "status": "pending",
        "shipping": shipping,
        "total": round(amount + shipping, 2),
    }
    return order, remaining
