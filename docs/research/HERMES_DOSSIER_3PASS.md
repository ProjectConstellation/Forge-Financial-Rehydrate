# Hermes + Prediction-Alpha Dossier — 3-pass analysis (2026-10-07)
Source: `FORGE_HERMES_PREDICTION_ALPHA_DOSSIER.md` (paste batch-20261007T042639Z-20522c; identical to …042520Z-6affd8;
sha256 `ea997f9e…d9581`, 961 lines). Verbatim copy read-only beside this file.

## Pass 1 — what it claims (faithful reading)
- Hermes = 24/7 "Economic Governor" ABOVE FORGE (research director, scheduler, skills, specialists), never in the order path;
  project-isolated HERMES_HOME under /srv/forge; project plugin `hermes-forge` with read tools → research tools → gated
  `forge_request_trade` (requests, re-checked by the Risk Governor). Lean roster (Governor, Quant Scientist, Critic, Scout,
  Ops Doctor), added only when attribution proves value. Script-only cron where no LLM is needed.
- Prediction alpha (inspired by an UNVERIFIED viral "$68 → $6,732" screenshot — dossier itself says not to trust the P&L):
  FSPA ensemble fair probability; implied probability-surface arbitrage; cross-rail lead/lag graph; edge half-life execution;
  capital-velocity sequencing. Phases A–D with readiness gates. Realism rule: no guaranteed hourly profit.

## Pass 2 — verification + mapping to what FORGE already runs
| Dossier item | Verified fact / FORGE status | Verdict |
|---|---|---|
| Hermes latest = v0.21.3 (2026-09-14) | STALE: v0.21.5 (2026-09-24) is latest; MIT; DeepSeek supported natively (`provider: deepseek`); cron (incl. no-agent script mode, cron_mode=deny default for dangerous cmds), delegation/batch subagents, plugins, goals, bot-mode docs exist | facts OK, version outdated |
| Kalshi = API rail behind Coinbase prediction markets | Verified; Coinbase Advanced API `PREDICTION_MARKET` returns HTTP 500 → Kalshi API is the path | ✔ already built (read-only) |
| BTC/ETH contracts settle on CF Benchmarks RTI, 60 s average | Consistent with Kalshi series metadata ("CF Benchmarks"); real-time RTI is a LICENSED feed (public endpoint rejects ids) | use Coinbase + public constituent-exchange proxy; license only if IVOI proves it |
| FSPA fair-probability ensemble | EXISTS as `opportunities/probability.py`: HAR-RV + GK + term structure + seasonality + FHS + 60 s averaging + Bayesian stacking vs market (LCB trading) | extend with order-flow & cross-rail components (inputs FORGE already streams) |
| Implied probability surface arbitrage | PARTIAL: ladder monotonicity + range-sum arbs exist; missing: isotonic/smoothed market CDF, per-strike SURFACE_RESIDUAL, curvature/stale-strike detection | BUILD (high value, cheap, deterministic) |
| Cross-rail lead/lag graph | MISSING. FORGE has Coinbase WS ms timestamps; Kalshi odds polled 15–60 s (WS needs a Kalshi key) | BUILD lagged-correlation/event-response estimator on data already captured; true lead/lag at second scale requires Kalshi WS |
| Edge half-life engine | MISSING for event contracts (spot has OHL concept only) | BUILD from shadow signals: track edge vs delay after first sighting |
| Capital-velocity sequencing | EXISTS (velocity engine, hurdle pricing, surface allocator score/day) | extend to event contracts (settlement time in score) |
| Strategy evolution lineage, sealed exams, trial ledger | EXISTS (P0.4/P0.5 shipped today) | ✔ |
| Intelligence attribution ledger / VOI routing | EXISTS (intel_artifacts, ROI-adaptive Intelligence Treasury OP-015) | Hermes spend must go through it |
| Self-healing L1/L2/L3 | L1 + L3 EXIST; L2 (LLM diagnosis of repeated failures) partial (diagnostician role) | Hermes Ops Doctor could own L2 — only after cost case |
| Hermes Economic Governor (24/7) | Overlaps FORGE brain (perception/scientist/diagnostician), supervisor, Improvement loop | NOT a duplicate if scoped to: web research, contract-rule parsing, operator comms, `/goal` research programs |

## Pass 3 — conflicts, risks, economics → resolution
1. **Budget reality.** DeepSeek credit ≈ $1.8; a Governor on Flash with cron + heartbeat + subagents can spend more per day than
   FORGE's whole intelligence pace ($0.57/24 h). → Hermes LLM work must draw from the SAME Intelligence Treasury budget
   (no second wallet), script-only cron by default, LLM only on events. Roster = Governor + Scout first.
2. **Security.** Hermes is a shell-capable agent that ingests web content (prompt injection) and is a fast-moving dependency
   (1,610 commits in one release window). → own service user (`forge-hermes`), no read access to /etc/forge, no trading
   keys, no DB writes; FORGE exposes an MCP/HTTP tool surface on 127.0.0.1 with per-tool allowlist + rate limits;
   cron_mode=deny; pinned release tag, upgrades reviewed. Satisfies AGENTS.md boundary (only /srv/forge).
3. **"Exponential" claim.** Earnings scale with validated edge × capital × velocity; agents add hypotheses, not evidence.
   The binding constraint today is evidence time (hourly settlements, forward trades), not idea volume (Modal already
   evaluates thousands of genomes/cycle). → Hermes value must be measured (attribution); start minimal.
4. **Highest-ROI parts need no Hermes:** surface residual/arb engine, lead/lag estimator, edge half-life, order-flow
   features in the stacked calibrator — deterministic code on data FORGE already has. Build these FIRST.
5. **CF Benchmarks.** Licensed real-time data; FORGE proxies RTI from Coinbase (+ optional public constituent exchanges).
   Proxy error is measured against Kalshi settlement values (`expiration_value`) — buy the license only if IVOI ≥ 1.5.
6. **Phase D (gated trade requests)** stays behind the existing readiness gate + Kalshi credentials + funding authorization.

## Build order (recommended)
1. Deterministic prediction alpha: probability-surface engine (isotonic market CDF, residuals, stale strikes), lead/lag
   estimator, edge-half-life tracker, order-flow features into stacking, RTI-proxy error vs settlement values.
2. FORGE tool surface (`/api/agent/*`, read-only, localhost, token) — useful to Hermes AND to FORGE's own brain.
3. Hermes Phase A, minimal: pinned v0.21.5, `forge-hermes` user, HERMES_HOME=/srv/forge/runtime/hermes, DeepSeek via the
   Intelligence Treasury, Scout cron (script-only docs/listings/rules diff; LLM only on change), daily operator report.
4. Measure 7 days of attribution → add Quant Scientist / Critic / Ops Doctor only where value/$ ≥ 1.5.
