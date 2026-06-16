# What do I want to do?
# I want to scrape data of every single skin that exists.
import sqlite3
from contextlib import closing
import httpx
import random
from httpx import AsyncClient
from utilities import (
    price_check, 
    wears, 
    create_skin_data_table_db, 
    populate_names_skin_data_db, 
    SKIN_DATA_DB, 
    populate_code_skin_data_db, 
    populate_extra_skin_data_db,
    populate_prices_skin_data_db,
    get_skin_code_db
)
import csv
import asyncio
import httpx
from urllib.parse import quote
from bs4 import BeautifulSoup
import sqlite3
import time

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

async def get_skin_code(client: AsyncClient, name: str, semaphore):
    async with semaphore:
        await asyncio.sleep(random.uniform(7.5, 15.5))
        for attempt in range(30):
            await asyncio.sleep(random.uniform(7.5, 15.5))
            try:
                response = await client.get(f"https://steamcommunity.com/market/listings/730/{quote(f"{name} {wears[4]}")}", follow_redirects=True)
                print("Final URL:", response.url)
                code = str(response.url).split("/")[-1]
                return [name, code]
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ConnectTimeout, httpx.ReadTimeout):
                print("Retrying")
                if attempt == 29:
                    print(f"exceeded 8 attempts to connect for {name}")
                    return None

async def get_all_codes(skins: list):
    semaphore = asyncio.Semaphore(3)
    skin_codes_list = []
    skin_code = {}
    for i in range(0, len(skins), 20):
        async with httpx.AsyncClient(headers=headers) as client:
            batch = skins[i:i+20]
            tasks = [get_skin_code(client, skin, semaphore) for skin in batch]
            skin_codes_list.extend(await asyncio.gather(*tasks))
            print(f"batch {i} to {i+20} finished processing")
            await asyncio.sleep(random.uniform(80, 120))
    for name, code in skin_codes_list:
        skin_code[name] = code
    return skin_code

if __name__ == "__main__":
    create_skin_data_table_db(SKIN_DATA_DB)
    with open("skin_names.csv", newline="\n", encoding="UTF-8") as f:
        csvr = csv.DictReader(f, lineterminator="\n", fieldnames=["name", "collection", "min_wear", "max_wear", "rarity"])
        skins = list(csvr)
    prices = {}
    #with closing(sqlite3.connect("skin_data.db", timeout=10)) as conn:
        # results = conn.execute("SELECT skin_name FROM skin_data WHERE skin_code NOT LIKE 'G18%'").fetchall()
    # 1. names = [skin["name"] for skin in skins]
    # 1. populate_names_skin_data_db(names, SKIN_DATA_DB)
    names = [skin["name"] for skin in skins]


    #extra_info = {skin["name"]: [skin["rarity"], skin["collection"], skin["min_wear"], skin["max_wear"]] for skin in skins}e 
    #name_code = asyncio.run(get_all_codes(names))
    #populate_code_skin_data_db(name_code, SKIN_DATA_DB)
    #print(name_code)
    #populate_extra_skin_data_db(extra_info, SKIN_DATA_DB)
    
    for name in names:
        fn = price_check(name, 0, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        mw = price_check(name, 1, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        ft = price_check(name, 2, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        ww = price_check(name, 3, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        bs = price_check(name, 4, get_skin_code_db)
        time.sleep(random.uniform(1, 10))
        prices[name] = [fn, mw, ft, ww, bs]
    populate_prices_skin_data_db(prices, SKIN_DATA_DB)


