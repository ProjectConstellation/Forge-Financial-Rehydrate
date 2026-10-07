# FORGE — 20 Strategic Research Answers: Probability Alpha, Cross-Rail Intelligence, and Adaptive Capital Compounding

**Date:** 2026-10-07  
**Purpose:** Directly ingestible research/engineering guidance for the FORGE builder.  
**Target:** Maximize **true net treasury growth after every cost** using Coinbase Advanced, Kalshi, official/public market data, Modal compute, and the Hermes research organization.

> **Operating stance**
>
> FORGE should be ambitious, fast, empirical, and adaptive. The system should continuously search for profitable edge, but it should never manufacture confidence to satisfy a profit target. The fastest path to large compounding is to discover **real positive expectancy**, preserve it through execution, recycle capital quickly, and scale only while the edge remains intact.
>
> The core compounding equation is multiplicative:
>
> \[
> W_{t+1}=W_t(1+r_t-c_t)
> \]
>
> where \(W_t\) is treasury, \(r_t\) is gross return, and \(c_t\) includes trading fees, spread, slippage, inference, compute, financing, and other operating costs. If the long-run mean of \(\log(1+r_t-c_t)\) is positive, wealth can compound exponentially. If it is not, increasing size only compounds losses faster.
>
> **Therefore: FORGE must maximize expected log growth, not raw trade count, raw ROI screenshots, or nominal win rate.**

---

# Executive conclusion — what FORGE should prioritize first

Based on FORGE's own live/shadow evidence and current public market structure, I would rank the next engines in this order:

1. **Kalshi threshold TAKE with exact-settlement modeling + stale-quote detection**  
   Highest current evidence because FORGE already observed +12.5¢/contract on a post-hoc threshold slice. The priority is to prove it out-of-sample and discover the mechanism.
2. **Settlement-source lead/lag alpha**  
   Use the actual Kalshi CF Benchmarks feed plus faster constituent/exchange microstructure to predict the next fair-probability move before the event-contract book fully reprices.
3. **Cross-strike / probability-surface constraint engine**  
   Not generic "arbitrage"; reconstruct the whole implied distribution, then trade only local inconsistencies that remain profitable after all legs and fees.
4. **Scheduled-event probability engines**  
   CPI/jobs/Fed and commodities have objective settlement sources and predictable information-release clocks. These are excellent for model-vs-market probability comparisons.
5. **Cross-rail information transfer**  
   Perp basis/funding/OI, PAXG, equity/ETF prices, BTC/ETH spot, Kalshi event odds, and options-implied volatility should feed each other even when only one rail is executable.
6. **Stablecoin microstructure as idle-capital scavenging, not the main growth engine**  
   Useful only when fees are near zero and the opportunity does not block a higher-EV signal.
7. **Coinbase spot trend continuation**  
   Keep as a slower incumbent, but only where the gross move comfortably clears the US fee hurdle.
8. **Passive Kalshi market making**  
   Disabled by default until FORGE proves that spread + incentives exceed adverse selection. Current shadow result is negative.

## Three proprietary meta-algorithms to build now

### 1. FORGE SAGE — Settlement-Aware Gap Engine

Finds discrepancies between:
- exact settlement rule,
- live settlement-source data,
- fast underlying markets,
- Kalshi executable prices,
- and the whole strike surface.

\[
\text{SAGEScore}_i =
\frac{
\operatorname{LCB}_{q}(p_i)-a_i-F_i-I_i
}{
\sqrt{V_i + U_i}
}
\cdot
e^{-\lambda_i d_i}
\cdot
\frac{1}{E[T_i]}
\]

Where:
- \(p_i\): calibrated FORGE fair probability
- \(a_i\): executable ask
- \(F_i\): fee in probability-equivalent dollars per contract
- \(I_i\): impact/slippage
- \(V_i\): outcome variance
- \(U_i\): model/calibration uncertainty
- \(d_i\): quote age / stale time
- \(\lambda_i\): learned edge-decay hazard
- \(E[T_i]\): expected capital lock time in hours

This explicitly optimizes **edge, confidence, urgency, and capital velocity simultaneously**.

### 2. FORGE VELA — Velocity-Expected Log Allocator

For candidate opportunity \(i\), position fraction \(f_i\):

\[
g_i(f_i)=
\frac{
E[\log(1+f_iR_i)]
}{
E[T_i]+\eta_i
}
-
\rho\,\mathrm{CVaR}_{95,i}
-
\gamma\,\mathrm{CorrCost}_i
\]

FORGE solves for the portfolio maximizing \(\sum_i g_i\) subject to cash, correlation, settlement, and ruin constraints. This is the correct formalization of "make the most money as quickly as possible" without forcing bad trades.

### 3. FORGE DARWIN — Contextual Strategy Ecology

Every strategy is an incumbent or challenger in a contextual Bayesian bandit. Context includes regime, venue, asset, time-to-settlement, volatility, spread, and market type. Capital allocation follows posterior expected **net log-growth**, not lifetime average ROI. A once-great strategy can hibernate and later reactivate when its regime returns.

---

# Ground-truth facts FORGE should encode as live provider policies

- Coinbase publicly lists the U.S. entry Advanced spot tier at **0.50% maker / 0.90% taker**. Advanced tier thresholds now begin at $10,000 qualifying volume. Fee tiers and stable-pair schedules can vary, so FORGE should query/record the actual account fee state before every strategy evaluation.
- Coinbase One Basic is publicly listed at **$4.99/month**, with zero-fee simple crypto trading up to a monthly allowance, but **Coinbase Advanced trades are excluded from the zero-fee benefit**. The public Coinbase One page currently advertises **3.50% USDC APY**; if the operator's logged-in account shows 3.75%, the account-specific value is the authoritative value for FORGE.
- Coinbase now offers U.S. stocks/ETFs with $0 commissions, fractional shares from $1 for eligible symbols, and 24/5 extended access for eligible symbols. Fractional trading is regular-hours only and equity settlement is typically T+1.
- Kalshi settles crypto event contracts from a **60-second average of CF Benchmarks RTI values**, one per second. Kalshi exposes CF Benchmarks values through its API as a direct pass-through.
- Kalshi provides authenticated WebSocket market data/order books and current API rate-limit tiers. API rules can change; FORGE should query current limits and endpoint costs rather than hardcode old numbers.
- Kalshi's Liquidity Incentive and Volume Incentive programs can add economic value, but they can change or terminate. FORGE should ingest current incentive definitions from the API and include them in net EV.
- CF Benchmarks BRTI is calculated from a consolidated multi-exchange order book and is published as a real-time benchmark; its methodology can change, so FORGE should treat methodology version as data.

---

# A. THE KALSHI PROBABILITY-ALPHA CORE

## Q1 — Why threshold contracts misprice, and how FORGE should capture the maximum

### 1. Mechanism

The strongest plausible mechanisms are:

1. **Settlement-model mismatch.** Human traders often think "spot at expiration" while the actual crypto contract settles on a 60-second average of CF Benchmarks RTI. Near strike, this distinction can move fair probability materially.
2. **Repricing latency.** Spot/perp markets can move before a thin event-contract order book fully reprices.
3. **Round-strike anchoring.** Retail demand clusters around psychologically salient strike levels, which can create local surface distortion.
4. **Time-decay error.** In the final 5–30 minutes, fair probability becomes extremely sensitive to remaining volatility and exact moneyness.
5. **YES/NO demand imbalance.** Prediction markets contain directional traders and hedgers. Price can temporarily reflect demand rather than calibrated probability.
6. **Book fragmentation.** Dozens of nearby strikes divide liquidity, producing local stale quotes.

Your own data strongly suggests threshold contracts are structurally different from narrow ranges. The correct response is **not** to generalize TAKE; it is to isolate and pre-register the threshold mechanism.

### 2. FORGE-specific equation

Define normalized distance to strike:

\[
z=\frac{\ln(K/\tilde S_t)}{\hat \sigma_{h}\sqrt{h}}
\]

where:
- \(K\): strike
- \(\tilde S_t\): settlement-index estimate, not generic spot
- \(h\): time to settlement in years or consistent fractional units
- \(\hat \sigma_h\): horizon-specific realized volatility

