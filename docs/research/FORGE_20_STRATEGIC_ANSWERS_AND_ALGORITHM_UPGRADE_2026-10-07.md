# FORGE — Strategic Research Answers, Algorithm Upgrade Set, and Deployment Guidance

**Date:** 2026-10-07  
**Audience:** The agent that built FORGE  
**Purpose:** Convert the 20 strategic research questions into concrete, testable FORGE upgrades, strategy genomes, execution rules, validation gates, intelligence-routing policies, capital-allocation logic, and expansion rails.

---

# Executive directive

FORGE means **Find Opportunities, Reinvest, Grow, Evolve**.

The mission is not to maximize the number of trades. The mission is to maximize **true net treasury growth after every cost**:

- exchange fees
- spread
- slippage
- failed fills
- adverse selection
- compute
- DeepSeek inference
- Modal compute
- data subscriptions
- membership/subscription costs
- capital lockup/opportunity cost

The engine should remain ambitious. It should constantly search, test, execute, learn, heal, and improve. But FORGE must never manufacture false confidence, overfit 50,000 strategy candidates, or force trades simply because it has a target.

The correct objective is:

\[
\max \sum_t \log(1+r_{t,\text{net}})
\]

subject to:

- survival constraints,
- calibrated uncertainty,
- liquidity constraints,
- finite strategy capacity,
- true wallet/account reconciliation,
- no unauthorized transfers,
- no leverage or shorting in the current Coinbase phase.

This naturally produces compounding. If FORGE earns and reinvests, future dollar profits can grow because the capital base grows. But constant percentage returns do **not** scale indefinitely; strategy capacity, liquidity, slippage, market regime, and edge decay must be modeled explicitly.

---

# Critical Coinbase One finding — the $4.99 plan

## What Coinbase One Basic currently gives

Coinbase currently lists **Coinbase One Basic** in the U.S. at:

- **$4.99/month**
- **$49.99/year**
- zero trading fees on up to **$500/month** of **simple Coinbase crypto trades**
- account protection up to **$1,000**
- **3.50% APY on USDC** on the main Coinbase One plan page
- +5% staking rewards boost
- member sweepstakes and other member benefits

Official source:

- https://www.coinbase.com/one?tier=basic

However, this is the crucial limitation:

> **The zero-fee benefit does not apply to Coinbase Advanced.**

Coinbase says this explicitly in its Coinbase One disclosures and help pages:

- https://help.coinbase.com/en/coinbase/other-topics/coinbase-one/benefit-disclosures
- https://help.coinbase.com/en/coinbase/other-topics/coinbase-one/account

Coinbase also says simple Coinbase buys/sells may include a **spread**, and a **1% limit-order execution fee** is not waived by the zero-fee benefit.

FORGE is currently using **Coinbase Advanced Trade API**, so **do not subtract Advanced maker/taker fees merely because the operator has Coinbase One Basic**.

### Important architecture rule

Build a `MembershipEconomicsAdapter` that treats Coinbase One as a separate economic input.

FORGE must query or configure:

```text
coinbase_one_tier
monthly_subscription_cost
simple_trade_zero_fee_cap
advanced_trade_rebate_percentage
advanced_trade_rebate_monthly_cap
usdc_reward_rate
staking_reward_boost
onchain_member_benefits
```

Then FORGE must calculate whether a Coinbase One tier creates **incremental value for FORGE**.

At the current ~$28 treasury:

- $4.99/month equals **17.82% of the entire treasury**
- 3.5% APY on $28 earns only about **$0.98/year**
- approximately **$0.0817/month**

If paying for Basic solely to earn the 3.5% USDC reward, the approximate average balance needed to cover the $4.99 monthly subscription is:

\[
\frac{4.99\times 12}{0.035}\approx \$1,710.86
\]

The annual $49.99 plan breaks even on a 3.5% USDC yield alone at roughly:

\[
\frac{49.99}{0.035}\approx \$1,428.29
\]

Therefore:

**Do not buy Coinbase One Basic solely as a FORGE fee/yield optimization at a $28 bankroll.**

If the operator already wants Coinbase One for personal/card/security/other benefits, FORGE should still recognize the benefit, but it should distinguish:

- `full_subscription_cost`
- `incremental_cost_attributable_to_FORGE`

### Coinbase One Preferred

Coinbase currently lists Preferred at **$29.99/month** and says it offers a **25% rebate on Advanced spot trading fees, up to $100/month**.

At $29.99/month, the membership would need about:

\[
\$29.99 / 0.25 \approx \$119.96
\]

in Advanced spot fees per month just to break even on the rebate alone.

That is obviously not appropriate for a ~$28 treasury.

### USDC rate discrepancy

Current Coinbase pages are not completely consistent: the Coinbase One plan page shows **3.50% APY** while the dedicated USDC landing page currently displays **3.75%** for Coinbase One members.

Relevant sources:

- https://www.coinbase.com/one?tier=basic
- https://www.coinbase.com/usdc

Therefore FORGE must **never hard-code the USDC APY**. Treat the account-displayed rate as authoritative and log the effective realized reward rate from posted rewards.

---

# Current Coinbase fee reality

Coinbase’s current U.S. entry-level Advanced spot rates are:

- **0.50% maker**
- **0.90% taker**

Source:

- https://www.coinbase.com/blog/were-lowering-fees-for-many-active-traders-on-coinbase-advanced
- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees

Coinbase says Advanced tiers now begin at **$10,000 qualifying volume**, down from $25,000. Fee tiers may also depend on USDC balance or other qualifying criteria, and certain stablecoin pairs can use separate schedules.

Therefore FORGE must obtain the actual current account/product fee schedule at runtime and never assume 0.50/0.90 forever.

Baseline costs at current rates:

```text
maker -> maker ~= 1.00% round trip before slippage/spread
maker -> taker ~= 1.40%
taker -> maker ~= 1.40%
taker -> taker ~= 1.80%
```

That one fact should shape the entire alpha stack.

---

# Proprietary FORGE metrics to add now

These are custom FORGE composite metrics. They are starting engineering specifications, not claims that academic literature has validated the exact coefficients.

## 1. Edge Coverage Ratio — ECR

\[
ECR=\frac{E[\text{gross return}]}{\text{expected fees + spread + slippage + execution uncertainty}}
\]

Starting gates:

```text
ECR < 1.5         REJECT
1.5 <= ECR < 2.0 SHADOW ONLY
2.0 <= ECR < 3.0 SMALL LIVE ELIGIBLE
3.0 <= ECR < 4.0 STRONG
ECR >= 4.0        CONCENTRATION CANDIDATE if all other gates pass
```

Never use ECR alone. It is a cost-survival gate.

## 2. Capital Velocity Growth Score — CVGS

\[
CVGS=\frac{E[\log(1+r_\text{net})]\times P(\text{fill})\times C_\text{calibration}}
{E[\text{capital-hours locked}]}
\]

Then subtract:

- correlation penalty,
- drawdown penalty,
- opportunity-cost penalty,
- model uncertainty penalty.

This makes FORGE compare a 3-day 8% opportunity against multiple shorter opportunities intelligently rather than merely choosing the largest percentage return.

## 3. Opportunity Half-Life — OHL

Every signal receives an estimated decay half-life:

```text
seconds
minutes
hours
days
```

The shorter the half-life, the more valuable low-latency execution and fast intelligence routing become.

## 4. Live Retention Ratio — LRR

Backtests are discounted according to how much of prior simulated edge survives shadow/live deployment.

For comparable annualized/log-growth quantities:

