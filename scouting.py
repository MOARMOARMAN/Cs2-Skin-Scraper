from collections import namedtuple

import requests
import sqlite3
import time
import re
import os
from dotenv import load_dotenv
import json
import random
from contextlib import closing
# api_key = os.getenv("GEMINI_API_KEY")
user_agent = os.getenv("STEAM_USER_AGENT")

DB_NAME = "analyzed.db"
# Tuple of Possible Wears
wears = ("(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)")
WEAR_RANGES = {
    "(Factory New)": "(0 - 0.07)",
    "(Minimal Wear)": "(0.07 - 0.15)",
    "(Field-Tested)": "(0.15 - 0.38)",
    "(Well-Worn)": "(0.38 - 0.45)",
    "(Battle-Scarred)": "(0.45 - 1.00)"
}
CURRENCY_TO_CAD = {
    "HKD": 0.177,   # 1 Hong Kong Dollar ~ 0.18 CAD
    "USD": 1.370,   # 1 US Dollar ~ 1.37 CAD
    "EUR": 1.480,   # 1 Euro ~ 1.48 CAD
    "GBP": 1.740,   # 1 British Pound ~ 1.74 CAD
    "CAD": 1.000    # Base currency fallback
}
headers = {
    "Host": "steamcommunity.com",
    "Origin": "https://steamcommunity.com",
    # Just an Example, is updated later in the scouting loop
    "Referer": "https://steamcommunity.com/market/listings/730/G1802208A0A3004",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json; charset=utf-8",
    # THE SECRET HANDSHAKE
    "x-valve-action-type": "4OPT6VBA:Search",
    "x-valve-request-type": "routeAction",
    # MAPPING BROWSER ID
    "User-Agent": user_agent,
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-dest": "empty"
}
# skinData = namedtuple('skinData', ['dID', 'float_val', 'price'])
skinData = namedtuple('skinData', ['dID', 'float_val', 'price'])

