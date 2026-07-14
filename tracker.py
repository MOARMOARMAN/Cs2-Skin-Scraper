# CS2 Market Data Pipeline
# Copyright (C) 2026 Charles Wang
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
import threading
import msvcrt
import sys
import time
import random
from scraper import scouting_loop
from display_chart import update_wear_bucket_data_for_skin
from utilities import (
    create_skin_listings_table_db, 
    clear_db_skins, 
    wears, 
    what_wear,
    LISTINGS_DB,
    SKIN_DATA_DB,
    HISTORICAL_DATA_DB,
    RELEVANT_CURRENCIES,
    create_tracked_table_db,
    delete_entry_tracked_table_db,
    get_tracked_listings_table_db,
    get_lowest_price_skin_data_db,
    insert_tracked_table_db,
    create_all_historical_listings_table_db,
    create_currency_exchange_table_db,
    update_currency_exchange_table_db,
    get_currency_exchange_rates_for_currency_db,
    get_exchange_rate,
    get_price_for_name_and_float_skin_data_db,
    update_currency_exchange_rates,
    seconds_to_time,
    WEAR_ABBRIEVIATIONS,
    CURRENCY_EXCHANGE_RATE,
    WEAR_TO_MAX,
    MAX_SCRAPE_TIME
)
from batch import analyze_batch_overpay_loop
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("Tracker")

def prompt_actions_user(actions: dict):
    actions_list = " | ".join(actions)
    user_in = input(f"\nCommands {actions_list} | continue\n")
    return user_in

def print_tracked():
    tracked = get_tracked_listings_table_db(LISTINGS_DB)
    print("\nThese are the skins that are currently being tracked:")
    for skin in tracked:
        print(f"id: {skin[0]} | skin_name: {skin[1]} | max_float: {skin[2]} | max_price: {skin[3]}$")

def add_skins(lowest_prices: dict):
    user_input = ""
    while user_input != '!':
        try:
            print_tracked()
            user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
            if user_input == "!":
                print_tracked()
                return
            skin_name, max_float = user_input.split("/")
            skin_name = skin_name.strip()
            max_float = max_float.strip()
            print(f"{max_float} type: {type(max_float)}")
            try:
                max_float = float(max_float.strip())
                wlevel = what_wear(max_float)
            except ValueError: 
                if str(max_float).lower() in WEAR_ABBRIEVIATIONS:
                    wlevel = WEAR_ABBRIEVIATIONS.index(max_float)
                    max_float = WEAR_TO_MAX[wlevel]
                else:
                    logger.error("Invalid input format. Please enter in the format: Skin name / Max Float")
                    user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")
                    continue

            cur_lowest_price = get_lowest_price_skin_data_db(skin_name, wlevel, SKIN_DATA_DB)
            user_input = input(f"The current lowest price for {skin_name} at a wear of {wears[wlevel]} is ${cur_lowest_price} CAD\nPlease input a price maximum in CAD: ")
            max_price = ""
            while not isinstance(max_price, float):
                try:
                    max_price = float(user_input.strip())
                except ValueError:
                    print("Invalid Price")
                    user_input = input(f"The current lowest price for {skin_name} at a wear of {wears[wlevel]} is ${cur_lowest_price} CAD\nPlease input a price maximum in CAD: ")
            lowest_prices[f"{skin_name} {wears[wlevel]}"] = cur_lowest_price
            insert_tracked_table_db(LISTINGS_DB, [[skin_name, max_float, max_price]])
            logger.info(f"Added skin to monitor: {skin_name} with max price {max_price} and max float {max_float} and wear {wears[wlevel]}")
        except ValueError:
            logger.error("Invalid input format. Please enter in the format: Skin name / Max Float")
            user_input = input("\nSkin name / Max Float (Type ! to stop entering)\n")

def remove_skins():
    ids = []
    user_input = ""
    while user_input != "!":
        try:
            print_tracked()
            user_input = input("\n\nWhich skin would you like to delete? (Type ! to stop entering)\nEnter the ID number: ")
            if user_input == "!":
                print_tracked()
                return
            delete_entry_tracked_table_db(int(user_input), LISTINGS_DB)
        except ValueError:
            print("Please enter a valid ID number!\n\n")

def update_exchange_rates_input():
    print(CURRENCY_EXCHANGE_RATE)
    user_input = ""
    while user_input not in RELEVANT_CURRENCIES:
        user_input = input("\nPlease input CAD / USD / EUR / HKD / GBP for currency of choice: ").upper()
    
    update_exchange_rates(user_input)
    print(f"The currently used exchange rates for currency {user_input} are:")
    for currency, rate in CURRENCY_EXCHANGE_RATE.items():
        print(f"{currency} to {user_input} is {rate}")

def update_exchange_rates(user_input: str):
    rates = {}
    for currency in RELEVANT_CURRENCIES:
        rates[currency] = get_exchange_rate(currency, user_input)
    print(rates)
    update_currency_exchange_table_db(user_input, rates, SKIN_DATA_DB)
    new_rates = get_currency_exchange_rates_for_currency_db(user_input, SKIN_DATA_DB)
    update_currency_exchange_rates(new_rates)

