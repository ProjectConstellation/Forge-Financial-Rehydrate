# 20 Strategic Answers (Probability Alpha) — 3-pass analysis & build plan (2026-10-07 16:00 UTC)
Source: `FORGE_20_STRATEGIC_RESEARCH_ANSWERS_PROBABILITY_ALPHA_2026-10-07.md` (paste batch-20261007T154801Z-6928c1,
sha256 a95e9950…, 2,193 lines, read in full). Verbatim copy read-only beside this file.

## Pass 1 — what the answers say
Priority: (1) TAKE_THRESH with exact-settlement modelling + stale-quote detection, (2) settlement-source lead/lag,
(3) constraint probability surface (watcher), (4) scheduled-event engines (macro, commodities), (5) cross-rail information
(perp basis/funding/OI, PAXG, DVOL), (6) stablecoins = idle scavenger only, (7) spot trend = slower incumbent, (8) maker OFF.
Meta-algorithms: SAGE (edge × confidence × urgency × velocity score), VELA (log-growth per capital-hour allocator with CVaR
and correlation), DARWIN (contextual Thompson-sampling strategy ecology). Launch: 1-contract TAKE_THRESH, $1/h soft and
$3/day hard loss stops, Bayesian sequential scale ladder, CUSUM live-vs-shadow monitor. KPI: true net log growth per
capital-hour.

## Pass 2 — verified facts + mapping onto FORGE
| Recommendation | Verified / FORGE status | Action |
|---|---|---|
| Kalshi passes CF Benchmarks data through its API | **VERIFIED**: docs "CF Benchmarks REST Passthrough" (needs Kalshi credentials) | P0: settlement-source client (replaces Coinbase proxy; proxy stays as fallback + lead feature) |
| Exact integer-contract fee incl. cent rounding | EXISTS (`kalshi_fee`, FCM cent rounding) | per-series fee_type/multiplier already applied; add per-order (n) rounding |
| TAKE_THRESH broadened (ask 0.35–0.82, z band, time bands, spread ≤4¢, depth) | V1 pre-registered (0.40–0.80) | keep V1 sealed; register **TAKE_THRESH_V2** (answers' priors) as a separate comparator — no editing a live test |
| Final-60-s settlement-path model P(A60>K) | Missing (we use τ_eff = τ − ⅔·60 s) | P1: Path Mode when |z|<0.5 and < 5 min, using CF 1-s values |
| Hierarchical residual calibrator + online EKF + edge-decay detector | Stacked logistic (batch, market prior) | P1: add series random effects, quote age, return-since-last-Kalshi-move, spread, depth; sequential update with discount Q≈0.998; log-score decay monitor |
| Stale-quote repricing hazard (Coinbase → Kalshi) | Lead/lag ticks + edge half-life exist; Kalshi polled 15–60 s | P1 after key: Kalshi WebSocket book; trigger log incl. untraded; hazard fit |
| MAKE off by default | MAKE −4.75¢ shadow | Keep shadow recording, never live until markouts ≥ 0 over 100 fills |
| Constraint surface (QP projection) | SURFACE_RV (isotonic) — negative; arbs never seen | Watcher only (low priority) |
| Discrete correlated Kelly with p_eff = p_mkt + κ(p_LCB − p_mkt), κ=0.75, 0.20 Kelly, ruin P(W<½W)<1% | `binary_kelly` single-contract | P1: integer enumeration 1–5 contracts, same-underlying cluster caps |
| VELA / DARWIN allocator | velocity hurdle (now utilization-aware), Opportunity Surface allocator | P2: VELA scoring for Kalshi + spot in one queue; DARWIN = posterior per strategy×context |
| Discovery: hierarchical Bayesian slices + BH-FDR q=0.02 + sealed streams; promotion ladder 10 → 25 → 50 sealed | ad-hoc slicing → pre-registration | P2: automated slice cube + auto pre-registration with hash |
| Launch protocol + CUSUM (k=1¢, h=8¢) + scale ladder (10/20/40 trades; P 0.90/0.95/0.99) | — | P0 inside the Kalshi live adapter |
| Data: Bybit funding, Deribit DVOL, BLS, NWS, EIA | none yet | P2 (public, free) |
| Equities: info source first; execution later | visible, eligibility unknown | data-only for now (answers agree) |
| Hermes cadence (Governor 15–30 min, Inventor/Adversary hourly, Critic 2–4 h, Rail Hunter 3 h, Architect 6 h) | Opus cadence ≈ this | align Governor to 30 min; add hypothesis-ID/kill-criterion fields to inventor output schema (genome v2 via Architect) |

## Pass 3 — conflicts & resolutions
1. **Live bar:** my pre-registration said n ≥ 150, P ≥ 0.90; the answers propose micro-live after 10–20 sealed outcomes
   (P > 0.90–0.95, mean > 2¢) at 1 contract with hard loss stops. Resolution: adopt the answers' ladder for 1-contract
   size only (risk ≤ $3/day); scaling still requires 20/40 sealed trades and P 0.95/0.99 (both documents agree there).
2. **Don't edit live tests:** V2 filters are registered as a new kind; V1 continues untouched.
3. **Prerequisites outside FORGE's control:** Kalshi API key (trade + read; also unlocks CF passthrough + WebSocket) and
   ~$15 funding. Until then: shadow + CF-less model.
4. **Server migration** in progress (dedicated 4 vCPU / 8 GB): build on the current server, ship with the migration.

## Build order (P0 → P1, next 8 h)
P0: Kalshi signed client (Ed25519/RSA-PSS) · balance/positions/orders/fills/settlements · exact per-order fee · live gate
(TAKE_THRESH V1 sealed ladder) · loss stops ($1/h soft, $3/day hard) · CUSUM monitor · wallet reconciliation ·
edge-retention telemetry · CF passthrough client · TAKE_THRESH_V2 registration.
P1: settlement Path Mode · hierarchical online calibrator · stale-quote trigger log + Kalshi WS · correlated discrete Kelly.
