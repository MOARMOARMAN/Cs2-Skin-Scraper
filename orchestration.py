import time
import logging

from scouting import scouting_loop, create_table_db
from batching import analyze_batch_loop
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    DB_NAME = "analyzed.db"
    load_dotenv()
    logger.info("Starting CS:GO Trading Bot...")
    create_table_db(DB_NAME)
    logger.info(f"Database initialized: {DB_NAME}")
    # List of skins
    # skins are represented by an array [name, max_price, max_float]
    # ["AK-47 | Ice Coaled", 20, 0.083], ["Dual Berettas | Polished Malachite", 0.5, 0.085], ["SG 553 | Basket Halftone", 0.6, 0.06]
    skins = []
    user_input = input("Skin name / Max Price / Max Float (Type ! to stop entering)\n")
    while user_input != "!":
        try:
            skin_name, max_price, max_float = user_input.split("/")
            skin_name = skin_name.strip()
            max_price = float(max_price.strip())
            max_float = float(max_float.strip())
            skins.append([skin_name, max_price, max_float])
            logger.info(f"Added skin to monitor: {skin_name} with max price {max_price} and max float {max_float}")
            user_input = input("\nSkin name / Max Price / Max Float (Type ! to stop entering)\n")
        except ValueError:
            logger.error("Invalid input format. Please enter in the format: Skin name / Max Price / Max Float")
            user_input = input("\nSkin name / Max Price / Max Float (Type ! to stop entering)\n")
    logger.info(f"Monitoring {len(skins)} skins with {len(skins) + 1} worker threads")
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
            logger.info(f"Spawning scouting thread for {skin[0]} (wear level {wlevel})")
            executor.submit(scouting_loop, False, skin[0], wlevel, float_max, skin[1])
