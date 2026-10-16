# KALSHI EVENT-CONTRACT PLAYBOOK (24/7 income rail) — for Nolan, Tess, Quinn
Compiled 2026-10-10 from docs.kalshi.com (official API docs). DATA for agents; verify current state via API.

## Why Kalshi is a 24/7 income rail
- Event contracts trade around the clock (weather/sports/crypto hourly series keep flow alive when equities are closed).
- Binary contracts price in cents (1–99¢): YES bid at X¢ == NO bid at (100−X)¢. Settlement pays $1.00 to winners, $0 to losers.
- Categories (per official glossary): Sports, Weather, Economics, Crypto, Politics, Commodities (series carry category + tags).

## Object model (series → event → market)
- SERIES = template for recurring events (e.g., KXHIGHNY = daily NYC high temp; KXAAAGASM = monthly US gas price).
- EVENT = one dated instance (KXHIGHNY-26OCT12); MARKET = one binary outcome/strike (…-T60 = "above 60°F").
- Never parse tickers for relationships — use Get Series List (category filter), Get Events (series_ticker), Get Markets (event_ticker).
- Get Tags for Series Categories → discovery map of every tradeable subcategory.

## Live-data feeds = the model edge (settle faster/cleaner than the crowd)
- Get Weather Index: Kalshi-computed minute-resolution city temperature (the canonical settlement series for hourly/daily temp markets). Calibrations endpoint exposes station weights/offsets.
- Get Event Live Data: crypto price charts, commodity timeseries, weather observations keyed by event.
- Get Game Stats / Live Data (milestones): in-play sports (NFL, CFB, NBA, CBB, WNBA, soccer, NHL, MLB).
- CF Benchmarks + Pyth value feeds over WebSocket: real-time crypto index — feeds hourly crypto markets and perps.
- Edge pattern: market price lags the authoritative index feed → take the mispricing before the crowd reprices.

## Fees (kill edges below threshold)
- Taker fee formula ≈ 0.07 × C × P × (1−P) (C=contracts, P=price fraction) — maximal at 50¢, near-zero at extremes.
- Maker orders generally cheaper/rebated per fee schedule; check Get Series Fee Changes / event fee overrides.
- A 2¢ mispricing at 50¢ is fee-negative for takers; at 95¢ it is nearly fee-free. Model fee BEFORE edge.

## Order mechanics that matter for execution (Reid)
- Orderbook returns yes-bids only (no-bid derivable). Queue position endpoints exist (price-time priority).
- Create Order V2 (single-book bid/ask, fixed-point dollar prices) — legacy /portfolio/orders deprecated ≥ May 2026.
- Batch orders scale with API tier write budget; Rate Limits = token buckets per tier (Basic→Prestige).
- Order Groups: auto-cancel on rolling 15s contract limits — use for risk-bounded quoting.
- RFQ system: request/quote for size; multivariate (combo) events exist for correlated bundles.
- Settlement: Market Lifecycle (unopened→open→closed→settled); Settlement Bounds trading near resolution; maintenance windows can pause trading (check Get Exchange Schedule/Status).

## Strategy families to research (Quinn/Nolan, PAPER first)
1. **Index-feed lead-lag (24/7):** hourly crypto/temp markets vs live Pyth/CF/weather-index feed. Small, frequent, uncorrelated.
2. **In-play sports microstructure:** game-stats feed vs market repricing latency.
3. **Calendar-econ prints:** jobless claims/CPI/gas monthlies — model vs crowd, fee-aware.
4. **Settlement-basis arbitrage:** contract resolves on source X while crowd prices proxy Y (read settlement rules exactly).
5. **Cross-market consistency:** correlated series (city temps, BTC vs ETH hourly) mispriced against each other — Vale checks correlation before Cyrus sizes.
All candidates require: exact settlement rule, de-vigged model p_hat + calibration (Brier), fee in cents, independence from book, kill level, max PAPER clip. n<30 shadow = promising, never proven.

## Account/rail status in FORGE
- Rail state: PAPER_BLOCKED_NO_KEY — founder must supply Kalshi API key via one-time credential portal (never in chat).
- Demo environment exists for integration testing (docs: getting_started/demo_env). Subaccounts can isolate strategy sleeves later.