Define calibrated fair probability \(p_F\) from the ensemble.

For buying YES at ask \(a\), number of contracts \(n\):

\[
EV_Y(n)=n\cdot p_{\text{fill}}(n)
\left[
p_F-a-\frac{Fee(n,a)}{n}-Slip(n)-OppCost(h)
\right]
\]

For buying NO, use \(p_N=1-p_F\) and the NO ask.

Kalshi general taker fee:

\[
Fee(n,a)=\left\lceil 100 \cdot 0.07na(1-a)\right\rceil/100
\]

unless that series has a special fee schedule.

At one contract priced 40–80¢, rounding often makes the fee roughly 1–2¢, which is enormous relative to small probability edges. Therefore the engine must compute the **actual integer-contract fee**, not a continuous approximation.

Hourly objective:

\[
EV_{\$/h}=
\frac{EV(n)}
{E[T_{\text{capital lock}}]+\epsilon}
\]

Then multiply by the estimated opportunity arrival rate only for capacity planning; do not double-count arrival rate in individual trade ranking.

### 3. Starting parameters

Start with the already-discovered region but tighten it:

- Contract type: threshold/above/below only
- Ask: **0.35–0.82** initially; preserve the original 0.40–0.80 slice as a sealed comparator
- \(|z|\): **0.15–1.25**
- Time to settlement:
  - 15m products: **2–12 min**
  - hourly products: **5–35 min**
  - daily products: **15–180 min**
- Spread: initially **≤ 4¢**, then learn conditional EV by spread bucket
- Best-level depth: at least **max(3n, 5 contracts)**
- LCB edge after fees: **≥ 3¢** provisional, **≥ 5¢** preferred
- Signal must be absent if settlement-source data is stale >2 s or Kalshi book sequencing is uncertain

Do not optimize these cutoffs on the same data that discovered TAKE_THRESH. Use them as broad priors and let the sealed/OOS process decide.

### 4. Pseudocode

```python
for market in threshold_markets:
    state = build_settlement_state(market)
    p_hat, p_lcb = probability_engine(state)

    for side in ("YES", "NO"):
        ask, depth = executable_ask(market, side)
        fee = exact_kalshi_fee(1, ask, market)
        slip = estimate_impact(market, side, 1)
        lock = expected_settlement_hours(market)

        edge = side_prob(p_lcb, side) - ask - fee - slip

        if (
            edge >= EDGE_MIN
            and spread(market) <= SPREAD_MAX
            and sufficient_depth(depth)
            and signal_is_fresh(state)
        ):
            n = discrete_growth_optimal_size(market, state, edge)
            score = expected_log_growth_per_capital_hour(n, state)
            queue_candidate(market, side, n, score)
```

### 5. Validation / effect size / kill criterion

**Known effect:** +12.5¢ per contract on 96 post-hoc threshold observations is encouraging but not yet causal proof.

Pre-register TAKE_THRESH-V1 and require:

- first 20 sealed outcomes: posterior \(P(\mu>0) > 0.95\) for 1-contract net P&L before size >1;
- 40+ sealed outcomes: posterior \(P(\mu>0) > 0.99\);
- mean net edge target: **≥ 3¢/contract**;
- edge must appear in at least **3 distinct sessions/days**;
- realized fill-to-model slippage must remain <20% of predicted edge.

**Kill / hibernate:** rolling 30-trade posterior \(P(\mu>0)<0.70\), or mean net ≤0, or calibration drift invalidates the LCB.

### 6. Alternatives ranked

1. **Settlement-source stale quote TAKE** — highest probability of net profit.
2. **Threshold-only probabilistic mispricing without explicit stale signal** — second.
3. **Narrow-range contracts** — currently low priority; negative observed evidence.

**Confidence:** High that this is the best current FORGE research direction; medium that the +12.5¢ survives OOS unchanged.

---

## Q2 — Strongest possible CF RTI settlement model

### 1. Mechanism

The single biggest design improvement is: **use Kalshi's direct CF Benchmarks value feed as primary truth**. Do not reconstruct RTI when the exact settlement-source feed is available.

Reconstruction still matters for:
- redundancy,
- forecasting the next RTI tick,
- measuring which constituent market leads,
- and explaining stale Kalshi quotes.

CF Benchmarks states BRTI aggregates major exchange order books and publishes a real-time index. Kalshi passes CF data through its API.

### 2. Path-aware settlement equation

During the final 60-second averaging window, settlement is:

\[
A_{60}=\frac{1}{60}\sum_{j=1}^{60}I_j
\]

At second \(m\), if \(m\) RTI values are already observed:

\[
P(A_{60}>K|\mathcal F_t)=
P\left(
\sum_{j=m+1}^{60}I_j >
60K-\sum_{j=1}^{m}I_j
\middle|\mathcal F_t
\right)
\]

This is fundamentally different from \(P(I_{60}>K)\).

FORGE should maintain:
- the realized partial average,
- remaining required average,
- conditional path distribution for the remaining seconds.

For fast approximation, model future log-index increments with a local drift \(\mu_t\), variance \(\sigma_t^2\), and AR(1) microstructure component. For the final minute, Monte Carlo 2,000–10,000 short paths is cheap enough.

### 3. Multi-venue predictive proxy

For venue \(j\), define:

\[
q_{j,t}=
\frac{
DepthQuality_{j,t}\cdot Freshness_{j,t}\cdot Reliability_j
}{
\widehat{Var}(S_{j,t}-I_t)+\epsilon
}
\]

Then:

\[
\hat I_{t+\delta}
=
\frac{\sum_j q_{j,t}(S_{j,t}-\hat b_{j,t})}
{\sum_jq_{j,t}}
\]

Use robust clipping:
- reject venue midpoints >4 rolling MAD from the cross-venue median;
- reduce weight sharply when sequence gaps or WebSocket lag occurs;
- learn venue-specific basis \(b_j\) with exponentially weighted updates.

### 4. How much is 1 bp worth near strike?

For a normal approximation:

\[
p=\Phi\left(\frac{\ln(S/K)}{\sigma\sqrt h}\right)
\]

Near strike \(z\approx0\):

\[
\frac{\partial p}{\partial \ln S}
\approx
\frac{0.399}{\sigma\sqrt h}
\]

If remaining horizon volatility is 50 bp (\(0.005\)), a **1 bp** price-estimation improvement changes fair probability by roughly:

\[
0.399/0.005 \times 0.0001 = 0.00798
\]

or about **0.8 percentage points ≈ 0.8¢ per $1 binary contract** near strike.

At 100 bp horizon vol, it is roughly **0.4¢/bp**. Far from strike the sensitivity is much smaller.

That is why 0.5–3 bp basis accuracy becomes economically important only in the near-strike / near-expiry state.

### 5. Final-5-minute policy

When:
- \(|z|<0.5\),
- <5 min remain,
- and quote age is high,

switch to **Path Mode**:
- consume direct CF feed every second;
- project the 60-second average;
- refresh probability after each tick;
- reduce model horizon uncertainty;
- allow faster taker execution if edge half-life is short.

Outside that state, use cheaper distribution models.

### 6. Validation / kill

Compare predicted settlement average vs actual settlement:
- MAE in bp;
- probability Brier score near strike;
- incremental P&L vs Coinbase-only proxy.

Promote reconstruction features only if they improve **sealed** near-strike Brier by ≥0.002 or increase net P&L by ≥1¢/contract without increasing false positives.

### Alternatives ranked

1. **Direct CF feed + predictive constituent overlay** — best.
2. **Direct CF feed only** — extremely strong baseline.
3. **Synthetic constituent reconstruction without direct CF feed** — fallback only.

**Confidence:** High.

---

## Q3 — Short-horizon distributions that can beat a single FHS/HAR model

### 1. Mechanism

Your raw model losing to market Brier while TAKE makes money is a clue: **the edge may be conditional, not global**. FORGE should stop trying to be "better than the market everywhere" and instead learn where its information is incremental.

### 2. FORGE Regime-Jump Mixture (RJM)

Use a K-state mixture:

\[
r_{t,h}|Z_t=k
\sim
(1-\pi_{J,k})\,t_{\nu_k}(\mu_{k,t}h,\sigma_{k,t}^2h)
+
\pi_{J,k}\,J_k
\]