\[
LRR = \mathrm{median}\left(\mathrm{clip}\left(
\frac{g_\text{shadow/live}}{g_\text{backtest}},0,1
\right)\right)
\]

Use hierarchical/Bayesian shrinkage rather than one raw ratio.

Given FORGE’s observed severe decay, begin with a conservative prior:

```text
backtest-to-live haircut H = 0.10 to 0.25
```

for highly searched strategy families.

Raise H only when forward/shadow/live evidence earns it.

## 5. Intelligence Value of Information — IVOI

\[
IVOI=\frac{EV_{\text{after extra intelligence}}-EV_{\text{before}}}
{\text{incremental inference/compute cost}}
\]

Starting rules:

```text
IVOI < 1.0   economically destructive
1.0-1.5      generally avoid
1.5-3.0      selective
>=3.0        worthwhile
>=5.0        aggressive escalation candidate
```

This applies to DeepSeek Pro, Flash, JEV if integrated, Modal simulations, and paid data.

---

# A. FINDING THE EDGE

## 1. Fee-hurdle-beating inefficiencies

### Direct answer

There is no credible basis for claiming that a fixed, generic Coinbase spot strategy reliably produces net positive expectancy after a 1.0–1.8% round-trip cost across all regimes.

The best-supported families worth testing are:

1. multi-hour/day **time-series momentum and breakout persistence**
2. **large/liquid-coin momentum** rather than naive cross-sectional churn
3. **panic/liquidation reversal** after capitulation plus order-flow recovery
4. **relative strength/residual momentum** with slow turnover
5. **event-driven/listing/news continuation or reversal**
6. **cross-market order-flow / derivatives context** as a filter
7. cross-coin **leader-laggard/spillover** signals

Research supports crypto momentum and return predictability, but recent cost-aware replication also shows that many attractive gross effects disappear after realistic transaction costs.

Evidence:

- Machine learning cross-section: price, past alpha, illiquidity and momentum were important predictors; long-side abnormal returns mattered.  
  https://www.sciencedirect.com/science/article/pii/S1057521924001765
- Recent net-of-costs replication warns cross-sectional momentum can disappear after costs on a tradable universe.  
  https://papers.ssrn.com/sol3/Delivery.cfm/7404139.pdf?abstractid=7404139
- Large/liquid coins can exhibit daily momentum while illiquid coins exhibit reversal.  
  https://www.sciencedirect.com/science/article/pii/S1057521921002349
- World order flow predicts crypto returns in 2026 research.  
  https://www.sciencedirect.com/science/article/pii/S1386418126000029
- Quarter-hour order imbalance in crypto futures predicts 4–12 hour returns in recent research.  
  https://arxiv.org/abs/2607.09426

### FORGE strategy families to test

#### `PERSISTENCE_BREAKOUT_V2`

```yaml
horizon: 24h-96h
entry:
  price_breakout:
    close_1h > prior_72h_high
  residual_strength_z_24h: ">= 1.0"
  breadth_positive_24h: ">= 0.60"
  volume_z_6h: ">= 1.0"
  btc_trend_score: "> 0"
  spread_percentile: "<= 75"
  trend_persistence_score: ">= 70"
execution:
  maker_first: true
  cross_only_if_signal_decay_justifies: true
exit:
  convex_trend_exit: true
```

**FORGE promotion targets, not claimed historical constants:**

```text
win rate target: 35%-50%
average win / average loss: 2.0x-3.5x
frequency: ~1-4 trades per market per month
```

The strategy is allowed to have a sub-50% win rate because trend strategies can derive expectancy from a few large winners.

Failure regimes:

- broad sideways chop
- false-breakout euphoria
- extremely high transaction costs/spreads
- abrupt macro risk-off reversal
- BTC reversal with collapsing breadth

#### `PANIC_ABSORB_V1`

Long-only liquidation/capitulation reversal.

Entry candidate:

```text
1h standardized return <= -3.0 sigma
AND volume >= 4x rolling same-hour median
AND aggressive sell-flow z-score <= -2.0
AND within 5-30m:
    order-flow imbalance recovers through 0
    bid depth replenishment >= 1.5x local trough
AND expected mean reversion >= 2.5x expected all-in transaction cost
```

Exit:

```text
first of:
- anchored VWAP recovery
- 1h EMA20 recovery with weakening impulse
- 2-8h time stop
- structural stop beneath capitulation low
```

Target research profile:

```text
win-rate target: 45%-60%
payoff target: 1.5x-3.0x
event frequency: rare; 0-2 high-quality events/market/month
```

Do not force frequency.

#### `RELATIVE_ALPHA_ROTATION_V1`

Instead of raw return, regress each asset on BTC and optionally ETH/market index.

\[
r_i=\alpha_i+\beta_{BTC}r_{BTC}+\beta_{ETH}r_{ETH}+\epsilon_i
\]

Rank:

\[
Score_i =
0.55 \cdot z(\text{residual return}_{24h})
+0.25 \cdot z(\text{residual return}_{72h})
+0.20 \cdot z(\text{liquidity-adjusted trend quality})
\]

Only rotate when the expected improvement exceeds the cost of selling the incumbent and buying the challenger.

This directly attacks turnover.

### Confidence

**High** that longer-horizon momentum/trend and event-driven families deserve priority.  
**Medium** that panic reversal and order-flow context add exploitable net edge.  
**Low** that any fixed published parameter will remain profitable without FORGE’s own validation.

---

## 2. Separating durable trend from exhausting rallies

### Build a proprietary `Trend Persistence Score — TPS`

Scale every feature to 0–100 or z-score and use:

\[
TPS =
0.25R
+0.20B
+0.15T
+0.15V
+0.15O
+0.10Q
-0.20X
\]

where:

- `R` = residual strength vs BTC/market
- `B` = market breadth
- `T` = BTC/market trend
- `V` = volume confirmation
- `O` = persistent order-flow confirmation
- `Q` = breakout quality
- `X` = exhaustion/divergence penalty

### Starting thresholds

```text
TPS >= 80: high-quality continuation candidate
TPS 70-79: normal entry candidate
TPS 55-69: monitor / small only
TPS < 55: do not open trend position
TPS < 45 for 2 consecutive 1h closes: exit/de-risk candidate
```

### Features

```text
breadth_24h = fraction(top60 with 24h return > 0)
breadth_above_h1_ema50 = fraction(top60 above H1 EMA50)

strong breadth:
  breadth_24h >= 0.60
very strong:
  >= 0.70
weak:
  < 0.40
danger:
  < 0.30

residual_strength_z_24h:
  strong >= +1.0
  exceptional >= +1.5

volume_z_6h:
  confirm >= +1.0
  climax/exhaustion warning >= +2.5 if price extension is extreme

price_extension:
  avoid new chase if price > 3 ATR above H1 EMA20
  unless regime-specific breakout model proves otherwise
```

### Breadth divergence exhaustion

If price makes a new 24/72h high but:

```text
breadth falls >= 20 percentage points from its recent peak
AND BTC trend weakens
AND asset volume climax occurs
```

subtract aggressively from TPS.

### External derivative context

Even though FORGE trades Coinbase spot only, external futures order flow, funding, OI and liquidation data can be used as **information**, not as a trading venue.

Recent research supports predictive content in order flow. Use it as a context feature, not a standalone trade.

### Confidence

**Medium-high** in the feature families.  
**Medium** in the exact weights; they must evolve under FORGE validation.

---

## 3. Range-bound and falling markets without shorting

The strongest rule is:

> **USDC is a valid position.**

