from collections import Counter


def top_products(orders, limit=5):
    sold = Counter()
    for order in orders:
        if order["status"] == "cancelled":
            continue
        for item in order["items"]:
            sold[item["sku"]] += 1
    return sold.most_common(limit)


def totals_by_status(orders):
    totals = Counter()
    for order in orders:
        totals[order["status"]] += order["total"]
    return dict(totals)
