# Dictionary mapping cooldown times with the listingID
cooldown_listings = {}

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