where \(J_k\) is an empirical jump distribution.

Regime posterior:

\[
P(Z_t=k)\propto
P(Z_t=k|Z_{t-1})
\cdot
L_k(x_t)
\]

Features \(x_t\):
- 1m/5m realized volatility
- realized skew/kurtosis
- Coinbase order-flow imbalance
- cross-venue return dispersion
- perp basis/funding/OI change
- time-of-day
- macro-event clock
- return since last Kalshi repricing
- distance to strike

Forecast:

\[
p_F=\sum_kP(Z_t=k)\cdot P_k(A_T>K)
\]

### 3. Compute-efficient online fit

Do not fit a huge HMM every tick.

- update features every 1–5 s;
- regime posterior every 15 s;
- refit transition matrix every 6 h;
- refit heavy-tail parameters every 1 h with exponential decay;
- keep K=3 or 4: quiet, trend, panic/jump, event.

Use NumPy/Numba; this easily fits 4 vCPUs.

### 4. Alternative model: conditional empirical transport

Maintain a nearest-neighbor library of historic normalized states. Weight history by state similarity:

\[
w_j\propto
\exp(-\tfrac12(x_t-x_j)^\top D^{-1}(x_t-x_j))
\]

and estimate probability from future realized settlement paths. This lets FORGE use actual fat-tailed paths without forcing a parametric law.

### 5. Validation

Because the market already has Brier 0.1513 and raw model 0.1564:
- require incremental Brier improvement ≥0.002 on sealed data;
- require threshold TAKE net P&L improvement ≥1.5¢/contract;
- reject any model that only improves global Brier while reducing economic P&L.

### Alternatives ranked

1. **Conditional empirical transport / analog states**
2. **Regime-jump heavy-tail mixture**
3. **Gradient-boosted direct outcome model with monotonic probability calibration**

**Confidence:** Medium-high for conditional improvement, low that any one model globally beats market prices.

---

## Q4 — Superior calibrator / ensemble

### 1. Mechanism

The market is a very strong prior. Your 4.5% model weight is not failure; it is evidence that FORGE should only deviate from market when context proves it has incremental information.

### 2. Hierarchical Bayesian residual calibrator

Let \(m=\operatorname{logit}(p_{market})\), \(d=\operatorname{logit}(p_{model})-m\).

\[
\operatorname{logit}(p_F)=
m+
\beta^\top x+
u_{\text{series}}+
u_{\text{regime}}
\]

where \(x\) includes:
- \(d\)
- moneyness
- \(\log(\tau)\)
- spread
- depth imbalance
- Coinbase return since last Kalshi move
- quote age
- order flow
- realized vol
- hour-of-day
- event type

Priors:
- \(\beta_d\sim N(0,0.25^2)\)
- other betas \(N(0,0.15^2)\)
- random effects \(u\sim N(0,\sigma_u^2)\) with half-normal prior on \(\sigma_u\)

These priors aggressively shrink FORGE back toward market until evidence accumulates.

### 3. Online update

Use sequential Laplace / extended Kalman logistic update:

\[
K_t=\Sigma_t x_t/(1+p_t(1-p_t)x_t^\top\Sigma_tx_t)
\]

\[
\beta_{t+1}=\beta_t+K_t(y_t-p_t)
\]

\[
\Sigma_{t+1}=(I-K_tx_t^\top)\Sigma_t/Q
\]

where \(Q\in[0.995,0.9999]\) is a forgetting/discount factor. Start at **0.998** and learn via predictive log loss.

### 4. Decision rule

Trade only when:

\[
LCB_{90}(p_F)-a-Fee-Impact > E_{\min}
\]

Starting \(E_{\min}=0.03\) dollars per contract.

If sample size grows >3,000, compare against monotonic gradient boosting as challenger, not as default.

### 5. Edge decay detector

Maintain exponentially discounted difference in log score:

\[
D_t=\lambda D_{t-1}+
[\ell(p_{market},y)-\ell(p_F,y)]
\]

If \(D_t\) falls below zero with posterior probability >0.9 over the recent 200 outcomes, shrink strategy weight toward market.

### 6. Alternatives ranked

1. Hierarchical Bayesian residual logistic
2. Beta calibration / isotonic on carefully defined slices
3. Monotonic GBDT after sample size is sufficient

**Confidence:** High that this is better suited to 1k–5k samples than a large unconstrained learner.

---

## Q5 — Stale-quote harvesting: Coinbase → Kalshi lead/lag

### 1. Mechanism

This is one of FORGE's most compelling edges. Crypto price discovery occurs rapidly across automated venues, while event-contract books can be thinner and fragmented. A Kalshi quote can remain executable after underlying information changed.

This is legitimate only using public/authorized data and normal exchange APIs. Do not manipulate or spam markets.

### 2. Fair-value jump model

At spot movement event \(e\):

\[
\Delta p^{fair}_0
=
\frac{\phi(z)}{\hat\sigma\sqrt h}
\cdot
\Delta\ln I
+
\theta^\top \Delta X
\]

where \(\Delta X\) includes OFI, cross-venue confirmation, volatility shock and RTI-vs-spot basis.

Learn edge decay:

\[
\Delta p^{fair}(d)=\Delta p^{fair}_0e^{-\lambda_c d}
\]

with class-specific \(\lambda_c\) for:
- 15m thresholds
- hourly thresholds
- daily thresholds
- range contracts

Then executable expected edge:

\[
E(d)=\Delta p^{fair}(d)-Gap_{book}-Fee-Impact
\]

### 3. Repricing hazard

Fit a Cox or simple exponential survival model for time until Kalshi best quote moves in the direction predicted by the Coinbase trigger.

Features:
- underlying move z-score
- quote age
- Kalshi depth
- spread
- time to expiry
- trade intensity
- cross-venue agreement

### 4. Latency targets

FORGE should instrument, not guess:

- timestamp Coinbase event
- probability update finish
- signed Kalshi request send
- exchange ack
- fill

Initial engineering target:
- **<250 ms internal trigger-to-order-send**
- **<500 ms total decision path** for stale-quote mode

If measured edge half-life is >5 s, this is ample.
If half-life <500 ms, FORGE should classify the opportunity as institutionally latency-sensitive and avoid competing unless actual fills prove otherwise.

### 5. Validation

Record every trigger whether traded or not.
Measure:
- quote repricing half-life;
- theoretical fair jump;
- actual post-trigger Kalshi mid movement;
- fill and realized P&L.

Promote only if:
- median repricing direction matches predicted direction >60%;
- net traded edge ≥3¢;
- slippage consumes <25% of pre-trade edge.

### 6. Alternatives ranked

1. CF/spot stale threshold quote
2. Cross-venue confirmed stale quote
3. Generic momentum-triggered Kalshi trade

**Confidence:** High as a research target, medium on capacity until measured.

---

## Q6 — Turning the losing maker strategy into something worth using

### 1. Mechanism

Current MAKE loses because fills are toxic: FORGE gets filled precisely when better-informed traders move against its stale quote.

Therefore **maker is OFF by default**.

### 2. Toxicity estimator

For quote \(q\), define post-fill markout:

\[
M_{\Delta}=s\cdot(P_{mid,t+\Delta}-P_{fill})
\]

where \(s=+1\) for buying YES and \(-1\) for selling/NO-equivalent direction.

Estimate toxicity:

\[
T_q=-E[M_{5s},M_{30s},M_{120s}|x_q]
\]

A quote is allowed only if:

\[
SpreadCapture + IncentiveEV - Fee - T_q - InventoryCost > 0
\]

### 3. Quote policy

Only quote when:
- no significant underlying move in past 5–15 s;
- settlement-source freshness good;
- repricing hazard low;
- >15 min from expiry initially;
- predicted 30s toxicity <0.5¢;
- spread ≥3¢ or incentive EV compensates;
- quote can be canceled within measured safe latency.

Offset:

\[
q_{bid}=p_F-\frac{spread^*}{2}-\alpha T_q-\beta Inventory
\]

### 4. Incentive integration

Kalshi liquidity rewards score resting orders based on size/proximity and can pay even when not filled. Treat incentive as a separate expected revenue stream:

