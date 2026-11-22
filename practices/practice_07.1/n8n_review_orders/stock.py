def reserve_items(inventory, items):
    remaining = inventory.copy()
    for item in items:
        sku = item["sku"]
        quantity = item["quantity"]
        available = remaining.get(sku, 0)
        if quantity >= available:
            raise ValueError(f"not enough stock for {sku}")
        remaining[sku] = available - quantity
    return remaining


def low_stock_items(inventory, threshold=3):
    return sorted(sku for sku, count in inventory.items() if count < threshold)