FORGE should not interpret “24/7 earning” as “always own a volatile coin.”

### `RANGE_RECLAIM_V1`

Only activate if:

```text
H1 ADX < 20-22
7d range width >= 4x expected round-trip cost
price is in bottom 10%-15% of validated range
spread <= 60th percentile
no broad panic regime
```

Trigger:

```text
false breakdown of range by >= 0.75-1.25 ATR
then reclaim range boundary/VWAP
and order flow turns positive
```

Entry maker-first.

Target gross excursion:

```text
minimum target >= 2.5x all-in expected cost
preferred >= 3.0x
```

Exit at midrange first only if expected net return remains worthwhile; otherwise upper 35%-40% of range.

### `PANIC_ABSORB_V1`

As above, only after capitulation and absorption—not during free-fall.

### `CASH_IS_ALPHA`

If:

```text
breadth < 30%
BTC trend negative
trend strategies have negative posterior EV
range width insufficient to overcome fees
```

hold USDC and keep research loops active.

Avoiding a negative-EV trade is economically equivalent to preserving capital for a better trade.

### Expected net return

Do **not** hard-code a promised expected return for these. FORGE must estimate from its own walk-forward/shadow history by regime. Any model showing net edge smaller than a 50%-100% margin above costs should remain shadow-only.

### Confidence

**High** that staying in USDC is required in hostile long-only regimes.  
**Medium** on panic/reclaim families.  
**Low-medium** on generic range scalping at current Coinbase fees.

---

## 4. Cross-sectional momentum on Coinbase top 60

Naive weekly rebalancing is likely too expensive at current fees.

### Recommended ranking signal

Prefer **residual** rather than raw momentum.

For each coin:

1. estimate rolling beta to BTC and optional broad top-60 equal-weight index,
2. compute residual return,
3. standardize by residual volatility.

\[
RAM_i =
0.50 z\left(\frac{\epsilon_{24h}}{\sigma_\epsilon}\right)
+0.35 z\left(\frac{\epsilon_{72h}}{\sigma_\epsilon}\right)
+0.15 z(\text{liquidity quality})
\]

### Starting design

```text
lookback: 24h + 72h ensemble
hold: 24h-96h
number holdings at $28: usually 1; at most 2 if weakly correlated
rebalance: event/score triggered, not clock-triggered
minimum rank improvement before switching: enough to clear BOTH exit+entry costs plus 50% buffer
```

### Turnover brake

Only rotate from incumbent `A` to candidate `B` if:

\[
EV(B)-EV(A) >
Cost(\text{sell A})+Cost(\text{buy B})+Buffer
\]

with starting `Buffer = 0.5 * switching_cost`.

This prevents churn.

Recent net-of-cost replication argues cost-aware cross-sectional momentum can disappear, so FORGE should treat cross-sectional ranking as an **allocation filter**, not assume it is a standalone alpha source.

### Confidence

**High** that residualization and turnover control are superior to raw frequent rotation for this setup.

---

## 5. Order-book signals at 1–4 hour horizons

Do not over-trust static L2 imbalance. Many order-book effects decay much faster than FORGE’s target horizons.

The better approach is **persistent flow state**.

### `Persistent Order-Flow State — POFS`

Measure:

```text
weighted depth imbalance at:
  +/-0.25%
  +/-0.50%
  +/-1.00%

aggressive trade imbalance:
  5m
  15m
  60m

liquidity withdrawal rate
replenishment after aggressive sweeps
spread percentile
depth recovery half-life
```

Composite:

\[
POFS =
0.30 z(OFI_{60m})
+0.20 z(OFI_{15m})
+0.15 z(depth\ imbalance_{0.5\%})
+0.15 z(replenishment)
-0.10 z(ask\ withdrawal\ against\ long)
-0.10 z(spread)
\]

Require persistence across at least 2 time windows.

Use POFS primarily as:

- confirmation,
- entry-timing improvement,
- exit-decay signal,
- panic-absorption detector.

Do not make it the only reason for a 3-day position.

Research:

- Order flow and cryptocurrency returns:  
  https://www.sciencedirect.com/science/article/pii/S1386418126000029
- Quarter-hour periodic order imbalance predicts 4–12h returns in futures:  
  https://arxiv.org/abs/2607.09426

### Confidence

**Medium-high** in persistent order-flow context.  
**Low** in raw snapshot imbalance as standalone hour-scale alpha.

---

# B. EXECUTION

## 6. Maker execution on Coinbase Advanced

Execution quality is part of alpha.

### Maker-first default

For 1–72h signals, use maker-first unless the expected cost of waiting exceeds the extra taker fee.

Current fee delta per leg:

```text
taker 0.90% - maker 0.50% = 0.40 percentage points
```

### `Cross-or-Wait` decision

Cross the spread only if:

\[
ExpectedAdverseMoveDuringWait
+
MissedOpportunityCost
>
FeeDelta + MakerSpreadBenefit + SafetyBuffer
\]

Starting safety buffer:

```text
5-15 bps depending on product liquidity/regime
```

At current fees, FORGE should generally require expected near-term adverse movement of roughly **0.45%-0.55% or more** during the expected maker wait before paying taker purely for urgency.

### Maker quoting policy

For buys:

```text
post-only near best bid / inside spread when valid
do not chase every tick
```

Requote triggers:

```text
touch moves away >= 1 tick AND >= 0.05%-0.10%
OR queue/fill model says fill probability deteriorated materially
OR quote age exceeds signal-specific TTL
```

Typical starting TTL:

```text
slow 24-72h trend: 60-180s
faster breakout: 10-30s
panic reversal: adaptive 5-30s
```

Do not use a universal timer.

### Learn fill probability

Maintain:

```text
P(fill | market, spread, distance_from_touch, queue_age, regime, volatility, time_of_day)
```

Track adverse selection:

```text
post_fill_return_1m
post_fill_return_5m
```

If maker fills systematically occur immediately before adverse moves, adjust quote distance or require stronger signal.

### Coinbase-specific operational rules

Coinbase Advanced has market states including:

- Full Trading
- Limit Only
- Post Only
- Cancel Only
- Trading Disabled
- View Only

Source:

- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/market-availability

The executor must respect state automatically.

Also use:

- unique client order IDs
- order preview where available
- idempotent retries
- post-restart reconciliation
- stale-book protection
- authoritative Coinbase fill/balance state

### Confidence

**High**.

---

## 7. Lowering fees legitimately

### Current facts

Coinbase Advanced U.S. entry level:

```text
maker 0.50%
taker 0.90%
```

Advanced lower tiers now start at **$10,000 qualifying volume**.

Coinbase says tier qualification can consider trading volume or USDC balance, whichever is favorable, and some pairs have separate fee schedules.

Sources:

- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees
- https://www.coinbase.com/blog/were-lowering-fees-for-many-active-traders-on-coinbase-advanced

### Never manufacture volume to reach a tier

Create:

\[
TierBenefit =
ExpectedFutureNotional \times (CurrentFee-NextFee)
-
CostOfAdditionalVolume
\]

Only allow additional volume if it is already positive-EV trading. Never wash/churn merely for fee tier advancement.

### Coinbase One Basic

Again:

**Basic does not rebate Advanced Trade fees.**

Its $500/month zero-fee allowance applies to simple Coinbase crypto trades, not Advanced.

FORGE’s current API execution should continue to assume normal Advanced fees.

### Coinbase One Preferred

Preferred currently says:

```text
25% back on Coinbase Advanced spot fees
up to $100 USDC/month
```

Only consider when expected monthly rebate exceeds membership cost by a comfortable margin.

