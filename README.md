# CS2 Skin Scraper & Market Analyzer

A multi-threaded data pipeline that monitors the Steam Community Market for underpriced CS2 skins, builds historical price baselines segmented by float value, and sends Discord alerts when a listing is priced meaningfully below its expected value for its wear level.

## Highlights

- **Multi-threaded producer/consumer pipeline** built on `ThreadPoolExecutor` — one persistent scraping thread per tracked skin, plus a single batch-analysis thread, all coordinated through shared SQLite storage.
- **Float-bucketed pricing baseline**: partitions listings into 100 buckets across the 0.00–1.00 float range (0.01 increments) and computes an outlier-resistant fair-value estimate per bucket using a capped harmonic mean.
- **Reverse-engineered Steam Market API integration**: replicates the internal search payload used by the Steam Community Market's listing search endpoint, including session/cookie management and custom headers.
- **Resilient network layer**: retry logic via `tenacity` (exponential backoff with jitter) layered with explicit handling for Steam's rate limiting.
- **Discord alerting**: pushes a formatted notification with a direct purchase link the moment a listing is flagged as underpriced.
- **Interactive CLI** for adding/removing tracked skins before launching the scraping/analysis threads.

## Architecture

```
tracker.py (entry point)
  │
  ├── CLI: add / remove / help / continue
  │
  └── on "continue" → ThreadPoolExecutor(max_workers = N tracked skins + 1)
          │
          ├── scouting_loop() × N   (one thread per tracked skin, scraper.py)
          │      → writes active listings to listings.db
          │      → appends every observed listing to historical_data.db
          │
          └── analyze_batch_overpay_loop() × 1   (batch.py)
                 → every 30s: reads listings.db + historical_data.db
                 → recomputes float-bucket price baselines (display_chart.py)
                 → flags listings priced >15% below their bucket's baseline
                 → sends Discord webhook alert per flagged listing
```

Three SQLite databases, all running in WAL mode for concurrent access:
- **`listings.db`** — currently active listings per tracked skin, plus the list of tracked skins/thresholds
- **`historical_data.db`** — append-only log of every listing ever observed, timestamped
- **`skin_data.db`** — skin metadata (internal Steam "skin code," per-wear-level reference prices, and the float-bucket price baselines used for comparison)

## Core Components

### `tracker.py` — Entry point & CLI
Initializes all three databases, then presents an interactive prompt (`add` / `remove` / `help` / `continue`). `add` walks the user through selecting a skin and float threshold, shows the current lowest listed price for context, and asks for a maximum price to buy at. On `continue`, it spawns one scraping thread per tracked skin plus one batch-analysis thread via `ThreadPoolExecutor`.

### `scraper.py` — Scraping loop (one thread per tracked skin)
`scouting_loop()` runs indefinitely for a single skin: it authenticates a session against Steam, then repeatedly calls `scout()`, which pages through the Steam Market's internal search endpoint (`POST /market/listings/730/{code}`) in batches of 20 listings, extracting float value and price from each listing's asset properties. Every observed listing (regardless of whether it meets the user's threshold) is written to `historical_data.db`; only listings meeting the user's float/price criteria are kept in the active `listings.db` table. Between paginated requests within a single scan, the scraper sleeps 45–75 seconds (randomized); between full scan cycles for a given skin, it sleeps 120–180 seconds.

**Known limitation:** currency conversion (`price_conversion()` in `assorted_utils.py`) only explicitly checks for `"CA"` (Canadian) and `"HK"` (Hong Kong) markers in the price text — any other currency (including EUR and GBP, despite having defined conversion rates) silently falls back to the USD rate. This works correctly for the currencies actually encountered in practice, but isn't the full multi-currency handling it might appear to be from the rate table alone.

### `batch.py` — Analysis loop (one thread, runs every 30 seconds)
`analyze_batch_overpay_loop()` loads all currently active listings across every tracked skin, recomputes that skin's float-bucket price baseline (see below), and computes each listing's percentage deviation from its bucket's baseline price. Listings priced more than 15% below baseline (`OVERPAY_PERCENTAGE_THRESHOLD = -15`) are flagged and pushed to Discord with a direct purchase link.

### `display_chart.py` — Baseline pricing & visualization
`calculate_wear_buckets()` partitions a skin's full historical listing data into 100 buckets by float value (0.00–0.01, 0.01–0.02, ... 0.99–1.00). Within each bucket, it keeps at most 10 listings — specifically, listings priced under 1.3× the current lowest observed price in that bucket — and computes the **harmonic mean** of their prices. This caps the influence of outlier-high listings and produces a more stable "floor price" estimate per float range than a simple average would. `update_wear_bucket_data_for_skin()` (called from `batch.py`) recomputes and stores these baselines into `skin_data.db`; running the file directly instead launches an interactive Plotly chart (dual-axis: price baseline as a line, listing volume as bars) for manual inspection of a chosen skin.

### `assorted_utils.py` / `db_utils.py` / `dataclass_utils.py` — Shared utilities
Aggregated as a `utilities` package. Includes: Steam session/cookie setup, the reverse-engineered request payload structure, `tenacity`-based retry wrappers for POST/GET requests (exponential backoff with jitter, 5 attempts), currency conversion, Discord webhook dispatch, and all SQLite read/write functions across the three databases (WAL mode + `synchronous=NORMAL` pragma for concurrent thread access).

### `update_skin_data_lowest_listing_price.py` — Maintenance script
A standalone script (not part of the main tracking loop) that refreshes each tracked skin's reference lowest price at every wear level (Factory New through Battle-Scarred) in `skin_data.db`. Run manually/periodically to keep reference prices current.

## Rate Limiting & Resilience

- All POST/GET requests are wrapped with `tenacity` retries using exponential backoff with jitter (5 attempts; POST requests start at 20s/max 100s wait, GET requests start at 1s/max 10s wait), triggered on request exceptions or 429/5xx responses.
- Separately, if the *initial* scan request for a skin returns HTTP 429, `scout()` sleeps for a flat 300 seconds before giving up on that cycle — a coarser fallback distinct from the retry wrapper's own backoff.
- Randomized sleep intervals (45–75s between paginated requests, 120–180s between full scan cycles) reduce the chance of triggering rate limits in the first place.

## Setup

### Prerequisites
- Python 3.10+
- SQLite3 (bundled with Python's standard library — no separate install needed)

### Installation
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the project root:
```ini
STEAM_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
SESSION_ID_FALLBACK="your_steam_cookie_session_id"
DISCORD_WEBHOOK="https://discord.com/api/webhooks/...your_webhook_url"
```

### Running
```bash
python tracker.py
```
Use `add` to register skins to track (by name and max float), `remove` to drop tracked skins, then `continue` to launch the scraping and analysis threads.

To manually inspect a skin's price-vs-float distribution:
```bash
python display_chart.py
```
