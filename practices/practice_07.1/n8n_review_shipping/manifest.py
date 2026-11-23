from .rates import shipping_fee


def create_manifest(parcels):
    entries = []
    for parcel in parcels:
        entries.append({
            "reference": parcel.reference,
            "zone": parcel.zone,
            "fee": shipping_fee(parcel),
        })
    return {
        "entries": entries,
        "total_fee": round(sum(entry["fee"] for entry in entries), 2),
    }
