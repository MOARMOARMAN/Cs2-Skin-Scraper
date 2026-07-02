from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    insert_skin_float_prices_skin_data_db,
    create_float_prices_skin_data_db,
    LISTINGS_DB,
    SKIN_DATA_DB,
    WearBucket
)
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def show_graph(float_ranges: list, listing_volume: list, price_harmonic_means: list):
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

LISTINGS_TO_INCLUDE = 10
LISTING_PRICING_MULTIPLIER = 1.3

def calculate_wear_buckets(skin_name: str) -> list[WearBucket]:
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, LISTINGS_DB)

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

if __name__ == "__main__":
    create_float_prices_skin_data_db(SKIN_DATA_DB)
    historical_options = load_all_skin_names_all_historical_data_db(LISTINGS_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"These are your options: {options}\n") 
    skin_name = None
    while skin_name not in options:
        skin_name = input("Please enter your choice: ")
        if skin_name not in options:
            print(f"{skin_name} is not a part of the options.\n")
            print(f"These are your options: {options}\n")

    wear_buckets = calculate_wear_buckets(skin_name)
    float_ranges, listing_volume, price_harmonic_means = split_wear_bucket_data(wear_buckets)

    insert_skin_float_prices_skin_data_db(skin_name, price_harmonic_means, SKIN_DATA_DB)
    show_graph(float_ranges, listing_volume, price_harmonic_means)