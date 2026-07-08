# CS2 Skin Scraper & Market Analyzer

A multi-threaded data pipeline that monitors the Steam Community Market for underpriced CS2 skins, builds statistically-grounded price baselines from historical data, and sends real-time Discord alerts the moment a listing is priced meaningfully below fair value.

## The problem

CS2 skin prices vary continuously with wear (float value), not just by the five broad wear categories Steam displays (Factory New, Minimal Wear, etc.). Two items both labeled "Field-Tested" can have meaningfully different fair prices depending on where they sit within that range — but manually tracking this across hundreds of listings, refreshing pages, and mentally estimating fair value doesn't scale. This project automates that entire process.

## How it works

The system runs as a pool of concurrent threads (`ThreadPoolExecutor`) — one persistent scraping thread per tracked skin, plus a single analysis thread — all coordinated through a shared SQLite store running in WAL mode for safe concurrent reads and writes.

**Scraping.** Each scraping thread authenticates a session against Steam and pages through the market's internal search endpoint (reverse-engineered, since it isn't publicly documented), extracting the float value and price of every listing for its assigned skin. Every listing observed is logged to a historical database; listings matching the user's float/price criteria are also kept in an active-listings table. Requests are rate-limited with randomized delays and wrapped in exponential-backoff retries to stay within Steam's tolerances.

**Pricing.** Rather than treating a wear category as one price bracket, the analyzer splits each skin's full float range (0.00–1.00) into 100 buckets. For each bucket, it takes the lowest-priced listings observed (filtering out obvious outliers) and computes their harmonic mean — a statistic that's naturally resistant to a handful of overpriced listings skewing the estimate. This produces a much finer-grained, more reliable "fair value" curve than a flat per-category average.

**Alerting.** Every 30 seconds, a dedicated analysis thread compares all currently active listings against their bucket's baseline price. Anything priced more than 15% below baseline gets pushed to Discord immediately, with a direct purchase link — no need to keep the terminal open or babysit the process.

## What I found interesting to build

The float-bucketing approach was the core design problem: naive averaging gets wrecked by a single mispriced outlier listing, and a simple minimum-price filter is too noisy listing-to-listing. Capping which listings count toward each bucket's baseline (only those within 30% of the current observed floor) and taking a harmonic mean of that filtered set struck a balance between stability and responsiveness to real price movement.

Reverse-engineering Steam's internal market search API was the other major piece — there's no public documentation for the exact request structure, so this involved inspecting real browser traffic to replicate the payload shape, headers, and session/cookie handling well enough to make authenticated requests reliably over long-running sessions.

## Stack

Python · SQLite (WAL mode) · `ThreadPoolExecutor` · `tenacity` (retry/backoff) · Plotly · Discord webhooks

[View source on GitHub →](https://github.com/MOARMOARMAN)