\[
IncentiveEV=\hat Share_{score}\times RewardPool
\]

but only count realized/clearly accrued program terms, and poll active incentives because programs can change.

### 5. Validation

Require the first 100 maker fills to have:
- mean 30s markout ≥0;
- total spread capture + incentives - adverse selection >0;
- no single incentive program responsible for >70% of expected future profitability unless it is active and stable.

### 6. Alternatives ranked

1. **Incentive-aware non-toxic quoting**
2. **One-sided passive entry only after fair-value stabilization**
3. Two-sided market making — lowest priority at current capital

**Confidence:** Medium-low until new shadow data overturns the existing -4.75¢ result.

---

## Q7 — Cross-strike / cross-expiry structure

### 1. Mechanism

For same expiry and underlying:

\[
K_1<K_2 \Rightarrow P(S_T>K_1)\ge P(S_T>K_2)
\]

Violations imply an incoherent probability surface.

A range contract should approximately satisfy:

\[
P(K_L<S_T<K_H)
=
P(S_T>K_L)-P(S_T\ge K_H)
\]

subject to exact settlement-rule conventions.

### 2. Constraint graph

Represent every contract as a node and mathematical relationship as an edge:
- monotonic strike constraints
- complement constraints
- range decomposition
- exhaustive bucket sum-to-one
- same-settlement cross-product consistency

Solve:

\[
\min_{p^*}
\sum_i w_i(p_i^*-p_i^{mkt})^2
\]

subject to all no-arbitrage constraints, where \(w_i\) scales with liquidity and quote reliability.

Residual:

\[
R_i=p_i^*-p_i^{mkt}
\]

Only trade residuals that survive fees, spread, and model uncertainty.

### 3. Important warning on expiries

Do **not** impose a false rule that \(P(S_{T_2}>K)\ge P(S_{T_1}>K)\) for \(T_2>T_1\). That is not generally true. Cross-expiry relationships need a dynamic distribution model, not simple monotonicity.

### 4. Portfolio search

Enumerate small leg combinations:
- verticals
- threshold + range decomposition
- complementary YES/NO structures

Compute guaranteed lower payoff across all settlement states. If minimum payoff minus cost/fees >0, it is true arbitrage; otherwise treat it as model-relative value.

### 5. Validation

Current observation: 0 ladder/range arbitrages. Therefore this is a **watcher**, not a capital-hungry engine.

Promote only after:
- at least 10 executable violations survive actual quoted depth and fees;
- micro-fill tests confirm both legs.

### 6. Alternatives ranked

1. Same-expiry constraint graph
2. Range-vs-threshold decomposition
3. Cross-expiry relative value

**Confidence:** High in mathematical correctness, low that frequent risk-free arb will exist.

---

## Q8 — Binary Kelly at scale with correlation and tiny capital

### 1. Mechanism

For a single YES contract costing \(a\), fee \(f\), probability \(p\), wealth \(W\), allocating fraction \(x\):

Winning wealth factor:
\[
1+x\frac{1-a-f}{a+f}
\]

Losing factor:
\[
1-x
\]

Kelly maximizes:

\[
G(x)=p\log(1+x b)+(1-p)\log(1-x)
\]

where \(b=(1-a-f)/(a+f)\).

### 2. Uncertainty-adjusted probability

Never use point \(p\). Use:

\[
p_{eff}=p_{mkt}+\kappa(p_{LCB}-p_{mkt})
\]

Start \(\kappa=0.75\). If calibration improves OOS, allow 0.9; if calibration worsens, shrink toward 0.

### 3. Correlated portfolio Kelly

For candidates \(i=1..m\), use numerical scenario optimization:

\[
\max_{\mathbf n\in \mathbb{Z}_{\ge0}}
E[\log(W+\Pi(\mathbf n))]
-\lambda_{cvar}\mathrm{CVaR}_{95}
\]

subject to:
- total cost ≤ deployable cash
- max same-underlying exposure
- correlation cluster limits
- ruin probability

At $10–30, integer enumeration over 1–5 contracts per signal is trivial and better than a continuous closed form.

### 4. Starting aggression

Use **0.20 Kelly** as baseline because model uncertainty dominates at this stage.

Allow:
- ordinary validated signal: max 10–15% treasury
- strong OOS LCB edge >5¢: max 20%
- exceptional pre-registered signal, LCB edge >10¢, low correlated exposure: max 30–35%

Do not place 100% of treasury on one binary; even a 95% calibrated probability still loses 5% of the time.

### 5. Ruin constraint

Require:

\[
P(W_{next}<0.5W_{current}) < 0.01
\]

over the next 20 scheduled opportunities under posterior predictive simulation.

### 6. Alternatives ranked

1. Discrete uncertainty-adjusted Kelly + CVaR
2. Equal-risk allocation across uncorrelated validated signals
3. Fixed fraction

**Confidence:** High.

---

# B. EXPAND THE OPPORTUNITY SURFACE

## Q9 — Best non-crypto Kalshi categories

### 1. Ranking

**#1 Commodities price thresholds — gold/WTI/silver**  
Why: objective price settlement, liquid reference markets, Pyth/market feeds, clear microstructure.

**#2 Scheduled macro releases — CPI/jobs/Fed**  
Why: exact release times, public official data, market-implied forecasts, discrete surprise mapping.

**#3 Weather — carefully selected temperature/precipitation contracts**  
Why: free official NWS data and model forecasts, but settlement-location details and delayed observations must be handled precisely.

### 2. Commodity probability engine

For gold:
- settlement source: contract-defined Pyth/source
- inputs: PAXG, gold futures/perp reference, DXY proxy if available, realized vol

Learn basis:

\[
B_t=S^{proxy}_t-I^{settlement}_t
\]

with state-dependent mean and variance.

Then:

\[
p=P(I_T>K|S^{proxy}_t,B_t,\sigma_t,regime)
\]

Trade only when lower-bound probability beats Kalshi executable price after fees.

### 3. Macro surprise engine

For a release \(X\):

\[
Surprise=\frac{X_{actual}-MedianForecast}{\sigma_{forecast-error}}
\]

Before release, FORGE should price the event distribution, not guess direction. Kalshi contracts themselves can provide probability information.

After release:
- official source timestamps event;
- parse authoritative BLS/Fed data;
- compare settled interpretation to stale market quotes;
- trade only if latency is sufficient and rules permit.

Use BLS public API for published CPI/jobs series; the API is official but release-page latency should be benchmarked against direct release pages.

### 4. Weather engine

Use NWS grid forecasts and observations; contract settlement station/rule must match exactly.

Blend:
- NWS point forecast
- forecast error distribution by station/month
- latest observation
- diurnal temperature profile

\[
T_{max}\sim N(\hat T_{NWS}+bias_{station,month}, \sigma_{err}^2)
\]

### 5. Validation targets

Do not invent an expected edge. Require:
- ≥50 settled observations/category
- Brier improvement ≥0.003 vs market
- live/shadow net EV ≥2¢/contract

### 6. Alternatives ranked

1. Commodity thresholds
2. Macro scheduled releases
3. Weather

**Confidence:** High on data availability, medium on actual alpha.

---

## Q10 — Coinbase stocks/ETFs with tiny capital

### 1. Mechanism

Coinbase now advertises $0-commission U.S. equities/ETFs, fractional eligible shares from $1, and 24/5 access for eligible symbols. However:
- fractional trading is regular-hours only,
- settlement is typically T+1,
- stock brokerage onboarding is separate,
- API eligibility must be confirmed in the operator's account.

At $10–30, equities are **not** the fastest compounding rail because T+1 and market hours reduce capital velocity. They are still valuable as both a future execution rail and a cross-rail information source.

### 2. Highest-probability strategies

#### A. Weekend crypto → Monday crypto-equity gap

Research published in 2025 finds weekend crypto return/volatility has predictive information for Monday stock returns.

For crypto-sensitive stock \(j\):

\[
\hat r_{j,Mon}=
\alpha_j+
\beta_{1j}r_{BTC,weekend}
+\beta_{2j}|r_{BTC,weekend}|
+\beta_{3j}\Delta IV_{BTC}
+\beta_{4j}FuturesGap
\]

