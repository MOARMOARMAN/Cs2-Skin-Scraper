from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    LISTINGS_DB
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

if __name__ == "__main__":
    historical_options = load_all_skin_names_all_historical_data_db(LISTINGS_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"These are your options: {options}\n")
    # skin_name = input("Please enter your choice: ")
    skin_name = "AK-47 | Ice Coaled"
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, LISTINGS_DB)
    print(len(listings_for_skin))
    # [harmonic sum of price, listing count, listings included, lowest price]
    harmonic_sum_listing_count = [[0, 0, 0, float("inf")] for _ in range(100)]
    for listing in listings_for_skin.values():
        listing_float_val = listing["float_val"]
        # wearlevel is 0-100 representing 0.01 intervals from 0-1
        listing_wearlevel = int(listing_float_val // 0.01)
        listing_price = listing["price"]
        cur_harmonic_sum_price, cur_listing_count, cur_included_count, lowest_price = harmonic_sum_listing_count[listing_wearlevel]
        if listing_price == 0: 
            continue
        if listing_price < 1.3 * lowest_price:
            if cur_included_count > LISTINGS_TO_INCLUDE:
                harmonic_sum_listing_count[listing_wearlevel] = [cur_harmonic_sum_price, cur_listing_count + 1, cur_included_count, lowest_price]
                continue
            listing_count = cur_listing_count + 1
            included_count = cur_included_count + 1
            lowest_price = min(listing_price, lowest_price)
            harmonic_sum = cur_harmonic_sum_price + 1 / listing_price
            harmonic_sum_listing_count[listing_wearlevel] = [harmonic_sum, listing_count, included_count, lowest_price]
    
    float_ranges = []
    listing_volume = []
    price_harmonic_means = []
    for x in range(100):
        float_ranges.append(f"{round(x/100, 2)}-{round(x/100 + 0.01, 2)}") 
        listing_volume.append(harmonic_sum_listing_count[x][1])
        included_volume = harmonic_sum_listing_count[x][2]
        if harmonic_sum_listing_count[x][0]:
            price_harmonic_means.append(included_volume / harmonic_sum_listing_count[x][0])
        else:
            price_harmonic_means.append(0)

    print(price_harmonic_means)
    print(listing_volume)
    show_graph(float_ranges, listing_volume, price_harmonic_means)