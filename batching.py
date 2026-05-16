import sqlite3
import time
import random
adbConnect = sqlite3.connect("analyzed.db")
adbCursor = adbConnect.execute("SELECT name FROM sqlite_master WHERE type='table';")
tracked_tables = [item[0] for item in adbCursor.fetchall()]
overpayPercent = 0.15
adbFloorPriceCursor = adbConnect.execute(f"SELECT MIN(Price) FROM '{tracked_tables[0]}'")
floor_price = adbFloorPriceCursor.fetchone()[0]
max_price = floor_price * (1 + overpayPercent)
max_price = round(max_price, 2)
