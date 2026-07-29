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
from collections import Counter
from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_prices_for_float_and_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    insert_skin_float_prices_skin_data_db,
    create_float_prices_skin_data_db,
    SKIN_DATA_DB,
    HISTORICAL_DATA_DB,
    WearBucket
)
import plotly.graph_objects as go
import math
from plotly.subplots import make_subplots

def show_float_bucket_graph(float_ranges: list, listing_volume: list, price_harmonic_means: list):
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Scatter(
            x=float_ranges,
            y=price_harmonic_means,
            name="Average Price",
            line=dict(color="limegreen", width=1.5),
            mode="lines",
            hovertemplate="Float: %{x}<br>Price: CDN$ %{y:.2f}<extra></extra>"
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(
            x=float_ranges,
            y=listing_volume,
            name="Listing Volume",
            marker=dict(color="steelblue", opacity=0.5),
            hovertemplate="Float: %{x}<br>Volume: %{y}<extra></extra>"
        ),
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(
        title_text="Price to Float + Volume"
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Float Ranges")

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>primary</b> Price", secondary_y=False)
    fig.update_yaxes(title_text="<b>secondary</b> Volume", secondary_y=True)

    fig.show()

def show_pricing_distribution_graph(points: list[float], density: list[float], volumes: list[float]):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=points,
            y=density,
            mode="lines",
            line=dict(color="limegreen", width=1.5),
            name="KDE",
            hovertemplate="Price: $CDN %{x:.2f}<br>Density: %{y:.6f}<extra></extra>"
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Bar(
            x=points,
            y=volumes,
            name="Listing Volumes",
            marker=dict(color="steelblue", opacity=0.5),
            hovertemplate="Price: $CDN %{x}<br>Volume: %{y}<extra></extra>"
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Seller Price Density with volume",
        xaxis_title="Price ($)",
        yaxis_title="Density",
    )

    fig.show()



LISTINGS_TO_INCLUDE = 30
LISTING_PRICING_MULTIPLIER = 1.8
GAUSSIAN_KDE_BANDWIDTH = 1.0
PRICING_BIN_SIZE = 0.1

def calculate_wear_buckets(skin_name: str) -> list[WearBucket]:
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, HISTORICAL_DATA_DB)

    # [harmonic sum of price, listing count, listings included, lowest price]
    wear_buckets = [WearBucket() for _ in range(100)]
    for listing in listings_for_skin.values():
        listing_float_val = listing["float_val"]
        # wearlevel is 0-100 representing 0.01 intervals from 0-1
        listing_wearlevel = int(listing_float_val // 0.01)
        listing_price = listing["price"]
        wb = wear_buckets[listing_wearlevel]
        if listing_price == 0: 
            continue
        if listing_price < LISTING_PRICING_MULTIPLIER * wb.lowest_price:
            if wb.included_count > LISTINGS_TO_INCLUDE:
                wb.listing_count += 1
                continue
            wb.listing_count += 1
            wb.included_count += 1
            wb.lowest_price = min(listing_price, wb.lowest_price)
            wb.harmonic_sum += 1 / listing_price
    return wear_buckets

def split_wear_bucket_data(wear_buckets: list[WearBucket]):
    float_ranges = []
    listing_volume = []
    price_harmonic_means = []
    for x in range(100):
        float_ranges.append(f"{round(x/100, 2)}-{round(x/100 + 0.01, 2)}") 
        listing_volume.append(wear_buckets[x].listing_count)
        included_volume = wear_buckets[x].included_count
        if wear_buckets[x].harmonic_sum:
            price_harmonic_means.append(included_volume / wear_buckets[x].harmonic_sum)
        else:
            price_harmonic_means.append(0)
    return float_ranges, listing_volume, price_harmonic_means

def update_wear_bucket_data_for_skin(skin_name: str):
    wear_buckets = calculate_wear_buckets(skin_name)
    float_ranges, listing_volume, price_harmonic_means = split_wear_bucket_data(wear_buckets)
    insert_skin_float_prices_skin_data_db(skin_name, price_harmonic_means, SKIN_DATA_DB)

def display_skin_chart():
    create_float_prices_skin_data_db(SKIN_DATA_DB)
    historical_options = load_all_skin_names_all_historical_data_db(HISTORICAL_DATA_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"\nThese are your options: {options}\n") 
    while True:
        skin_name = input("Please enter your choice (Enter ! to cancel): ")
        if skin_name in options:
            break
        elif skin_name == "!":
            return
        print(f"{skin_name} is not a part of the options.\n")
        print(f"These are your options: {options}\n")

    wear_buckets = calculate_wear_buckets(skin_name)
    float_ranges, listing_volume, price_harmonic_means = split_wear_bucket_data(wear_buckets)

    insert_skin_float_prices_skin_data_db(skin_name, price_harmonic_means, SKIN_DATA_DB)
    show_float_bucket_graph(float_ranges, listing_volume, price_harmonic_means)

def calculate_mean(values: list[float|int]) -> float: 
    """rounded to 2 digits. Expects input to not be empty."""
    return round((sum(values)/len(values)), 2)

def calculate_median(values: list[float|int]) -> float: 
    """Expects input to not be empty."""
    length = len(values)
    if length % 2 == 0:
        return round((values[length / 2 - 1] + values[length / 2]), 2)
    else:
        return values[length // 2]
    
def gaussian_kde(data: list[float|int], points: list[float], bandwidth: float):
    densities = []

    for point in points:
        total = 0

        for value in data:
            u = (point - value) / bandwidth
            total += math.exp(-0.5 * u * u)

        density = total / (len(data) * bandwidth * math.sqrt(2 * math.pi))

        densities.append(density)
    
    return densities

def volume_spread(data: list[float|int], points: list[float]):
    """Requires sorted ascending data"""
    volumes = [0 for _ in range(len(points))]
    points_index = 0
    for value in data:
        while value > points[points_index] + PRICING_BIN_SIZE:
            #print(f"points[points_index]: {points[points_index]} value: {value}")
            points_index += 1
        volumes[points_index] += 1
    return volumes

def display_seller_pricing_distribution_chart(skin_name: str, float_bucket: int):
    listing_prices = load_prices_for_float_and_name_all_historical_listings_db(skin_name, 6, HISTORICAL_DATA_DB)
    max_price = max(listing_prices)
    min_price = min(listing_prices)
    points = [round(min_price + PRICING_BIN_SIZE * i, 2) for i in range(int((max_price - min_price) / PRICING_BIN_SIZE) + 1)]
    density = gaussian_kde(listing_prices, points, GAUSSIAN_KDE_BANDWIDTH)
    volumes = volume_spread(listing_prices, points)
    show_pricing_distribution_graph(points, density, volumes)

if __name__ == "__main__":
    display_seller_pricing_distribution_chart("AK-47 | Ice Coaled", 6)