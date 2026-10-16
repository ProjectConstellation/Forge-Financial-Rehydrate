# FORGE — 20 Strategic Questions (2026-10-07)
**Purpose:** answers become direct inputs to FORGE's algorithms (new strategy genomes, exit/sizing rules, validation thresholds, data sources, income rails). Please answer with **concrete numbers, exact rules, parameter ranges, named sources/APIs, and evidence** wherever possible. "It depends" answers should say *on what*, with thresholds.

## Context (so answers fit FORGE exactly)
- Autonomous engine on **Coinbase Advanced Trade, personal account, spot only, no leverage, no shorting**. Treasury ≈ **$28**; $1 minimum order.
- Fees (Intro tier, verified): **maker 0.50%, taker 0.90%** → round trip ≈ 1.0–1.4% + spread/slippage.
- Live: **60 most liquid USD markets** (WebSocket BBO, L2 book, trades) + 5-minute and 1-hour bars; regime engine (trend/range/vol/panic/euphoria/breakout).
- Strategies = declarative "genomes" (entry conditions on ~40 causal features, regime filters, ATR-scaled TP/SL, time stops, maker/taker entry, Kelly sizing). Evolution (MAP-Elites) tests ~50,000 genomes per cycle on Modal; DeepSeek V4 Pro designs new genomes; validation = walk-forward folds + untouched 30% holdout + parameter-perturbation robustness + deflated Sharpe + alpha-vs-market-drift test.
- **Findings so far:** (1) at these fees, 5-minute scalping is net-negative; real gross edge exists in panic-wick catches, relative strength and breakouts but fees consume most of it. (2) Best validated strategies are long-only breakouts holding ~3 days; much of their profit is market beta. (3) A full-portfolio replay showed early profit locks (arm at +2.2%) turned **+31% into −20%** — the edge lives in a few large winners. (4) Monte Carlo of the validated portfolio: **unseen 60 days median +3.3% (90% of runs profitable, worst −2.2%)** vs **earlier period median +71%** — large decay out of sample.
- Goal: maximize **true net treasury growth after all costs**, compounding fast, reinvesting everything, improving every hour.

---

## A. Finding the edge
1. **Fee-hurdle-beating inefficiencies.** On Coinbase spot with a 1.0–1.4% round-trip cost, which specific, documented, repeatable crypto inefficiencies have historically produced **net** positive expectancy at **1–72 hour** horizons? For each: exact entry/exit rules, typical win rate and payoff ratio, trade frequency per market per month, and the market regime in which it fails.
2. **Separating durable trend from exhausting rallies.** Our breakouts make money mostly from market beta. Which measurable signals (price, volume, order book, breadth across many coins, BTC dominance proxies) best predict that a crypto move will **persist for 24–72 hours** versus reverse? Give thresholds we can encode.
3. **Making money in range-bound and falling markets without shorting.** Often 70%+ of our markets are quiet ranges or downtrends. What spot-only strategies profit there (mean-reversion bands, deep limit-order ladders that catch liquidation wicks, rotation into relative-strength leaders, sitting in stablecoins)? Exact parameters and expected net returns after 0.5–0.9% fees.
4. **Cross-sectional momentum on the Coinbase top 60.** Optimal ranking signal (raw return, volatility-adjusted return, residual return versus BTC), lookback, holding period, number of holdings and rebalance frequency so that turnover stays below the fee drag? Published evidence welcome.
5. **Order-book signals that last hours, not milliseconds.** Which L2 order-book features (depth imbalance at ±0.25–1%, liquidity withdrawal, replenishment speed, large resting orders, spread regime) have predictive power at **1–4 hour** horizons, usable by a small account that cannot compete on latency?

## B. Execution (keeping the edge we find)
6. **Maker execution on Coinbase Advanced.** Best practices to maximize post-only fill probability while avoiding adverse selection: where to place relative to the touch, re-quote cadence, how long to wait, when crossing the spread (paying 0.90%) is worth it. Any Coinbase-specific behaviors (self-trade prevention, post-only rejects, order-book update rates)?
7. **Lowering fees legitimately.** Current Coinbase Advanced fee tiers and 30-day volume thresholds; whether stablecoin pairs (e.g., USDC/USDT) or specific markets have reduced fees; whether Coinbase One or any program lowers Advanced Trade fees; any maker rebates or promotions accessible to a personal account.

