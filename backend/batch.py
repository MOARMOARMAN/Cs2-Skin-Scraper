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
from math import floor
import time
import logging
from .display_chart import update_wear_bucket_data_for_skin
from .utilities import (
    load_all_data_listings_db,
    get_price_float_buckets_skin_data_db,
    SKIN_DATA_DB,
    LISTINGS_DB,
    get_skin_code_db,
    discord_notification,
    listingData
)
logger = logging.getLogger("Batching")

OVERPAY_PERCENTAGE_THRESHOLD = -15

def calculate_overpay_percentages(skin_name: str, skin_listings: dict[str, listingData]):
    float_price_buckets = get_price_float_buckets_skin_data_db(skin_name, SKIN_DATA_DB)
    listings = {}
    for listing_ID, listing_data in skin_listings.items():
        float_val = listing_data.float_val
        price = listing_data.price
        average_price = float_price_buckets.get(int(float_val // 0.01), 0)
        if average_price == 0:
            continue
        overpay_percentage = round((price / average_price - 1) * 100, 4)

        listings[listing_ID] = {
            "name": skin_name,
            "float": float_val,
            "price": price,
            "overpay_percentage": overpay_percentage
        }
    return listings

def generate_overpay_percentages():
    listings = {}
    load_all_data_listings_db(listings, LISTINGS_DB)
    if not listings:
        return None
    results = {}
    for skin_name, skin_listings in listings.items():
        print(f"There are a total of {len(skin_listings)} listings for {skin_name}")
        update_wear_bucket_data_for_skin(skin_name)
        results = calculate_overpay_percentages(skin_name, skin_listings)

    # Want lowest priced listings
    sorted_results = sorted(results.items(), key=lambda x: x[1]["overpay_percentage"])
    return sorted_results

def analyze_batch_overpay() -> None|dict[str, dict]:
    sorted_overpay_results = generate_overpay_percentages()
    if not sorted_overpay_results:
        return None
    filtered_overpay_results = {}
    for listing_ID, listing_info in sorted_overpay_results:
        if not listing_info:
            continue
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
            discord_notification("@everyone")
            count = 1
            for listing_ID, data in underpriced_listings.items():
                skin_code = get_skin_code_db(SKIN_DATA_DB, data.get("name"))
                purchase_link = f"https://steamcommunity.com/market/listings/730/{skin_code}?detail={listing_ID}"
                message = ""
                message += f"\n{count}:\n    Link to Purchase: {purchase_link}"
                message += f"\nFloat: {data.get("float")}"
                message += f"\nPrice: {data.get("price")}"
                message += f"\nPrice_deviation: {data.get("overpay_percentage")}%\n"
                discord_notification(message)
                
                count += 1
        time.sleep(30)

if __name__ == "__main__":
    print(analyze_batch_overpay_loop())
