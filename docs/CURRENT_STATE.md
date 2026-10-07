# CURRENT STATE — 2026-10-07 (read AGENTS.md → OPERATOR_POLICY → this → BUILD_STATUS)
- Founder portal LIVE: https://forge.northstarimagine.com (tunnel service `forge-tunnel`, config /etc/forge/tunnel/). Real-time SSE /api/live (1 s snapshots).
- `forge.service` (systemd, user forge) RUNNING in **PAPER** mode on live Coinbase data; FORGE_HOME=/srv/forge/var; API 127.0.0.1:8470.
- Paper treasury $28.27 mirrors the live USD balance. LIVE disabled until `forge readiness` green (needs ≥1 CHALLENGER).
- Improvement Loop: alternating 5m/1h evolution; Modal bursts (8×2 CPU) while budget GREEN and no validated edge.
- Supervision: 15 loops with heartbeats + auto-restart; systemd Type=notify WatchdogSec=180.
- Brain: Flash perception every 10–15 min; budget scales with measured ROI and earnings (OP-010); Pro (high) research every 3h or on escalation; Pro (max) on critical events.
- Key research lessons: docs/RESEARCH_LOG.md. Decisions: docs/DECISIONS.md. Incidents: docs/INCIDENTS.md.
- Dev: tests `.venv/bin/pytest`; dev home `.devvar/`; deploy Modal `scripts/deploy-modal.sh`; restart `sudo systemctl restart forge`.
- Open operator actions: rotate keys; top up DeepSeek (~$1.88 left); optional FORGE portfolio; domain for public dashboard.

## 2026-10-07 02:05 UTC update
- Portal v3 (money counter, Live Systems board, forging-money logo) at https://forge.northstarimagine.com — real-time SSE.
- Universe 60 live markets (WS + bars). 9 validated (beta-sleeve breakout) strategies paper-trading; first paper positions opened (QNT-USD).
- Live Strategy Analyst (60 s): CUSUM decay vs evidence → THRIVING/ON_TRACK/DRIFTING/FAILING; cut + succession + DeepSeek rebuild/repair/amplify.
- Portfolio: one position per market, 6 concurrent (SURVIVAL), family diversity cap 6, profit lock on every position.
- Fixed: ISO timestamp window comparisons (earnings windows were inflated); JS global `history` redeclaration (portal blank).
- Next upgrades (planned): meta-label filter (calibrated logistic on counterfactual data), data-driven beta kill switch from paper
  exploration, Thompson-sampling capital allocator, consensus boosting, maker repricing/execution alpha, Kalshi rail.

## 2026-10-07 04:00 UTC update (answers tranche + OP-013)
- Shipped: Convex Exit gene (default OFF, measured worse), ECR gate, haircut H=0.25, sealed exam window + Research Trial Ledger,
  risk-at-stop cap, breadth/vol/drawdown exposure states, WS L2 sharding (60/60 books), genome schema-drift self-repair
  (evolution had been failing every cycle 02:09–03:53 — fixed), OP-013 Opportunity Surface Registry + allocator, Listing
  Sentinel, Kalshi cross-rail engine (probability stack + stacked calibrator + maker shadow), /api/surface.
- Real money: $28.27 USD, PAPER mode, 0 closed positions. Live blocked by readiness gate (correctly: validated set lost
  −33…−53% on the earlier 42-day window).
- Rails: spot SHADOW(executable) · Kalshi SHADOW (no key/funding) · equities CANDIDATE (eligibility+fees unverified) ·
  futures DATA_ONLY (no CFM acct, leverage policy) · Coinbase prediction UNAVAILABLE (API 500) · USDC rewards CANDIDATE ·
  CDP onchain/staking BLOCKED · x402 CANDIDATE.
- Next: settle ≥ 300 Kalshi calibration samples (hourly contracts settle every hour) → refit stacked calibrator → decide
  Kalshi funding on evidence; equity T-bill (SGOV) idle rail once eligibility verified; barrier model for MAX/MIN series;
  portal panel for /api/surface.