## C. Exits, sizing and risk
8. **Exit architecture for trend strategies.** Given that early profit locks destroyed returns, which exit designs maximize expectancy for 1–3 day crypto trend trades: ATR chandelier stops (which multiple?), time stops, partial take-profits, volatility-regime-switching exits, signal-decay exits? Exact parameter ranges to test.
9. **Position sizing and concurrency for a tiny, correlated portfolio.** With ~$28, a $1 minimum, crypto correlations around 0.6, and 5–12 simultaneous candidates: fractional Kelly vs equal-risk vs volatility parity — which maximizes long-run growth? How many concurrent positions is optimal given correlation, and how should size scale as capital grows?
10. **Drawdown control that doesn't kill compounding.** Which methods (equity-curve filters, regime-based exposure scaling, breadth-based kill switches, volatility targeting) reduce drawdowns in crypto **without** materially reducing long-run growth? Quantified evidence preferred.

## D. Validation (proving it before money goes in)
11. **Fast promotion without fooling ourselves.** We test ~50,000 genomes per cycle and reuse the same holdout across cycles. What practical protocol (combinatorially purged cross-validation, rolling/expanding holdouts, probability of backtest overfitting, deflated Sharpe thresholds, minimum trade counts) keeps false discoveries low **while still promoting winners quickly**? Concrete thresholds please.
12. **Predicting live performance.** Our validated portfolio shows strong decay (earlier period +71% median vs unseen +3.3%). Which backtest statistics best predict live results in crypto, and how much haircut should we apply to backtest returns by default?

## E. Intelligence (DeepSeek and data)
13. **LLM-generated strategy invention.** What prompting, tool-loop and critique patterns make a reasoning model (DeepSeek V4 Pro) produce **genuinely novel, falsifiable** trading hypotheses rather than re-skinned indicator combinations? Example prompt structures, adversarial critic loops, self-consistency checks, and how to feed it failure data effectively.
14. **What should an always-on cheap model watch that code cannot?** Specific **free or cheap** real-time data sources and APIs (exchange listing/delisting announcements, project news, social sentiment, on-chain flows, funding/open-interest from other venues) that have documented predictive value for spot crypto at hour-to-day horizons.

## F. More ways to earn (income rails)
15. **Coinbase-native yield for idle cash.** For a **US personal account**, what is accessible programmatically: USDC rewards (eligibility, current rate, does it accrue in Advanced Trade balances?), staking via API, Coinbase Earn/lending? Exact API endpoints if they exist.
16. **Listing and announcement events.** Do Coinbase listing announcements, roadmap additions or "new market" launches produce systematic price moves **on Coinbase itself** after the announcement? Timing, magnitude, decay, and how to detect them programmatically (RSS, API, X accounts, status pages).
17. **Kalshi as the second rail (≤$50 starting).** Which contract categories show systematic mispricing a model can exploit, current fee structure, API access requirements and rate limits, minimum sizes, and the best first three strategies for a small automated account?

## G. Compounding and self-funding
18. **Capital velocity vs fee drag.** At small capital, how should a system choose trade horizon and frequency to maximize **compound growth per hour/day** after fees? Is there a formula or heuristic (e.g., maximize expected log-growth per hour of capital locked) and what realistic hourly/daily growth rates are sustainable for a well-built small crypto system?
19. **Funding the brain from profits.** What share of realized profits should be reinvested into compute and AI inference versus trading capital, and what ROI thresholds should trigger scaling research spend up or down?

## H. Continuous learning
20. **Adaptive strategy weighting from sparse outcomes.** Best online-learning method to shift capital between strategies and regimes when each strategy produces only a few trades per week (discounted Thompson sampling, Exp3/Exp4, contextual bandits, Bayesian model averaging)? Recommended hyperparameters (discount factors, priors), and how to combine with regime context.

---
**Return format suggestion:** one section per question number, with (a) the direct answer, (b) exact parameters/thresholds, (c) sources/evidence, (d) how confident you are. FORGE will convert answers into testable genomes and policies, run them through the Time Machine and evolution gates, and adopt only what proves itself.
