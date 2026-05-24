import sqlite3
import time
import random
from contextlib import closing
from scouting import skinData
DB_NAME = "analyzed.db"

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
valid_skins = {}
load_all_data_db(valid_skins, DB_NAME)

available_skins = {}
""" available_skins structure
Skin_name : {
    listingID : {
        price : float,
        float_val : float
    }
}"""
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
print(prompt)