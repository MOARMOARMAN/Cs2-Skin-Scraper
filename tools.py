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
adbConnect = sqlite3.connect("analyzed.db")
scraper_session = requests.Session()
scraper_session.get("https://steamcommunity.com/market/")
session_id = scraper_session.cookies.get('sessionid', domain='steamcommunity.com')
if not session_id:
    session_id = "ecfa287520111ed4f64e6d6e" # Your known good ID
    scraper_session.cookies.set('sessionid', session_id, domain='steamcommunity.com')
else:
    print("Session Connected to Steam!")
    print(session_id)
print(api_key)

if api_key:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
else:
    print("Missing Gemini API Key")
    exit()

# Using Gemini 2.5 Flash-Lite as free tier is sufficient

""" model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-lite",
    generation_config={
        "temperature": 0.1,
        "response_mime_type": "application/json"
    },
    system_instruction="""
"""    You are a CS2 skin trading assistant. Analyze price/float data to determine if a tradeup input is a good deal. 
    IMPORTANT: Always classify skins based on these strict boundaries:
    Factory New (0 - 0.0699999), 
    Minimal Wear (0.07 - 0.149999), 
    Field-Tested (0.15 - 0.379999), 
    Well-Worn (0.38 - 0.449999), 
    Battle-Scarred (0.45 - 1). 
    Their float ranges are in the brackets and skins closer to the lower bounds of a range are more valuable.
    Within your reasoning, include, if relevant if the skin is close to the lower bounds. 
    """
""") """



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
headers = {
    "Host": "steamcommunity.com",
    "Origin": "https://steamcommunity.com",
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
cookies = {
    "sessionid": session_id,
    "timezoneName": "America/New_York"
}

def scout(skin_name: str, wear: int, max_float: float, max_price: float):
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
    # Scout the total number of skins
    scout_params = {
        "start": 0,
        "count": 1,
        "currency": 20,
        "language": "english"
    }
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
        "start": 0,
    }]
    # Steam forces 20 listings at a time.
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
        scan_limit = min(int(total_listings * 0.2), 200)
        print(f"Total Listings: {total_listings}. Scanning top: {scan_limit} items")
    elif scout_r.status_code == 429:
        print("Steam rate limit reached.")
        time.sleep(300)
        return []

    for offset in range (0, scan_limit, 20):
        Payload[0]['start'] = offset
        r = scraper_session.post(f"https://steamcommunity.com/market/listings/730/{scout_code}", json=Payload, headers=headers, cookies=cookies)
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
            #print(f"fval: {float_val} | dID: {dID}")
            if float_val < max_float and price / 100 <= max_price:
                availableSkins.append(Skin(listingID, price / 100, assetID, dID, float_val, mkt_pos + 20 * pg))
            #else:
                #print("Too High Float")

        print(f"Processed up to offset {offset + 20}...")
        # Increment to next page
        pg += 1
        time.sleep(random.uniform(3,5))
    # for skin in availableSkins:
        # print(skin.price)
        # print(skin.float_val)
        # print(f"___________________{skin.market_pos}")
    return availableSkins

def analyze_skin_value(scout_results, budget_multiplier: float, max_float: float, wear_level: int, full_results):
    if not scout_results:
        return None
    
    # Calculate the base_price of the skin by finding the cheapest skin.
    # This is called list comprehension.
    base_price = min(s.price for s in scout_results)

    # Filter out the far too expensive skins that are greater than the base_price times the budget multiplier.
    potential_skins = [s for s in scout_results if s.price <= base_price * budget_multiplier]

    if not potential_skins:
        print("No viable skins.")
    
    potential_skins.sort(key=lambda x: x.float_val)
    
    # List of top5 skins to hand over to the model.
    top_5 = potential_skins[:5]

    # Building the prompt to the agent
    # It will return the listingID's of the should be purchased skins.
    market_context = ""
    for i, s in enumerate(top_5):
        market_context += f"Candidate {i+1} has price of {s.price} CAD, float value of {s.float_val} and listingID of {s.listingID}\n"

    all_listings_context = ""
    for i, s in enumerate(full_results):
        all_listings_context += f"Listing {i+1} has price of {s.price} CAD, float value of {s.float_val} and listingID of {s.listingID}\n"
    
    lower_bound = WEAR_RANGES[wears[wear_level]].strip("()").split("-")[0].strip()

    prompt = f"""
    Current Market Floor: ${base_price:.2f}
    Maximum float: {max_float}

    All Market Listings including Candidates:
    {all_listings_context}

    Candidates:
    {market_context}

    Decision Criteria:
    1. Percentile: Where does the float sit within the {WEAR_RANGES[wears[wear_level]]}?
    2. Value: Is the float significantly lower for a negligible price increase?
    3. Floor proximity: How close is it to the absolute minimum of {lower_bound}?

    Task: Provide me with the top 3 best value skins out of the 5 provided. Numerical evidence required: price/float relationships

    Example JSON structure to return:
    [
        {{
            "listingID": "123",
            "reasoning": "this skin had a very low float compared to other skins and was only slightly more expensive ($0.03).",
            "rank": 1
        }},
        {{
            "listingID": "456",
            "reasoning": "this skin is decently low float and is at the base price.",
            "rank": 2
        }},
        {{
            "listingID": "342",
            "reasoning": "this skin is under the max float and is nearly base price.",
            "rank": 3
        }}
    ]
    """
    # instead i want the code to only mark ids off when they have been analyzed.
    try:
        #print(prompt)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.1  # Lower temperature = more consistent formatting
            }
        )
        #print(response.text)
        jsonResult = json.loads(response.text)
        #print(jsonResult)

        top3IDS = {s.get('listingID') for s in jsonResult}
        print(f"\nBest 3 skins of the Batch! ({len(jsonResult)}) skins found.")
        for skin in jsonResult:
            print(f"At rank {skin.get('rank')}, is listing {skin.get('listingID')} because:\n   {skin.get('reasoning')}")
            for s in top_5:
                if skin.get('listingID') == s.listingID:
                    analyzed_listings[str(s.listingID)] = s
                    #print(analyzed_listings)
                    #print(f"-----> [Price: {s.price} | Float Value: {s.float_val}]")
        
        # Set the last analyzed time
        for skin in top_5:
            if skin.listingID not in top3IDS:
                cooldown_listings[str(skin.listingID)] = time.time()
    except Exception as e:
        print(f"Analysis Error: {e}")

