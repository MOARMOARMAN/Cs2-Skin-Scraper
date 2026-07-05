from math import floor
import time
import logging
from display_chart import update_wear_bucket_data_for_skin
from utilities import (
    load_all_data_listings_db,
    get_price_float_buckets_skin_data_db,
    SKIN_DATA_DB,
    LISTINGS_DB,
    get_skin_code_db,
    discord_notification
)
logger = logging.getLogger("Batching")

OVERPAY_PERCENTAGE_THRESHOLD = -15

def calculate_overpay_percentages(listings: dict, skin_name: str, skin_listings: dict):
    float_price_buckets = get_price_float_buckets_skin_data_db(skin_name, SKIN_DATA_DB)
    for listing_ID, listing_data in skin_listings.items():
        float_val = listing_data.float_val
        price = listing_data.price
        average_price = float_price_buckets.get(int(floor(float_val * 100)))
        if average_price == 0:
            continue
        overpay_percentage = round((price / average_price - 1) * 100, 4)

        listings[listing_ID] = {
            "name": skin_name,
            "float": float_val,
            "price": price,
            "overpay_percentage": overpay_percentage
        }
    return None

def generate_overpay_percentages():
    listings = {}
    load_all_data_listings_db(listings, LISTINGS_DB)
    if not listings:
        return None
    results = {}
    for skin_name, skin_listings in listings.items():
        print(f"There are a total of {len(skin_listings)} listings for {skin_name}")
        update_wear_bucket_data_for_skin(skin_name)
        calculate_overpay_percentages(results, skin_name, skin_listings)

    # Want lowest priced listings
    sorted_results = sorted(results.items(), key=lambda x: x[1]["overpay_percentage"])
    return sorted_results

def analyze_batch_overpay() -> None|dict[str, dict]:
    sorted_overpay_results = generate_overpay_percentages()
    if not sorted_overpay_results:
        return None
    filtered_overpay_results = {}
    for listing_ID, listing_info in sorted_overpay_results:
        if listing_info["overpay_percentage"] < OVERPAY_PERCENTAGE_THRESHOLD:
            filtered_overpay_results[listing_ID] = listing_info
    return filtered_overpay_results

def analyze_batch_overpay_loop():
    while True:
        start = time.perf_counter()
        underpriced_listings = analyze_batch_overpay()
        # Example listing link:
        # https://steamcommunity.com/market/listings/730/G180720B7093004?detail=525379962958603527
        if underpriced_listings:
            logger.info(f"There is/are {len(underpriced_listings)} underpriced listings\n")
            count = 1
            for listing_ID, data in underpriced_listings.items():
                skin_code = get_skin_code_db(SKIN_DATA_DB, data.get("name"))
                purchase_link = f"https://steamcommunity.com/market/listings/730/{skin_code}?detail={listing_ID}"
                message = ""
                message += f"\n{count}:\n    Link to Purchase: {purchase_link}"
                message += f"\n>>>>>Float>>>>>: {data.get("float")}"
                message += f"\n>>>>>Price>>>>>: {data.get("price")}"
                message += f"\n>>>>>Price_deviation>>>>>: {data.get("overpay_percentage")}%\n"
                print(message) 
                discord_notification(message)
                
                count += 1
            print("\n\n\n")
        else:
            logger.info(f"There are currently no listings that are underpriced.")
        logger.info(f"batch analysis took {(time.perf_counter() - start) * 1000}")
        time.sleep(30)

if __name__ == "__main__":
    print(analyze_batch_overpay_loop())
