# CS2 Quantitative Trading Pipeline & Inventory Dashboard

A full-stack, multi-threaded quantitative data pipeline and portfolio dashboard that monitors the Steam Community Market for underpriced CS2 skins. It builds statistically-grounded price baselines from historical data, sends real-time Discord alerts for arbitrage opportunities, and tracks real-time unrealized profit/loss of purchased assets.

## The problem

CS2 skin prices vary continuously with wear (float value), not just by the five broad wear categories Steam displays (Factory New, Minimal Wear, etc.). Two items both labeled "Field-Tested" can have meaningfully different fair prices depending on where they sit within that range — but manually tracking this across hundreds of listings, estimating fair value, and calculating portfolio profitability at scale is tedious and error-prone. What started as a simple script to find underpriced skins evolved into a need for a complete quantitative trading pipeline and portfolio management system.

## How it works

The system is split into a high-throughput backend data pipeline and a responsive frontend dashboard, all coordinated through shared SQLite databases running in WAL mode for safe concurrent access.

**Data Pipeline & Scraping.** A pool of concurrent threads (`ThreadPoolExecutor`) constantly monitors the market. Each thread authenticates a session against Steam and pages through the market's internal search endpoint (reverse-engineered from browser traffic), extracting the float value and price of every listing. Requests are rate-limited with randomized delays and wrapped in exponential-backoff retries to respect Steam's network tolerances.

**Quantitative Pricing Model.** Rather than treating a wear category as one price bracket, the analyzer splits each skin's full float range (0.00–1.00) into 100 buckets. For each bucket, it isolates the lowest-priced listings (filtering out obvious outliers) and computes a capped harmonic mean. This statistic is naturally resistant to a handful of overpriced listings skewing the estimate, producing a fine-grained, highly reliable "fair value" curve.

**Signal Generation & Alerting.** A dedicated analysis thread compares all currently active listings against their bucket's baseline price. Anything priced more than 15% below the statistical baseline generates a signal, immediately pushing a Discord webhook with a direct purchase link.

**Portfolio Dashboard.** To manage acquired assets, a FastAPI backend serves a React/TypeScript frontend (built with Vite). The dashboard reads the user's inventory and transaction ledger, continuously recalculating the real-time expected sale price of every holding based on the scraper's live baseline model. This allows for instant visibility into unrealized profit/loss and portfolio balance.

## What I found interesting to build

The float-bucketing quantitative approach was the core design problem: naive averaging gets wrecked by a single mispriced outlier listing, and a simple minimum-price filter is too noisy listing-to-listing. Capping which listings count toward each bucket's baseline and taking a harmonic mean of that filtered set struck a perfect balance between stability and responsiveness to real price movement.

Additionally, evolving the project from a headless Python script into a full-stack application was a rewarding architectural challenge. Designing the FastAPI backend to seamlessly hook into the same active SQLite databases that the high-frequency scraper threads were concurrently writing to—without triggering database locks or deadlocks—required careful concurrency management and WAL mode tuning. 

## Stack

**Backend:** Python · FastAPI · SQLite (WAL mode) · `ThreadPoolExecutor` · `tenacity`  
**Frontend:** React · TypeScript · Vite  
**Integrations:** Discord Webhooks

[View source on GitHub →](https://github.com/MOARMOARMAN)