### Stablecoin pairs

Coinbase notes some stablecoin pairs have separate schedules.

FORGE should:

```text
fetch current pair-level fees
compare stablecoin routes
never assume USDC/USDT or another pair is free
```

### Confidence

**Very high** on current Coinbase facts.

---

# C. EXITS, SIZING AND RISK

## 8. Exit architecture for 1–3 day trend trades

Your replay already produced a crucial lesson:

> Early profit locking killed the convexity.

The edge appears concentrated in relatively few large winners. Therefore FORGE should optimize for **positive skew**, not a high percentage of small wins.

### `Convex Trend Exit V1`

#### Initial catastrophe stop

Use:

```text
stop_distance = max(
  2.5 * ATR14_1h,
  distance_to_valid_structural_swing_low
)
```

Do not make the structural stop absurdly wide; position sizing must adjust instead.

Test range:

```text
2.0 ATR
2.5 ATR
3.0 ATR
3.5 ATR
```

#### Do not arm breakeven early

No automatic breakeven/profit lock merely because price is +2%.

Instead begin trailing only after:

```text
MFE >= 1.5-2.0 ATR
```

#### Chandelier stop

\[
Stop = HighestSinceEntry - k\cdot ATR
\]

Test:

```text
low/normal volatility: k = 2.5-3.5
normal:                k = 3.0-4.5
high volatility:       k = 4.0-5.5
```

The wider trail in high volatility prevents large winners from being strangled.

#### Signal-decay exit

Exit/de-risk when at least two of:

```text
TPS < 45 for 2 hourly closes
H1 EMA20 slope negative for 2 closes
breadth falls >=20 percentage points from trade peak
BTC regime flips bearish
POFS turns strongly negative
```

#### Time stop

At `24h`:

```text
if unrealized progress < 0.5 ATR
AND TPS < 55
=> exit
```

Allow extension to 72–96h only if the strategy renews its edge.

#### Partial take profits

Default: **OFF** for convex trend strategies.

Test only:

```text
10%-25% trim after >=4 ATR MFE
```

and retain only if walk-forward log growth improves without destroying right-tail participation.

### Confidence

**High** that exits must preserve convexity.  
**Medium-high** on these ATR ranges as test priors.

---

## 9. Position sizing and concurrency

Use **Bayesian fractional Kelly**, not raw Kelly.

Binary approximation:

\[
f^*=p-\frac{1-p}{b}
\]

Continuous approximation:

\[
f^*\approx \frac{\mu}{\sigma^2}
\]

Then use only:

```text
0.10-0.25 Kelly
```

until substantial live evidence exists.

### Correlation penalty

For `n` similarly exposed positions with average correlation `rho`:

\[
Penalty=\frac{1}{1+(n-1)\rho}
\]

At `rho = 0.6`:

```text
n=2 -> 0.625
n=3 -> 0.455
n=5 -> 0.294
```

This shows why “six positions” with $28 is fake diversification.

### Tiny treasury policy

At roughly $28:

```text
normal: 1 live position
occasionally: 2, only if truly differentiated / weakly correlated
```

Risk-at-stop is more meaningful than notional allocation.

Starting experimental prior:

```text
per-position risk-at-stop: 2%-5% treasury
aggregate open risk: 6%-10%
```

Notional can be much larger if stop distance is tight and the strategy has earned confidence.

Suggested formula:

\[
riskFraction =
\min(
RegimeCap,\ 
0.25Kelly,\ 
0.05\times CalibrationFactor\times RobustnessFactor
)
\]

\[
Notional =
\frac{Equity\times riskFraction}
{StopDistanceFraction}
\]

then cap by:

- liquidity,
- concentration,
- exchange minimums,
- strategy capacity,
- account reserve policy.

### Confidence

**High**.

---

## 10. Drawdown control without killing compounding

Do not use one global “off” switch for every strategy.

Use **conditional exposure scaling**.

### Market breadth exposure gate

Starting prior:

```text
breadth >= 60%:
    trend exposure = 100%

breadth 40%-60%:
    trend exposure = 50%-75%

breadth 30%-40%:
    trend exposure = 25%-50%

breadth < 30%:
    generic long-trend exposure = 0%-25%
    panic specialists may still operate
```

### Volatility gate

```text
realized volatility percentile > 90:
    halve generic strategy notional

>97:
    only specialized high-volatility strategies unless exceptional validated edge
```

### Treasury drawdown state

Starting experimental values:

```text
-5% from high-water mark:
    new-risk multiplier 0.75

-10%:
    multiplier 0.50
    mandatory DeepSeek postmortem
    promote only highly validated candidates

-15%:
    pause generic live deployment
    research/shadow continues
    specialized live strategy only if explicit recovery gate passes
```

These should later become dynamic based on empirical survival probabilities.

### Confidence

**Medium-high**.

---

# D. VALIDATION

## 11. Fast promotion without fooling ourselves

This is one of the most important FORGE upgrades.

Testing 50,000 genomes repeatedly against the same holdout creates holdout contamination.

### Required redesign: `Research Trial Ledger`

Every candidate records:

```text
strategy_family
ancestor
features
parameters
datasets_seen
folds_seen
holdouts_seen
number_of_revisions
research_model_used
reason_generated
```

### Sealed data protocol

Use:

1. training windows,
2. purged/combinatorial cross-validation,
3. family validation window,
4. one-time sealed final exam,
5. subsequent live/shadow forward period.

Once a final holdout has influenced strategy design, it is no longer a holdout.

### CPCV / purging

Use combinatorially purged cross-validation when labels overlap in time and purge/embargo enough bars to prevent leakage from the maximum lookahead/holding period.

### Starting promotion gates

#### Research candidate

```text
>=20 independent-ish trades pooled across assets/regimes
positive net OOS expectancy in >=70% of folds
ECR >=1.5
no obvious leakage
```

#### Shadow promotion

```text
>=30 net-of-cost OOS trades/events
Deflated Sharpe confidence >=95%
estimated PBO <20%
positive sealed validation
parameter perturbation survival >=70%
no catastrophic single-regime dependence unless explicitly regime-specialized
```

#### Tiny live capital

```text
shadow/live tracking confirms direction
transaction-cost model calibrated
LRR prior applied
small calibration order succeeds
risk governor approves
```

#### Larger live promotion

Aim for:

```text
50-100+ OOS/shadow/live trades or independent events
PBO <10%
DSR confidence >=95%-97.5%
positive performance across >=3 separated windows
evidence in >=2 relevant regimes unless intentionally specialized
```

Rare event strategies can borrow evidence hierarchically across assets/markets and start with tiny exposure rather than wait for an arbitrary count.

### Multiple testing

The 50,000 MAP-Elites population is useful for search, but FORGE should not equate the top backtest with discovery.

The more strategies examined, the more aggressive the multiple-testing penalty must become.

Research:

- Deflated Sharpe / backtest overfitting framework:
  https://papers.ssrn.com/
- Recent audit-grade pre-validation discussion:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7308022

### Confidence

**Very high**.

---

## 12. Predicting live performance and backtest haircut

The best predictors of live survival are usually not raw backtest CAGR.

Prioritize:

1. fold consistency,
2. parameter stability,
3. perturbation robustness,
4. PBO / DSR,
5. cost cushion / ECR,
6. edge across separated periods,
7. regime specificity,
8. slippage sensitivity,
9. turnover sensitivity,
10. dependence on one or two giant winners,
11. beta exposure,
12. feature causality/plausibility.

### FORGE `Backtest Haircut Engine`

For every strategy family:

