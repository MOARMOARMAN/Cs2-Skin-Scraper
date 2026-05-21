import requests
import sqlite3
import time
import re
from google import genai
import os
from dotenv import load_dotenv
import json
import random

api_key = os.getenv("GEMINI_API_KEY")
user_agent = os.getenv("STEAM_USER_AGENT")
print(api_key)

if api_key:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
else:
    print("Missing Gemini API Key")
    exit()

class Skin:
    def __init__(self, listingID, price, assetID, dID, float_val, market_pos):
        self.assetID = assetID
        self.listingID = listingID
        self.price = price
        self.dID = dID
        self.float_val = float_val
        self.market_pos = market_pos
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

def scout(skin_name: str, wear: int, max_float: float, max_price: float, scraper_session: requests.Session, cookies: dict):
    # List of availableSkins that will be returned.
    availableSkins = []
    # Page number
    pg = 0

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
        scan_limit = min(int(total_listings * 0.2), 140)
        print(f"Total Listings: {total_listings}. Scanning top: {scan_limit} items")
    elif scout_r.status_code == 429:
        print("Steam rate limit reached.")
        time.sleep(300)
        return []

    for offset in range (0, scan_limit, 20):
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
            asset_data = item['asset']
            assetID = asset_data['assetid']
            properties = asset_data['asset_properties']
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
                converted_price = price /100
            print(f"CONVERTED PRICE IN CAD: CA${converted_price}")
            if float_val < max_float:
                availableSkins.append(Skin(listingID, converted_price, assetID, dID, float_val, mkt_pos + 20 * pg))
            #else:
                #print("Too High Float")

        print(f"Processed up to offset {offset + 20}...")
        # Increment to next page
        pg += 1
        time.sleep(random.uniform(10,20))
    # for skin in availableSkins:
        # print(skin.price)
        # print(skin.float_val)
        # print(f"___________________{skin.market_pos}")
    return availableSkins

def scouting_loop(isTesting: bool, skin_name: str, wlevel: int, maximum_float: float, maximum_price: float):
    # Dictionary containing all of the information on the skins
    # Stored as listingID for key
    # Skin Object as the value.
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

    table_name = skin_name + wears[wlevel]
    table_name = re.sub(r'[^0-9a-zA-Z]', '', table_name)
    table_name = f'"{table_name}"'
    dbReadWrite = not isTesting
    if dbReadWrite:
        adbConnect.execute(f"CREATE table if NOT EXISTS {table_name} (ListingID TEXT PRIMARY KEY, Price REAL, AssetID TEXT, dID TEXT, float_val REAL, market_pos INTEGER)")
    # Load data from past analysis.
    adbPastCur = adbConnect.execute(f"SELECT ListingID, Price, AssetID, dID, float_val, market_pos FROM {table_name}")
    past_analyzed = adbPastCur.fetchall()
    for values in past_analyzed:
        temporary_skin = Skin(*values)
        valid_listings[temporary_skin.listingID] = temporary_skin
        print(f"Loaded listing {temporary_skin.listingID}")
    while True:
        try:
            scout_results = scout(skin_name, wlevel, maximum_float, maximum_price, scraper_session, cookies)
            print(f"THESE ARE THE VALID LISTINGS {valid_listings}")
            if scout_results:
                existing_IDS = [s.listingID for s in scout_results]
                print(existing_IDS)
                # Update the valid_listings
                print("LISTING UPDATE _______________________________________________________________________")
                # Must loop over a list of the keys because the valid_listings dictionary is being modified during the loop
                for listingID in list(valid_listings):
                    if listingID not in existing_IDS:
                        print(f"Listing {listingID} no longer present")
                        if dbReadWrite:
                            adbConnect.execute(f"DELETE FROM {table_name} WHERE ListingID = ?", (listingID,))
                        del valid_listings[listingID]
                    else:
                        print(f"Listing {listingID} is still present")
                if dbReadWrite:
                    adbConnect.commit()
                for s in scout_results:
                    valid_listings[s.listingID] = s
            print("Loop complete. Resting to avoid rate limits...")
            for index, lID in enumerate(valid_listings):
                skin = valid_listings[lID]
                if dbReadWrite:
                    adbConnect.execute(f"INSERT OR REPLACE INTO {table_name} VALUES(?, ?, ?, ?, ?, ?)", (skin.listingID, skin.price, skin.assetID, skin.dID, skin.float_val, skin.market_pos))
                print(f"{index + 1} Listing ID: {skin.listingID} | Price: {skin.price} | Float Value: {skin.float_val} | Market Position: {skin.market_pos}")
            if dbReadWrite:
                adbConnect.commit()
            time.sleep(random.randint(45, 60))
        except Exception as e:
            print(f"Loop Failed: {e}")
            time.sleep(random.randint(60,120))

testing = True
dbReadWrite = not testing
if not testing:
    def is_float(value):
        return value.replace('.', '', 1).isdigit()
    user_input = input("Please input a skin's name (Gun Name | Finish Name):\n")
    skin_name = user_input.strip()
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
    skin_name = "Dual Berettas | Polished Malachite"
    wlevel = 1
    maximum_float = 0.083
    maximum_price = 0.45
scouting_loop(testing, skin_name, wlevel, maximum_float, maximum_price)