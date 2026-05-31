# Cs2-Skin-Scraper
## 🌟 Highlights
Here are some of the main features of this `CS2` Skin Scraper:
- Tracks any `CS2` skin listed on the `Steam Community Market`.
- Gathers all listings of tracked `CS2` skins that meet a maximum float and maximum price.
- Determines best deals out of gathered listings using `Gemini API`.
- Solves the time-consuming process of sifting through Steam Community Market listings and determining profitable skin purchases.

### How it works
As of this version, the CS2 Skin Scraper has 3 main components:
1. Multiple Scraping Loops (Producer) which work through messy `Steam Community Market` data.
2. A SQLite3 database using Write Ahead Logging (WAL) for handling high-frequency writes, which are necessary to support the multiple scraping loops.
3. A Batch Analysis Loop (Consumer) which pulls data from the database, processes it and feeds it to Gemini in an engineered prompt to return the top 5 best deals of the current batch.
