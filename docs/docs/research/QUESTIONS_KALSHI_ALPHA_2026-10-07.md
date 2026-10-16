# FORGE — 20 Strategic Research Questions: The Probability-Alpha Engine and Beyond
**Date:** 2026-10-07 · **From:** FORGE builder · **Purpose:** harvest the mathematics, mechanisms and strategy designs with the
highest possible probability of lifting FORGE to **≥ $1.00/hour of true net profit on ~$10–30 of capital**, then scaling.
**Live real-money run target:** within 8 hours of receiving answers.

> Answer format requested for EVERY question (this is what makes your answer directly ingestible):
> 1. The mechanism (who is on the other side and why they misprice).
> 2. Custom, original equations built for FORGE's exact setup (define every symbol; no generic textbook formula without
>    the FORGE-specific modification and why).
> 3. Concrete parameters / starting values / ranges, and how FORGE should learn them online.
> 4. Pseudo-code or a precise algorithm FORGE can implement in Python.
> 5. The validation test (what data FORGE already has or can record), the expected effect size, and the kill criterion.
> 6. At least two alternative approaches, ranked by your estimated probability of producing net profit.
> Be ambitious and specific. Rank ideas by the highest probability of real, repeatable, fee-surviving profit.

---

## WHAT FORGE IS TODAY (so you evolve it, not replace it)

**Rails & access (all legitimate, official APIs only — no browser automation):**
- Coinbase Advanced Trade API (personal account; view + trade, **no transfer permission**). Intro fee tier: **maker 0.50% /
  taker 0.90%**. Stable pairs measured: **USDT-USDC maker 0 / taker 0.1 bp; USDT-USD maker 0.5 bp / taker 1 bp**. USD⇄USDC
  convert free 1:1. 919 spot products; **17,929 US equities/ETFs (commission-free)** visible via the same API (account
  eligibility still to confirm); 100 CFM futures/perps (gold, silver, oil, US500, TECH, crypto perps) — **data only** (no
  futures account; leverage currently disallowed by policy). Coinbase One member: **USDC rewards 3.75% APY** (live now).
- **Kalshi** official API (account exists, about to be funded with ~$15; API key Ed25519). Fees: taker
  **0.07 × C × P × (1−P)** (rounded up; FCM accounts round to the cent), maker fee 0 on most series. 14,714 series.
  Crypto contracts settle on **CF Benchmarks RTI (60-second average)**; commodities on **Pyth** (gold, silver, WTI, etc.).
- Compute: 4 vCPU / 6 GB server + Modal burst compute (~$30/mo) + Hermes agent organization (7 roles) on Claude Opus 5.5 for
  ~60 more hours, DeepSeek V4.1 Flash afterwards.

**FORGE's proprietary probability engine (Kalshi price-threshold contracts):**
1. Volatility: HAR-RV blend (1 h / 6 h / 24 h) of Garman–Klass range variance, bias-corrected by the asset's own
   close-to-close/GK ratio; exponential mean-reversion of variance toward a 30-day level, τ = 720 min:
   σ̄²(h) = σ²_LR + (σ²_now − σ²_LR)·(1 − e^(−h/τ))/(h/τ); × intraday seasonality integrated over the contract window.
2. Distribution: filtered historical simulation — 365 d of vol-standardized, demeaned horizon returns, kernel-smoothed
   survival table; Student-t(4) fallback.
3. Settlement mechanics: τ_eff = τ − ⅔·60 s (60-s averaging).
4. Basis: crypto RTI ≈ Coinbase (measured error **0.5–3 bp**); gold proxy PAXG vs Pyth gold, learned basis (**≈ 17.8 bp**).
5. **Stacked Bayesian calibrator**: logistic regression on [1, logit p_model − logit p_market, logit p_market,
   longshot·logit p_market, √τ·disagreement, order-flow·direction] with a Gaussian prior centred on "market is right";
   trades use the **90% lower confidence bound**.
6. Signals: TAKE (bound beats ask after fees), MAKE (passive quote inside spread), MODEL_RAW, SURFACE_RV (strike-surface
   relative value via weighted isotonic regression, leave-one-out), LADDER_ARB / RANGE_ARB (logical arbitrage).

