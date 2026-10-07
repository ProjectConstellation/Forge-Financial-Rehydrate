# Operator policy overrides (chronological; newest wins; overrides DIRECTIVE and DOSSIER where they conflict)
Recorded verbatim-in-substance from operator instructions in the build session. Only the operator may add entries.

## OP-001 — 2026-10-06T23:2xZ — Treasury = entire Coinbase balance
> "We can use all of it. Let's say whatever is in that balance is able to earn money and should aggressively earn as much as it can 24/7 always."

- Replaces the $20 treasury / $20 external-injection cap (DOSSIER §21, DIRECTIVE §6).
- FORGE's treasury = the full value of the configured Coinbase portfolio (USD + held assets), including future deposits and profits.
  At adoption: USD 28.27 (Default portfolio).
- Unchanged (hard constraints of both documents): trade only with positive expected net value after all costs; restart reserve 5–20% below $100,
  $25 floor at ≥ $100; no leverage; deterministic Risk Governor; readiness gate before LIVE; no forced trades.

## OP-002 — 2026-10-06 — Coinbase integration
- Use the operator's existing **personal** Coinbase account via the **Advanced Trade API** (CDP Secret API key, ECDSA). Do NOT require Coinbase Business.
- Initial key permissions: View + Trade (+ Receive allowed). No Transfer/Export/Manage. Adapter must stay modular (permissions / Agentic Wallet later).

## OP-003 — 2026-10-06 — Cash-out capability
- Build an operator-initiated, intelligent cash-out: Stage 1 = liquidate to USD in-account (Trade permission only). Stage 2 = transfer to operator-registered
  destinations only, when the operator explicitly authorizes Transfer on a key. Never initiated by the LLM or strategies.

## OP-004 — 2026-10-06 — Two-brain DeepSeek, real-time tools, hard thresholds, high-probability edges
> "We're going to leverage Deepseek V4.1 Pro at its maximum capability in compute and utilize tool function calls always to have real-time
> data at all times and have it generate new algorithms. If something doesn't work we have to have thresholds. We need to try something else.
> It must be aggressive but not lose money." · "the algorithms can be built to have ... 90% or higher statistics or probability of income"

- **Two brains**: `deepseek-v4-pro` at effort `max` = algorithm inventor / critic / postmortem (deep work). `deepseek-flash` = high-frequency
  tool-loop analyst. Both always work through typed tools fed with real-time data (never from memory).
- **90% rule**: no strategy receives real capital unless the posterior probability that its *net-of-all-costs* edge is positive is **≥ 0.90**
  (with minimum sample, walk-forward and robustness gates). Trades additionally require calibrated P(net win) above the strategy's threshold.
- **Thresholds → try something else**: hard per-trade stop, per-strategy demotion/retirement triggers, portfolio daily/weekly loss limits;
  every trip triggers an automatic DeepSeek-Pro postmortem and replacement challengers.
- **Aggressive capital use, capital preservation first**: full sizing on proven edges; losses capped by the thresholds above.
- DeepSeek pricing verified 2026-10-06 (USD / 1M tokens, off-peak | peak): Flash hit 0.003|0.006, miss 0.15|0.30, out 0.60|1.20;
  Pro hit 0.022|0.044, miss 0.66|1.32, out 1.98|3.96. Peak = 01–04 and 06–10 UTC Mon–Fri; all else off-peak.

## OP-005 — 2026-10-06 — Intelligent, always-live, multi-way earning
> "It must be intelligent. It must always be live in real time ... It should be able to find and earn money in many different ways not limited to one scope."

- FORGE runs continuously on live streams (WebSocket market data, live balances, live provider state); decisions are made on real-time data only.
- Earning is organized as pluggable **Income Rails** that all publish opportunities to one bus and compete for capital on the same
  true-net-value scale: spot trading families (many), maker liquidity/volatility harvesting, cross-sectional rotation, idle-capital yield
  (USD/USDC where eligible), and future rails (Kalshi/prediction markets, Base on-chain via Agentic Wallet, x402 machine-payable services,
  bounty/work marketplaces). The Venue Explorer continuously researches and proposes new rails.

