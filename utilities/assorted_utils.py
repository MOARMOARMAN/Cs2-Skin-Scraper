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
import os
import requests
import time
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception
from requests.exceptions import HTTPError
from collections import namedtuple
from typing import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASES_DIR = PROJECT_ROOT / "databases"
SKIN_DATA_DB = DATABASES_DIR / "skin_data.db"
LISTINGS_DB = DATABASES_DIR / "listings.db"
HISTORICAL_DATA_DB = DATABASES_DIR / "historical_data.db"
user_agent = os.getenv("STEAM_USER_AGENT")
logger = logging.getLogger("CS2-System")
discord_webhook_url = os.getenv("DISCORD_WEBHOOK")

PREFERRED_CURRENCY = "CAD"

# Tuple of Possible Wears
wears = ("(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)")
WEAR_RANGES = {
    "(Factory New)": "(0 - 0.07)",
    "(Minimal Wear)": "(0.07 - 0.15)",
    "(Field-Tested)": "(0.15 - 0.38)",
    "(Well-Worn)": "(0.38 - 0.45)",
    "(Battle-Scarred)": "(0.45 - 1.00)"
}
WEAR_ABBRIEVIATIONS = ["fn", "mw", "ft", "ww", "bs"]
WEAR_TO_MAX = [0.0699, 0.1499, 0.3799, 0.4499, 0.9999]
CURRENCY_EXCHANGE_RATE = {
    "HKD": 0.181,   # 1 Hong Kong Dollar ~ 0.18 CAD
    "USD": 1.420,   # 1 US Dollar ~ 1.42 CAD
    "EUR": 1.624,   # 1 Euro ~ 1.62 CAD
    "GBP": 1.895,   # 1 British Pound ~ 1.90 CAD
    "CAD": 1.000    # Base currency fallback
}

RELEVANT_CURRENCIES = ["HKD", "USD", "EUR", "GBP", "CAD"]

headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": "steamcommunity.com",
    "Origin": "https://steamcommunity.com",
    # Just an Example, is updated later in the scouting loop
    "Referer": "https://steamcommunity.com/market/listings/730/G1802208A0A3004",
    "Content-Type": "application/json; charset=utf-8",
    # THE SECRET HANDSHAKE
    "x-valve-action-type": "4OPT6VBA:Search",
    "x-valve-request-type": "routeAction",
    # MAPPING BROWSER ID
    "User-Agent": user_agent,
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-dest": "empty",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-viewport-height": "932",
    "sec-ch-viewport-width": "637"
}

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

def is_retryable_error(exception):
    if isinstance(exception, requests.exceptions.HTTPError):
        return exception.response.status_code == 429 or exception.response.status_code >= 500   
    return isinstance(exception, requests.exceptions.RequestException)

# Helper to retry transient network errors on POST requests
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=60, max=1500),
    retry=retry_if_exception(is_retryable_error),
)
def post_with_retry(session: requests.Session, url: str, json_payload: dict, local_headers: dict, cookies: dict, timeout: int = 15):
    """POST request wrapper with retries for transient HTTP/network failures."""
    start = time.perf_counter()
    resp = session.post(url, json=json_payload, headers=local_headers, cookies=cookies, timeout=timeout)
    # If server replies with 5xx or 429, raise to trigger retry
    logger.info(f"{resp.headers}")
    logger.info(f"{resp.text[:500]}")
    logger.info(f"took {time.perf_counter() - start}")
    if resp.status_code == 429 or resp.status_code >= 500:
        if resp.status_code == 500:
            logger.info(f"POST to {url} returned 500; treating as empty response")
            resp = requests.Response()
        else:
            logger.warning(f"POST to {url} returned {resp.status_code}; raising to retry")
            resp.raise_for_status()
    return resp

# Helper to retry transient network errors on GET requests
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception(is_retryable_error),
)
def get_with_retry(session: requests.Session | None, url: str, local_headers: dict | None = None, timeout: int = 10):
    """GET with retries for transient network errors.

    If `session` is provided it will be used, otherwise `requests` module is used.
    Raises the last requests exception when retries are exhausted.
    """
    sess = session if session is not None else requests
    resp = sess.get(url, headers=local_headers, timeout=timeout)
    if resp.status_code == 429 or resp.status_code > 500:
        logger.warning(f"GET to {url} returned {resp.status_code}; raising to retry")
        resp.raise_for_status()
    elif resp.status_code == 500:
        logger.info(f"GET to {url} returned 500; treating as empty response")
        resp = requests.Response()
    return resp