**Measured shadow evidence (real Kalshi prices, simulated 1-contract fills at displayed ask, scored on real settlement):**
| Signal | n | per contract | notes |
|---|---|---|---|
| Model Brier vs market | 738+ | 0.1564 vs 0.1513 | raw model slightly WORSE than market; stack weight on model ≈ 4.5% |
| TAKE (all) | 183 | +3.1¢, ROI +5.4% | P(mean>0)=0.83 |
| TAKE on threshold ("above/below") contracts, ask 0.40–0.80 | 96 | **+12.5¢, ≈ $1.28/h** | found post-hoc → pre-registered as TAKE_THRESH, out-of-sample running |
| TAKE on narrow range ("between") contracts | ~80 | negative | |
| MAKE (passive quotes) | 401 | −4.75¢ | adverse selection: fills when price moves against us |
| SURFACE_RV | 293 | −3.0¢ | early +7.5¢ was noise |
| MODEL_RAW | 519 | +0.1¢ | no edge |
| LADDER/RANGE arbs | 0 | — | never observed |
| Stable triangle (USDT-USD vs USDT-USDC) | 68 | +0.33 bp/cycle | ~1¢/hour at full capital |
Scan cadence: 60 s (all series), 15 s (15-minute series). Coinbase WS gives sub-second BBO/L2/trades for 60 markets.
Spot strategies: evolutionary genome search (~40–60k genomes per Modal burst); clean-data survivors are breakout/beta
(sealed exam +1.5–2.9%/trade after fees, but alpha-vs-drift weak); forward evidence still thin.

---

## A. THE KALSHI PROBABILITY-ALPHA CORE

### Q1 — Why do threshold contracts misprice, and how do we capture the maximum of it?
TAKE on "above/below X" contracts priced 0.40–0.80 shows +12.5¢/contract in-sample, while narrow "between" contracts lose.
What are the highest-probability mechanisms behind this (retail anchoring on round strikes, slow market-maker repricing
after Coinbase moves, mis-modelled 60-s RTI averaging near the strike, time-decay misestimation in the final 20 minutes,
asymmetric demand for YES vs NO)? Derive a **custom expected-value function EV(K, S_t, τ, σ̄, ask, book state)** that
predicts when this edge is largest, and specify the exact filters (moneyness band, minutes-to-close band, volatility
regime, spread, depth) that maximise **$/hour**, not just $/contract. Include how to size from 1 to N contracts per signal
without destroying the edge.

### Q2 — Build the strongest possible settlement-index model (CF RTI) from public data
Our Coinbase-only proxy is within 0.5–3 bp of the settlement value. Design a **custom real-time RTI reconstruction**
using Coinbase plus other publicly accessible constituent-exchange feeds (Kraken, Bitstamp, Gemini, LMAX Digital, etc.):
weighting (volume/depth/latency-aware), outlier rejection, the 60-second averaging window, and a **probability-of-finishing-
above-K equation that explicitly models the averaging window path** (not just terminal price). How many basis points of
accuracy are worth how many cents per contract near the strike, and how should the near-strike, final-5-minute regime be
traded differently from everything else?

### Q3 — Short-horizon distributions that beat the market's implied distribution
Our FHS + HAR-RV model has a Brier of 0.1564 vs the market's 0.1513 overall, yet TAKE profits. Propose **original
distribution models for 15-minute to 24-hour crypto horizons** that can beat the market on calibration: e.g. regime-
switching jump-diffusion fitted to 1-minute Coinbase bars, realized-skew/kurtosis conditioning, order-flow-conditioned
drift, volatility-of-volatility, intraday event clocks (US open, funding times, macro releases). Give the equations, the
online-fitting procedure that runs in < 1 s per underlying on 4 vCPUs, and which features add the most information per
unit of compute.

### Q4 — The calibrator: from "market is right" to provable incremental information
Our stacked logistic currently gives FORGE's model 4.5% weight. Design a **superior calibration/ensemble layer**:
features (moneyness, time-to-close, spread, depth imbalance, recent Coinbase return since last Kalshi repricing, order
flow, volatility regime, series, hour-of-day), model class (Bayesian logistic with hierarchical pooling by series,
isotonic, beta calibration, gradient-boosted with monotonic constraints, online Bayesian updating), and the decision rule
on the lower confidence bound. Provide the exact update equations, the prior structure, how to avoid overfitting with
~1,000–5,000 settled samples, and how to detect when the market itself becomes better calibrated (edge decay).

