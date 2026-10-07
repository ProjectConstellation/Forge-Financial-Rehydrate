# Answers → FORGE implementation map (3-pass analysis, 2026-10-07)
Source: `FORGE_20_STRATEGIC_ANSWERS_AND_ALGORITHM_UPGRADE_2026-10-07.md` (verbatim, sha256 in `FORGE_20_STRATEGIC_ANSWERS.sha256`).

## Pass 2 — mapping to existing code
| Recommendation | Status before | Action |
|---|---|---|
| P0.1 runtime fee query | EXISTS (transaction_summary at discovery, hourly) | keep; per-pair fees later |
| P0.2 Edge Coverage Ratio | NEW | gate in opportunity path: <1.5 reject, 1.5–2 paper-only, ≥2 live-eligible |
| P0.3 LRR / backtest haircut | partial (analyst 0.5×) | haircut prior H=0.25 on backtest-derived expectations until forward evidence |
| P0.4 contaminated holdouts | gap | 3-way split: selection 60% / validation 20% / sealed 20% (sealed = one-time final exam, recorded) |
| P0.5 Research Trial Ledger | gap | `research_trials` table, every adjudicated genome recorded (datasets/holdouts seen, revisions, origin) |
| P0.6 convex trend exits | partial (lock off) | `Convex Trend Exit V1` gene: catastrophe stop max(k_cat·ATR), arm trailing at MFE ≥ arm·ATR, chandelier k by vol regime, 24h no-progress time stop |
| P0.7 Bayesian fractional Kelly / risk-at-stop | Kelly×(0.15…1.0) notional | risk-at-stop sizing: per-position risk ≤ 5% equity, aggregate open risk ≤ 10%, ≤0.25 Kelly, calibration×robustness factors |
| P0.8 no fixed concurrency | DONE (economic) | aggregate-risk cap makes 1–2 positions natural at $28 |
| P0.9 calibration | EXISTS | keep |
| P0.10 wallet-truth | EXISTS (live recon, paper heal) | keep |
| P1 TPS / residual ranking / breadth | partial (rs_btc_48, breadth) | new causal features: `mkt_breadth_24h`, `mkt_trend_24h`, `resid_z_24`, `resid_z_72`, `ext_atr_ema20`; breadth exposure gate |
| P1 drawdown states / vol gate | gap | exposure multipliers: breadth tiers, vol>p90 halve, HWM −5/−10/−15% states |
| P1 Listing Sentinel | gap | product-universe diff every 60 s → timeline + event record (no blind buying) |
| P1 POFS, maker fill learner, panic absorb, ext derivatives | gap | queued (next tranche) |
| P2 Hypothesis Foundry | partial | scientist prompt upgraded: mechanism, falsification, novelty, bounded revisions, failure clusters; no sealed results exposed |
| P3 Kalshi | queued | after Coinbase production-ready |
| Coinbase One | n/a | config only: tier=none; never assume Advanced rebates |

## Pass 3 — conflicts & resolutions
1. **Sizing conflict:** answers say 0.10–0.25 Kelly; our Time Machine found top-3 elite + full Kelly best on unseen data (+22%).
   Resolution: adopt risk-at-stop sizing (5%/position, 10% aggregate) — for 6–15% stops this already deploys 33–80% of equity
   per position, i.e. similar exposure to the measured winner but bounded by risk rather than raw Kelly. Validate both in the
   Time Machine on unseen data; keep the one that wins.
2. **"50–70% minimum" vs answers' growth-rate warning:** answers (G.18) confirm no fixed daily/period return is sustainable; FORGE
   optimizes log-growth and reports decomposition (beta vs alpha). Keep the ambition; never force trades to meet a quota.
3. **Haircut 10–25%** vs elite ranking: ranking stays on selection; expected returns used for sizing get H=0.25 until forward
   evidence raises it.
