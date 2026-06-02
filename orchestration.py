import time
import logging

from scouting import scouting_loop, create_table_db, clear_db_skins, price_check, wears
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

def what_wear(float_val: float):
    if float_val < 0.07:
        return 0
    elif float_val < 0.15:
        return 1
    elif float_val < 0.38:
        return 2
    elif float_val < 0.45:
        return 3
    else:
        return 4

logger = logging.getLogger(__name__)
if __name__ == "__main__":
    DB_NAME = "analyzed.db"
    load_dotenv()
    logger.info("Starting CS:GO Trading Bot...")
    create_table_db(DB_NAME)
    logger.info(f"Database initialized: {DB_NAME}")
    # Ask for skin name and max_float -> show skin price and ask for max_price
    # List of skins
    # skins are represented by an array [name, max_price, max_float]
    # ["AK-47 | Ice Coaled", 20, 0.083], ["Dual Berettas | Polished Malachite", 0.5, 0.085], ["SG 553 | Basket Halftone", 0.6, 0.06]
    # AK-47 | Ice Coaled / 20 / 0.083
    # Dual Berettas | Polished Malachite / 0.5 / 0.085
    # SG 553 | Basket Halftone / 0.6 / 0.06
    # 
    skins = []
    user_input = input("Skin name / Max Float (Type ! to stop entering)\n")
    while user_input != "!":
        try:
            skin_name, max_float = user_input.split("/")
            skin_name = skin_name.strip()
            max_float = float(max_float.strip())
            wlevel = what_wear(max_float)
            cur_lowest_price = price_check(skin_name, wlevel)
            if not cur_lowest_price:
                print(f"There are currently no listings for {skin_name} {wears[wlevel]}")
                continue
            max_price = 0
            while user_input != "no" and max_price == 0:
                user_input = input(f"The current lowest price for {skin_name} at a wear of {wears[wlevel]} is {cur_lowest_price}\nPlease input a price maximum in CAD or type 'no' if you don't want this skin: ")
                try:
                    max_price = float(user_input.strip())
                except:
                    if user_input != "no":
                        print("invalid input")
            if user_input == "no":
                user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
                continue
            skins.append([skin_name, max_price, max_float])
            logger.info(f"Added skin to monitor: {skin_name} with max price {max_price} and max float {max_float}")
            user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
        except ValueError:
            logger.error("Invalid input format. Please enter in the format: Skin name / Max Float")
            user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
    if not skins:
        logger.error("Empty input and no skins chosen for tracking.")
        exit()
    
    while user_input != "y" and user_input != "n":
        try:
            user_input = input("Would you like to clear other skins from the database? [Y/N]: ").lower()
            if user_input == "y":
                keepers = [skin[0] for skin in skins]
                logger.info(f"These are the keepers {keepers}")
                clear_db_skins(DB_NAME, keepers)
        except Exception as e:
            logger.error(f"Enter a letter dude. Exception {e}")
    
    logger.info(f"Monitoring {len(skins)} skins with {len(skins) + 1} worker threads")
    with ThreadPoolExecutor(max_workers=len(skins) + 1) as executor:
        executor.submit(analyze_batch_loop, DB_NAME)

        for skin in skins:
            float_max = skin[2]
            wlevel = what_wear(float_max)
            logger.info(f"Spawning scouting thread for {skin[0]} (wear level {wlevel})")
            executor.submit(scouting_loop, False, skin[0], wlevel, float_max, skin[1])
