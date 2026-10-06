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