# Dictionary containing all of the information on the skins
# Stored as listingID for key
# Skin Object as the value.
analyzed_listings = {}

# Dictionary mapping cooldown times with the listingID
cooldown_listings = {}

testing = False
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
    maximum_float = 0.085
    maximum_price = 0.45
table_name = skin_name + wears[wlevel]
table_name = re.sub(r'[^0-9a-zA-Z]', '', table_name)
table_name = f'"{table_name}"'

if dbReadWrite:
    adbConnect.execute(f"CREATE table if NOT EXISTS {table_name} (ListingID TEXT PRIMARY KEY, Price REAL, AssetID TEXT, dID TEXT, float_val REAL, market_pos INTEGER)")
# Load data from past analysis.
adbPastCur = adbConnect.execute(f"SELECT ListingID, Price, AssetID, dID, float_val, market_pos FROM {table_name}")
past_analyzed = adbPastCur.fetchall()
for values in past_analyzed:
    temporary_skin = Skin(*values)
    analyzed_listings[temporary_skin.listingID] = temporary_skin
    print(f"Loaded listing {temporary_skin.listingID}")
while True:
    try:
        scout_results = scout(skin_name, wlevel, maximum_float, maximum_price)
        print(f"THESE ARE THE ANALYZED LISTINGS {analyzed_listings}")
        if scout_results:
            existing_IDS = [s.listingID for s in scout_results]

            # Update the analyzed_listings
            for listingID in list(analyzed_listings.keys()):
                if listingID not in existing_IDS:
                    print(f"Listing {listingID} no longer present")
                    if dbReadWrite:
                        adbConnect.execute(f"DELETE FROM {table_name} WHERE ListingID = ?", (listingID,))
                    del analyzed_listings[listingID]
                else:
                    print(f"Listing {listingID} is still present")
            if dbReadWrite:
                adbConnect.commit()
            currentTime = time.time()
            # 2. Check for NEW, un-analyzed skins
            new_candidates = [s for s in scout_results if (str(s.listingID) not in analyzed_listings and (currentTime - cooldown_listings.get(str(s.listingID), 0)) > 600)]
            #for s in new_candidates:
                #print(s.listingID)

            if new_candidates:
                # 3. Call the Analysis function
                analyze_skin_value(new_candidates, 1.1, maximum_float, wlevel, scout_results)
            else: 
                print("No new skins this update")
        print("Loop complete. Resting to avoid rate limits...")
        for lID in analyzed_listings:
            skin = analyzed_listings[lID]
            if dbReadWrite:
                adbConnect.execute(f"INSERT OR REPLACE INTO {table_name} VALUES(?, ?, ?, ?, ?, ?)", (skin.listingID, skin.price, skin.assetID, skin.dID, skin.float_val, skin.market_pos))
            print(f"Listing ID: {skin.listingID} | Price: {skin.price} | Float Value: {skin.float_val} | Market Position: {skin.market_pos}")
        if dbReadWrite:
            adbConnect.commit()
        time.sleep(random.randint(45, 60))
    except Exception as e:
        print(f"Loop Failed: {e}")
        time.sleep(random.randint(60,120))
