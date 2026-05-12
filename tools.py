import requests
import sqlite3
import time
from google import genai
import os
from dotenv import load_dotenv
import json

api_key = os.getenv("GEMINI_API_KEY")
user_agent = os.getenv("STEAM_USER_AGENT")
adbConnect = sqlite3.connect("analyzed.db")
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
# Header to let steam know this isn't a typical bot request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scout(skin_name: str, wear: int, max_float: float):
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
    scout_r = requests.get(f"https://steamcommunity.com/market/listings/730/{search_name}/render", params=scout_params, headers=headers)

    if scout_r.status_code == 200:
        total_listings = scout_r.json().get('total_count', 0)
        scan_limit = min(int(total_listings * 0.2), 1000)
        print(f"Total Listings: {total_listings}. Scanning top: {scan_limit} items")
    if scout_r.status_code == 429:
        print("Steam rate limit reached.")
        time.sleep(300)
        return []

    for offset in range (0, scan_limit, 100):
        params = {
            "start": offset,
            "count": 100,
            "currency": 20,
            "language": "english"
        }

        r = requests.get(f"https://steamcommunity.com/market/listings/730/{search_name}/render", params=params, headers=headers)

        data = r.json()
        for mkt_pos, item in enumerate(data['listinginfo'].items()):
            # Tuple 
            # steamitemID = 0
            # dict containing everything else = 1
            # dict_keys(['listingid', 'price', 'fee', 'publisher_fee_app', 'publisher_fee_percent', 'currencyid', 
            # 'steam_fee', 'publisher_fee', 'converted_price', 'converted_fee', 'converted_currencyid', 'converted_steam_fee', 
            # 'converted_publisher_fee', 'converted_price_per_unit', 'converted_fee_per_unit', 'converted_steam_fee_per_unit', 
            # 'converted_publisher_fee_per_unit', 'asset'])
            listingID = item[0]
            #print(item[1].keys())
            price = item[1].get('converted_publisher_fee', 0) + item[1].get('converted_price', 0) + item[1].get('converted_steam_fee', 0)
            if price:
                price = float(price)
            else:
                continue
            
            assetID = item[1].get('asset').get('id')

            # Accesses the asset_properties' 6th property for the D code.
            asset_data = data.get('assets', {}).get('730', {}).get('2', {}).get(assetID)
            if not asset_data:
                print(f"Listing {listingID} is not able to be accessed, Skipping...")
                continue

            properties = asset_data.get('asset_properties')
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

            if float_val < max_float:
                availableSkins.append(Skin(listingID, price / 100, assetID, dID, float_val, mkt_pos + 100 * pg))
            #else:
                #print("Too High Float")
            # print(availableSkins[i].listingID)
            # print(availableSkins[i].price)
            # print(availableSkins[i].assetID)
            # print(availableSkins[i].dID)
            # print(availableSkins[i].float)

        print(f"Processed up to offset {offset + 100}...")
        # Increment to next page
        pg += 1
        time.sleep(10)
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
adbConnect.execute("CREATE table if NOT EXISTS 'Analyzed Skins' "
"(ListingID TEXT PRIMARY KEY, Price REAL, AssetID TEXT, dID TEXT, float_val REAL, market_pos INTEGER)")
# Load data from past analysis.
adbPastCur = adbConnect.execute("SELECT ListingID, Price, AssetID, dID, float_val, market_pos FROM 'Analyzed Skins'")
past_analyzed = adbPastCur.fetchall()
for values in past_analyzed:
    temporary_skin = Skin(*values)
    analyzed_listings[temporary_skin.listingID] = temporary_skin
while True:
    try:
        scout_results = scout(skin_name, wlevel, maximum_float)
        print(f"THESE ARE THE ANALYZED LISTINGS {analyzed_listings}")
        if scout_results:
            existing_IDS = [s.listingID for s in scout_results]

            # Update the analyzed_listings
            for listingID in list(analyzed_listings.keys()):
                if listingID not in existing_IDS:
                    print(f"Listing {listingID} no longer present")
                    adbConnect.execute("DELETE FROM 'Analyzed Skins' WHERE ListingID = ?", (listingID,))
                    del analyzed_listings[listingID]
            adbConnect.commit()
            currentTime = time.time()
            # 2. Check for NEW, un-analyzed skins
            new_candidates = [s for s in scout_results if (str(s.listingID) not in analyzed_listings and (currentTime - cooldown_listings.get(str(s.listingID), 0)) > 600)]
            #for s in new_candidates:a45
                #print(s.listingID)

            if new_candidates:
                # 3. Call the Analysis function
                analyze_skin_value(new_candidates, 1.1, maximum_float, wlevel, scout_results)
            else: 
                print("No new skins this update")
        print("Loop complete. Resting to avoid rate limits...")
        for lID in analyzed_listings:
            skin = analyzed_listings[lID]
            adbConnect.execute("INSERT OR REPLACE INTO 'Analyzed Skins' VALUES(?, ?, ?, ?, ?, ?)", (skin.listingID, skin.price, skin.assetID, skin.dID, skin.float_val, skin.market_pos))
            print(f"Listing ID: {skin.listingID} | Price: {skin.price} | Float Value: {skin.float_val} | Market Position: {skin.market_pos}")
        adbConnect.commit()
        time.sleep(30)
    except Exception as e:
        print(f"Loop Failed: {e}")
        time.sleep(60)