## OP-006 — 2026-10-06 — CIO directive: optimize AI (don't minimize it), tiered escalation, Intelligence Attribution Ledger
Operator directive (verbatim core):
> Act as an elite Autonomous Multi-Strategy Quantitative Capital Growth CIO, Algorithmic Trading Architect, and Economic Opportunity Hunter whose sole
> mandate is to make FORGE exceptionally effective at autonomous capital growth. [...] Do NOT think narrowly in terms of stocks or one trading strategy.
> Continuously consider every legitimate, API-accessible way capital could earn more capital [...]. DeepSeek inference is not merely a cost or a trade
> predictor. Treat AI as a core economic intelligence layer [...]. Use DeepSeek V4.1 Flash continuously where economical. Escalate unusually valuable,
> complex, or ambiguous problems to the strongest DeepSeek reasoning model available, including V4 Pro/high reasoning when its expected information value
> justifies the additional cost. Use Modal aggressively [...] whenever expected economic benefit exceeds compute cost. [...] OBSERVE → DISCOVER →
> HYPOTHESIZE → CREATE → TEST → SHADOW → DEPLOY → MEASURE → LEARN → MUTATE → RETIRE → REINVEST → REPEAT. Every failed strategy becomes knowledge. Every
> successful strategy becomes reusable DNA. [...] Incorporate the strongest lessons from your earn-or-die-agent research [...] but do NOT allow academic
> caution to paralyze FORGE. Scale exposure progressively as evidence strengthens. Measure AI value broadly. [...] Build an Intelligence Attribution
> Ledger that traces inference/compute spend to downstream economic outcomes so FORGE learns where intelligence itself has the highest ROI. Your mission
> is not maximum trading frequency. Your mission is maximum sustainable net treasury growth after every cost. Take initiative. [...]

Operator clarification (same message): "Don't minimize AI. Optimize AI." The question is not "did the LLM make this trade profitable?" but
"did spending this intelligence ultimately increase FORGE's expected or realized net economic value?" (avoided losses, discovered strategies,
successors that survive, regime detection, venue discovery, compute routing). A no-LLM twin is at most one calibration signal, never a gate.

Canonical escalation loop:
market anomaly → Flash investigates → unusual? → Pro (max) investigates → Modal runs ~1,000 simulations → deterministic risk engine evaluates
→ execute / reject → result enters memory → routing policy learns from it.

Roles: Flash = continuous perception/orchestration · Pro (strongest available) = escalation brain · deterministic code = execution + risk ·
Modal = parallel computational muscle.

Adopted research takeaways (2026-10-06 brief): strategy-level metabolism/survival pressure, runway tiers for operating budgets, wallet-truth P&L,
$1 calibration trades, learned backtest→live haircut, pre-registered power targets, planted-signal (positive-control) evaluator tests, cost-ruler
versioning with automatic re-adjudication, loop/meltdown watchdog, stepping-stone archive, conduct rules in code, verified-independent-payer
admission for new income rails. Applied with progressive exposure scaling — caution must not paralyze.

## OP-007 — 2026-10-06 — PERMANENT ARCHITECTURE: two continuous concurrent loops (Earning + Improvement)
Permanent architectural requirement (not optional, not future):
1. **EARNING LOOP** — proven strategies keep operating while their real, fee-adjusted, risk-adjusted edge remains valid. Never interrupt a
   profitable incumbent merely because a newer idea exists. Capital stays deployed where evidence shows it is currently productive.
2. **IMPROVEMENT LOOP** — runs continuously in parallel with live earning; FORGE must never become strategically stagnant. Always capable of
   producing: new families, mutations, parameter improvements, component combinations, market hypotheses, indicators/features, asset/venue
   opportunities, regime variants, alternative execution methods, new legitimate API income rails.
- Every live strategy is an **incumbent, never a finished product**, continuously challenged by candidates:
  generated → simulated → backtested → walk-forward → shadow → compared → promoted or rejected.
- Strategy states: **PRODUCTION · CHALLENGER · EXPERIMENTAL · SHADOW · HIBERNATING · RETIRED** (+ QUARANTINED for invalid/bug results).
- Capital and compute continuously migrate toward the strongest demonstrated opportunities (real net performance, EV, uncertainty, liquidity,
  fees, slippage, drawdown, correlation, probability of ruin).
