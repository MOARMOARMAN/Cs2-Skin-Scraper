import sqlite3
import time
import random
from scouting import Skin

adbConnect = sqlite3.connect("analyzed.db")
dbMode = adbConnect.execute("PRAGMA journal_mode=WAL;").fetchone()[0] # This enables Write Ahead Logging which allows multiple cursors to read from a database at once.
print(dbMode)
adbCursor = adbConnect.execute("SELECT name FROM sqlite_master WHERE type='table';")
tracked_tables = [item[0] for item in adbCursor.fetchall()]
overpayPercent = 0.15
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
for table in tracked_tables:
    valid_skins = []
    rows = adbConnect.execute(f"SELECT ListingID, Price, float_val FROM [{table}] ORDER BY float_val ASC LIMIT 5").fetchall()
    prices = [row[1] for row in rows]
    max_price = round(average(prices) * (1 + overpayPercent), 2)
    if rows:
        prompt += f"\nSkin Name: {table} Max Price Willing to Pay: {max_price}\n"
        available_skins[table] = {
            row[0]:{
                'price' : row[1],
                'float_val' : row[2]
            }
            for row in rows
        }
        prompt_lines = [
            f"- ID: {r[0]} | Price: ${r[1]} | Float: {r[2]}"
            for r in rows
        ]
        prompt += "\n".join(prompt_lines) + "\n"
    print(max_price)
print(available_skins)


print(prompt)
