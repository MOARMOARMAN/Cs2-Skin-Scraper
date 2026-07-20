# CS2 Market Data Pipeline
# Copyright (C) 2026 Charles Wang
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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