- Weak strategies never just disappear; FORGE decides: repair · mutate · reduce · hibernate (until regime returns) · combine · retire into
  permanent institutional memory (lineage, assumptions, results, failure reasons, applicable regimes retained).
- 24/7 = economically and intellectually active, not forced trading. Always at least one of: **EARNING → LEARNING → PREPARING TO EARN BETTER**.
- Implement by extending the existing architecture (no redesign).

## OP-008 — 2026-10-06 — Capital Regime + Capital Velocity Engine + Opportunity Cost Engine (enhancement, no redesign)
- Objective: ambitious treasury growth; while capital is small prefer opportunities that return capital + profit quickly for reinvestment.
  NOT a hard holding-time limit — exceptional longer-duration opportunities remain eligible; time enters scoring, not rules.
- Score every opportunity on: realistic earnings, confidence, capital required, time capital is unavailable (time-to-profit/liquidity),
  reinvestment speed, opportunities blocked by locked capital (opportunity cost), and whether smaller/faster compounding is superior.
- Treasury regimes (starting parameters, learnable/adjustable): SURVIVAL/ACCELERATION < $100 (rapid turnover, high-confidence short duration,
  intensive research; falling below $100 escalates intelligence/research/opportunity hunting — never reckless gambling) · GROWTH $100–$500
  (aggressive compounding, moderately longer durations, strengthen reserves + diversification) · EXPANSION $500+ (broader allocation, longer
  high-EV durations, multiple concurrent strategies, larger research budgets, portfolio construction).
- Capital Velocity Score in allocation decisions; Opportunity Cost Engine estimates EV lost while capital is locked.
- Auto-evolve with treasury: reserves, max allocation size, acceptable holding periods, research/inference budget, Modal allocation,
  concurrent strategies, strategy diversity, liquidity requirements.
- Never "grow quickly" via false confidence or bad bets; aggression comes from evidence, algorithms, intelligence, faster recycling, discovery.
- Governing principle: MAKE CAPITAL WORK HARD, RETURN IT QUICKLY WHEN POSSIBLE, REINVEST IT INTELLIGENTLY, AND NEVER LEAVE A BETTER
  OPPORTUNITY UNEXPLORED SIMPLY BECAUSE THE CURRENT RULES WERE STATIC.

## OP-009 — 2026-10-06 — Final Alpha & Acceleration Directive (enhancements, no redesign)
Immediate experimental objective: maximize the probability of positive REALIZED NET P&L within the first 24h of live operation while
preserving unlimited scalability. Never force trades to satisfy it.
1. Value-of-Information Intelligence Router — Flash continuous; escalate to strongest authorized DeepSeek reasoning when value is high,
   uncertainty economically significant, major failure diagnosis, potential new family, contradictory signals, or positive EVI. Optimize AI.
2. Opportunity Half-Life — every opportunity carries an estimated decay/half-life (seconds…days); prioritize by magnitude × urgency.
3. Execution Alpha — separate optimization of maker/taker, market/limit, entry timing, cancel timing, partial fills, liquidity, spread,
   slippage, depth, size impact, latency, realized fees. Preserve discovered alpha through execution.
4. Counterfactual Learning — no-trade, later entry, different size, second-best strategy, rejected-then-profitable, accepted-should-reject.
5. Confidence Calibration — empirical; recalibrate prediction classes automatically; sizing follows calibrated evidence only.
6. Evolution Safety — generated strategies run sandboxed and pass validation before meaningful capital. Evolution may NOT rewrite: wallet
   security, credential handling, immutable hard spending ceilings, emergency-stop behavior, the core Risk Governor.
7. Mission Treasury — three pools: GROWTH (compounding), SURVIVAL/PROTECTED (organism protection), MISSION (realized profit permanently
   removed from trading risk to fund North Star Imagine projects such as Ascend). Tiny-capital phase: prioritize compounding; extraction
   policy begins as growth makes it economically sensible (configurable, evolving).
