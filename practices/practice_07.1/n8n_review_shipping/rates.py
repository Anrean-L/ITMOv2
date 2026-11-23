from math import floor

RATE_PER_KG = {"local": 2.5, "regional": 4.0, "remote": 6.5}


def shipping_fee(parcel):
    """Charge per started kilogram, with a one-kilogram minimum."""
    if parcel.weight_kg <= 0:
        raise ValueError("parcel weight must be positive")
    billable_weight = max(1, floor(parcel.weight_kg))
    return round(billable_weight * RATE_PER_KG[parcel.zone], 2)
