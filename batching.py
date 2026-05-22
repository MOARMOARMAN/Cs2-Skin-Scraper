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
adbFloorPriceCursor = adbConnect.execute(f"SELECT MIN(Price) FROM '{tracked_tables[0]}'")
floor_price = adbFloorPriceCursor.fetchone()[0]
max_price = floor_price * (1 + overpayPercent)
max_price = round(max_price, 2)
# Skin_name : "ID: | Price: | Float Value: "
available_skins = {}
prompt = ""
for table in tracked_tables:
    valid_skins = []
    prompt += f"\nSkin Name: {table}\n"
    rows = adbConnect.execute(f"SELECT ListingID, Price, float_val FROM [{table}] ORDER BY float_val ASC LIMIT 5").fetchall()
    if rows:
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
print(available_skins)

print(prompt)