```text
backtest net edge
shadow net edge
tiny-live net edge
normal-live net edge
```

Estimate live retention ratio hierarchically.

Given FORGE’s observed earlier-vs-unseen collapse, initialize heavily searched strategy families at:

```text
10%-25% of estimated backtest edge
```

until shadow/live evidence improves the haircut.

Do **not** simply divide +3.3% by +71% unless the two measurements are normalized to identical horizon/risk assumptions.

### Winner concentration

Your trend strategies rely on a few large winners.

Do not automatically penalize this as “bad.” Instead measure:

```text
top_1_trade_contribution
top_5_trade_contribution
return_without_top_winners
tail_capture_ratio
```

Then ensure exit logic preserves the source of expectancy.

### Confidence

**High**.

---

# E. INTELLIGENCE — DEEPSEEK AND DATA

## 13. LLM-generated strategy invention

### DeepSeek current architecture note

DeepSeek currently supports both:

- `deepseek-flash` = DeepSeek V4.1 Flash
- `deepseek-v4-pro` = DeepSeek V4 Pro

Both support:

- thinking/non-thinking modes,
- JSON output,
- tool calls,
- Responses API,
- very long context.

Official sources:

- https://api-docs.deepseek.com/quick_start/pricing/
- https://api-docs.deepseek.com/updates/
- https://www.deepseek.com/en/news/deepseek-v4-1-flash/

DeepSeek says V4.1 Flash is newer and extremely capable; keep Pro available only where its measured incremental value warrants it.

### Do not ask the model: “invent a profitable strategy”

Use a scientific loop.

## `FORGE Hypothesis Foundry`

### Stage 1 — Evidence pack

Give the Scientist:

```text
market-regime summary
feature behavior
failed strategy clusters
winner clusters
execution losses
false-positive patterns
missed opportunities
counterfactual outcomes
cost model
allowed actions
```

**Do not expose sealed holdout results.**

### Stage 2 — Scientist prompt

Require:

```text
1. observed anomaly
2. proposed economic/mechanical cause
3. predicted direction
4. expected horizon
5. market/regime where it should work
6. market/regime where it should fail
7. exact falsifiable entry/exit hypothesis
8. data required
9. transaction-cost sensitivity
10. reasons this is structurally different from existing strategy families
11. what result would make you reject the hypothesis
```

### Stage 3 — Adversarial critic

Fresh context/model pass:

```text
Find leakage.
Find beta masquerading as alpha.
Find fee sensitivity.
Find regime confounding.
Find post-hoc parameter choices.
Find unsupported causal story.
Find duplicate ideas in the strategy archive.
```

### Stage 4 — Mechanism judge

Ask whether there is a plausible mechanism for why another market participant would leave the edge available.

Possible classes:

- attention delay,
- forced liquidation,
- liquidity imbalance,
- cross-market information lead,
- inventory pressure,
- behavioral over/underreaction,
- event probability repricing,
- structural fee/incentive difference.

### Stage 5 — Genome compiler

Use a low-cost strict structured-output pass to convert only surviving hypotheses into declarative genomes.

### Stage 6 — bounded revision

Maximum ~3 revisions from test feedback before the candidate is frozen or discarded.

This prevents an LLM from p-hacking endlessly.

### Novelty score

A “new family” must be structurally distinct.

Starting rule:

```text
feature overlap <70%
OR program/tree structural distance >25%
OR genuinely different causal mechanism/horizon/execution logic
```

Otherwise classify it as a mutation, not a novel family.

### Failure-data prompt structure

Give DeepSeek failures in clusters:

```json
{
  "failure_mode": "false breakout",
  "regime": "range_high_vol",
  "n": 37,
  "median_mfe": 0.8,
  "median_mae": 1.9,
  "common_features": [...],
  "execution_cost_bps": ...,
  "counterfactual_best_action": ...
}
```

Ask it to improve the **mechanism**, not merely tune a threshold.

### Confidence

**High** in this process as a research framework; actual alpha remains empirical.

---

## 14. What should an always-on cheap model watch?

Code should handle structured numerical feeds. Cheap AI should watch **unstructured, semantic, multi-source context**.

### Free/cheap sources to add

#### Coinbase official

1. **Coinbase market data / WebSocket**
2. **Coinbase Status API**
   - https://status.coinbase.com/api
3. **Coinbase new asset/listing phases**
   - https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/new-asset-listings

Use these for:

- market status,
- outage risk,
- launch transitions,
- product discovery,
- listing events.

#### CoinGecko Demo

Current free plan:

- 10,000 calls/month
- up to 100 calls/minute
- 60+ endpoints
- ~60-second data freshness on free tier

Source:

- https://www.coingecko.com/en/api/pricing

Use for:

```text
global market cap
BTC dominance
cross-exchange price sanity
market cap / liquidity context
new asset metadata
```

#### CryptoQuant Basic

Current free plan:

- 10,000 credits/month
- 10 calls/minute
- 30 days history
- market data on free tier
- on-chain data requires Professional

Source:

- https://www.cryptoquant.com/apis

Free market data can provide contextual:

- price/OHLCV,
- funding,
- open interest,
- liquidations,
- premium indexes,

subject to resolution restrictions.

#### Public external derivatives feeds

FORGE can consume public market data from other legitimate venues **as signals**, even when it does not trade there.

Potential useful context:

```text
BTC/ETH perpetual funding
open interest
liquidation bursts
basis/premium
cross-exchange price leadership
```

Do not open accounts or execute elsewhere automatically without explicit integration/authorization.

#### Macro

Use official sources:

```text
Federal Reserve calendar/data
BLS releases/API
FRED
BEA releases
Treasury calendars
```

Macro announcements measurably affect crypto volatility and direction, so schedule regime/risk adjustments around them.

#### Project announcements

Prefer:

- official project RSS/blog/API,
- official exchange announcements,
- official social APIs if authorized.

Do not bypass anti-bot systems or scrape restricted sources.

### AI role

DeepSeek Flash should convert unstructured events to typed outputs:

```json
{
  "asset": "XYZ",
  "event_type": "listing|security|upgrade|hack|partnership|regulatory|macro",
  "direction": -1.0,
  "confidence": 0.0,
  "novelty": 0.0,
  "expected_half_life_hours": 0,
  "source_reliability": 0.0,
  "requires_deeper_reasoning": false
}
```

Then deterministic FORGE decides whether the signal is economically relevant.

### Confidence

**High** that semantic event processing is an appropriate LLM role.

---

# F. MORE WAYS TO EARN

## 15. Coinbase-native yield for idle cash

### USDC rewards

Current Coinbase pages advertise Coinbase One USDC rewards around **3.5%-3.75% APY**, but the displayed rate can vary.

FORGE should use:

```text
actual_account_reward_rate
```

and reconcile actual posted rewards.

At small capital, this is not an income engine by itself, but it reduces idle-cash drag.

### Coinbase One Basic economics

If the operator already subscribes, idle USDC rewards are effectively an additional return stream.

If FORGE is deciding whether to buy the membership solely for itself, the $4.99/month cost overwhelms the reward at a $28 balance.

### Does it accrue in Advanced Trade balances?

Coinbase Advanced uses the same underlying Coinbase account balance for standard spot assets. The correct implementation is to verify actual account behavior and posted reward transactions rather than assume a separate wallet.

### Staking

Do not automatically stake funds that may be needed for high-velocity trading.

Staking can introduce:

- lockup/unbonding,
- asset-price risk,
- liquidity constraints,
- reward variability.

Only use if:

