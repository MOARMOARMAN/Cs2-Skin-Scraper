from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    LISTINGS_DB
)
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LOWEST_PRICE_LISTINGS_TO_INCLUDE = 10

if __name__ == "__main__":
    historical_options = load_all_skin_names_all_historical_data_db(LISTINGS_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"These are your options: {options}\n")
    # skin_name = input("Please enter your choice: ")
    skin_name = "AK-47 | Ice Coaled"
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, LISTINGS_DB)
    print(len(listings_for_skin))
    harmonic_sum_listing_count = [[0 for _ in range(3)] for _ in range(100)]
    for listing in listings_for_skin.values():
        listing_float_val = listing["float_val"]
        # wearlevel is 0-100 representing 0.01 intervals from 0-1
        listing_wearlevel = int(listing_float_val // 0.01)
        listing_price = listing["price"]
        cur_harmonic_sum_price, cur_listing_count, cur_included_count = harmonic_sum_listing_count[listing_wearlevel]
        if listing_price == 0: 
            continue
        if cur_included_count > LOWEST_PRICE_LISTINGS_TO_INCLUDE:
            harmonic_sum_listing_count[listing_wearlevel] = [cur_harmonic_sum_price, cur_listing_count + 1, cur_included_count]
            continue
        listing_count = cur_listing_count + 1
        included_count = cur_included_count + 1
        harmonic_sum = cur_harmonic_sum_price + 1 / listing_price
        harmonic_sum_listing_count[listing_wearlevel] = [harmonic_sum, listing_count, included_count]
    
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
    """# Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Scatter(x=[1, 2, 3], y=[40, 50, 60], name="yaxis data"),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=[2, 3, 4], y=[4, 5, 6], name="yaxis2 data"),
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(
        title_text="Double Y Axis Example"
    )

    # Set x-axis title
    fig.update_xaxes(title_text="xaxis title")

    # Set y-axes titles
    fig.update_yaxes(title_text="<b>primary</b> yaxis title", secondary_y=False)
    fig.update_yaxes(title_text="<b>secondary</b> yaxis title", secondary_y=True)

    fig.show()"""