import sqlite3
import time
import random
import os
from dotenv import load_dotenv
from contextlib import closing
from scouting import skinData
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, Field
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

class SkinDeal(BaseModel):
    listing_id: str = Field(description="The unique alphanumeric identifier of the specific listing row.")
    skin_name: str = Field(description="The exact name of the skin this listing belongs to (e.g., 'AK-47 | Redline (Field-Tested)').")
    raw_price: float = Field(description="The current listed price of the asset.")
    raw_float: float = Field(description="The current precise float value of the asset.")
    deal_justification: str = Field(description="A brief 1-sentence analytical breakdown explaining why this listing is mathematically a top-5 deal (e.g., 'Priced $4.50 under average market value with a cleaner-than-average float').")

class TopSkinsResponse(BaseModel):
    deals: List[SkinDeal] = Field(description="A strictly ordered array containing exactly the 5 best market deals found in the data, sorted from best to worst.")

def load_all_data_db(valid_skins: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        print("LOADING")
        try:
            stored_skins = conn.execute(f"SELECT skin_name, listing_ID, price, d_ID, float_val FROM skin_listings").fetchall()
            for skin in stored_skins:
                #print(f"{skin}")
                if skin[0] not in valid_skins:
                    valid_skins[skin[0]] = {}
                valid_skins[skin[0]][skin[1]] = skinData(dID=skin[3], float_val=skin[4], price=skin[2])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print(f"table skin_listings doesn't exist yet")
            else:
                raise   

@retry(retry=retry_if_exception_type(errors.APIError), wait=wait_exponential_jitter(initial=5, max=200))
def gemini_return_top5(prompt: str):
    best_deals = []
    print("gemini")
    api_key = os.getenv("GEMINI_API_KEY")
    print(api_key)
    try:
        client = genai.Client(api_key=api_key)
        instructions="""
        You are a highly analytical, deterministic Steam Market Valuation Engine for an automated CS trading bot. Your sole purpose is to analyze a provided markdown document containing statistical summaries and tabular listing data for various weapon skins, identify the absolute best financial deals, and return them in a strict JSON format.

        CRITICAL EVALUATION ENGINE CONSTRAINTS:
        1. You must select exactly the top 5 best deals across all skins provided in the context, sorted from the absolute best deal to the fifth-best deal.
        2. A "Best Deal" is determined by a combined evaluation of Price Variance (Price Diff) and Float Variance (Float Diff):
        - Float Difference (Primary Weight): Listings where the Float Diff is highly negative (meaning the wear value is significantly lower/cleaner than the average float for that specific skin).
        - Price Difference (Secondary Weight): Listings where the Price Diff is highly negative (meaning the listing price is significantly BELOW the average market price for that specific skin).
        - Exceptionally underpriced items (large negative Price Diff) take highest priority. Items with a slightly negative or neutral Price Diff but an exceptionally low float (large negative Float Diff) represent "low-float over-paying opportunities" and should fill out the remaining deals.

        OPERATIONAL SAFETY PIPELINE:
        - Do not make up, hallucinate, or extrapolate listings. Only choose IDs that explicitly exist in the provided Markdown tables.
        - Cross-reference the "Skin Name" header under which a listing resides to ensure you populate the correct skin name for each listing entry in the output array.
        - Treat all numerical comparisons uniformly. A negative variance is good (undervalued/cleaner), a positive variance is bad (overpriced/dirtier).
        - Output must strictly adhere to the provided JSON Schema. Do not include markdown formatting or wrapper code like ```json ... ``` in your raw API payload response if requested to output raw JSON text, or let the SDK handle schema enforcement directly.
        """
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
            system_instruction=instructions,
            response_mime_type="application/json",
            response_schema=TopSkinsResponse,
            temperature=0.1,
            ),
        )
        print(response.text)
        for deal in response.parsed.deals:
            best_deals.append((deal.listing_id, deal.skin_name, deal.raw_price, deal.raw_float, deal.deal_justification))
        client.close()
    except Exception as e:
        print(f"gemini error: {e}")
    return best_deals

def analyze_batch(db: str):
    valid_skins = {}
    load_all_data_db(valid_skins, db)
    prompt = ""
    average = lambda num: sum(num) / len(num) if num else 0

    for skin_name, listings in valid_skins.items():
        price_values = [listings[l].price for l in listings]
        float_values = [listings[l].float_val for l in listings]
        average_price = average(price_values)
        average_float = average(float_values)
        prompt += f"\nSkin Name: {skin_name}\n" 
        prompt += f"- Average Listing Price: {average_price}\n"
        prompt += f"- Average Listing Float Value: {average_float}\n\n"
        prompt += "| Listing ID | Price Diff | Float Diff | Raw Price | Raw Float |\n"
        prompt += "| :--- | ---: | ---: | ---: | ---: |\n"
        for id, data in listings.items():
            float_diff = data.float_val - average_float
            price_diff = data.price - average_price
            prompt += f"| {id} | {price_diff:.2f} | {float_diff:.6f} | {data.price:.2f} | {data.float_val:.6f} |\n"
    print("__________________________________________________________________________________________________________")
    print(prompt)
    if prompt:
        return gemini_return_top5(prompt)
    else:
        return []
    
def analyze_batch_loop(db: str):
    time.sleep(10)
    print("Starting analyze batch loop")
    while True:
        try:
            analyze_batch(db)
        except Exception as e:
            print(f"Gemini analysis cycle failed: {e}")
        finally:
            time.sleep(600)

if __name__ == "__main__":
    DB_NAME = "analyzed.db"
    print(analyze_batch(DB_NAME))
