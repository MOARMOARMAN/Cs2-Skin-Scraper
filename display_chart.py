from utilities import (
    load_for_skin_name_all_historical_listings_db,
    load_all_skin_names_all_historical_data_db,
    LISTINGS_DB
)

if __name__ == "__main__":
    historical_options = load_all_skin_names_all_historical_data_db(LISTINGS_DB)
    options = " --- ".join([f'"{name[0]}"' for name in historical_options])
    print(f"These are your options: {options}\n")
    skin_name = input("Please enter your choice: ")
    listings_for_skin = load_for_skin_name_all_historical_listings_db(skin_name, LISTINGS_DB)
    print(listings_for_skin)
    print(len(listings_for_skin))