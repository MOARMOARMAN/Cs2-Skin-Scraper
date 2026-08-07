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
from pathlib import Path
import sqlite3
import logging
from math import floor
from contextlib import closing
from .assorted_utils import get_skin_code, WEAR_ABBRIEVIATIONS
from .dataclass_utils import listingData

logger = logging.getLogger("CS2-System.DB")

def get_skin_code_db(db_name: str | Path, search_name: str = "", skin_name: str = "") -> str | None:
    """Get skin code from database and if it isn't in the database then get the skin code through a GET request"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        if not skin_name:
            if not search_name:
                logger.error("Please provide at least a search_name or skin_name.")
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

def create_skin_listings_table_db(db_name: str | Path) -> None:
    """Creates the skin listings table which holds all scraped listings."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS skin_listings (listing_ID TEXT PRIMARY KEY, skin_name TEXT, float_val REAL, price REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skin_listings_skin_name ON skin_listings (skin_name)")

def clear_db_skins(db_name: str | Path) -> None:
    """Clear the listings.db of any listings in skin_listings"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            logger.debug(f"Clearing out active listings database.")
            conn.execute(f"DELETE FROM skin_listings")

def write_listings_db(skin_name: str, valid_listings: dict, db_name: str | Path) -> None:
    """Inserts or replaces listings into skin_listings of listing.db with listing_ID as the primary key."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Writing {len(valid_listings)} listings for {skin_name} to database")
            listingData = tuple(
                (lID, skin_name.strip('"'), data.float_val, data.price)
                for lID, data in valid_listings.items()
            )
            conn.executemany("INSERT OR REPLACE INTO skin_listings (listing_ID, skin_name, float_val, price) VALUES(?, ?, ?, ?)", listingData)

def del_missing_ID_listing_db(skin_name: str, gone_listingIDs: list, db_name: str | Path) -> None:
    """Deletes all listings of a specific id of a specific skin."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Deleting {len(gone_listingIDs)} missing listings for {skin_name} | {gone_listingIDs}")
            delete_data = ((ID[0], skin_name) for ID in gone_listingIDs)
            conn.executemany("DELETE FROM skin_listings WHERE listing_ID = ? AND skin_name = ?", delete_data)

def load_data_listings_db(skin_name: str, valid_listings: dict, db_name: str | Path) -> None:
    """Loads all listings into a passed in dict for a given skin_name"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("SELECT listing_ID, price, float_val FROM skin_listings WHERE skin_name = ?", (skin_name, )).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} stored listings for {skin_name}")
            for skin in stored_skins:
                valid_listings[skin[0]] = listingData(float_val=skin[2], price=skin[1])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

def load_all_data_listings_db(valid_skins: dict, db_name: str | Path) -> None:
    """Loads every single skin in the skin_listings table into valid_skins, the passed in dict."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("SELECT skin_name, listing_ID, price, float_val FROM skin_listings").fetchall()
            logger.debug(f"Loaded {len(stored_skins)} total listings from database")
            for skin in stored_skins:
                if skin[0] not in valid_skins:
                    valid_skins[skin[0]] = {}
                valid_skins[skin[0]][skin[1]] = listingData(float_val=skin[3], price=skin[2])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table skin_listings doesn't exist yet")
            else:
                logger.error(f"Database error: {e}")
                raise   

def create_tracked_table_db(db_name: str | Path) -> None:
    """Creates a table on listings.db for currently tracked skins"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS tracked_skins (id INTEGER PRIMARY KEY, skin_name TEXT, max_float_val REAL, max_price REAL)")

def populate_tracked_table_db(db_name: str | Path, skins: list) -> None:
    """populates the tracked skins table with """
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [
                (skin[0], skin[1], skin[2]) for skin in skins
            ]
            conn.executemany("INSERT OR REPLACE INTO tracked_skins (skin_name, max_float_val, max_price) VALUES(?, ?, ?)", values)

def insert_tracked_table_db(db_name: str | Path, skin: tuple):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.executemany("INSERT OR REPLACE INTO tracked_skins (skin_name, max_float_val, max_price) VALUES(?, ?, ?)", skin)

