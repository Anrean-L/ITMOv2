from datetime import timedelta


def dispatch_day(order_day, cutoff_hour=16):
    """Use the next business day for orders at or after the cutoff."""
    day = order_day.date()
    if order_day.hour > cutoff_hour:
        day += timedelta(days=1)

    if day.weekday() >= 5:
        day += timedelta(days=1)
    return day