8. Permanent operating principle — continuously optimize ALPHA · VELOCITY · INTELLIGENCE · EVOLUTION. No profitable algorithm is "finished".

## OP-010 — 2026-10-07 — Spending scales with confidence and earnings (no small-account friction)
> "Don't mistakenly create friction for this to be a system that only has a little bit of money to work with. As it earns money it has more
> money to invest and more money to use. ... spending scales based off of its confidence in how it's going to earn money. The idea is the most
> money the soonest, using the most advanced algorithms to ensure the highest returns possible."
- Inference and compute are INVESTMENTS allocated by expected value (attribution-ledger ROI per role/model/effort), not fixed small budgets.
- Spend rate scales up with measured value-per-$ and with realized earnings; scales down only when measured ROI is poor or funds run out.
- No fixed research timers: escalation is event/EV-driven (near-miss strategies, anomalies, failures, idle capital).
- Compute concentrates on near-miss candidates (closest to the evidence gate) — "racing" — to reach validated earning edges sooner.
- Hard limits that remain: cannot spend money that does not exist (DeepSeek balance; Modal monthly ceiling set by operator, raisable),
  and the evidence gate for capital (OP-004) — confidence must be earned, then capital and intelligence scale with it.

## OP-011 — 2026-10-07 — DeepSeek balance sentinel ($5 threshold → $10 refill)
Operator request: monitor DeepSeek balance continuously (lightweight); when it falls below $5, add exactly $10, once, intelligently.
Verified 2026-10-07: DeepSeek API has no top-up/payment endpoint (chat, models, balance only); OpenRouter's programmatic crypto
top-up is deprecated/removed. Credential-based website automation rejected (fragile, likely ToS violation, DIRECTIVE forbids bypassing
browser protections, puts card-spending power on the server). Implemented instead: Balance Sentinel — 5-min free balance polling;
below $5 → ONE "add $10" alert per episode (dashboard banner + optional ntfy push); detects top-ups and books them as inference funding;
tracks self-funding progress; graceful degradation (engine never stops). Upgrade path: provider-side auto-reload if available, or a
future programmatic payment rail (e.g. x402-capable inference provider paid from an allowlisted agentic wallet) when authorized.

## OP-012 — 2026-10-07 — FORGE MUST BE SELF-HEALING AT EVERY LAYER (+ corrections)
Four concurrent healing layers: (1) OPERATIONAL — supervise every process/worker/scheduler/stream/DB/Modal/provider connection; detect crashes,
hangs, stale heartbeats, memory/resource problems, WS disconnects, abnormal latency; restart/reconnect with exponential backoff + state
checkpoints; failures isolated from unrelated loops. (2) ECONOMIC — degraded live strategies lose capital automatically; strongest validated
challenger promoted; failed strategy + evidence preserved; DeepSeek diagnoses WHY; targeted mutations/new families (never random);
backtest→walk-forward→shadow→challenge→promote; profitable incumbents keep earning while challengers evolve. (3) DATA + EXECUTION — detect
stale/missing/contradictory/corrupt market & account data; Coinbase wallet/balance/order truth is authoritative; on uncertainty stop only the
affected execution, reconcile, rebuild local state, resume; every order idempotent. (4) INTELLIGENCE — DeepSeek never a single point of
failure; Flash for continuous perception; stronger reasoning when value/complexity justifies; if inference unavailable, deterministic
strategies/risk/execution continue and reasoning work queues for retry.
Corrections: no fixed concurrency (economic, dynamic: treasury, fees, quality, correlation); no mechanical breakeven exits (keep downside
protection; regime-aware trailing lets exceptional winners run); 50k candidates only useful with OOS/walk-forward, realistic costs and
multiple-testing controls; second-opinion model = calibrated evidence (measured on realized outcomes), not an automatic veto; continuous
probability/evidence-weighted allocation; keep smarter order placement + agreement boosting; Kalshi next after Coinbase is production-ready.
SELF-HEALING HEALTH SCORE on the dashboard: system, feed, execution, strategy, AI, treasury.
Operating law: always have a tested replacement strategy waiting whenever reasonably possible.
The organism is always EARNING, LEARNING, HEALING, or PREPARING TO EARN BETTER.
