from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    LISTINGS_DB
)

if __name__ == "__main__":
    historical_options = load_all_skin_names_all_historical_data_db(LISTINGS_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"These are your options: {options}\n")
    skin_name = input("Please enter your choice: ")
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, LISTINGS_DB)
    print(len(listings_for_skin))
    price_float_listing_count = [[0 for _ in range(3)] for _ in range(100)]
    for listing in listings_for_skin.values():
        listing_float_val = listing["float_val"]
        # wearlevel is 0-20 representing 0.05 intervals from 0-1
        listing_wearlevel = int(listing_float_val // 0.01)
        listing_price = listing["price"]
        cur_average_price, cur_average_float, cur_listing_count = price_float_listing_count[listing_wearlevel]
        listing_count = cur_listing_count + 1
        price_average = (cur_average_price * cur_listing_count + listing_price) / listing_count
        float_average = (cur_average_float * cur_listing_count + listing_float_val) / listing_count
        price_float_listing_count[listing_wearlevel] = [price_average, float_average, listing_count]

    print(price_float_listing_count)