def recommend_sale_price():
    user_input = ""
    while user_input != "!":
        try:
            user_input = input("\nSkin name / Float (Type ! to stop entering)\n")
            if user_input == "!":
                return
            skin_name, float_val = user_input.split("/")
            skin_name = skin_name.strip()
            float_val = float(float_val.strip()) 
            update_wear_bucket_data_for_skin(skin_name)
            average_price = get_price_for_name_and_float_skin_data_db(skin_name, float_val, SKIN_DATA_DB)
            average_price = round(average_price, 2)
            if average_price:
                print(f"\nThe recommended listing price for {skin_name} at {float_val} is ${average_price}\n")
            else:
                print(f"\nThere is no recommended price for {skin_name} at {float_val} within the database currently.\n")
        except ValueError:
            logger.error("Invalid input format. Please enter in the format: Skin name / Float")
            user_input = input("\nSkin name / Float (Type ! to stop entering)\n")

def help():
    print(f"\nDescriptions of each Tool:")
    print(f"add: Add skins to be tracked by the scraper")
    print(f"remove: Remove skins from the list of tracked skins")
    print(f"exit: Exits the program saving the currently tracked skins.")
    print(f"update exchange rates: Choose the currency that is preferred and updates the exchange rates as of today.")
    print(f"recommendation: Provides you the recommended listing price based on the specific float bucket that a skin belongs to.")
    print(f"continue: Continue to the next step to begin scraping listings. Press ! to exit when the script is running.")

def shutdown_script_after(seconds: float):
    print(f"Shut down after {seconds_to_time(seconds)}")
    sys.exit(0)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8",
        handlers=[
            logging.FileHandler('bot.log', encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logger.info("Starting CS:GO Trading Bot...")
    create_skin_listings_table_db(LISTINGS_DB)
    create_tracked_table_db(LISTINGS_DB)
    create_all_historical_listings_table_db(HISTORICAL_DATA_DB)
    create_currency_exchange_table_db(SKIN_DATA_DB)

    # Create the CURRENCY_EXCHANGE_RATES
    cad_rates = get_currency_exchange_rates_for_currency_db("CAD", SKIN_DATA_DB)
    if len(cad_rates) != len(RELEVANT_CURRENCIES):
        update_exchange_rates("CAD")
    else:
        update_currency_exchange_rates(cad_rates)
    
    # tracked [[id, name, float, price], ...]
    tracked = get_tracked_listings_table_db(LISTINGS_DB)
    skins = [[skin[1], skin[2], skin[3], what_wear(skin[2])] for skin in tracked]
    new_skins = []
    print(f"There are currently {len(skins)} skins being tracked. ")
    lowest_prices = {}
    
    user_actions = {
        "add": lambda: add_skins(lowest_prices),
        "remove": lambda: remove_skins(),
        "help" : lambda: help(),
        "exit" : lambda: sys.exit(0),
        "update exchange rates" : lambda: update_exchange_rates_input(),
        "recommendation" : lambda: recommend_sale_price()
    }
    print_tracked()
    user_input = prompt_actions_user(user_actions)
    while user_input != "continue":
        try:
            user_actions[user_input]()
            user_input = prompt_actions_user(user_actions)
        except Exception as e:
            print(f"Invalid command")
            logger.error(f"Error {e}")
            user_input = prompt_actions_user(user_actions)
        
    if not get_tracked_listings_table_db(LISTINGS_DB):
        logger.error("Empty input and no skins chosen for tracking.")
        exit()
    clear_db_skins(LISTINGS_DB)
    # id, name, float, price
    updated_tracked = get_tracked_listings_table_db(LISTINGS_DB)
    updated_skins = [[skin[1], skin[2], skin[3]] for skin in updated_tracked]

    logger.info(f"Monitoring {len(updated_skins)} skins with {len(updated_skins) + 1} worker threads")
    logger.info(f"These are the updated skins {updated_skins}")
    for num, skin in enumerate(updated_skins):
        logger.info(f"Spawning scouting thread for {skin[0]} at max float of {skin[1]} with max price of {skin[2]}")
        st = threading.Timer(
            interval=random.uniform((num + 1) * 7, (num + 1) * 10),
            function=scouting_loop,
            args=(skin[0], skin[1], skin[2]),
        )
        st.daemon = True
        st.start()
    
    logger.info(f"Spawning batch analysis thread")
    bt = threading.Timer(1000, analyze_batch_overpay_loop)
    bt.daemon = True
    bt.start()


    end_thread = threading.Timer(interval=MAX_SCRAPE_TIME, function=shutdown_script_after, args=(MAX_SCRAPE_TIME,))

    start_time = time.time()
    stop_event = threading.Event()
    print("Press ! to exit the script and all threads.")
    try:
        while True:
            if msvcrt.kbhit(): 
                key = msvcrt.getwch()

                if key == "!" or key == "shift+!":
                    time_elapsed = time.time() - start_time
                    print(f"ending threads after {seconds_to_time(time_elapsed)}")
                    sys.exit(0)
    except KeyboardInterrupt:
        time_elapsed = time.time() - start_time
        print(f"ending threads after {seconds_to_time(time_elapsed)}")
        sys.exit(0)