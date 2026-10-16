# FOUNDER STANDING ORDERS — FORGE (command-center copy, 2026-10-10)

Authoritative copy lives on the Forge server (`/srv/forge/docs/continuity/`). This mirror keeps the
command center in sync for rehydration from either machine. Last sync: 2026-10-10T15:15Z (Kilo).

## 1. LUKE IS NEVER PAUSED (founder order 2026-10-10)
- Luke (forge-ops / role `ops`) stays online 24/7 — including whenever "the team" is paused.
- Luke owns the workforce power switch: pause/resume all 13 officer cron jobs and the Hermes gateways
  on the founder's word, or on evidence of unnecessary token/Credit spend, runaway loops, or debug need —
  always keeping forge-ops itself alive.
- Luke is reachable from Telegram (and any channel the founder uses) for "how are we doing?", debriefs,
  milestone status, and power-switch commands.
- Pause procedure (what Kilo executed 2026-10-10T03:20Z): `hermes cron pause` ×13 jobs, then
  `systemctl stop forge-hermes forge-ops forge-eng`. NOTE: per founder order, future pauses keep
  forge-ops RUNNING. Resume: start gateways → `hermes cron resume` ×13 → verify `state=scheduled`
  + allow-gate `wake=true`.

## 2. FIRM SCHEDULE (business hours = Alibaba cheap window)
- Alibaba Token Plan Credits for qwen3.8-max are 60% cheaper **14:00–24:00 UTC (~10:00–20:00 US Eastern)**
  (off-peak per Alibaba docs; 40% off at other times). That window = **FIRM BUSINESS HOURS**: full team works.
- Outside business hours: only the **24/7 EARNER CREW** wakes — prediction (Kalshi events), execution
  (crypto microstructure), scout, doctor, governor, treasury, ops (Luke). Deep-work roles (alpha-inventor,
  adversary, critic, intelligence, rail-hunter, architect) skip at ZERO token cost and resume at window open.
- Venue hours: Coinbase crypto 24/7 · Kalshi event contracts 24/7 (sports, weather, econ, crypto) ·
  Alpaca US equities 24/5 (closed weekends, thin overnight). Never spend inference analyzing equity
  trades while the stock market is closed.
- Enforced deterministically in `runtime/hermes/home/scripts/forge_gate.py` (gate v2) — no tokens burned deciding.

## 3. MILESTONE LADDER (Constitution C3 §9 — immutable, all agents)
- Climb sustained TRUE-NET rate: **$0.25/h → $0.50/h → $0.75/h → $1.00/h → beyond.**
- On crossing a rung: FIRST name exactly what earned it (stream, edge, capital, regime), record as protected
  `what_is_working`, and DEFEND it. New algorithms are ADDITIVE — never cannibalize a proven earner.
- Losing a proven income stream = reportable regression.
- LIVE-money transition only at a sustained reconciled rung (first candidate ≥$0.25/h) AND explicit
  founder authorization via the confirmation gate. Founder intent: possibly this evening / tomorrow morning
  if ≥$0.25/h is being proven — evidence first.

## 4. PROTECT THE SECRET SAUCE (C3 §10)
- Moat = FORGE proprietary algorithms/models/allocator/execution edge. Never leak, log, echo or externalize
  proprietary edge internals or keys. Attribute every earned dollar to the mechanism that produced it.

## 5. CAPITAL SCALING (C3 §8, from 2026-10-09)
- FORGE is a rate engine: prove TRUE-NET $/capital-hour, the regime engine auto-scales positions/concurrency/
  research as treasury grows (SURVIVAL <$100 → GROWTH $100–500 → EXPANSION >$500). Founder plans deposits of
  $300–500 within weeks. New deposits must reach the proven frontier within one allocation cycle;
  idle proven capital = defect.

## 6. STATE AS OF THIS SYNC (2026-10-10T15:15Z)
- Team: all 15 agents live on Qwen3.8-Max (xhigh decision-makers / medium monitors), wake gate healthy
  (subscription mode — no DeepSeek-balance starvation). 13/13 briefs carry C3 + ladder + schedule doctrine.
- 16 durable genome-bound reports in first 45 min after upgrade; zero DeepSeek leakage in Hermes layer.
- Team already self-surfaced the blocker to deploying capital: peg ledger corruption (phantom deployed_usd
  surviving restarts, peg_mm telemetry resets fills 38→0, frozen USDT-USD mark) → Vale RISK_GATE FREEZE.
  NEXT ENGINEERING LEVER = FQ0 ledger truth, then deploy loop, then trustworthy measured $/h.
- Kalshi rail: PAPER_BLOCKED_NO_KEY — founder to supply API key via one-time credential portal when ready
  (24/7 event-contract income rail; playbook at /srv/forge/hermes/research/kalshi_playbook.md).