Long only when forecast lower bound > expected spread/slippage + threshold.

#### B. IBIT/FBTC vs BTC spot information transfer

Do not call this arbitrage without a short/hedge leg. Instead use:
- BTC weekend/overnight return
- ETF prior close
- premarket quote
- estimated NAV

to predict opening gap continuation/reversion.

#### C. COIN/MSTR lead-lag

Use BTC return, vol and options/funding state to forecast next equity session. This is directional beta, not pure alpha; residualize against Nasdaq/SPY.

### 3. Session rules

- Fractional: 09:30–16:00 ET only
- Extended sessions: use whole-share constraints/order types actually supported by account
- No trade if spread > forecast edge/3
- Avoid $1 fractional orders where spread/price improvement is not measurable

### 4. Idle yield comparison

Compare USDC APY to SGOV/BIL only after:
- account eligibility,
- settlement/cash availability,
- spread,
- dividend timing,
- T+1 opportunity cost.

At tiny capital, USDC is operationally superior because it remains immediately available for crypto trades.

### 5. Validation

Paper first. Promote only if:
- 30+ events
- residual alpha after SPY/QQQ/BTC beta >0
- average net forecast edge >20 bp for commission-free stocks

### 6. Alternatives ranked

1. Cross-rail data source only
2. Weekend crypto→Monday beta/residual model
3. ETF/NAV directional gap

**Confidence:** Medium. Do not divert $20 treasury here until capital or proven edge justifies the lower velocity.

---

## Q11 — Highest-probability cross-rail strategies

### 1. Mechanism

The most valuable use of extra rails is **information transfer**. A rail does not need to be tradeable to be predictive.

### 2. FORGE Cross-Rail State Vector

Build:

\[
X_t=[
SpotRet,\ OFI,\ PerpBasis,\ Funding,\ OIChange,\ DVOL,\ ETFGap,\ PAXGBasis,\ KalshiResidual
]
\]

Estimate a regime-specific state-space model:

\[
r^{target}_{t+h}=A_{regime}X_t+\epsilon
\]

For binary markets, feed \(A X_t\) into the logit probability residual.

### 3. Top cross-rail signals

1. **Perp basis/funding/OI → crypto threshold probability**
2. **PAXG/gold reference → Kalshi gold thresholds**
3. **24/7 BTC/ETH price action → Monday COIN/MSTR/IBIT opening state**
4. **Prediction-market probability → spot/event risk regime**
5. **US500/TECH futures reference → index event contracts / equity open**

### 4. Example transmission equation

\[
\Delta \operatorname{logit}(p_{BTC>K})=
\beta_1 z_{\text{spot}}
+\beta_2 z_{\text{basis}}
+\beta_3 z_{\text{funding}}
+\beta_4 z_{\Delta OI}
+\beta_5 z_{\text{DVOL}}
\]

Shrink all coefficients heavily and let OOS evidence determine whether they survive.

### 5. Validation

A new cross-rail feature must improve:
- predictive log loss or Brier on sealed outcomes,
- and economic TAKE P&L.

Kill if it improves statistical fit but does not improve net economic decisions.

### 6. Alternatives ranked

1. Perp/funding/OI → Kalshi crypto
2. settlement-proxy → commodity prediction markets
3. weekend crypto → equities

**Confidence:** High that cross-rail information is valuable; medium on specific signs/magnitudes.

---

## Q12 — Stablecoin and fee-structure alpha

### 1. Mechanism

FORGE measured +0.33 bp/cycle in a stable triangle. This is real-looking but tiny. Stablecoin strategies should function as a **capital scavenger** when idle, not block a 5–10¢ binary edge.

### 2. Peg mean-reversion maker engine

Define deviation:

\[
d_t=mid_t-1
\]

Estimate conditional reversion:

\[
E[d_{t+h}]=d_t e^{-h/\tau}
\]

Quote only if:

\[
E[\text{capture}]
=
|d_t|(1-e^{-h/\tau})
+MakerRebate
-Fee
-AdverseSelection
>Threshold
\]

### 3. Queue position estimator

Approximate volume ahead:

\[
Q^{ahead}_t = VisibleDepthAtPriceBeforeOurOrder
\]

Update from:
- trades consuming level,
- cancellations inferred from L2 deltas,
- new size ahead/behind where sequencing permits.

Fill probability over \(h\):

\[
P(fill<h)
\approx
P(ConsumedVolume_h > Q^{ahead}_t)
\]

learned empirically by survival analysis.

### 4. Triangle engine

For path USD→USDC→USDT→USD or allowed equivalent:

\[
R_{cycle}=
\prod_{\ell=1}^{L}
(PriceRatio_\ell(1-fee_\ell-impact_\ell))-1
\]

Execute only atomically enough that stale-leg risk is bounded. With no transfer permission, remain entirely inside available trading/convert rails.

### 5. Daily expected profit

Do not project a large number from 0.33 bp. On $10:

\[
10\times0.000033=\$0.00033
\]

per completed full-capital cycle. Even 30 such clean cycles is only about one cent. That confirms it is a background scavenger, not the path to $1/hour.

### 6. Fee-tier optimization

- Query Coinbase actual fee tier and stable-pair schedule.
- Track 30-day qualifying volume.
- Do **not** churn volume solely to reach a tier unless discounted future fees exceed the churn cost.
- Coinbase One Basic's zero-fee simple-trade allowance does not apply to Advanced API trades; do not assume otherwise.

Alternatives:
1. Zero/near-zero-fee stable maker
2. Stable triangle
3. Depeg-tail mean reversion after extraordinary dislocation

**Confidence:** High on low expected absolute profit at current capital.

---

## Q13 — Event-driven crypto

### 1. New listings

Mechanism: exchange listing/cross-listing can increase access, liquidity and attention. Academic work documents positive abnormal effects around crypto cross-listings, but the largest effect may occur before FORGE can execute on Coinbase.

Rules:
- monitor official Coinbase product/listing status and official announcements;
- timestamp first public notice;
- compare other-venue price move, Coinbase auction/book state and volume;
- do not chase if price already moved >2.5 ATR_5m from pre-announcement level;
- only trade spot if expected remaining move >1.5× all-in Coinbase round-trip cost.

### 2. Token unlocks

Use official project/token distribution schedules where possible. Hypothesis:
- large unlock relative to circulating volume + weak demand can create negative pressure.
Because FORGE cannot short, use unlocks mainly as:
- avoid/exit filter,
- or wait-for-panic/reversal opportunity.

### 3. Funding reset events

Use public perpetual funding histories (e.g., Bybit) and permitted reference data.
Signals:
- extreme positive funding + falling OI can imply crowded longs;
- negative funding + price strength can imply squeeze risk.

Feed to probability calibrator; do not trade funding mechanically.

### 4. CPI/FOMC

Crypto responds rapidly to macro announcements; 2026 research documents high-frequency reactions conditioned by sentiment.

Before event:
- reduce generic spot risk unless strategy is event-specific.
After official release:
- compute standardized surprise;
- use Kalshi event odds and spot reaction;
- trade only if order-book repricing lags.

### 5. Weekend/holiday

Use wider-spread and thinner-liquidity state as a separate regime. Raise required edge, lower size, and favor limit/taker choice based on actual depth.

### 6. Validation

Each event family gets its own sealed event history. Minimum 20–30 independent events before material scaling.

Alternatives ranked:
1. Scheduled macro reaction
2. listing state machine
3. funding/OI event overlay

**Confidence:** Medium-high.

---

# C. EXECUTION, CAPITAL VELOCITY AND COMPOUNDING

## Q14 — The $/hour opportunity-sequencing optimizer

### 1. Mechanism

The correct objective is **expected log growth per unit of locked capital-time**, not standalone ROI.

### 2. FORGE VELA objective

For opportunity \(i\):

\[
V_i(f)=
\frac{E[\log(1+fR_i)]}
{E[T_i]}
-
\lambda_r Risk_i
-
\lambda_c CorrelationCost_i
\]

For a set of opportunities:

\[
\max_{\mathbf f}
\sum_i V_i(f_i)
+
E[V_{future}|CashRemaining]
\]