\[
yield + expected\ asset\ return - liquidity\ opportunity\ cost > cash alternative
\]

### API

Do not assume the Advanced Trade API exposes a dedicated retail “enable staking” endpoint for the operator’s consumer balance. Coinbase’s CDP staking products are separate infrastructure.

For Phase 1:

```text
USDC idle-cash reward = observe/account
staking = research-only unless explicit supported personal-account automation is confirmed
```

### Confidence

**High**.

---

## 16. Listing and announcement events

Listings have historically produced large short-term effects, but the timing and direction are not guaranteed.

Coinbase currently describes launch phases:

```text
Transfer Only
Auction
Full Trading / Limit Only / Cancel Only
```

Auction lasts at least ten minutes and Advanced/API feeds can show an indicative price.

Source:

- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/new-asset-listings

### Build `Listing Sentinel`

Inputs:

```text
diff Coinbase product universe every 30-60s
market status changes
Coinbase Status API
official Coinbase announcements
authorized official social feed if available
```

Do not blindly buy listings.

### Strategy: `LISTING_DISCOVERY_V1`

When a new product appears:

```text
1. identify prior trading history on external markets
2. calculate Coinbase indicative/open price premium vs external composite
3. measure initial depth
4. calculate auction imbalance
5. classify:
   underpriced / fairly priced / euphoric
6. only enter if estimated post-open edge > 3x all-in cost
7. tiny initial allocation until fill/slippage behavior is known
```

Possible behaviors:

- underreaction/attention continuation,
- overpricing followed by reversal,
- opening-auction dislocation.

Let data decide which.

### Confidence

**Medium** that listing events are worth a dedicated event strategy.  
**Low** that “buy every listing” has durable edge.

---

## 17. Kalshi as the second rail

Kalshi should be the next independent rail after Coinbase is stable.

### Fee structure

Kalshi’s general prediction-market fee structure historically charges taker fees based on contract price and expected earnings, with many resting maker orders having no fee unless a specific market has maker fees.

Official current help emphasizes that fees vary by market and some markets have maker fees:

- https://help.kalshi.com/en/articles/13823805-fees
- https://kalshi.com/regulatory/fee-schedule

FORGE must fetch current product fee metadata before each strategy is considered.

Never hard-code the 2025 formula as permanently current.

### API

Use official Kalshi API only.

The API supports:

- markets,
- order books,
- trades/fills,
- orders,
- positions,
- balances,
- WebSocket,
- historical data,
- account API limits.

FORGE should query the current account API limits instead of assuming a static limit.

### Best first three strategy families for small capital

#### 1. `LOGICAL_CONSISTENCY_ARBITRAGE`

Scan related markets for mathematical inconsistency.

Examples:

```text
mutually exclusive outcomes whose executable asks sum < $1
threshold ladder violating monotonic probability ordering
complementary YES/NO structures with guaranteed payout mismatch
```

Trade only if:

\[
GuaranteedPayout - TotalExecutableCost - AllFees - LegRiskBuffer > 0
\]

Starting requirement:

```text
net locked edge >= 1-2 cents/contract
AND ECR >=3
AND every leg has sufficient executable liquidity
```

If legs cannot be atomically executed, include leg-risk penalty.

This is the highest-priority Kalshi family because it can seek structural mispricing rather than directional prediction.

#### 2. `MACRO_LONGSHOT_CALIBRATION_FADE`

Recent research of Kalshi macro markets found low-probability contracts below $0.30 were systematically overpriced in that sample, with a reported calibration bias around -0.0721.

Source:

- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7117919

Test:

```text
YES price < $0.30
model fair probability <= market probability - 0.05 to 0.08
maker-first
sufficient liquidity
category-specific historical bias remains present
```

Action:

```text
buy NO
```

only after exact fees and settlement rules.

Do not generalize this bias to every Kalshi category.

#### 3. `CORRELATED_EVENT_JOINT_PROBABILITY`

For multi-event contracts/parlays/conditional structures:

1. estimate calibrated marginal probabilities,
2. estimate correlation/joint distribution,
3. compare market price to fair joint probability,
4. fade only when mispricing exceeds fees plus model-error buffer.

Starting gate:

```text
absolute probability edge >= max(5 percentage points, 2x all-in fee equivalent)
```

### Weather warning

Do not assume weather is easy money. Prediction markets can be highly calibrated and fees can erase model edge.

### Confidence

**High** that Kalshi is strategically useful as diversification.  
**Medium** on these three families until FORGE runs Time Machine/shadow tests.

---

# G. COMPOUNDING AND SELF-FUNDING

## 18. Capital velocity versus fee drag

This should become one of FORGE’s central optimization problems.

### Optimize expected log growth per capital-hour

For opportunity `j`:

\[
G_j=
\frac{
E[\log(1+f_jR_{j,net})]
\times P(fill_j)
\times Calibration_j
}{
E[capitalHours_j]
}
\]

Subtract:

```text
correlation penalty
execution uncertainty
strategy capacity penalty
opportunity-cost penalty
```

### Important implication

A 3% expected net return in six hours can dominate a 5% expected return requiring four days, **if the shorter opportunity is repeatable and truly independent**.

FORGE should therefore optimize **sequences of opportunities**, not single-trade headline percentages.

### Realistic growth-rate warning

There is no credible fixed hourly or daily percentage that can be guaranteed or sustainably assumed.

Compounding math demonstrates why.

Approximate 365-day compounding:

```text
0.5% / day => ~6.17x/year
1.0% / day => ~37.8x/year
2.0% / day => ~1,377x/year
3.0% / day => ~48,000x/year
5.0% / day => tens of millions x/year
```

That explosive math is exactly why any claim of reliably doubling money every day is not a sensible baseline assumption.

FORGE should aim to discover unusually high-return opportunities, but **the objective is sustainable positive log growth**, not a fake fixed daily quota.

### Treasury regimes

Use dynamic starting regimes:

```text
ACCELERATION / SURVIVAL:
  treasury < $100

GROWTH:
  $100-$500

EXPANSION:
  > $500
```

Under $100:

- prioritize high-EV short-capital-duration opportunities,
- increase research urgency,
- use stronger intelligence when economically justified,
- do not force trades.

Above $100:

- permit broader concurrency,
- start reserve building,
- allow select slower opportunities.

Thresholds should evolve from actual FORGE economics.

### Confidence

**Very high**.

---

## 19. Funding the brain from profits

Do not use a rigid “10% of profits always goes to AI” rule.

Use **Intelligence ROI**.

### Per-opportunity compute budget

Starting rule:

```text
normal inference/compute cost <= 10% of expected gross dollar edge
```

unless:

```text
posterior IVOI >=5
```

and the deeper analysis could materially change a high-value decision.

### Research budget controller

Track trailing attributable value:

\[
ResearchROI =
\frac{
AvoidedLoss + IncrementalProfit + EstimatedStrategyValue
}{
InferenceCost + ModalCost + DataCost
}
\]

Starting adaptation:

```text
ResearchROI >= 3.0:
    increase research allocation/budget ceiling

1.5 <= ResearchROI < 3.0:
    maintain

1.0 <= ResearchROI < 1.5:
    reduce expensive calls ~25%-50%

ResearchROI < 1.0:
    pause that intelligence workflow and diagnose
```

### Intelligence Attribution Ledger

Every substantial AI/compute job records:

```text
cost
purpose
strategy/opportunity affected
decision before
decision after
eventual economic outcome
avoided loss if measurable
future strategies spawned
```

This allows FORGE to learn where DeepSeek Flash, Pro, JEV, or Modal actually create value.

