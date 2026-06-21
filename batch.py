import time
import os
import logging
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, Field
from typing import List
from tenacity import retry, wait_exponential_jitter, retry_if_exception_type
from utilities import load_all_data_listings_db

logger = logging.getLogger("Batching")

class SkinDeal(BaseModel):
    listing_id: str = Field(description="The unique alphanumeric identifier of the specific listing row.")
    skin_name: str = Field(description="The exact name of the skin this listing belongs to (e.g., 'AK-47 | Redline (Field-Tested)').")
    raw_price: float = Field(description="The current listed price of the asset.")
    raw_float: float = Field(description="The current precise float value of the asset.")
    deal_justification: str = Field(description="A brief 1-sentence analytical breakdown explaining why this listing is mathematically a top-10 deal (e.g., 'Only 0.1% Price Overpay and 4.50 percent under average market value with a very low float value').")

class TopSkinsResponse(BaseModel):
    deals: List[SkinDeal] = Field(description="A strictly ordered array containing exactly the 10 best market deals found in the data, sorted from best to worst.")

@retry(retry=retry_if_exception_type(errors.APIError), wait=wait_exponential_jitter(initial=5, max=200))
def gemini_return_top10(prompt: str):
    best_deals = []
    logger.debug("Sending request to Gemini API")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return best_deals
    try:
        instructions="""
        You are a highly analytical, deterministic Steam Market Valuation Engine for an automated CS trading bot. Your sole purpose is to analyze a provided markdown document containing statistical summaries and tabular listing data for various weapon skins, identify the absolute best financial deals, and return them in a strict JSON format.

        CRITICAL EVALUATION ENGINE CONSTRAINTS:
        1. You must select exactly the top 10 best deals across all skins provided in the context, sorted from the absolute best deal to the fifth-best deal.
        2. A "Best Deal" is determined by a combined evaluation of Price Variance (Price Diff) and Float Variance (Float Diff):
        - Float Difference (Primary Weight): Listings where the Float Diff is highly negative (meaning the wear value is significantly lower/cleaner than the average float for that specific skin).
        - Price Deviation From AVG (Secondary Weight): Listings where the Price Diff is highly negative (meaning the listing price is significantly BELOW the average market price for that specific skin).
        - Exceptionally underpriced items (Very close to 0 Price Overpay) take highest priority. Items with a slightly negative or neutral Price Diff but an exceptionally low float (large negative Float Diff) represent "low-float over-paying opportunities" and should fill out the remaining deals.

        OPERATIONAL SAFETY PIPELINE:
        - Do not make up, hallucinate, or extrapolate listings. Only choose IDs that explicitly exist in the provided Markdown tables.
        - Cross-reference the "Skin Name" header under which a listing resides to ensure you populate the correct skin name for each listing entry in the output array.
        - Treat all numerical comparisons uniformly. A negative variance is good (undervalued/cleaner), a positive variance is bad (overpriced/dirtier).
        - Output must strictly adhere to the provided JSON Schema. Do not include markdown formatting or wrapper code like ```json ... ``` in your raw API payload response if requested to output raw JSON text, or let the SDK handle schema enforcement directly.
        """
        with genai.Client(api_key=api_key) as client:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"), # type: ignore
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instructions,
                    response_mime_type="application/json",
                    response_schema=TopSkinsResponse,
                    temperature=0,
                ),
            )
        print("Worker Thread: Response received successfully from Gemini.")
        
        if response.parsed and hasattr(response.parsed, 'deals'):
            logger.debug(f"Parsed {len(response.parsed.deals)} deals from Gemini response") # type: ignore
            for deal in response.parsed.deals: # type: ignore
                best_deals.append((deal.listing_id, deal.skin_name, deal.raw_price, deal.raw_float, deal.deal_justification))
        else:
            logger.warning("Gemini API evaluated but response parsing failed structural criteria")      
    except errors.APIError as api_err:
        logger.error(f"Gemini Endpoint API Error: {api_err}")
    except Exception as e:
        logger.error(f"Critical exception during Gemini generation: {e}")
    return best_deals

def analyze_batch(db: str, lowest_market_prices: dict[str:float|str]):
    valid_skins = {}
    load_all_data_listings_db(valid_skins, db)
    prompt = ""
    average = lambda num: sum(num) / len(num) if num else 0
    logger.info(f"These are the lowest prices {lowest_market_prices}")
    for skin_name, listings in valid_skins.items():
        lowest_price = lowest_market_prices.get(f"{skin_name}", "n/a")
        price_values = [listings[l].price for l in listings]
        float_values = [listings[l].float_val for l in listings]
        average_price = average(price_values)
        average_float = average(float_values)
        prompt += f"\nSkin Name: {skin_name}\n" 
        prompt += f"- Average Listing Price: {average_price}\n"
        prompt += f"- Lowest Listing Price: {lowest_price}"
        prompt += f"- Average Listing Float Value: {average_float}\n\n"
        prompt += "| Listing ID | Price Deviation From AVG | Price Overpay | Float Diff | Raw Price | Raw Float |\n"
        prompt += "| :--- | ---: | ---: | ---: | ---: | ---: |\n"
        for id, data in listings.items():
            float_diff = data.float_val - average_float
            price_deviation = (data.price - average_price) / average_price * 100
            if type(lowest_price) == float: 
                price_overpay = round((data.price - lowest_price) / lowest_price * 100, 2)
            else:
                price_overpay = "N/A"
            prompt += f"| {id} | {price_deviation:.2f}% | {price_overpay}% | {float_diff:.6f} | {data.price:.2f} | {data.float_val:.6f} |\n"
    if prompt:
        logger.info(f"Analyzing {len(valid_skins)} skins")
        logger.info(prompt)
        result = gemini_return_top10(prompt)
        return result
    else:
        logger.warning("No data available for analysis")
        return []
    
def analyze_batch_loop(db: str, lowest_market_prices: dict[str:float|str]):
    time.sleep(100)
    logger.info("Starting analyze batch loop")
    while True:
        try:
            best_10 = analyze_batch(db, lowest_market_prices)
            logger.info(f"Here are the top {len(best_10)} deals")
            for listing in best_10:
                logger.info(f"DEAL: {listing[1]} | Float: {listing[3]:.6f} | Price: ${listing[2]:.2f} | ID: {listing[0]}")
                logger.info(f"      Reasoning: {listing[4]}")
        except Exception as e:
            logger.error(f"Gemini analysis cycle failed: {e}")
        finally:
            logger.debug("Analysis cycle complete, sleeping 60 minutes")
            time.sleep(3600)

if __name__ == "__main__":
    print()