subject to:
- \(\sum_i f_i\le 1-Reserve\)
- correlation cluster limits
- minimum contract/order size
- settlement timing
- available cash

### 3. Real-time approximation

Full dynamic programming is unnecessary at $10–30.

Use a 6-hour rolling Model Predictive Control horizon:

1. Estimate current candidate log-growth/hour.
2. Estimate expected opportunity arrivals by rail/time-of-day.
3. Penalize any position that blocks expected better opportunities.
4. Enumerate integer position combinations.
5. Choose maximum posterior expected objective.
6. Recompute on every material market event.

### 4. Cash reservation

If next-hour expected opportunity value is \(H\), define reservation shadow price:

\[
\lambda_{cash}=E[\max(0,Edge_{future})]
\]

Current trade must exceed \(\lambda_{cash}\times T_i\) before consuming scarce cash.

### 5. Learning

Estimate settlement time and opportunity arrival from actual FORGE logs, with EWMA half-life 7 days initially.

### 6. Alternatives ranked

1. MPC + integer enumeration
2. greedy log-growth/hour with correlation penalties
3. static priority queue

**Confidence:** High.

---

## Q15 — Fill realism and capacity

### 1. Kalshi taker fills

For immediate orders, walk the actual book:

\[
VWAP(n)=\frac{\sum_l p_l q_l}{n}
\]

for enough levels to fill \(n\).

Impact:

\[
I(n)=VWAP(n)-BestAsk
\]

Do not assume 1-contract displayed ask scales.

### 2. Maker fills

Estimate queue survival / fill from:
- volume ahead at level,
- trade rate at level,
- cancellation rate,
- price-move hazard.

\[
P(fill\le h)=1-\exp(-\Lambda_{consume}(h)/Q^{ahead})
\]

Use learned hazard, not this simple form, once enough data exists.

### 3. Capacity curve

Fit:

\[
Edge(n)=Edge_1-\alpha\log(1+n/D)-\beta n
\]

where \(D\) is near-touch depth.

Capacity \(n^*\) is largest n such that:

\[
Edge(n)\ge0.8Edge_1
\]
and
\[
LCB(Edge(n))>0
\]

### 4. First-8-hour micro-trades

For each promoted signal:
- start n=1;
- collect ack latency, actual fee, fill price, post-fill markouts;
- after 5 clean fills, simulate n=2/3 using book snapshots before actually scaling;
- only scale if estimated edge retention ≥80%.

### 5. Coinbase

Use L2 walk similarly. For a market order, expected slippage = VWAP against current book + latency drift distribution.

### 6. Kill criterion

Any signal whose actual edge retention falls below 50% of shadow edge for 10 consecutive executions is automatically reduced to minimum size and sent to Doctor/Scientist diagnosis.

Alternatives ranked:
1. empirical capacity curve
2. orderbook walk + conservative buffer
3. naive fixed slippage — unacceptable

**Confidence:** High.

---

## Q16 — First 8 hours of real money

### 1. Priority

The fastest credible live path is not "activate everything." It is:

1. TAKE_THRESH only, at 1 contract.
2. Stale-quote variant only after shadow trigger logging confirms repricing.
3. Stable scavenger only when no higher-value position is blocked.
4. Spot trend remains paper/shadow unless an existing validated signal fires with clear fee coverage.

### 2. Loss limits for the experiment

For a $15 Kalshi rail:
- first 10 live trades: max 1 contract
- soft hourly loss stop: **$1.00**
- daily experimental loss stop: **$3.00**
- after a stop, research/shadow continues; live rail pauses until diagnosis

These limits are about preserving learning capital, not pessimism.

### 3. Sequential posterior

Model per-contract net P&L \(x_t\) with robust Student-t mean posterior.

Scale rule:

- 10+ live trades and \(P(\mu>0)>0.90\): continue 1 contract
- 20+ and \(P(\mu>0)>0.95\), posterior mean >3¢: allow 2
- 40+ and \(P(\mu>0)>0.99\), LCB mean >2¢: allow 3–5, subject to capacity
- any posterior \(P(\mu>0)<0.60\): suspend live strategy

### 4. CUSUM divergence monitor

For difference between live and shadow P&L \(d_t\):

\[
S_t^-=\min(0,S_{t-1}^- + d_t + k)
\]

Alert if \(S_t^-<-h\).

Start:
- k = 1¢
- h = 8¢

Learn from observed live-shadow noise.

### 5. Effect target

The stated target is ≥$1/hour. Treat that as an **economic milestone**, not a forced quota.

If TAKE_THRESH truly retains even 3–5¢ net/contract and produces enough independent signals/capacity, $1/hour becomes plausible only through multiple contracts and/or multiple simultaneous markets. FORGE must prove the capacity curve before projecting it.

### 6. Alternatives ranked

1. 1-contract TAKE_THRESH sequential launch
2. 1-contract stale-quote sub-strategy
3. live Coinbase spot — slower evidence due long holding periods

**Confidence:** High in launch protocol.

---

# D. INTELLIGENCE THAT COMPOUNDS

## Q17 — Hermes agents as a quant research desk

The Hermes organization should run on a **permanent research clock** while deterministic FORGE execution runs independently.

### Governor / CIO — every 15–30 minutes

Task:
- rank all live rails/strategies by posterior expected log-growth/hour;
- identify capital locked in low-value opportunities;
- approve/reduce research budgets;
- issue 1–3 research priorities.

Evidence:
- treasury state
- allocation table
- posterior edge
- capital-hour cost
- opportunity cost

Economic attribution:
\[
Value_{Governor}
=
PnL_{actual}-PnL_{counterfactual\ allocator}
\]

Use shadow counterfactual allocations.

### Alpha Inventor — hourly

Task template:
> Find one falsifiable mechanism explaining a current pricing residual. Use only observed FORGE data and legitimate external data. Define a signal, causal story, expected sign, regime, decay horizon, and disconfirming test.

Must output:
- hypothesis ID
- mechanism
- exact formula
- required data
- pre-registered slice
- kill criterion

Attribution: eventual net P&L of promoted descendants minus research compute cost.

### Adversarial Scientist — hourly

Attack the top 3 candidates:
- leakage
- post-selection
- market beta
- fee omission
- non-independent observations
- settlement mismatch
- impossible fills

Cannot reject without specifying the evidence.

### Red-Team Critic — every 2–4 h

Stress:
- exchange outage
- stale data
- 2× slippage
- 50% edge decay
- correlated losses
- API rate limits
- settlement-source change

### SRE Doctor — continuous + 30m audit

Monitors:
- stale feeds
- WebSocket gaps
- reconciliation mismatches
- agent loops
- compute burn
- strategy health
- database health

### Rail Hunter — every 3 h

Research current official APIs/incentives/products:
- new Kalshi incentive programs
- new Coinbase tradable rails
- fee changes
- new settlement sources
- new public data feeds

### Prompt Architect — every 6 h

A/B tests prompt genomes on identical research packets.
Promote only when newer prompt yields:
- higher validation survival,
- lower hallucination rate,
- better economic attribution per token.

**Confidence:** High.

---

## Q18 — Automatic anomaly-and-edge discovery

### 1. Mechanism

FORGE needs to discover TAKE_THRESH-like slices without fooling itself after 50k tests.

### 2. Feature cube

Continuously slice by:
- market family
- threshold/range
- ask decile
- moneyness z
- time-to-close bucket
- spread bucket
- depth
- quote age
- underlying return z-score
- OFI
- vol regime
- hour/day
- model-market disagreement
- incentive state

### 3. Discovery stage

Use hierarchical Bayesian shrinkage rather than raw subgroup averages.

For slice \(s\):

\[
\mu_s\sim N(\mu_{parent},\tau^2)
\]

\[
x_{s,i}\sim t_\nu(\mu_s,\sigma_s)
\]

Rank by posterior probability \(\Pr(\mu_s>0)\) and expected value, but label all discoveries **exploratory**.

### 4. Multiple-testing control

For classical screening use Benjamini-Hochberg FDR q=0.01–0.05. Start q=0.02.

But promotion requires a new sealed stream:
1. freeze definition;
2. timestamp/pre-register hash;
3. collect next observations only;
4. no editing the slice mid-test.

