from asyncio import timeout
import sqlite3
import logging
from contextlib import closing
from .assorted_utils import headers, skinData, get_skin_code

logger = logging.getLogger("CS2-System.DB")

def get_skin_code_db(db_name: str, search_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        with conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS skin_codes (skin_name TEXT PRIMARY KEY, skin_code TEXT)")
            skin_name = search_name.rsplit(" (", 1)[0]
            skin_code = conn.execute(f"SELECT skin_code FROM skin_codes WHERE skin_name = ?", (skin_name,)).fetchone()
            if skin_code:
                logger.info(f"skin code {skin_code[0]} exists for {skin_name}")
                return skin_code[0]
            else:
                try:
                    skin_code = get_skin_code(search_name)
                    conn.execute(f"INSERT INTO skin_codes (skin_name, skin_code) Values(?, ?)", (skin_name, skin_code))
                    logger.info(f"skin code {skin_code} for {skin_name} inserted into {db_name}")
                    return skin_code
                except Exception as e:
                    logger.error(f"Error occurred while fetching scout code for {skin_name}: {e}")
                    return None

def create_skin_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS skin_listings (listing_ID TEXT PRIMARY KEY, skin_name TEXT, d_ID TEXT, float_val REAL, price REAL)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_skin_listings_skin_name ON skin_listings (skin_name)")

def clear_db_skins(db_name: str, skin_names: list):
    if not skin_names:
        logger.error("skin_names provided to clear_db_skins is empty")
        return 404
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            logger.debug(f"Clearing out database by deleting all listings not in {skin_names}")
            placeholders = ",".join("?" for _ in skin_names)
            conn.execute(f"DELETE FROM skin_listings WHERE skin_name NOT IN ({placeholders})", skin_names)
    return 200

def write_listings_db(skin_name: str, valid_listings: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Writing {len(valid_listings)} listings for {skin_name} to database")
            listingData = tuple(
                (lID, skin_name.strip('"'), data.dID, data.float_val, data.price)
                for lID, data in valid_listings.items()
            )
            conn.executemany("INSERT OR REPLACE INTO skin_listings (listing_ID, skin_name, d_ID, float_val, price) VALUES(?, ?, ?, ?, ?)", listingData)

def del_missing_ID_listing_db(skin_name: str, gone_listingIDs: list, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Deleting {len(gone_listingIDs)} missing listings for {skin_name} | {gone_listingIDs}")
            delete_data = ((ID[0], skin_name) for ID in gone_listingIDs)
            conn.executemany("DELETE FROM skin_listings WHERE listing_ID = ? AND skin_name = ?", delete_data)

# For loading data of an individual skin. (scout)
def load_data_listings_db(skin_name: str, valid_listings: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute(f"SELECT listing_ID, price, d_ID, float_val FROM skin_listings WHERE skin_name = ?", (skin_name, )).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} stored listings for {skin_name}")
            for skin in stored_skins:
                valid_listings[skin[0]] = skinData(dID=skin[2], float_val=skin[3], price=skin[1])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning(f"Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

# For loading data of the entire database. (batch)
def load_all_data_listings_db(valid_skins: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute(f"SELECT skin_name, listing_ID, price, d_ID, float_val FROM skin_listings").fetchall()
            logger.debug(f"Loaded {len(stored_skins)} total listings from database")
            for skin in stored_skins:
                if skin[0] not in valid_skins:
                    valid_skins[skin[0]] = {}
                valid_skins[skin[0]][skin[1]] = skinData(dID=skin[3], float_val=skin[4], price=skin[2])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning(f"Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error: {e}")
                raise   

def insert_listings_info_db(lowest_prices: list[list[float]], skins: list[dict], skin_codes: list[str], db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS skin_info (skin_name TEXT, skin_code TEXT PRIMARY KEY, fn REAL, mw REAL, ft REAL, ww REAL, bs REAL, rarity TEXT, collection TEXT, min_wear REAL, max_wear REAL)")
            logger.debug(f"Writing {len(lowest_prices)} listings to database")
            values = tuple(
                (skins[index]["name"], skin_codes[index], *lowest_prices[index], skins[index]["rarity"], skins[index]["collection"], skins[index]["min_wear"], skins[index]["max_wear"]) 
                for index in range(0, len(lowest_prices))
            )
            conn.executemany("INSERT OR REPLACE INTO skin_info (skin_name, skin_code, fn, mw, ft, ww, bs, rarity, collection, min_wear, max_wear) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
                