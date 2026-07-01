from dataclasses import dataclass

@dataclass
class WearBucket:
    harmonic_sum: float = 0.0
    listing_count: int = 0
    included_count: int = 0
    lowest_price: float = float("inf")

@dataclass
class listingData:
    float_val: float
    price: float