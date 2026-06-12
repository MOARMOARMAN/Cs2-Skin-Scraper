# What do I want to do?
# I want to scrape data of every single skin that exists.
from utilities import setup_session_cookies, post_with_retry, insert_listings_info_db

# dict
# name: str
# collection: str
# min_wear: float
# max_wear: float
# rarity: str
# code: str
skin = {}
    