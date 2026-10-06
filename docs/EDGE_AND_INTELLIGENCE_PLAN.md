# FORGE — Edge & Intelligence Plan (how FORGE earns, learns, and scales)

Status: design of record (2026-10-06). Implements DOSSIER §10–16, §21–29, §43; DIRECTIVE §13–24, §34–39;
operator instructions OP-001..OP-003 and the operator's direction to (a) upgrade every algorithm where possible,
(b) plan for unbounded scaling, (c) use DeepSeek V4.1 Flash aggressively with state-of-the-art prompt engineering.

Honesty constraint (both source documents): no system can guarantee profit every hour. FORGE is engineered so that
(1) capital is never idle without reason, (2) it only takes positive-expected-value actions after **all** costs,
(3) it learns continuously from far more data than it trades, and (4) its edge compounds as capital grows.

---------------------------------------------------------------------------------------------------------------
## 1. The economic reality FORGE is designed around (measured 2026-10-06)
- Account: personal Coinbase, Advanced Trade, Intro tier: **maker 0.50%, taker 0.90%**. Min order **$1** on all 804 online USD/USDC spot markets.
- Round trip: maker→maker 1.0% · maker→taker 1.4% · taker→taker 1.8% (+ spread for taker).
- Consequence: sub-minute scalping is negative-EV at this tier. Viable edges must clear a ~1–1.5% hurdle
  → horizons of hours to days, maker-first execution, and selective entries. The feasibility engine
  recomputes hurdles from the **live fee tier**, so shorter-horizon families activate automatically as volume
  lowers fees (tier progression is itself a scaling mechanism).

## 2. Upgrades over the blueprint — earning layer
| # | Upgrade | Why it earns more |
|---|---|---|
| E1 | **Maker-first execution intelligence**: post-only entries priced inside the spread from a learned fill-probability model; adaptive repricing; switch to taker only if the remaining edge > taker cost (opportunity-decay model). | Saves ~0.4% per side vs taker — at this tier that alone turns many marginal edges positive. |
| E2 | **Fee-hurdle-aware triple-barrier labeling** (take-profit / stop / time barriers set net of round-trip cost) on every bar of every watched market. | Strategies are trained and scored on *net* outcomes, never gross. |
| E3 | **Meta-labeling with calibrated probabilities**: genome signals propose entries; an online, walk-forward-trained logistic model (per family × regime) estimates P(TP before SL); isotonic calibration on out-of-sample data. | Converts "signal fired" into a calibrated probability that drives sizing — the core of evidence-before-confidence. |
| E4 | **Growth-optimal sizing**: fractional Kelly on the calibrated distribution, shrunk by posterior uncertainty, drawdown-aware, capped by liquidity (square-root impact) and policy. | Maximizes long-run compounding while controlling ruin. |
| E5 | **Bayesian Thompson-sampling capital allocator** with discounting (non-stationary): capital follows posterior net edge per strategy×regime. | Winners get more capital automatically; decayed edges lose it without human action. |
| E6 | **Regime engine** (probabilistic: trend/range/vol/liquidity states from online clustering + change-point detection, with hysteresis). Strategies are regime specialists that sleep and wake. | Avoids running the right strategy in the wrong market. |
| E7 | **Idle-capital policy**: when no positive-EV trade exists, capital sits in the best eligible zero-risk form (USD ↔ USDC conversion is supported; USDC rewards apply only if the account is eligible — to be verified at integration, never assumed). | "Waiting" is not zero-return when eligible. |
| E8 | **Cross-sectional rotation**: periodic relative-strength ranking across the liquid universe; hold leaders, rebalance only when edge > switching cost. | Captures crypto's documented cross-sectional/time-series momentum at low turnover. |
| E9 | **Volatility-harvest maker ladders** in range regimes with grid spacing ≥ 2× maker fee + buffer, regime-gated and stop-protected. | Earns from oscillation without predicting direction. |
| E10 | **Panic-wick catch orders**: resting post-only bids deep below fair value during liquidation-cascade regimes. | Gets paid as maker exactly when others pay taker. |