### 5. Rapid promotion ladder

- Discovery: posterior >0.95 on historical/shadow
- Provisional shadow: next 10 sealed cases
- Micro-live: after 10 sealed with posterior >0.90 and mean >2¢
- Production-small: 25+ sealed, posterior >0.97
- Scale: 50+ sealed, posterior >0.99, LCB >1¢, live edge retention ≥70%

This is how FORGE moves within hours without pretending 10 trades are proof of permanence.

### 6. Alternatives ranked

1. Hierarchical Bayesian slices + sealed promotion
2. FDR + sealed replication
3. MAP-Elites alone — insufficient without replication

**Confidence:** High.

---

## Q19 — Alternative data with highest information/cost ratio

### 1. Direct settlement-source data — highest priority

**Kalshi CF Benchmarks feed**  
Mechanism: directly determines crypto event-contract settlement.

Integration:
\[
p_F \leftarrow P(A_{60}>K|CF\ RTI\ path)
\]

Expected improvement: do not guess; require ≥0.002 Brier improvement near expiry vs Coinbase proxy.

### 2. Public exchange order books

Coinbase + Kraken/Bitstamp/other eligible public feeds.

Mechanism: cross-venue price discovery and settlement-index prediction.

Feature:
\[
Dispersion_t=\operatorname{std}_j(r_{j,t})
\]

and lead-lag residuals.

### 3. Perp funding and open interest

Bybit publishes public funding-rate history. Other major venues expose similar public data.

Mechanism: crowding, basis and leveraged positioning.

Features:
\[
z_{fund},\quad \Delta OI,\quad Basis=(Perp-Spot)/Spot
\]

Use as conditional predictor, not standalone signal.

### 4. Deribit options / DVOL / order books

Deribit offers public market-data APIs over WebSocket/HTTP. Use options-implied state:
- IV term structure
- skew
- put/call demand
- DVOL where available

Mechanism: forward-looking volatility and tail pricing.

Feature:
\[
VolGap = IV_{options}-RV_{HAR}
\]

### 5. BLS

Official BLS API for CPI/jobs historical data. For release trading, benchmark the fastest authoritative release endpoint; historical API alone may not be lowest latency.

### 6. NWS

Free official API provides forecasts, observations and alerts. Best use: weather contracts with exact station/rule mapping.

### 7. EIA

Free registered API for petroleum/natural-gas data. Best use:
- energy inventory/event contracts
- commodity regime context

### 8. Coinbase/Kalshi incentive and product metadata

These are not "market data" but can create direct economic value:
- fee schedules
- liquidity programs
- volume rewards
- newly listed contract families.

### 9. Information-gain admission rule

A new feature \(x\) is admitted only if:

\[
IG_x =
Loss_{baseline,OOS}-Loss_{+x,OOS}>0
\]

and it improves economic P&L after added latency/cost.

Starting thresholds:
- ΔBrier ≥0.0015, or
- Δlogloss statistically positive and
- net P&L improvement ≥0.5¢/decision.

### 10. Do not pay for expensive alternative data yet

At $10–30 capital, a $50/month dataset needs extraordinary incremental edge. Use public/cheap data until FORGE can demonstrate an Intelligence ROI >3×.

Alternatives ranked:
1. direct settlement feeds + public exchange microstructure
2. perp/options state
3. official macro/weather/energy data
4. social sentiment — lower priority because noisy/manipulable

**Confidence:** High.

---

## Q20 — The breakthrough edge

### The single strongest candidate: Settlement-Aware Cross-Rail Constraint Alpha

This is the edge I would try to make FORGE own.

It is not one indicator. It is a structural advantage:

> **FORGE knows the exact settlement rule, watches the settlement source and faster related markets in real time, reconstructs the entire fair probability surface, and trades only when executable event-contract prices lag or violate that dynamically updated surface.**

Why this fits a small account:
- capacity can be too small for large firms to prioritize;
- dozens/hundreds of strikes fragment attention;
- short-dated contracts recycle capital quickly;
- exact settlement details matter disproportionately near expiry;
- FORGE can monitor everything continuously;
- small capital can take one or a few contracts without moving the book much.

### 1. Mechanism

For each contract \(i\):

\[
p^{settle}_i
=
P(g_i(A_T)=1|\mathcal F_t)
\]

where \(g_i\) is the exact settlement rule.

Market-implied executable probability:

\[
p^{mkt}_i=a_i+Fee_i+Impact_i
\]

Information residual:

\[
R_i=p^{settle}_i-p^{mkt}_i
\]

Then constraint-adjust fair probabilities by projecting all \(p_i\) onto the feasible strike/range surface:

\[
\mathbf p^*=
\arg\min_{\mathbf p\in\mathcal C}
(\mathbf p-\hat{\mathbf p})^\top W(\mathbf p-\hat{\mathbf p})
\]

where \(\mathcal C\) contains monotonicity/complement/range constraints.

Finally:

\[
Alpha_i=
LCB(p_i^*)-p_i^{mkt}
\]

### 2. Add quote-decay / urgency

\[
TradableAlpha_i(d)=Alpha_i e^{-\lambda_i d}
\]

and rank by:

\[
Score_i=
\frac{
TradableAlpha_i
\times FillProb_i
\times Capacity_i
}{
Capital_i\times ExpectedHours_i
}
\]

subject to log-growth and risk constraints.

### 3. Implementation steps

**Phase 1 — 0–4 hours**
- wire direct CF feed
- record Kalshi book changes at highest practical cadence
- timestamp Coinbase/other venue events
- implement exact settlement-path state
- preserve every missed opportunity for counterfactual study

**Phase 2 — 4–12 hours**
- fit quote-repricing hazard
- create stale-quote trigger
- run sealed shadow
- micro-live only on pre-registered TAKE_THRESH

**Phase 3 — 12–24 hours**
- build surface constraints
- estimate edge half-life
- calibrate exact fee/impact/capacity

**Phase 4 — 24–48 hours**
- expand to BTC/ETH/SOL
- expand to gold if settlement-source mapping is reliable
- compare incumbent vs cross-rail model OOS
- increase size only where actual edge retention remains high

### 4. Confirmation evidence within 48h

Strong evidence would be:

- ≥40 sealed threshold signals
- posterior \(P(\mu_{net}>0)>0.99\)
- mean net ≥3¢/contract
- median Kalshi quote moves in predicted direction after stale trigger
- live edge retention ≥70% of shadow
- effect appears across at least 2 underlyings or multiple independent sessions
- Brier/log-loss improvement concentrated in the exact traded slice

Even stronger:
- strategy remains profitable after intentionally worsening latency by 250–500 ms;
- this proves it is not a fragile artifact requiring colocated HFT speed.

### 5. Protecting against decay

- never publish live signals externally;
- constantly estimate edge half-life;
- lower allocation as residual shrinks;
- evolve models, not settlement facts;
- preserve multiple independent sub-strategies;
- use direct settlement-source truth;
- monitor market calibration improvement;
- treat every fee/methodology change as a forced revalidation event.

### 6. Alternatives ranked

1. **Settlement-aware stale quote + surface constraints**
2. **Scheduled macro/commodity probability mispricing**
3. **Cross-rail funding/options state → event probabilities**

**Confidence:** This is the highest-priority legitimate edge I can identify for FORGE's exact setup. It is not guaranteed, but it has the best combination of structural rationale, current internal evidence, low-capital suitability and rapid capital recycling.

---

# THE ULTIMATE ADAPTIVE ALGORITHM — FORGE META-CORTEX

Everything above should feed one adaptive controller.

## State

\[
C_t=[
Treasury,\ Reserve,\ Regime,\ Vol,\ Liquidity,\ Fees,\ RailState,\ StrategyPosteriors,\ OpportunityArrival,\ ComputeBudget
]
\]

## Candidate strategy posterior

For every strategy \(s\):

\[
\theta_s(C_t)\sim
Posterior(NetLogGrowthPerCapitalHour)
\]

Use **discounted contextual Thompson sampling**:

- sample \(\tilde\theta_s\) from each strategy posterior;
- subtract correlation/risk/cost penalties;
- feed sampled opportunity values into VELA;
- allocate capital to the portfolio with highest sampled objective;
- update posteriors after settlement.

