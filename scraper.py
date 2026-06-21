from typing import TYPE_CHECKING
import logging
import time
import random
from utilities import (
    write_listings_db, 
    del_missing_ID_listing_db, 
    load_data_listings_db, 
    post_with_retry, 
    wears, 
    headers, 
    skinData, 
    setup_session_cookies, 
    price_conversion, 
    get_skin_code_db, 
    SKIN_DATA_DB,
    what_wear
)

DB_NAME = "listings.db"
logger = logging.getLogger("Scouting")

if TYPE_CHECKING:
    import requests

def scout(search_name: str, wear: int, max_float: float, max_price: float, scraper_session: requests.Session, cookies: dict, scout_code: str):
    # List of available_skins that will be returned.
    available_skins = {}
    scan_limit = 0
    Payload = [{
        "appid":730,
        "strItemName": scout_code, # Unique identifier, will have to calculate later
        "sort":{"field":1,"direction":0,"assetpropertyid":2},
        "filters":{"category_730_Exterior":[f"tag_WearCategory{wear}"]}, # Set these using the inputs
        "accessoryFilters":{},
        "propertyFilters":{},
        "price":{"eCurrency":20, "unMax":max_price * 100},
        "start": 0,
    }]
    # Steam forces 20 listings at a time.
    headers["Referer"] = f"https://steamcommunity.com/market/listings/730/{scout_code}"
    try:
        scout_r = post_with_retry(scraper_session, f"https://steamcommunity.com/market/listings/730/{scout_code}", Payload, headers, cookies) # type: ignore
    except Exception as e:
        logger.error(f"Initial scout request failed for {search_name}: {e}")
        return {}
    response_text = scout_r.text

    if scout_r.status_code == 200:
        total_listings = scout_r.json().get('total_count', 0)
        scan_limit = max(min(int(total_listings * 0.3), 100), 20)
        logger.info(f"Total Listings: {total_listings}. Scanning top: {scan_limit} items for {search_name}")
    elif scout_r.status_code == 429:
        logger.warning("Steam rate limit reached. Sleeping 300 seconds...")
        time.sleep(300)
        return []
    elif scout_r.status_code == 500:
        logger.info(f"No listings found for {search_name} under this float value {max_float} and price {max_price}.")
    else:
        logger.error(f"Unexpected status code {scout_r.status_code} for {search_name}")
        return []
    for offset in range (0, scan_limit, min(scan_limit, 20)):
        Payload[0]['start'] = offset
        try:
            r = post_with_retry(
                scraper_session,
                f"https://steamcommunity.com/market/listings/730/{scout_code}",
                Payload, # type: ignore
                headers,
                cookies,
            )
        except Exception as e:
            logger.error(f"Request failed at offset {offset} for {search_name}: {e}")
            # Skip this batch and continue the loop
            time.sleep(random.uniform(5, 10))
            continue
        data = r.json()
        #print(data)
        if not data['listings']:
            continue
        for mkt_pos, item in enumerate(data['listings']):
            listingID = item['listingid']
            price = item['unPrice'] + item['unFee']
            if price:
                price = float(price)
            else:
                continue
            properties = item['asset']['asset_properties']
            dID = ''
            float_val = 1
            for prop in properties:
                if prop.get('propertyid') == 2:
                    float_val = prop.get('float_value')
                    if float_val:
                        float_val = float(float_val)
                    else:
                        continue
                if prop.get('propertyid') == 6:
                    dID = prop.get('string_value')
                    break
            salePriceText = item['strSubtotal']
            converted_price = price_conversion(salePriceText, price)
            if float_val < max_float:
                available_skins[listingID] = skinData(dID=dID, float_val=float_val, price=converted_price)
            else:
                logger.info(f"Found skin with higher float at {offset + mkt_pos}")
                logger.info(f"Writing these skins to the database {available_skins}")
                return available_skins
        logger.debug(f"Processed up to offset {offset + 20}...")
        time.sleep(random.uniform(12,15))
    return available_skins

def scouting_loop(skin_name: str, maximum_float: float, maximum_price: float):
    logger.info(f"Scouting Loop for {skin_name} has been started")
    time.sleep(random.randint(3,20))
    # Dictionary containing all of the information on the skins
    # Stored as listingID for key
    # namedtuple containing the skin data like dID, float_val, and price
    valid_listings = {}
    wlevel = what_wear(maximum_float)
    session_cookies = setup_session_cookies()
    if not session_cookies:
        logger.error("Session setup failed and resulted in empty session and cookies")
        return 0
    else:
        logger.info(f"Session connected successfully to steam for {skin_name}")
    scraper_session = session_cookies[0]
    cookies = session_cookies[1]
    if wlevel < 0 or wlevel > 4:
        logger.error(f"Invalid wear level: {wlevel}")
        return
    skin_wear = wears[wlevel]
    search_name = f"{skin_name} {skin_wear}"
    load_data_listings_db(search_name, valid_listings, DB_NAME)
    scout_code = get_skin_code_db(SKIN_DATA_DB, search_name)
    if not scout_code:
        logger.error("could not access the scout_code in any form.")
        time.sleep(60)
        return
    
    try:
        while True:
            try:
                scout_results = scout(search_name, wlevel, maximum_float, maximum_price, scraper_session, cookies, scout_code)
                if scout_results:
                    currentlyAvailableIDS = [lID for lID in scout_results]
                    toRemoveIDs = []
                    for listingID in list(valid_listings):
                        if listingID not in currentlyAvailableIDS:
                            toRemoveIDs.append((listingID,))
                            del valid_listings[listingID]
                    del_missing_ID_listing_db(search_name, toRemoveIDs, DB_NAME)
                    for listingID in scout_results:
                        valid_listings[listingID] = scout_results[listingID]
                    write_listings_db(search_name, valid_listings, DB_NAME)
                    logger.info(f"{skin_name} Loop complete. Resting to avoid rate limits...")
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

if __name__ == "__main__":
    testing = True
    temp_name = "AK-47 | Ice Coaled"
    wlevel = 1
    maximum_float = 0.1
    maximum_price = 20.07
    # scouting_loop(testing, temp_name, wlevel, maximum_float, maximum_price)