def write_db(skin_name: str, valid_listings: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            print("WRITING")
            listingData = (
                (lID, skin_name, data.dID, data.float_val, data.price)
                for lID, data in valid_listings.items()
            )
            conn.executemany(f"INSERT OR REPLACE INTO skin_listings (listing_ID, skin_name, d_ID, float_val, price) VALUES(?, ?, ?, ?, ?)", listingData)

def del_missing_ID_db(skin_name: str, gone_listingIDs: list, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            print("DELETING")
            print(gone_listingIDs)
            delete_data = ((ID[0], skin_name) for ID in gone_listingIDs)
            conn.executemany(f"DELETE FROM skin_listings WHERE listing_ID = ? AND skin_name = ?", delete_data)

def load_data_db(skin_name: str, valid_listings: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            print("LOADING")
            try:
                stored_skins = conn.execute(f"SELECT listing_ID, price, d_ID, float_val FROM skin_listings WHERE skin_name = ?", (skin_name, )).fetchall()
                for skin in stored_skins:
                    valid_listings[skin[0]] = skinData(dID=skin[2], float_val=skin[3], price=skin[1])
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"table skin_listings doesn't exist yet")
                else:
                    raise      

def create_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS skin_listings (listing_ID TEXT PRIMARY KEY, skin_name TEXT, d_ID TEXT, float_val REAL, price REAL)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_skin_listings_skin_name ON skin_listings (skin_name)")

def scout(skin_name: str, wear: int, max_float: float, max_price: float, scraper_session: requests.Session, cookies: dict):
    # List of availableSkins that will be returned.
    availableSkins = {}

    # Skin Name
    if wear < 0 or wear > 4:
        print("invalid wear")
        return
    skin_wear = wears[wear]
    search_name = f"{skin_name} {skin_wear}"
    print(search_name)
    # skin_name = "AK-47 | Ice Coaled (Field-Tested)"

    scan_limit = 0
    # Obtaining the skin's specific code.
    scout_code = requests.get(f"https://steamcommunity.com/market/listings/730/{search_name}")
    scout_code = scout_code.url.split('/')[-1]
    #print(scout_code.text)
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
    scout_r = scraper_session.post(f"https://steamcommunity.com/market/listings/730/{scout_code}", json=Payload, headers=headers, cookies=cookies)
    print(scout_r.url)
    print(scout_r.status_code)
    #print(f"JSON FILE IS: {scout_r.json()}")
    #data = scout_r.json().get('listings', [])
    #print(f"num listings: {len(data)}")

    #print(f"WEBSITE OUTPUT: {scout_r.text}")
    
    response_text = scout_r.text
    print(f"length of response_text: {len(response_text)}")

    if scout_r.status_code == 200:
        total_listings = scout_r.json().get('total_count', 0)
        scan_limit = max(min(int(total_listings * 0.1), 100), 20)
        print(f"Total Listings: {total_listings}. Scanning top: {scan_limit} items")
    elif scout_r.status_code == 429:
        print("Steam rate limit reached.")
        time.sleep(300)
        return []

    for offset in range (0, scan_limit, min(scan_limit, 20)):
        Payload[0]['start'] = offset
        r = scraper_session.post(
            f"https://steamcommunity.com/market/listings/730/{scout_code}",
            json=Payload,
            headers=headers,
            cookies=cookies
        )
        data = r.json()
        #print(data)
        for mkt_pos, item in enumerate(data['listings']):
            listingID = item['listingid']
            #print(listingID)
            #price = item[1].get('converted_publisher_fee', 0) + item[1].get('converted_price', 0) + item[1].get('converted_steam_fee', 0)
            price = item['unPrice'] + item['unFee']
            #print(price)
            if price:
                price = float(price)
            else:
                continue
            
            #assetID = item[1].get('asset').get('id')
            #print(item.keys())
            properties = item['asset']['asset_properties']
            #print(properties)
            dID = ''
            float_val = None
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
            print(f"fval: {float_val} | price: {price / 100} | max_price: {max_price}")
            salePriceText = item['strSubtotal']
            #print(f"SALE PRICE TEXT: {salePriceText}")
            # Price checking handled by the filter located in the header.
            converted_price = 0
            if "CA" not in salePriceText:
                #print("Needs Converting")
                if "HK" in salePriceText:
                    converted_price = round(price * CURRENCY_TO_CAD["HKD"] / 100, 2)
            else:
                converted_price = price / 100
            print(f"CONVERTED PRICE IN CAD: CA${converted_price}")
            if float_val < max_float:
                availableSkins[listingID] = skinData(dID=dID, float_val=float_val, price=converted_price)
                #availableSkins.append(Skin(listingID, converted_price, assetID, dID, float_val, mkt_pos + 20 * pg))
            #else:
                #print("Too High Float")

        print(f"Processed up to offset {offset + 20}...")
        time.sleep(random.uniform(8,10))
    # for skin in availableSkins:
        # print(skin.price)
        # print(skin.float_val)
        # print(f"___________________{skin.market_pos}")
    return availableSkins

def scouting_loop(isTesting: bool, skin_name: str, wlevel: int, maximum_float: float, maximum_price: float):
    # Dictionary containing all of the information on the skins
    # Stored as listingID for key
    # namedtuple containing the skin data like dID, float_val, and price
    valid_listings = {}
    adbConnect = sqlite3.connect("analyzed.db", timeout=60)
    dbMode = adbConnect.execute("PRAGMA journal_mode=WAL;").fetchone()[0] # This enables Write Ahead Logging which allows multiple cursors to read from a database at once.
    print(dbMode)
    scraper_session = requests.Session()
    try:
        scraper_session.get("https://steamcommunity.com/market/")
    except Exception as e:
        print(e)
    if not scraper_session:
        print("Failed to create Steam market session")
    else:
        print("Session to Steam Created.")
    session_id = scraper_session.cookies.get('sessionid', domain='steamcommunity.com')
    if not session_id:
        session_id = os.getenv("SESSION_ID_FALLBACK") # Your known good ID
        scraper_session.cookies.set('sessionid', session_id, domain='steamcommunity.com')
    else:
        print("Session Connected to Steam!")
        print(session_id)
    cookies = {
        "sessionid": session_id,
        "timezoneName": "America/New_York",
    }
    scraper_session.cookies.update(cookies)

    processed_name = skin_name + wears[wlevel]
    processed_name = re.sub(r'[^0-9a-zA-Z]', '', processed_name)
    processed_name = f'"{processed_name}"'
    dbReadWrite = not isTesting
    create_table_db(DB_NAME)
    load_data_db(processed_name, valid_listings, DB_NAME)
    
    try:
        while True:
            try:
                scout_results = scout(skin_name, wlevel, maximum_float, maximum_price, scraper_session, cookies)
                #print(f"THESE ARE THE SCOUT RESULTS {scout_results}")
                #print(f"THESE ARE THE VALID LISTINGS {valid_listings}")
                if scout_results:
                    currentlyAvailableIDS = [lID for lID in scout_results]
                    print(currentlyAvailableIDS)
                    # Update the valid_listings
                    print("LISTING UPDATE _______________________________________________________________________")
                    if dbReadWrite:
                        toRemoveIDs = []
                        for listingID in list(valid_listings):
                            if listingID not in currentlyAvailableIDS:
                                toRemoveIDs.append((listingID,))
                                print(f"Listing {listingID} no longer present")
                                del valid_listings[listingID]
                            else:
                                print(f"Listing {listingID} is still present")
                        del_missing_ID_db(processed_name, toRemoveIDs, DB_NAME)
                    for listingID in scout_results:
                        valid_listings[listingID] = scout_results[listingID]
                        print(f"Price: {valid_listings[listingID].price} | Float: {valid_listings[listingID].float_val} | dID: {valid_listings[listingID].dID}")
                    if dbReadWrite:
                        write_db(processed_name, valid_listings, DB_NAME)
                    print("Loop complete. Resting to avoid rate limits...")
                time.sleep(random.randint(45, 60))
            except Exception as e:
                print(f"Loop Failed: {e}")
                time.sleep(random.randint(60,120))
    except KeyboardInterrupt:
        print("User Terminated scouting-loop, saving reads to database.")
    except Exception as e:
        print(f"Exception {e} resulted in a crash.")
    # This runs before the script fully closes.
    finally:
        print(f"{skin_name} scraping loop ended.")
        
if __name__ == "__main__":
    testing = False
    if testing:
        def is_float(value):
            return value.replace('.', '', 1).isdigit()
        user_input = input("Please input a skin's name (Gun Name | Finish Name):\n")
        temp_name = user_input.strip()
        while not user_input.isdigit():
            user_input = input("\nPlease input a wear level 0-4:\n").strip()

        wlevel = int(user_input)
        user_input = ""

        while not is_float(user_input):
            user_input = input("\nPlease enter the maximum float:\n").strip()
        maximum_float = float(user_input)

        user_input = input("\nPlease enter the maximum price in CAD:\n").strip()
        maximum_price = float(user_input)
    else:
        temp_name = "Dual Berettas | Polished Malachite"
        wlevel = 1
        maximum_float = 0.086
        maximum_price = 0.45
    scouting_loop(testing, temp_name, wlevel, maximum_float, maximum_price)