Recommended discount factor:
- fast event strategies: **0.97 per 20 observations**
- hourly strategies: **0.985**
- multi-day spot: **0.995**

Instead of one fixed factor, optimize predictive log score quarterly/weekly as evidence grows.

## Strategy birth

A Hermes Scientist may create a genome only if it includes:
- falsifiable mechanism
- feature list
- venue/regime
- expected sign
- cost model
- kill criterion
- nearest known ancestors
- reason existing strategies cannot capture the same mechanism.

## Strategy promotion

```text
IDEA
  ↓
REPLAY
  ↓
PURGED / WALK-FORWARD
  ↓
SEALED SHADOW
  ↓
MICRO-LIVE
  ↓
PRODUCTION-SMALL
  ↓
SCALE
```

No strategy may skip from LLM idea to meaningful money.

## Strategy death / hibernation

If posterior net edge deteriorates:
- first reduce capital;
- determine whether regime changed;
- compare with archived lineage;
- mutate only based on diagnosed failure;
- hibernate if regime-specific;
- retire if structural edge disappeared.

## Capital compounding

Let deployable treasury be \(W_t-R_t\).

FORGE reinvests realized profit automatically:

\[
W_{t+1}=W_t+\Pi_t
\]

Position size rises because the same fractional-growth rule acts on a larger base. This creates exponential-style compounding **only while capacity and edge scale**.

Capacity-aware scaling law:

\[
f_{effective}=
f_{Kelly}
\cdot
\min\left(
1,\frac{Capacity_{80\%edge}}{W_tf_{Kelly}}
\right)
\]

When a strategy saturates, incremental capital must move to another independent edge rather than forcing more size into the same book.

---

# Immediate build order for the next 8 hours

## P0 — must exist before more live capital
1. Exact fee engine by product/side/order type.
2. Direct CF Benchmarks Kalshi feed.
3. Full event-time logging with synchronized timestamps.
4. One-contract TAKE_THRESH live gate.
5. Wallet/account reconciliation.
6. Edge-retention telemetry.

## P1 — highest expected improvement
7. Stale-quote repricing hazard.
8. Final-60-second settlement-path model.
9. Hierarchical market-residual calibrator.
10. Discrete correlated Kelly / VELA allocator.
11. Counterfactual recorder for skipped opportunities.

## P2 — expansion
12. Constraint probability surface.
13. Perp funding/OI features.
14. Deribit implied-volatility features.
15. Gold/Pyth rail.
16. Macro release rail.

## P3 — only after proof
17. Incentive-aware maker quoting.
18. equities execution.
19. paid alternative data.
20. larger contract size.

---

# Quantitative success dashboard FORGE should expose

Every hour:

- realized net P&L
- unrealized P&L
- P&L after DeepSeek + Modal cost
- net $/capital-hour
- geometric growth rate
- expected vs realized edge
- fill edge retention
- calibration Brier/log loss
- active strategy posterior \(P(\mu>0)\)
- edge half-life
- capital utilization
- opportunity cost of deployed capital
- income by rail
- income by strategy family
- compute ROI
- false discovery count
- strategy births / promotions / hibernations / deaths
- current probability of 10%, 25%, and 50% drawdown under posterior predictive simulation

The most important number is:

\[
\boxed{\text{TRUE NET LOG GROWTH PER CAPITAL-HOUR}}
\]

That is the KPI that aligns speed, profitability, fees, and compounding.

---

# Non-negotiable scientific rules that increase — not reduce — earning potential

1. **No theoretical P&L when wallet/fill truth exists.**
2. **Every discovered slice gets a sealed forward test.**
3. **Every model competes against market price and a no-model baseline.**
4. **Every inference/compute expense has an economic attribution path.**
5. **Every strategy has a capacity curve.**
6. **Every stale-quote strategy estimates its own half-life.**
7. **Every live strategy has a validated replacement/challenger pipeline.**
8. **Every provider-methodology/fee change triggers automatic revalidation.**
9. **Profitable incumbents keep earning while challengers are developed.**
10. **FORGE is never strategically idle: EARN → LEARN → HEAL → EVOLVE.**

---

# Source and evidence register

These sources are evidence inputs, not substitutes for FORGE's own live validation.

1. Coinbase — lowering Advanced fees, U.S. 0.50% maker / 0.90% taker; lower tiers starting at $10k qualifying volume:  
   https://www.coinbase.com/blog/were-lowering-fees-for-many-active-traders-on-coinbase-advanced

2. Coinbase Advanced fee mechanics / tiers:  
   https://help.coinbase.com/en-gb/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees

3. Coinbase One Basic — $4.99 plan, simple-trade allowance, USDC rewards; Advanced excluded from zero-fee trading:  
   https://www.coinbase.com/one?tier=basic

4. Coinbase stocks — $0 commission, fractional shares from $1, 24/5 eligible symbols:  
   https://www.coinbase.com/stocks

5. Coinbase fractional-share restrictions and $1 minimum:  
   https://help.coinbase.com/en/trading-and-funding/fractional-shares

6. Coinbase stocks vs crypto — T+1 equities settlement:  
   https://help.coinbase.com/en/other-topics/stocks-vs-crypto

7. Kalshi crypto settlement — 60-second CF Benchmarks RTI average and API pass-through:  
   https://help.kalshi.com/en/articles/13823838-crypto-markets

8. Kalshi API overview:  
   https://help.kalshi.com/en/articles/13823854-kalshi-api

9. Kalshi fee schedule / general fee formula:  
   https://kalshi.com/regulatory/fee-schedule

10. Kalshi liquidity incentives:  
    https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program

11. Kalshi volume incentives:  
    https://help.kalshi.com/en/articles/13823850-what-is-the-kalshi-volume-incentive-program

12. Kalshi market-maker program:  
    https://help.kalshi.com/en/articles/13823819-how-to-become-a-market-maker-on-kalshi

13. CF Benchmarks BRTI — benchmark design and real-time index:  
    https://www.cfbenchmarks.com/data/indices/BRTI

14. CF Benchmarks methodology/documentation:  
    https://www.cfbenchmarks.com/documentation/indices

15. Momentum in Cryptocurrency Markets under realistic assumptions — strong time-series, weak cross-sectional evidence:  
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565

16. Bailey & López de Prado — Deflated Sharpe Ratio:  
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

17. Bailey et al. — Probability of Backtest Overfitting:  
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

18. 2026 research — order flow predicts cryptocurrency returns:  
    https://www.sciencedirect.com/science/article/pii/S1386418126000029

19. 2026 crypto macro-news high-frequency reactions:  
    https://www.sciencedirect.com/science/article/pii/S2214635026000456

20. Crypto cross-listing returns/network effects:  
    https://www.sciencedirect.com/science/article/pii/S0929119920302972

21. Weekend crypto → Monday stock return research:  
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5382090

22. Bybit public funding-rate API docs:  
    https://bybit-exchange.github.io/docs/v5/market/history-fund-rate

23. Deribit API documentation:  
    https://docs.deribit.com/

24. BLS public API:  
    https://www.bls.gov/developers/home.htm

25. NWS free API:  
    https://www.weather.gov/documentation/services-web-api

26. EIA Open Data API:  
    https://www.eia.gov/opendata/

---

# Final directive to the FORGE builder

Treat this document as a **strategy research upgrade**, not a command to blindly enable everything.

The objective is aggressive, continuous compounding. The way to achieve that is:

**Find structural edge → prove it quickly → allocate intelligently → preserve it through execution → recycle capital → scale until capacity → move surplus capital to the next independent edge → keep evolving 24/7.**

The highest-priority near-term hypothesis is **Settlement-Aware Cross-Rail Constraint Alpha**, especially threshold contracts where FORGE's own shadow data already shows promising economics.

Do not slow FORGE down with unnecessary ceremony. Instead make every safety/validation gate computational, automated, and fast. A good gate should help FORGE move **faster toward real money** by killing false edge early and accelerating genuinely profitable signals.

FORGE should continuously become better at answering one question:

> **Where can the next dollar produce the highest evidence-adjusted net log growth per hour right now?**

That is the engine.