def setup_session_cookies():
    try:
        scraper_session = requests.Session()
        try:
            scraper_session.get("https://steamcommunity.com/market/")
        except Exception as e:
            logger.error(f"Failed to initialize Steam market session: {e}")
            return
        logger.info("Session to Steam Created.")
        session_id = scraper_session.cookies.get('sessionid', domain='steamcommunity.com')
        if not session_id:
            session_id = os.getenv("SESSION_ID_FALLBACK") # Your known good ID
            if not session_id:
                logger.error("Failed to retrieve session ID from environment variables.")
                return
            logger.warning("Using fallback session ID from environment")
            scraper_session.cookies.set('sessionid', session_id, domain='steamcommunity.com')
        cookies = {
            "marketPrefs":"%7B%22itemSort%22%3A1%2C%22itemSortDir%22%3A0%2C%22itemSortProperty%22%3A2%7D",
            "sessionid":"b474ed7d95b7df4260d4c320",
            "steamCountry":"US%7Ce79b3001e60d17b2cb2750215a34f985",
            "clientHints":"%7B%22vw%22%3A%7B%22v%22%3A536%2C%22s%22%3A1%7D%2C%22vh%22%3A%7B%22v%22%3A932%2C%22s%22%3A1%7D%7D",
            "timezoneName":"Asia%2FShanghai"
        }
        scraper_session.cookies.update(cookies)
        return [scraper_session, cookies]
    except Exception as e:
        logger.error("Steam session setup failure within setup_session_cookies")
        return []

def get_skin_code(search_name: str):
    response = get_with_retry(None, url=f"https://steamcommunity.com/market/listings/730/{search_name}", local_headers=headers)
    return response.url.split("/")[-1]

def price_conversion(salePriceText: str, price: float):
    if "CA" not in salePriceText:
        #print("Needs Converting")
        if "HK" in salePriceText:
            converted_price = round(price * CURRENCY_EXCHANGE_RATE["HKD"] / 100, 2)
        else:
            converted_price = round(price * CURRENCY_EXCHANGE_RATE["USD"] / 100, 2)
    else:
        converted_price = price / 100
    return converted_price

def price_check(skin_name: str, wlevel: int, get_skin_code_db: Callable, scout_code: str|None = None):
    session_cookies = setup_session_cookies()
    if not session_cookies:
        logger.error("Session setup failed and resulted in empty session and cookies")
        return 0
    else:
        logger.info(f"Session connected successfully to steam for {skin_name}")
    scraper_session = session_cookies[0]
    cookies = session_cookies[1]
    skin_wear = wears[wlevel]
    search_name = f"{skin_name} {skin_wear}"
    logger.info(f"Searching for {skin_name}")
    if not scout_code:
        scout_code = get_skin_code_db(SKIN_DATA_DB, skin_name=skin_name)
    Payload = [{
        "appid":730,
        "strItemName": scout_code, # Unique identifier, will have to calculate later
        "sort":{"field":0,"direction":0},
        "filters":{"Exterior":[f"WearCategory{wlevel}"]}, # Set these using the inputs
        "accessoryFilters":{},
        "propertyFilters":{},
        "price":{"eCurrency":20},
        "start": 0,
    }]
    # Steam forces 20 listings at a time.
    local_headers = headers.copy()
    local_headers["Referer"] = f"https://steamcommunity.com/market/listings/730/{scout_code}"
    try:
        scout_r = post_with_retry(scraper_session, f"https://steamcommunity.com/market/listings/730/{scout_code}", Payload, local_headers, cookies) # type: ignore
    except Exception as e:
        logger.error(f"Initial scout request failed for {search_name}: {e}")
        return 0
    return_subtotal = ""
    try:
        listings = scout_r.json().get('listings')
        if not listings:
            logger.error(f"No listings found or strSubtotal for {search_name}")
            return -1
        lowest_listing = listings[0]
        lowest_listing_subtotal = lowest_listing.get('strSubtotal')
        lowest_listing_price = lowest_listing.get('unPrice', 0) + lowest_listing.get('unFee', 0)
        logger.info(f"Converting {lowest_listing_subtotal}")
        converted_listing_price = price_conversion(lowest_listing_subtotal, lowest_listing_price)
        if lowest_listing_price == converted_listing_price:
            return_subtotal = lowest_listing_price
        else:
            return_subtotal = converted_listing_price

    except Exception as e:
        logger.error(f"No listings found or strSubtotal for {search_name}")
        return -1
    
    return return_subtotal

def discord_notification(message: str):
    try:
        webhook_payload = {
            "content": message
        }
        post_to_discord = requests.post(url=discord_webhook_url, json=webhook_payload)
    except Exception as e:
        logger.error(f"Discord Notification failed because of: {e}")

def get_exchange_rate(base: str, quote: str) -> float:
    return get_with_retry(None, url=f"https://api.frankfurter.dev/v2/rate/{base}/{quote}").json().get("rate")

def initialise_currency_exchange_rates(cad_rates: dict[str, float]):
    global CURRENCY_EXCHANGE_RATE
    CURRENCY_EXCHANGE_RATE

def update_currency_exchange_rates(new_rates: dict[str, float]):
    global CURRENCY_EXCHANGE_RATE
    CURRENCY_EXCHANGE_RATE.clear()
    CURRENCY_EXCHANGE_RATE.update(new_rates)