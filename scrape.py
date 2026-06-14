# What do I want to do?
# I want to scrape data of every single skin that exists.
import httpx
import time
import random
from httpx import AsyncClient
from utilities import price_check, insert_listings_info_db, wears, get_skin_code_db
import csv
import asyncio
import httpx
from urllib.parse import quote
import re

# name: str
# collection: str
# min_wear: float
# max_wear: float
# rarity: str
# code: str 
headers = {
    "Origin": "https://steamcommunity.com",
    # Just an Example, is updated later in the scouting loop
    "Referer": "https://steamcommunity.com/market/listings/730/G1802208A0A3004",
}

async def get_skin_code(client: AsyncClient, url: str, semaphore):
    async with semaphore:
        await asyncio.sleep(random.uniform(7.5, 15.5))
        for attempt in range(30):
            await asyncio.sleep(random.uniform(7.5, 15.5))
            try:
                response = await client.get(url, follow_redirects=True)
                print("Final URL:", response.url)
                return str(response.url).split("/")[-1]
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ConnectTimeout, httpx.ReadTimeout):
                print("Retrying")
                if attempt == 29:
                    print(f"exceeded 8 attempts to connect for {url}")
                    return None

async def get_all_codes(skins: list):
    semaphore = asyncio.Semaphore(3)
    codes = []
    for i in range(0, len(skins), 20):
        async with httpx.AsyncClient(headers=headers) as client:
            batch = skins[i:i+20]
            tasks = [get_skin_code(client, f"https://steamcommunity.com/market/listings/730/{quote(f"{skin["name"]} {wears[2]}")}", semaphore) for skin in batch]
            codes.extend(await asyncio.gather(*tasks))
            print(f"batch {i} to {i+20} finished processing")
            await asyncio.sleep(random.uniform(80, 120))
    return codes

if __name__ == "__main__":
    with open("skin_names.csv", newline="\n", encoding="UTF-8") as f:
        csvr = csv.DictReader(f, lineterminator="\n", fieldnames=["name", "collection", "min_wear", "max_wear", "rarity"])
        skins = list(csvr)
    results = asyncio.run(get_all_codes(skins))
    prices = []
    for index, code in enumerate(results):
        fn = price_check(skins[index]["name"], 0, get_skin_code_db, code)
        time.sleep(random.uniform(1, 4))
        mw = price_check(skins[index]["name"], 1, get_skin_code_db, code)
        time.sleep(random.uniform(1, 4))
        ft = price_check(skins[index]["name"], 2, get_skin_code_db, code)
        time.sleep(random.uniform(1, 4))
        ww = price_check(skins[index]["name"], 3, get_skin_code_db, code)
        time.sleep(random.uniform(1, 4))
        bs = price_check(skins[index]["name"], 4, get_skin_code_db, code)
        time.sleep(random.uniform(1, 10))
        prices.append([fn, mw, ft, ww, bs])
    insert_listings_info_db(prices, skins, results, "skin_info.db")


