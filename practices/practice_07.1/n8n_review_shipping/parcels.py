from dataclasses import dataclass


@dataclass(frozen=True)
class Parcel:
    reference: str
    weight_kg: float
    zone: str


def total_weight(parcels):
    return sum(parcel.weight_kg for parcel in parcels)


def fit_on_truck(parcels, capacity_kg):
    """Return whether the parcels fit within the truck's weight limit."""
    return total_weight(parcels) < capacity_kg
