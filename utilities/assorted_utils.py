import logging
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from collections import namedtuple
from typing import Callable

SKIN_CODES_DB = "skin_codes.db"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
user_agent = os.getenv("STEAM_USER_AGENT")
logger = logging.getLogger("CS2-System")

# Tuple of Possible Wears
wears = ("(Factory New)", "(Minimal Wear)", "(Field-Tested)", "(Well-Worn)", "(Battle-Scarred)")
WEAR_RANGES = {
    "(Factory New)": "(0 - 0.07)",
    "(Minimal Wear)": "(0.07 - 0.15)",
    "(Field-Tested)": "(0.15 - 0.38)",
    "(Well-Worn)": "(0.38 - 0.45)",
    "(Battle-Scarred)": "(0.45 - 1.00)"
}

CURRENCY_TO_CAD = {
    "HKD": 0.177,   # 1 Hong Kong Dollar ~ 0.18 CAD
    "USD": 1.370,   # 1 US Dollar ~ 1.37 CAD
    "EUR": 1.480,   # 1 Euro ~ 1.48 CAD
    "GBP": 1.740,   # 1 British Pound ~ 1.74 CAD
    "CAD": 1.000    # Base currency fallback
}

headers = {
    "Host": "steamcommunity.com",
    "Origin": "https://steamcommunity.com",
    # Just an Example, is updated later in the scouting loop
    "Referer": "https://steamcommunity.com/market/listings/730/G1802208A0A3004",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json; charset=utf-8",
    # THE SECRET HANDSHAKE
    "x-valve-action-type": "4OPT6VBA:Search",
    "x-valve-request-type": "routeAction",
    # MAPPING BROWSER ID
    "User-Agent": user_agent,
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-dest": "empty"
}

skinData = namedtuple('skinData', ['dID', 'float_val', 'price'])

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

# Helper to retry transient network errors on POST requests
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def post_with_retry(session: requests.Session, url: str, json_payload: dict, headers: dict, cookies: dict, timeout: int = 15):
    """POST with retries for transient network errors.

    Raises the last requests exception when retries are exhausted.
    """
    resp = session.post(url, json=json_payload, headers=headers, cookies=cookies, timeout=timeout)
    # If server replies with 5xx or 429, raise to trigger retry
    if resp.status_code == 429 or resp.status_code > 500:
        logger.warning(f"POST to {url} returned {resp.status_code}; raising to retry")
        resp.raise_for_status()
    elif resp.status_code == 500:
        logger.info(f"POST to {url} returned 500; treating as empty response")
        resp = requests.Response()
    return resp

# Helper to retry transient network errors on GET requests
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def get_with_retry(session: requests.Session | None, url: str, headers: dict | None = None, timeout: int = 10):
    """GET with retries for transient network errors.

    If `session` is provided it will be used, otherwise `requests` module is used.
    Raises the last requests exception when retries are exhausted.
    """
    sess = session if session is not None else requests
    resp = sess.get(url, headers=headers, timeout=timeout)
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
            "sessionid": session_id,
            "timezoneName": "America/New_York",
        }
        scraper_session.cookies.update(cookies)
        return [scraper_session, cookies]
    except Exception as e:
        logger.error("Steam session setup failure within setup_session_cookies")
        return []

def price_conversion(salePriceText: str, price: float):
    if "CA" not in salePriceText:
        #print("Needs Converting")
        if "HK" in salePriceText:
            converted_price = round(price * CURRENCY_TO_CAD["HKD"] / 100, 2)
        else:
            converted_price = round(price * CURRENCY_TO_CAD["USD"] / 100, 2)
    else:
        converted_price = price / 100
    return converted_price

def price_check(skin_name: str, wlevel: int, get_skin_code_db: Callable):
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
    scout_code = get_skin_code_db(SKIN_CODES_DB, search_name)
    Payload = [{
        "appid":730,
        "strItemName": scout_code, # Unique identifier, will have to calculate later
        "sort":{"field":0,"direction":0},
        "filters":{"category_730_Exterior":[f"tag_WearCategory{wlevel}"]}, # Set these using the inputs
        "accessoryFilters":{},
        "propertyFilters":{},
        "price":{"eCurrency":20},
        "start": 0,
    }]
    # Steam forces 20 listings at a time.
    headers["Referer"] = f"https://steamcommunity.com/market/listings/730/{scout_code}"
    try:
        scout_r = post_with_retry(scraper_session, f"https://steamcommunity.com/market/listings/730/{scout_code}", Payload, headers, cookies) # type: ignore
    except Exception as e:
        logger.error(f"Initial scout request failed for {search_name}: {e}")
        return 0
    return_subtotal = ""
    try:
        lowest_listing = scout_r.json().get('listings', 0)[0]
        lowest_listing_subtotal = lowest_listing.get('strSubtotal')
        lowest_listing_price = lowest_listing.get('unPrice', 0) + lowest_listing.get('unFee', 0)
        logger.info(f"Converting {lowest_listing_subtotal}")
        converted_listing_price = price_conversion(lowest_listing_subtotal, lowest_listing_price)
        if lowest_listing_price == converted_listing_price:
            return_subtotal = return_subtotal
        else:
            return_subtotal = converted_listing_price

    except Exception as e:
        logger.error(f"No listings found or strSubtotal for {search_name}")
        return f"No Listings Found for {search_name}"
    
    return return_subtotal