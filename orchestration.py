import time

from scouting import scouting_loop, create_table_db
from batching import analyze_batch_loop
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
if __name__ == "__main__":
    DB_NAME = "analyzed.db"
    load_dotenv()
    create_table_db(DB_NAME)
    # List of skins
    # skins are represented by an array [name, max_price, max_float]
    skins = [["AK-47 | Ice Coaled", 20, 0.083], ["Dual Berettas | Polished Malachite", 0.5, 0.085], ["SG 553 | Basket Halftone", 0.55, 0.055]]
    with ThreadPoolExecutor(max_workers=len(skins) + 1) as executor:
        executor.submit(analyze_batch_loop, DB_NAME)

        for skin in skins:
            float_max = skin[2]
            wlevel = 0
            if float_max < 0.07:
                wlevel = 0
            elif float_max < 0.15:
                wlevel = 1
            elif float_max < 0.38:
                wlevel = 2
            elif float_max < 0.45:
                wlevel = 3
            else:
                wlevel = 4
            executor.submit(scouting_loop, False, skin[0], wlevel, float_max, skin[1])