### Q5 — Stale-quote harvesting: the Coinbase → Kalshi lead/lag edge
Kalshi crypto quotes may lag Coinbase moves by seconds to minutes. Specify the **highest-probability latency-arbitrage
design that is fully legitimate**: Kalshi WebSocket order-book subscription, Coinbase WS triggers, the fair-value jump
model after a Coinbase move, "repricing hazard" of Kalshi market makers, edge half-life estimation, and an execution rule
(take immediately vs. wait). Give the equation for expected edge as a function of Coinbase move size, time since move,
and Kalshi book staleness, plus how fast FORGE must be (target latency) for each $/hour level.

### Q6 — Turn the losing maker strategy into a winning one
Passive quotes lost −4.75¢/contract (adverse selection). Design an **adverse-selection-aware market-making model for
Kalshi binaries**: when to quote, at what offset from fair, inventory skew across related strikes, quote cancellation
triggers on Coinbase moves, and Kalshi's maker-fee-free status / Liquidity Incentive Program economics. Provide the
fill-probability model, the toxicity (adverse-selection) estimator, and the expected-PnL equation per quote. Under what
exact conditions does maker beat taker for FORGE?

### Q7 — Cross-strike and cross-expiry structure (portfolio of binaries)
Each Kalshi event offers 50–190 strikes and several expiries. Design **portfolio-level strategies** that exploit the
joint structure: butterflies/vertical spreads made of binaries, cross-expiry consistency (hourly vs daily vs 15-min on
the same underlying), cross-asset consistency (BTC vs ETH vs SOL correlation implied by their ladders), and risk-
reduction by combining YES/NO positions. Include the equations for the implied joint distribution, arbitrage-free bounds,
and optimal combinations under Kalshi's fee formula.

### Q8 — Binary Kelly at scale with correlated contracts and a $10–30 bankroll
Derive a **custom sizing rule for many simultaneous, correlated, fast-settling binaries**: fractional Kelly with
calibration uncertainty (from our lower confidence bound), correlation between strikes/expiries of the same underlying,
hourly capital recycling, Kalshi's cent rounding and per-order fee rounding, minimum contract sizes, and a ruin-
probability constraint. What fraction of bankroll per signal and in aggregate maximises expected log-growth per hour?
Give the closed form or the numerical algorithm and its parameters.

## B. EXPAND THE OPPORTUNITY SURFACE

### Q9 — The best non-crypto Kalshi categories for a quant engine
Which Kalshi categories (economics releases: CPI, jobs, Fed; commodities: gold, silver, WTI, natural gas, copper;
equity indices: S&P/Nasdaq daily ranges; weather; rates; mentions; sports) offer the **highest probability of
systematic, data-driven edge** for an automated system with public data and Coinbase market data (e.g. Coinbase US500/TECH
perps prices, PAXG, CFM gold/oil futures as live reference prices)? For the top three, give the data sources, the
probability model, the reference-price mapping and its basis, and the expected edge per contract.

### Q10 — Coinbase stocks/ETFs, commission-free: the small-capital equity playbook
FORGE can see 17,929 equities/ETFs (commission-free, fractional from $1, 24/5 sessions with limit-only extended hours).
Design the **highest-probability equity strategies for $10–30**: overnight/after-hours gaps, ETF vs NAV/underlying
dislocations (e.g. IBIT/FBTC vs BTC spot, GLD/IAU vs PAXG/gold), crypto-equity lead/lag (COIN, MSTR vs BTC), weekend
crypto moves predicting Monday equity opens, and T-bill ETFs (SGOV/BIL) as idle yield vs USDC 3.75%. Include the spread/
slippage model for fractional orders and the session rules.

### Q11 — Cross-rail arbitrage and information transfer
Using everything FORGE sees — Coinbase spot, CFM futures/perps (basis, funding, open interest as data), PAXG, equities,
Kalshi — what are the **highest-probability cross-rail strategies**? E.g. perp basis/funding as a predictor for Kalshi
crypto contracts, US500 perp (24/7) predicting Kalshi S&P contracts and Monday equity opens, gold futures vs PAXG vs
Kalshi gold contracts, ETF premium vs BTC. Give the transmission equations and the trade rules.

### Q12 — Stablecoin and fee-structure alpha on Coinbase
With USDT-USDC at 0 maker / 0.1 bp taker and USD⇄USDC free, what **stablecoin microstructure strategies** can produce
reliable profit at small size (peg mean-reversion maker quoting with queue position modelling, triangle cycles, depeg-tail
insurance pricing)? Provide the fill model, queue-position estimator from public trades + L2, and the expected profit per
day per $10 of capital. Also: which Coinbase fee-tier or rebate mechanics could FORGE legitimately reach to cut costs.