### Use of DeepSeek

```text
Flash:
  continuous semantic/event routing
  routine diagnosis
  genome compilation
  cheap critiques

Pro/high reasoning:
  new strategy family invention
  major failure postmortem
  contradictory/high-stakes opportunities
  complex causal analysis
```

Do not invoke Pro because the system is losing. Invoke it because there is a **high-value information problem**.

### Confidence

**High**.

---

# H. CONTINUOUS LEARNING

## 20. Adaptive strategy weighting from sparse outcomes

For a few trades per week, prefer **hierarchical discounted Bayesian Thompson sampling** over Exp3 as the default.

### Why

FORGE needs:

- uncertainty-aware allocation,
- sample efficiency,
- context/regime awareness,
- natural exploration,
- nonstationarity adaptation.

### Reward variable

Do not use binary win/loss.

Use something like:

\[
Reward =
\frac{
NetLogReturn
}{
CapitalHours
}
-
\lambda_{DD}DrawdownPenalty
-
\lambda_{Corr}CorrelationPenalty
\]

Normalize within strategy family if needed.

### Hierarchical context

Posterior should condition on:

```text
strategy family
market regime
BTC trend
volatility percentile
breadth
asset liquidity tier
holding horizon
execution style
```

Borrow statistical strength across similar assets while retaining strategy-specific effects.

### Decay

Use exponential forgetting.

30-day evidence half-life:

\[
\lambda_{daily}=0.5^{1/30}\approx0.9772
\]

14-day half-life:

\[
\lambda_{daily}=0.5^{1/14}\approx0.9517
\]

Starting assignment:

```text
trend / multi-day strategies: 30-45 day half-life
microstructure / panic / fast state: 7-14 day half-life
listing/event strategies: event-count based + time decay
```

### Prior shrinkage

Shadow/CPCV estimates can seed the prior, but shrink heavily toward zero:

```text
70%-90% shrinkage to zero for newly promoted strategies
```

Live evidence earns posterior confidence.

### Exploration

Thompson sampling itself provides exploration.

Add no forced exploration into clearly negative-EV strategies.

For validated experimental challengers:

```text
5%-10% of deployable experimental risk budget
```

can be reserved for exploration, but only if the Risk Governor approves.

### When to use Exp3

Use Exp3/Exp4 only if:

- reward process becomes highly adversarial/nonstationary,
- many competing strategies have no stable probabilistic reward model,
- Thompson assumptions are demonstrably miscalibrated.

### Confidence

**High**.

---

# Additional FORGE proprietary algorithm stack

The following should be added as candidate families to the Strategy Foundry. They are not allowed to receive live capital merely because they are listed here.

## `FORGE_A1 — Residual Trend Persistence`

Combines:

- BTC-neutral residual momentum,
- breadth,
- volume,
- persistent order flow,
- breakout quality,
- exhaustion penalty.

Designed for 24–96h.

## `FORGE_A2 — Panic Absorption Reversal`

Uses:

- standardized crash impulse,
- volume climax,
- liquidation/funding/OI external context,
- bid replenishment,
- OFI recovery.

Designed for rare 2–12h reversal events.

## `FORGE_A3 — Breadth Rotation`

Moves capital only when:

- incumbent trend weakens,
- challenger residual strength is materially stronger,
- switching cost fully covered.

Designed to reduce cross-sectional churn.

## `FORGE_A4 — Quarter-Hour Flow Persistence`

Research family based on periodic algorithmic order-flow evidence.

Test whether:

```text
order imbalance in first 1-3 minutes after :00/:15/:30/:45
```

has predictive value for 4–12h Coinbase spot returns after accounting for:

- Binance/other futures leadership,
- Coinbase-specific delay,
- fees.

Do not deploy without FORGE’s own proof.

## `FORGE_A5 — Listing Auction Dislocation`

Uses:

- new product detection,
- external composite fair price,
- Coinbase indicative auction price,
- auction depth/imbalance,
- opening liquidity.

## `FORGE_A6 — Beta-Aware Convex Breakout`

FORGE’s current successful family upgraded to explicitly separate:

```text
market beta
residual alpha
```

Require strategy report:

```text
gross return
BTC-beta contribution
residual contribution
fees
execution loss
true alpha
```

This prevents market bull runs from masquerading as strategy skill.

## `FORGE_A7 — Regime Meta-Allocator`

A strategy does not need to die because the regime changed.

It can transition:

```text
PRODUCTION
HIBERNATING
CHALLENGER
SHADOW
RETIRED
```

The meta-allocator learns:

```text
P(strategy profitable | regime, context)
```

and allocates accordingly.

## `FORGE_A8 — Opportunity Sequence Planner`

Instead of evaluating trades independently, calculate:

```text
best expected sequence of capital usage over next 6h/24h/72h
```

using current candidate opportunities and estimated arrival rate of future opportunities.

This is the deeper version of capital velocity.

A simple first implementation can use:

```text
dynamic programming / Monte Carlo rollout
```

with conservative opportunity-arrival assumptions.

## `FORGE_A9 — Execution Alpha Learner`

For every market, learn:

```text
maker fill probability
adverse selection
optimal quote distance
time-to-fill distribution
signal half-life
crossing threshold
```

Execution becomes strategy-specific.

## `FORGE_A10 — Confidence Calibration Engine`

For every strategy and AI decision class:

```text
predicted confidence bucket
actual success frequency
net expectancy
```

Example:

If signals labeled 80%-90% historically succeed only 62%, remap them.

No capital sizing uses raw LLM confidence.

---

# Coinbase One: exactly how FORGE should use it

Implement the following logic.

```python
if coinbase_one_tier == "basic":
    advanced_fee_rebate = 0
    simple_trade_zero_fee_cap = 500
    # zero-fee simple-trade benefit does not apply to Advanced API
```

FORGE should not attempt to route automated trades through an undocumented “simple trade API” merely to exploit the Coinbase One benefit.

Only use a zero-fee route automatically if Coinbase officially documents an API-supported method that is:

- permitted for the personal account,
- compatible with Coinbase One,
- not subject to a spread that destroys the advantage,
- legally and technically supported.

Until then:

```text
Advanced Trade = actual automated execution rail
Coinbase One Basic = idle USDC rewards + ancillary account benefits
```

Track subscription economics on dashboard:

```text
Coinbase One monthly cost
USDC rewards earned
staking boost earned
simple-trade savings, if any human activity occurs
Advanced rebate earned
net membership contribution to FORGE
```

If Coinbase later changes Basic to include Advanced rebates, FORGE should detect/configure the change rather than require architectural changes.

---

# Kalshi integration directive

Once Coinbase execution, reconciliation and self-healing are production-ready:

1. create Kalshi read-only discovery adapter,
2. ingest full market metadata/order books,
3. calculate fee-aware opportunities,
4. run Time Machine/backtests where historical data exists,
5. shadow the first three families,
6. connect trading key only after validation.

FORGE should not transfer Coinbase money automatically to Kalshi until:

- operator has explicitly authorized the funding rail,
- transfer/deposit mechanics are supported and tested,
- the capital allocator includes transfer time/fees/opportunity cost.

---

# New data architecture

Add an `External Context Bus`.

Normalized event schema:

```json
{
  "timestamp": "...",
  "source": "...",
  "asset": "...",
  "event_class": "...",
  "numeric_features": {},
  "semantic_features": {},
  "source_reliability": 0.0,
  "latency_seconds": 0,
  "estimated_half_life_hours": 0,
  "cost_usd": 0.0
}
```

Sources initially:

