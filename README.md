# CS2 Skin Scraper, Market Analyzer, & Inventory Dashboard

A multi-threaded data pipeline that monitors the Steam Community Market for underpriced CS2 skins, builds historical price baselines segmented by float value, and sends Discord alerts when a listing is priced meaningfully below its expected value. Additionally, it features a full-stack Inventory Management Dashboard to track your purchases, calculate real-time profitability based on the quantitative pricing model, and maintain a transaction ledger.

## Highlights

- **Inventory & Portfolio Dashboard**: A full-stack web application (React/Vite frontend, FastAPI backend) to track purchased skins, calculate live unrealized profit/loss based on historical pricing baselines, and maintain a running balance via a transaction ledger.
- **Multi-threaded producer/consumer pipeline** built on `ThreadPoolExecutor` — one persistent scraping thread per tracked skin, plus a single batch-analysis thread, all coordinated through shared SQLite storage.
- **Float-bucketed pricing baseline**: partitions listings into 100 buckets across the 0.00–1.00 float range (0.01 increments) and computes an outlier-resistant fair-value estimate per bucket using a capped harmonic mean.
- **Reverse-engineered Steam Market API integration**: replicates the internal search payload used by the Steam Community Market's listing search endpoint, including session/cookie management and custom headers.
- **Resilient network layer**: retry logic via `tenacity` (exponential backoff with jitter) layered with explicit handling for Steam's rate limiting.
- **Discord alerting**: pushes a formatted notification with a direct purchase link the moment a listing is flagged as underpriced.

## Architecture

```
tracker.py (Scraper Entry Point)
  │
  ├── CLI: add / remove / help / continue
  │
  └── on "continue" → ThreadPoolExecutor(max_workers = N tracked skins + 1)
          │
          ├── scouting_loop() × N   (backend/scraper.py)
          │      → writes active listings to listings.db
          │      → appends every observed listing to historical_data.db
          │
          └── analyze_batch_overpay_loop() × 1   (backend/batch.py)
                 → recomputes float-bucket baselines (backend/display_chart.py)
                 → sends Discord webhook alert per flagged listing

inventory_dashboard.py (Dashboard Entry Point)
  │
  ├── FastAPI Backend (backend/inventory.py on :8000)
  │      → Exposes endpoints for CRUD operations on inventory and transactions.
  │      → Calculates real-time valuation of inventory items against baselines.
  │
  └── React Frontend (frontend/ via Vite on :5173)
         → Inventory tracking, Skin management, and Transaction ledger UI.
```

## Core Components

### `tracker.py` — Scraper Entry Point & CLI
Initializes scraping databases, then presents an interactive prompt (`add` / `remove` / `help` / `continue`) to configure which skins to track. On `continue`, it spawns scraping threads and a batch-analysis thread.

### `inventory_dashboard.py` — Dashboard Launcher
A runner script that spins up the FastAPI backend and the Vite React frontend concurrently, opening the full-stack dashboard in your default browser.

### `backend/` — Data Pipeline & APIs
- **`scraper.py`**: The scraping loop (one thread per tracked skin) that authenticates against Steam and pages through the market's internal search endpoint.
- **`batch.py`**: Runs every 30 seconds to load active listings, recompute price baselines, and push Discord alerts for listings priced >15% below baseline.
- **`display_chart.py`**: Partitions a skin's full historical data into 100 buckets by float value and computes the harmonic mean for a stable baseline.
- **`inventory.py`**: The FastAPI server that interacts with the frontend dashboard and calculates current expected sale prices by querying the baseline model.
- **`utilities/`**: Shared functions including Steam session/cookie setup, network retry logic, currency conversion, Discord webhook dispatch, and SQLite read/write operations.

### `frontend/` — React Dashboard
A React + TypeScript + Vite web app offering an intuitive UI to manage skins you've added to your portfolio, track their estimated value over time, and log cash transactions.

## Setup

### Prerequisites
- Python 3.10+
- Node.js (v16+) and npm
- SQLite3 (bundled with Python's standard library)

### Installation

1. **Python Backend Setup:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **React Frontend Setup:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Environment Variables:**
   Create a `.env` file in the project root:
   ```ini
   STEAM_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
   SESSION_ID_FALLBACK="your_steam_cookie_session_id"
   DISCORD_WEBHOOK="https://discord.com/api/webhooks/...your_webhook_url"
   ```

## Running the Application

### 1. The Dashboard (Inventory Management)
Launch the full-stack web dashboard to track your portfolio:
```bash
python inventory_dashboard.py
```
This will automatically open `http://localhost:5173` in your browser.

### 2. The Scraper (Market Analysis & Alerts)
Run the core quantitative data pipeline:
```bash
python tracker.py
```
Use `add` to register skins to track, then `continue` to launch the multi-threaded scanning and alerting loops.