## 3. Upgrades over the blueprint — learning/evolution layer ("algorithms that build algorithms")
| # | Upgrade | Why it compounds |
|---|---|---|
| L1 | **Shadow population**: hundreds of genomes paper-trade live data simultaneously at ~zero marginal cost; only proven ones get capital. | Learns ~100× faster than live trading alone, with no capital at risk. |
| L2 | **Counterfactual learning**: every rejected opportunity is scored later against what actually happened (triple barrier). | Missed-winner/avoided-loser data feeds calibration and mutation. |
| L3 | **Quality-diversity archive (MAP-Elites)** over behavior descriptors (holding period × regime × turnover × family). | Keeps a diverse bench of specialists instead of collapsing onto one fragile champion. |
| L4 | **LLM-guided evolutionary search (AlphaEvolve/FunSearch-style)**: DeepSeek acts as an intelligent mutation/crossover operator on the declarative genome; a deterministic evaluator (walk-forward + perturbation + Monte Carlo, locally or on Modal) is the judge. | Hypothesis-driven mutations instead of random search; results are fed back so proposals improve. |
| L5 | **Anti-self-deception statistics**: trial counting, deflated Sharpe, false-discovery control, parameter-plateau tests, purged walk-forward, untouched holdout. | Prevents the evolution engine from becoming an overfitting machine. |
| L6 | **Failure attribution → targeted mutation**: mistake taxonomy (false positive, regime misclass, slippage, late entry/exit, fee drag, …) selects which genome region to mutate. | Every loss becomes a specific, testable fix. |
| L7 | **Lesson memory with decay**: repeated episodes become structured lessons injected into DeepSeek context; contradicted lessons lose confidence. | FORGE becomes progressively harder to fool twice. |

## 4. DeepSeek V4.1 Flash — the brain (aggressive, engineered, ROI-measured)
Facts (verified via API): `deepseek-flash` = DeepSeek-V4.1-Flash, 1M context, effort levels low/high/max,
JSON output + tool calls; prefix cache hits ≈ 50× cheaper than misses; off-peak ≈ 50% off.

Prompt-engineering architecture:
1. **Cache-stable prefix design.** Every agent prompt = [immutable constitution + role + Strategy-DSL grammar +
   tool schemas + curated exemplars + lesson digest] (large, identical across calls → cache hits) followed by a
   small variable "situation pack". Makes heavy, frequent reasoning affordable.
2. **Specialized agents with versioned prompts**: Scientist (hypotheses & mutations), Critic (adversarial
   falsification), Diagnostician (failure attribution), Strategist (regime/portfolio review), Venue Explorer,
   Self-Reviewer. Each output is strict JSON validated by Pydantic with an automatic repair pass.
3. **Pre-registered predictions**: before any test, the LLM must state the expected effect and failure modes.
   FORGE scores those predictions → the LLM's own calibration becomes a measured quantity.
4. **Batch proposal + parallel evaluation**: one call yields 8–20 structured candidates (amortizes the prefix);
   the evaluator tests them in parallel (Modal burst when worth it); results return in the next call.
5. **Self-consistency & debate for high-stakes decisions**: multiple samples / Scientist-vs-Critic with a
   deterministic judge; disagreement is an uncertainty signal that reduces size.
6. **Effort routing (InferenceGovernor L0–L4)**: deterministic first; DeepSeek `low` for routine triage,
   `high` for design/diagnosis, `max` + Modal for exceptional opportunities — chosen by expected value of information.
7. **Prompt evolution**: prompts are versioned genomes too; variants are A/B tested on downstream value
   (validation pass-rate of proposals, realized net P&L). DeepSeek may propose prompt improvements; adoption is
   gated by measured improvement.
8. **Off-peak bulk research** scheduling; time-critical work is never delayed for price.
9. **Injection containment**: all external text is wrapped as untrusted data; the LLM can only act through
   typed tools; it never sees keys and cannot bypass the Risk Governor.
10. **Budget-adaptive throughput**: spend rate scales with remaining DeepSeek balance (read from the provider)
    and with measured Intelligence-ROI. More balance → more research automatically.

## 5. Unbounded scaling (same code at $28 or $28M)
- Scale-invariant policy (fractions, posterior-driven allocation, liquidity-capacity caps via impact model).
- Universe widens automatically as capital grows (more markets clear min-size and fee hurdles).
- Fee-tier progression lowers hurdles → shorter-horizon families unlock automatically.
- Capacity awareness: each strategy learns its own capacity; capital overflows to the next-best edge or venue.
- Venue/rail expansion via adapters: Kalshi/prediction markets, Base on-chain via Agentic Wallet, x402
  machine-payable services, and income rails that earn *new* capital (not just deploy existing capital).
- Compute scales with value: Modal bursts sized by expected value of information; local footprint stays ≤3 vCPU.

## 6. What FORGE will never do (to keep earning sustainable)
Force trades, use leverage (Phase 1), let an LLM place orders directly, bypass platform rules, or report
gross P&L as profit. Every claim of edge is backed by recorded evidence.