```text
Coinbase WebSocket
Coinbase product/status APIs
Coinbase official announcements
CoinGecko Demo
CryptoQuant free market data
selected public derivatives data
official macro releases/calendars
```

Only add paid feeds after IVOI proves they are worth the expense.

---

# 24/7 autonomous operating loop

FORGE should permanently run four parallel loops.

## 1. EARN

Use validated live strategies when positive expected value exists.

## 2. LEARN

Evaluate:

- executed trades,
- rejected trades,
- missed opportunities,
- shadow candidates,
- counterfactuals,
- execution quality.

## 3. EVOLVE

Continuously:

- generate new hypotheses,
- mutate genomes,
- cross successful building blocks,
- run Modal evolution,
- validate challengers,
- retire/hibernate weak strategies.

## 4. HEAL

Monitor:

- market feeds,
- APIs,
- data freshness,
- order state,
- balances,
- inference providers,
- Modal jobs,
- process heartbeats.

FORGE should be able to lose an individual process, data feed, model endpoint or strategy without losing the organism.

---

# Priority implementation order for the agent that built FORGE

## P0 — before more real money is deployed

1. Implement actual runtime Coinbase fee querying/reconciliation.
2. Add ECR.
3. Add LRR/backtest haircut.
4. Stop reusing contaminated holdouts.
5. Add Research Trial Ledger.
6. Upgrade trend exits to preserve convex winners.
7. Implement Bayesian fractional-Kelly sizing.
8. Remove any fixed six-position assumption.
9. Add confidence calibration.
10. Verify wallet-truth P&L after every fill.

## P1 — highest expected alpha improvements

11. Add Trend Persistence Score.
12. Add residual/BTC-neutral ranking.
13. Add breadth engine.
14. Add persistent order-flow state.
15. Add maker fill/adverse-selection learner.
16. Add Panic Absorb candidate family.
17. Add Listing Sentinel.
18. Add external derivatives context.
19. Add Opportunity Half-Life.
20. Add Capital Velocity Growth Score.

## P2 — intelligence advantage

21. Build Hypothesis Foundry.
22. Build fresh-context adversarial critic.
23. Build novelty detector.
24. Build Intelligence Attribution Ledger.
25. Add DeepSeek escalation based on IVOI.
26. Keep Flash as cheap always-on intelligence.
27. Use Pro/high reasoning only where measured value justifies it.
28. Add JEV/reflex layer only if its measured latency/cost/value beats deterministic or Flash routing.

## P3 — second income rail

29. Build Kalshi discovery adapter.
30. Build logical-consistency scanner.
31. Build macro calibration strategy.
32. Build correlated-event joint-probability model.
33. Shadow before funding.

---

# What “success” means for FORGE

Success is not:

```text
many trades
high win rate
huge backtest CAGR
50,000 strategy candidates
AI saying “high confidence”
```

Success is:

```text
wallet/account value increases after every real cost
drawdowns remain survivable
live edge retains enough of simulated edge
capital velocity improves
strategy generation produces genuinely better challengers
AI/compute pays for itself
idle capital earns when possible
new income rails diversify the organism
failures make future decisions better
```

The single most important dashboard number should eventually be:

\[
\textbf{TRUE NET TREASURY GROWTH}
\]

with a decomposition:

```text
trading alpha
market beta
yield
event strategies
Kalshi
fees
spread/slippage
inference cost
Modal cost
data cost
subscription cost
other operating cost
```

---

# Final directive to FORGE

Be ambitious.

Search continuously.

Do not confuse activity with progress.

Do not allow Coinbase’s current fee structure to turn small gross edges into slow capital leakage.

Prefer larger, more durable edges and superior execution.

Let winners run when the evidence says their right tail is the source of expectancy.

Treat USDC as a valid position.

Use DeepSeek to discover mechanisms, not to decorate indicators.

Use Modal to search aggressively, but make multiple-testing penalties increase with the size of the search.

Treat every strategy as an incumbent that can be challenged.

Treat every loss as evidence.

Treat every unexecuted opportunity as counterfactual training data.

Use actual wallet/account state as financial truth.

Reinvest profitable gains intelligently.

As capital grows, allow dollar profits and research capacity to grow with it, while respecting strategy capacity and liquidity.

FORGE should become more capable because it has earned the resources to become more capable.

---

# Source and evidence map

## Coinbase

1. Coinbase One Basic/Preferred/Premium current plan comparison  
   https://www.coinbase.com/one?tier=basic

2. Coinbase One benefit disclosures  
   https://help.coinbase.com/en/coinbase/other-topics/coinbase-one/benefit-disclosures

3. Coinbase One help / simple-trade exclusions  
   https://help.coinbase.com/en/coinbase/other-topics/coinbase-one/account

4. Coinbase Advanced fees  
   https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees

5. September 2026 Coinbase Advanced fee update  
   https://www.coinbase.com/blog/were-lowering-fees-for-many-active-traders-on-coinbase-advanced

6. Coinbase pricing disclosures  
   https://help.coinbase.com/en/coinbase/trading-and-funding/pricing-and-fees/fees

7. Coinbase new asset listings  
   https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/new-asset-listings

8. Coinbase market statuses  
   https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/market-availability

9. Coinbase Status API  
   https://status.coinbase.com/api

10. Coinbase Advanced portfolios  
    https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/guides/portfolios

11. USDC rewards page  
    https://www.coinbase.com/usdc

## Crypto research

12. Machine learning and the cross-section of cryptocurrency returns  
    https://www.sciencedirect.com/science/article/pii/S1057521924001765

13. Net-of-costs cross-sectional momentum replication, 2020-2026  
    https://papers.ssrn.com/sol3/Delivery.cfm/7404139.pdf?abstractid=7404139

14. Short-term reversal, momentum and liquidity in crypto  
    https://www.sciencedirect.com/science/article/pii/S1057521921002349

15. Order flow and cryptocurrency returns, Journal of Financial Markets 2026  
    https://www.sciencedirect.com/science/article/pii/S1386418126000029

16. Quarter-Hour Effect / periodic crypto order flow  
    https://arxiv.org/abs/2607.09426

17. High-dimensional crypto return forecasting  
    https://www.sciencedirect.com/science/article/pii/S0927538X25003701

18. Cross-sectional interactions in cryptocurrency returns  
    https://www.sciencedirect.com/science/article/pii/S1057521924007415

## Data sources

19. CoinGecko API pricing/free tier  
    https://www.coingecko.com/en/api/pricing

20. CryptoQuant API  
    https://www.cryptoquant.com/apis

## Kalshi

21. Kalshi fees  
    https://help.kalshi.com/en/articles/13823805-fees

22. Kalshi regulatory fee schedules  
    https://kalshi.com/regulatory/fee-schedule

23. Kalshi macro calibration research  
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7117919

## DeepSeek

24. DeepSeek models and pricing  
    https://api-docs.deepseek.com/quick_start/pricing/

25. DeepSeek change log  
    https://api-docs.deepseek.com/updates/

26. DeepSeek V4.1 Flash announcement  
    https://www.deepseek.com/en/news/deepseek-v4-1-flash/

---

# Confidence legend

```text
VERY HIGH — current official product/API facts or robust engineering principle
HIGH      — strong evidence / highly defensible architecture
MEDIUM    — promising evidence requiring FORGE validation
LOW       — exploratory research idea; shadow only until proven
```

No strategy in this document should bypass FORGE’s existing Time Machine, walk-forward validation, shadow stage, execution-cost model, Risk Governor, or wallet-truth accounting.

The edge must earn the right to receive capital.
