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
from typing import TYPE_CHECKING
import logging
import time
import random
from .utilities import (
    write_listings_db, 
    write_to_historical_db,
    del_missing_ID_listing_db, 
    load_data_listings_db,
    post_with_retry, 
    wears, 
    headers, 
    listingData,
    setup_session_cookies, 
    price_conversion, 
    get_skin_code_db, 
    LISTINGS_DB,
    SKIN_DATA_DB,
    HISTORICAL_DATA_DB,
    what_wear
)

logger = logging.getLogger("Scouting")

if TYPE_CHECKING:
    import requests

def scout(search_name: str, wear: int, max_float: float, max_price: float, scraper_session: requests.Session, cookies: dict, scout_code: str) -> tuple[set[str], bool] | None:
    scan_complete = True
    skin_name = search_name.rsplit('(', 1)[0].strip()
    existing_listing_ids = set()
    Payload = [{
        "appid":730,
        "strItemName": scout_code, # Unique identifier, will have to calculate later
        "filters":{"Exterior":[f"WearCategory{wear}"]}, # Set these using the inputs
        "accessoryFilters":{},
        "propertyFilters":{},
        "price":{"eCurrency":20, "unMax":max_price * 400},
        "start": 0,
    }]
    local_headers = headers.copy()
    local_headers["Referer"] = (
        f"https://steamcommunity.com/market/listings/730/{scout_code}"
        f"?price_max={int(max_price * 400)}"
        f"&price_currency=20"
        f"&category_Exterior=WearCategory{wear}"
        f"&appid=730"
    )
    try:
        scout_r = post_with_retry(scraper_session, local_headers["Referer"], Payload, local_headers, cookies) # type: ignore
    except Exception as e:
        logger.error(f"Initial scout request failed for {search_name}: {e}")
        return None

    if scout_r.status_code == 200:
        total_listings = scout_r.json().get('total_count', 0)
        logger.info(f"Total Listings: {total_listings}. Scanning top: {total_listings} items for {search_name}")
    else:
        logger.error(f"Unexpected status code {scout_r.status_code} for {search_name}")
        return None
    
    if total_listings == 0:
        logger.warning(f"No listings returned for {search_name}")
        return None
    for offset in range (0, total_listings, 20):
        available_skins = {}
        valid_skins = {}
        Payload[0]['start'] = offset
        try:
            r = post_with_retry(
                scraper_session,
                local_headers["Referer"], 
                Payload, # type: ignore
                local_headers,
                cookies,
            )
        except Exception as e:
            scan_complete = False
            logger.error(f"Request failed at offset {offset} for {search_name}: {e}")
            time.sleep(random.uniform(5, 10))
            continue
        data = r.json()
        if not data['listings']:
            scan_complete = False
            continue
        for mkt_pos, item in enumerate(data['listings']):
            listingID = item['listingid']
            price = item['unPrice'] + item['unFee']
            if price:
                price = float(price)
            else:
                continue
            asset = item.get('asset')
            if not asset:
                continue
            properties = asset.get('asset_properties')
            if not properties:
                continue
            float_val = 1
            for prop in properties:
                if prop.get('propertyid') == 2:
                    float_val = prop.get('float_value')
                    if float_val:
                        float_val = float(float_val)
                    else:
                        continue
            salePriceText = item['strSubtotal']
            converted_price = price_conversion(salePriceText, price)
            if float_val < max_float and converted_price < max_price:
                valid_skins[listingID] = listingData(float_val=float_val, price=converted_price)
            available_skins[listingID] = listingData(float_val=float_val, price=converted_price)
            existing_listing_ids.add(listingID)
         
        write_to_historical_db(skin_name, available_skins, HISTORICAL_DATA_DB)
        if valid_skins:
            write_listings_db(skin_name, valid_skins, LISTINGS_DB)
        if offset % 100 == 0:
            logger.info(f"Processed up to offset {offset + 20} for {search_name}")
        time.sleep(random.uniform(45, 75))
        if random.random() <= 0.1:
            time.sleep(random.uniform(300,600))
    return (existing_listing_ids, scan_complete)


def scouting_loop(skin_name: str, maximum_float: float, maximum_price: float):
    logger.info(f"Scouting Loop for {skin_name} has been started")
    previous_ids = set()
    wlevel = what_wear(maximum_float)
    session_cookies = setup_session_cookies()
    if not session_cookies:
        logger.error("Session setup failed and resulted in empty session and cookies")
        return 0
    else:
        logger.info(f"Session and cookies setup successfully for {skin_name}")
    scraper_session = session_cookies[0]
    cookies = session_cookies[1]
    if wlevel < 0 or wlevel > 4:
        logger.error(f"Invalid wear level: {wlevel}")
        return
    skin_wear = wears[wlevel]
    search_name = f"{skin_name} {skin_wear}"
    scout_code = get_skin_code_db(SKIN_DATA_DB, skin_name=skin_name)
    if not scout_code:
        logger.error("could not access the scout_code in any form.")
        time.sleep(60)
        return
    
    try:
        while True:
            try:
                scout_results = scout(search_name, wlevel, maximum_float, maximum_price, scraper_session, cookies, scout_code)
                if scout_results:
                    current_listing_ids, scan_completed = scout_results
                    if scan_completed:
                        set_of_ids_to_remove = previous_ids - current_listing_ids
                        ids_to_remove = [(listing_id, ) for listing_id in set_of_ids_to_remove]
                        if ids_to_remove:
                            del_missing_ID_listing_db(skin_name, ids_to_remove, LISTINGS_DB)
                        previous_ids = current_listing_ids.copy()
                    else:
                        previous_ids.update(current_listing_ids)
                    logger.info(f"{skin_name} Loop complete. Resting to avoid rate limits...")
                else:
                    logger.info(f"{skin_name} Loop is empty")
                time.sleep(random.randint(120, 180))
            except Exception as e:
                logger.error(f"Loop Failed: {e}")
                time.sleep(random.randint(120,180))
    except KeyboardInterrupt:
        logger.info("User Terminated scouting-loop, saving reads to database.")
    except Exception as e:
        logger.error(f"Exception {e} resulted in a crash.")
    # This runs before the script fully closes.
    finally:
        logger.info(f"{skin_name} scraping loop ended.")
        time.sleep(random.randint(120,180))

if __name__ == "__main__":
    testing = True
    temp_name = "AK-47 | Ice Coaled"
    wlevel = 1
    maximum_float = 0.1
    maximum_price = 20.07
    # scouting_loop(testing, temp_name, wlevel, maximum_float, maximum_price)