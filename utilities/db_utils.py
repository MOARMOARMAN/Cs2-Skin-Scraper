from asyncio import timeout
import sqlite3
import logging
from contextlib import closing
from .assorted_utils import headers, skinData, get_skin_code, WEAR_ABBRIEVIATIONS

logger = logging.getLogger("CS2-System.DB")

def get_skin_code_db(db_name: str, search_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        skin_name = search_name.rsplit(" (", 1)[0]
        skin_code = conn.execute(f"SELECT skin_code FROM skin_data WHERE skin_name = ?", (skin_name,)).fetchone()
        if skin_code:
            logger.info(f"skin code {skin_code[0]} exists for {skin_name}")
            return skin_code[0]
        else:
            try:
                skin_code = get_skin_code(search_name)
                logger.info(f"skin code {skin_code} for {skin_name} retrieved")
                return skin_code
            except Exception as e:
                logger.error(f"Error occurred while fetching scout code for {skin_name}: {e}")
                return None

# ______________________________________________________________ listings.db functions ___________________________________________________________________

def create_skin_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS skin_listings (listing_ID TEXT PRIMARY KEY, skin_name TEXT, d_ID TEXT, float_val REAL, price REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skin_listings_skin_name ON skin_listings (skin_name)")

def clear_db_skins(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            logger.debug(f"Clearing out active listings database.")
            conn.execute(f"DELETE FROM skin_listings")

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
            stored_skins = conn.execute("SELECT listing_ID, price, d_ID, float_val FROM skin_listings WHERE skin_name = ?", (skin_name, )).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} stored listings for {skin_name}")
            for skin in stored_skins:
                valid_listings[skin[0]] = skinData(dID=skin[2], float_val=skin[3], price=skin[1])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

# For loading data of the entire database. (batch)
def load_all_data_listings_db(valid_skins: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("SELECT skin_name, listing_ID, price, d_ID, float_val FROM skin_listings").fetchall()
            logger.debug(f"Loaded {len(stored_skins)} total listings from database")
            for skin in stored_skins:
                if skin[0] not in valid_skins:
                    valid_skins[skin[0]] = {}
                valid_skins[skin[0]][skin[1]] = skinData(dID=skin[3], float_val=skin[4], price=skin[2])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error: {e}")
                raise   

def create_tracked_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS tracked_skins (id INTEGER PRIMARY KEY, skin_name TEXT, max_float_val REAL, max_price REAL)")

def populate_tracked_table_db(db_name: str, skins: list):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [
                (skin[0], skin[1], skin[2]) for skin in skins
            ]
            conn.executemany("INSERT OR REPLACE INTO tracked_skins (skin_name, max_float_val, max_price) VALUES(?, ?, ?)", values)

def insert_tracked_table_db(db_name: str, skin: list):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            skin = tuple(skin)
            conn.executemany("INSERT OR REPLACE INTO tracked_skins (skin_name, max_float_val, max_price) VALUES(?, ?, ?)", skin)

def delete_entry_tracked_table_db(id: int, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("DELETE FROM tracked_skins WHERE id=?", (id, ))

def get_tracked_listings_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        tracked_listings = conn.execute("SELECT * FROM tracked_skins").fetchall()
        return tracked_listings

def create_all_historical_listings_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS all_historical_listings (
                listing_ID TEXT PRIMARY KEY,
                skin_name TEXT,
                d_ID TEXT,
                float_val REAL,
                price REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_all_historical_listings_skin_name ON all_historical_listings (skin_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_all_historical_listings_recorded_at ON all_historical_listings (recorded_at)")

def write_to_historical_db(skin_name: str, valid_listings: dict, db_name: str):
    """Write listings to historical table - follows same pattern as write_listings_db"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Writing {len(valid_listings)} historical listings for {skin_name} to database")
            listingData = tuple(
                (lID, skin_name.strip('"'), data.dID, data.float_val, data.price)
                for lID, data in valid_listings.items()
            )
            conn.executemany("INSERT OR IGNORE INTO all_historical_listings (listing_ID, skin_name, d_ID, float_val, price) VALUES(?, ?, ?, ?, ?)", listingData)

def load_all_historical_data_listings_for_skin_name_db(skin_name: str, db_name: str):
    """Load all historical listings for a specific skin - returns dict with timestamp"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("SELECT listing_ID, price, d_ID, float_val, recorded_at FROM all_historical_listings WHERE skin_name = ?", (skin_name, )).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} historical listings for {skin_name}")
            return {skin[0]: {"price": skin[1], "d_ID": skin[2], "float_val": skin[3], "recorded_at": skin[4]} for skin in stored_skins}
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table all_historical_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

def load_all_historical_data_from_db(db_name: str):
    """Load all historical listings from database - returns dict with timestamps"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("""SELECT skin_name, listing_ID, price, d_ID, float_val, recorded_at FROM all_historical_listings ORDER BY recorded_at DESC""").fetchall()
            logger.debug(f"Loaded {len(stored_skins)} total historical listings from database")
            result = {}
            for skin in stored_skins:
                if skin[0] not in result:
                    result[skin[0]] = []
                result[skin[0]].append({
                    "listing_ID": skin[1],
                    "price": skin[2],
                    "d_ID": skin[3],
                    "float_val": skin[4],
                    "recorded_at": skin[5]
                })
            return result
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table all_historical_listings doesn't exist yet")
            else:
                logger.error(f"Database error: {e}")
                raise

def del_from_historical_db(skin_name: str, listingIDs: list, db_name: str):
    """Delete listings from historical database"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            logger.debug(f"Deleting {len(listingIDs)} historical listings for {skin_name} | {listingIDs}")
            delete_data = ((ID[0], skin_name) for ID in listingIDs)
            conn.executemany("DELETE FROM all_historical_listings WHERE listing_ID = ? AND skin_name = ?", delete_data)

# ______________________________________________________________ skin_data.db functions ___________________________________________________________________

def create_skin_data_table_db(db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS skin_data (skin_name TEXT PRIMARY KEY, skin_code TEXT, fn REAL, mw REAL, ft REAL, ww REAL, bs REAL, rarity TEXT, collection TEXT, min_wear REAL, max_wear REAL)")

def populate_names_skin_data_db(names: list, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [(name,) for name in names]
            conn.executemany("INSERT OR REPLACE INTO skin_data (skin_name) VALUES(?)", values)

def populate_code_skin_data_db(skin_code: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [(code, name,) for name, code in skin_code.items()]
            conn.executemany("UPDATE skin_data SET skin_code=? WHERE skin_name=?", values)

def populate_extra_skin_data_db(extra_info: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            # list: rarity, collection, min_wear, max_wear
            values = []
            for name, info in extra_info.items():
                values.append((*info, name,))
            conn.executemany("UPDATE skin_data SET rarity=?, collection=?, min_wear=?, max_wear=? WHERE skin_name=?", values)

def populate_prices_skin_data_db(prices: dict, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            # list: rarity, collection, min_wear, max_wear
            values = []
            for name, price in prices.items():
                values.append((*price, name,))
            conn.executemany("UPDATE skin_data SET fn=?, mw=?, ft=?, ww=?, bs=? WHERE skin_name=?", values)

def get_lowest_price_skin_data_db(skin_name: str, wear_level: int, db_name: str):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        result = conn.execute(f"SELECT {WEAR_ABBRIEVIATIONS[wear_level]} FROM skin_data WHERE skin_name=?", (skin_name,)).fetchone()
        return result[0]