def delete_entry_tracked_table_db(id: int, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("DELETE FROM tracked_skins WHERE id=?", (id, ))

def get_tracked_listings_table_db(db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        tracked_listings = conn.execute("SELECT * FROM tracked_skins").fetchall()
        return tracked_listings

# ______________________________________________________________ historical_data.db functions ___________________________________________________________________

def create_all_historical_listings_table_db(db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS all_historical_listings (
                listing_ID TEXT PRIMARY KEY,
                skin_name TEXT,
                float_val REAL,
                price REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_all_historical_listings_skin_name ON all_historical_listings (skin_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_all_historical_listings_recorded_at ON all_historical_listings (recorded_at)")

def write_to_historical_db(skin_name: str, valid_listings: dict, db_name: str | Path):
    """Write listings to historical table - follows same pattern as write_listings_db"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            logger.debug(f"Writing {len(valid_listings)} historical listings for {skin_name} to database")
            listingData = tuple(
                (lID, skin_name.strip('"'), data.float_val, data.price)
                for lID, data in valid_listings.items()
            )
            conn.executemany("INSERT OR IGNORE INTO all_historical_listings (listing_ID, skin_name, float_val, price) VALUES(?, ?, ?, ?)", listingData)

def load_for_skin_name_all_historical_listings_db(skin_name: str, db_name: str | Path):
    """Load all historical listings for a specific skin - returns dict with timestamp"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            stored_skins = conn.execute("SELECT listing_ID, price, float_val, recorded_at FROM all_historical_listings WHERE skin_name = ? ORDER BY price", (skin_name, )).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} historical listings for {skin_name}")
            return {skin[0]: {"price": skin[1], "float_val": skin[2], "recorded_at": skin[3]} for skin in stored_skins}
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table all_historical_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

def load_prices_for_float_and_name_all_historical_listings_db(skin_name: str, float_bucket: int, db_name: str | Path):
    """Load all historical listings for a specific skin and float bucket (0-99) -> ([0.00-0.01]-[0.99-1.00]). - returns dict with timestamp"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        min_float = float_bucket * 0.01
        max_float = min_float + 0.01
        try:
            stored_skins = conn.execute("SELECT price FROM all_historical_listings WHERE skin_name = ? AND float_val >= ? AND float_val <= ? ORDER BY price", (skin_name, min_float, max_float)).fetchall()
            logger.debug(f"Loaded {len(stored_skins)} historical listings for {skin_name}")
            return [skin[0] for skin in stored_skins]
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table all_historical_listings doesn't exist yet")
            else:
                logger.error(f"Database error loading {skin_name}: {e}")
                raise

def load_all_skin_names_all_historical_data_db(db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            skin_names = conn.execute("SELECT DISTINCT skin_name FROM all_historical_listings ORDER BY skin_name").fetchall()
            return skin_names
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):

                logger.warning("Table all_historical_listings doesn't exist yet")
            else:
                logger.error(f"Loading skin names from all historical data table ERROR: {e}")
                raise
            
def del_from_historical_db(skin_name: str, listingIDs: list, db_name: str | Path):
    """Delete listings from historical database"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            logger.debug(f"Deleting {len(listingIDs)} historical listings for {skin_name} | {listingIDs}")
            delete_data = ((ID[0], skin_name) for ID in listingIDs)
            conn.executemany("DELETE FROM all_historical_listings WHERE listing_ID = ? AND skin_name = ?", delete_data)

# ______________________________________________________________ skin_data.db functions ___________________________________________________________________

def create_skin_data_table_db(db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS skin_data (skin_name TEXT PRIMARY KEY, skin_code TEXT, fn REAL, mw REAL, ft REAL, ww REAL, bs REAL, rarity TEXT, collection TEXT, min_wear REAL, max_wear REAL)")

def populate_names_skin_data_db(names: list, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [(name,) for name in names]
            conn.executemany("INSERT OR REPLACE INTO skin_data (skin_name) VALUES(?)", values)

def populate_code_skin_data_db(skin_code: dict, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [(code, name,) for name, code in skin_code.items()]
            conn.executemany("UPDATE skin_data SET skin_code=? WHERE skin_name=?", values)

def populate_extra_skin_data_db(extra_info: dict, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            # list: rarity, collection, min_wear, max_wear
            values = []
            for name, info in extra_info.items():
                values.append((*info, name,))
            conn.executemany("UPDATE skin_data SET rarity=?, collection=?, min_wear=?, max_wear=? WHERE skin_name=?", values)

def populate_prices_skin_data_db(prices: dict, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            # list: rarity, collection, min_wear, max_wear
            values = []
            for name, price in prices.items():
                values.append((*price, name,))
            conn.executemany("UPDATE skin_data SET fn=?, mw=?, ft=?, ww=?, bs=? WHERE skin_name=?", values)

def get_lowest_price_skin_data_db(skin_name: str, wear_level: int, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        result = conn.execute(f"SELECT {WEAR_ABBRIEVIATIONS[wear_level]} FROM skin_data WHERE skin_name=?", (skin_name,)).fetchone()
        return result[0]

def create_float_prices_skin_data_db(db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            # float_bucket is from 0 - 99 representing 0.00 - 0.01 to 0.99 - 1.00
            conn.execute("""CREATE TABLE IF NOT EXISTS float_prices (
                skin_name TEXT, 
                float_bucket INTEGER, 
                average_price REAL, 
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (skin_name, float_bucket)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skin_name_float_prices ON float_prices (skin_name)")
                
def insert_skin_float_prices_skin_data_db(skin_name: str, prices: list, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = tuple(
                (skin_name, x, price) for x, price in enumerate(prices)
            )
            conn.executemany("INSERT OR REPLACE INTO float_prices (skin_name, float_bucket, average_price) VALUES(?, ?, ?)", values)

# listings is list[float_val, price, listingID]
def get_price_float_buckets_skin_data_db(skin_name: str, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        price_buckets = {}
        stored_buckets = conn.execute("SELECT float_bucket, average_price FROM float_prices WHERE skin_name=?", (skin_name,)).fetchall()
        # bucket = (float_bucket, average_price)
        for bucket in stored_buckets:
            price_buckets[bucket[0]] = bucket[1]

        return price_buckets

def get_price_for_name_and_float_skin_data_db(skin_name: str, float_val: float, db_name: str | Path):
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        float_bucket = int(float_val // 0.01)
        values = (skin_name, float_bucket)
        average_price = conn.execute("SELECT average_price FROM float_prices WHERE skin_name=? AND float_bucket=?", values).fetchone()[0]
        return average_price

def create_currency_exchange_table_db(db_name: str | Path) -> None:
    """Creates a currency exchange rates table."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn: 
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS currency_exchange_rates (
                    currency_from TEXT NOT NULL,
                    currency_to TEXT NOT NULL,
                    rate REAL NOT NULL,
                    time_inserted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (currency_from, currency_to)
                )
            """)
            
            # Create indexes for faster queries on currency pairs
            conn.execute("CREATE INDEX IF NOT EXISTS idx_currency_exchange ON currency_exchange_rates (currency_to)")
            
def update_currency_exchange_table_db(currency_to: str, from_rates: dict[str, float], db_name: str | Path) -> None:
    """Updates the currency exchange rates within the currency exchange rate table."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        with conn:
            values = [
                (currency_from, currency_to, rate) for currency_from, rate in from_rates.items()
            ]
            conn.executemany("""INSERT OR REPLACE INTO currency_exchange_rates (currency_from, currency_to, rate) VALUES(?,?,?)""", values)

def get_currency_exchange_rates_for_currency_db(currency: str, db_name: str | Path) -> dict[str, float]:
    """Retrieves the currency exchange rates for a specific currency from others."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        rates = conn.execute("SELECT currency_from, rate FROM currency_exchange_rates WHERE currency_to=?", (currency,)).fetchall()
        exchange_rates = {currency_from:rate for currency_from, rate in rates}
        return exchange_rates


# ______________________________________________________________ inventory.db functions ___________________________________________________________________

def create_inventory_skins_table_db(db_name: str | Path) -> None:
    """Creates the inventory_skins table in inventory.db which will hold the skins that exist in the inventory currently"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA journal_mode=WAL;")
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS inventory_skins (
                id INTEGER PRIMARY KEY,
                skin_name TEXT,
                float_val REAL,
                purchase_price REAL,
                recorded_at TEXT DEFAULT CURRENT_DATE
            )""")

def add_inventory_skins_table_db(skin_name: str, float_val: float, skin_price: float, db_name: str | Path) -> None:
    """Adds in the base values for a skin given the name, float and price. Always inserts (never updates)."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            conn.execute("""INSERT INTO inventory_skins (skin_name, float_val, purchase_price) 
                VALUES (?, ?, ?)""", (skin_name.strip('"'), float_val, skin_price))

def remove_inventory_skins_table_db(skin_id: int, db_name: str | Path) -> bool:
    """Removes a specific skin from the inventory based on the skin_id."""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        with conn:
            row_count = conn.execute("DELETE FROM inventory_skins WHERE id=?", (skin_id,)).rowcount
            return row_count > 0

def load_all_inventory_skins_table_db(db_name: str | Path) -> list:
    """Loads all inventory from inventory.db into a list"""
    with closing(sqlite3.connect(db_name, timeout=60)) as conn:
        conn.execute("PRAGMA synchronous=NORMAL;") 
        try:
            inventory_data = conn.execute("SELECT id, skin_name, float_val, purchase_price, recorded_at FROM inventory_skins").fetchall()
            logger.debug(f"Loaded {len(inventory_data)} total inventory entries from database")
            
            #id, name, float, price, recorded_at
            inventory_list = [[int(row[0]), row[1], float(row[2]), float(row[3]), row[4]] for row in inventory_data]
            return inventory_list
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning("Table inventory_skins doesn't exist yet")
                return []
            else:
                logger.error(f"Database error loading inventory: {e}")
                raise
    