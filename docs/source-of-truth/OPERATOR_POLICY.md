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