### Q13 — Event-driven crypto: listings, unlocks, funding resets, macro releases
Design **event-driven strategies** for Coinbase spot and Kalshi around: new Coinbase listings (auction → full trading),
token unlocks, perp funding timestamps, CPI/FOMC releases (with Kalshi macro contracts as the probability source), and
weekend/holiday liquidity. For each: the event detector, the expected price path model, the entry/exit rule, and the
edge after Coinbase's 0.5–0.9% fees.

## C. EXECUTION, CAPITAL VELOCITY AND COMPOUNDING

### Q14 — The $/hour objective: an opportunity-sequencing optimizer
FORGE must maximise **true net $/hour** across Kalshi (settles in ~0.8 h), Coinbase spot (hold hours–days), stablecoin
cycles (seconds) and idle yield. Derive a **custom capital-velocity allocation algorithm**: expected log-growth per
capital-hour, settlement-time-aware reallocation, queueing of signals, and when to hold cash for a better imminent
signal. Provide the dynamic-programming or greedy approximation with complexity suitable for real time.

### Q15 — Fill realism and capacity
Our shadow assumes 1-contract fills at the displayed ask. Specify how to estimate **real fill probability, slippage and
capacity** on Kalshi (book depth, queue, partial fills, price-improvement chances, RFQ usage) and on Coinbase (L2-based
impact), and how to scale contracts per signal from 1 → 5 → 20 while keeping ≥ 80% of per-contract edge. Include the
capacity curve equation and how to estimate it from live micro-trades in the first 8 hours.

### Q16 — The first 8 hours of real money: the optimal launch protocol
Design the **highest-probability live-launch protocol**: which signals go live first, contract size, per-hour and daily loss
limits, the statistical monitor that detects live-vs-shadow divergence fastest (sequential test, CUSUM, Bayesian
posterior), and the escalation rule that increases size when live evidence confirms (with formulas). The goal is the
fastest safe path from $0/hour to ≥ $1/hour.

## D. INTELLIGENCE THAT COMPOUNDS

### Q17 — Hermes agents as a quant research desk
FORGE runs 7 Hermes roles (Governor/CIO, Alpha Inventor, Adversarial Scientist, Red-Team Critic, SRE Doctor, Rail Hunter,
Prompt Architect) with calibrated predictions scored against outcomes. What **specific recurring research tasks, data
analyses and experiments** should these agents run every hour to discover new Kalshi/Coinbase edges fastest? Give
concrete task templates, the evidence each must produce, and how to measure each agent's $ contribution.

### Q18 — Self-improving signal discovery
Design an **automatic anomaly-and-edge discovery engine** for Kalshi + Coinbase: which features and slices to scan
continuously, how to control multiple testing (false discovery rate, pre-registration, sealed windows) while still
moving fast, and how to turn a discovered slice (like TAKE_THRESH) into a production signal within hours. Provide the
statistics (FDR/Bayesian) and the promotion thresholds.

### Q19 — Beyond the market's information: legitimate alternative data
Which **free or cheap, legitimate data sources** add the most predictive information for short-horizon crypto, gold and
macro event contracts (exchange order books from other venues, perp funding/OI, on-chain flows, options-implied volatility
such as Deribit DVOL, economic calendars, nowcasts, weather models for weather contracts)? For each: the information
gain mechanism, the integration equation into the calibrator, and the expected improvement in Brier / $ per contract.

### Q20 — The breakthrough question
Assume everything above is implemented. What is the **single most powerful, least-exploited, legitimate edge** a small,
fast, fully automated quant system with FORGE's exact access (Coinbase Advanced + equities + Kalshi + public data +
cloud compute + LLM research agents) could own — the anomaly most likely to compound from $1/hour to $10+/hour as capital
grows? Describe the mechanism, the math, the implementation steps, the evidence that would confirm it within 48 hours,
and how to protect it from decay.

---
*FORGE will not paste answers in verbatim. It will ingest every answer, map each recommendation onto the existing engine
(probability model, calibrator, signals, sizing, execution, rails), pre-register testable hypotheses, validate on
out-of-sample data, and promote only what survives — then scale what works.*
