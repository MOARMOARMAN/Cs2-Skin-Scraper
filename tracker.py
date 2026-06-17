import logging
from scraping import scouting_loop
from utilities import (
    create_skin_table_db, 
    clear_db_skins, 
    get_skin_code_db, 
    price_check, 
    wears, 
    what_wear,
    LISTINGS_DB
)
from batch import analyze_batch_loop
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("Tracker")

if __name__ == "__main__":
    DB_NAME = LISTINGS_DB
    logger.info("Starting CS:GO Trading Bot...")
    create_skin_table_db(DB_NAME)
    logger.info(f"Database initialized: {DB_NAME}")
    # Ask for skin name and max_float -> show skin price and ask for max_price
    # List of skins
    # skins are represented by an array [name, max_price, max_float]
    # ["AK-47 | Ice Coaled", 20, 0.083], ["Dual Berettas | Polished Malachite", 0.5, 0.085], ["SG 553 | Basket Halftone", 0.6, 0.06]
    # AK-47 | Ice Coaled / 0.09
    # AK-47 | Ice Coaled / 0.185
    # AK-47 | Slate / 0.09
    # Dual Berettas | Polished Malachite / 0.085
    # SG 553 | Basket Halftone / 0.06
    # 
    skins = []
    lowest_prices = {}
    user_input = input("Skin name / Max Float (Type ! to stop entering)\n")
    while user_input != "!":
        try:
            skin_name, max_float = user_input.split("/")
            skin_name = skin_name.strip()
            max_float = float(max_float.strip())
            wlevel = what_wear(max_float)
            cur_lowest_price = price_check(skin_name, wlevel, get_skin_code_db)
            if not cur_lowest_price:
                print(f"There are currently no listings for {skin_name} {wears[wlevel]}")
                continue
            max_price = 0
            while user_input != "no" and max_price == 0:
                user_input = input(f"The current lowest price for {skin_name} at a wear of {wears[wlevel]} is ${cur_lowest_price} CAD\nPlease input a price maximum in CAD or type 'no' if you don't want this skin: ")
                try:
                    max_price = float(user_input.strip())
                except:
                    if user_input != "no":
                        print("invalid input")
            if user_input == "no":
                user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
                continue
            lowest_prices[f"{skin_name} {wears[wlevel]}"] = cur_lowest_price
            skins.append([skin_name, max_price, max_float, wlevel])
            logger.info(f"Added skin to monitor: {skin_name} with max price {max_price} and max float {max_float} and wear {wears[wlevel]}")
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
                keepers = [f"{skin[0]} {wears[skin[3]]}" for skin in skins]
                logger.info(f"These are the keepers {keepers}")
                clear_db_skins(DB_NAME, keepers)
        except Exception as e:
            logger.error(f"Enter a letter dude. Exception {e}")
    
    logger.info(f"Monitoring {len(skins)} skins with {len(skins) + 1} worker threads")
    with ThreadPoolExecutor(max_workers=len(skins) + 1) as executor:
        executor.submit(analyze_batch_loop, DB_NAME, lowest_prices)

        for skin in skins:
            logger.info(f"Spawning scouting thread for {skin[0]} (wear level {skin[3]})")
            executor.submit(scouting_loop, False, skin[0], skin[3], skin[2], skin[1])
