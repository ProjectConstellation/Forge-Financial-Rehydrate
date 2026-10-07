# Research log (institutional memory; newest first)

## 2026-10-07 (night) — Data integrity root cause, clean-data results, first cross-rail evidence
- ROOT CAUSE: CandleStore.merge sorted kept rows by ROW POSITION, not time → after the 365 d backfill 66 history files were
  time-scrambled (HYPE 5m: first 2026-08-07, last 2026-02-05). Effects: stale "latest" bars, quarantine/repair loops, negative
  forward hold times, validation splits on the wrong periods. Found by Hermes Doctor + Critic (HIGH RISK) within 1 h of
  launch. Fixed (sort by ts + defensive sorted load), files re-sorted, 9 strategies demoted to re-validate.
- Clean-data evolution (5m, 90 d window): 38,316 genomes → 20 passed validation AND the one-time sealed exam
  (sealed net +1.5…+2.9 %/trade after fees, n 114–164, P 0.92–0.98) — all breakout family, BETA sleeve (alpha P 0.16–0.52).
  Diversity cap keeps 6 in SHADOW. Not live: forward evidence must confirm (arena → CHALLENGER → readiness).
- Kalshi cross-rail (738 settled calibration samples): model Brier 0.1564 vs market 0.1513 → model WORSE than market; the
  stacked calibrator correctly cut model weight to 4.5 %. MAKE quotes −16¢/contract (adverse selection), MODEL_RAW −3¢.
  SURFACE_RV (model-free strike-surface relative value) +7.5¢/contract, ROI +37 %, n=40, bootstrap P(mean>0)=0.86 —
  promising, NOT yet significant. RTI proxy: Coinbase vs CF settlement 0.5–3 bp (crypto), PAXG–gold basis 17.8 bp.
- Live money: idle cash → USDC rewards (Coinbase One 3.75 % APY): $23.27 converted (fee 0), $5 USD buffer (OP-019).

## 2026-10-07 — Answers tranche A/B (Time Machine, 9 validated 5m strategies, 62 markets, sel 42d / unseen 18d)
- Sizing: risk-at-stop (5%/10% and 3%/8%) produced IDENTICAL results to Kelly-elite — both bind on the 50% max-fraction cap because
  5m stops are tight (risk/stop ≫ equity). At $28, risk-at-stop is a safety cap, not the active constraint → adopted as a cap
  (aggregate open risk ≤ 10%), Kelly-elite stays the sizing engine.
- Convex Trend Exit V1 with raw 5m ATR: **−92%** (2.5·ATR₅ₘ ≈ 1.2% stop < 1.4% round-trip fee → every trade bleeds). Fixed by
  hour-equivalent ATR (×√(3600/interval)). Even fixed, convex exits were worse than the evolved time-stop exits on BOTH windows
  (all-strategies: −86%/−15% vs −53%/+49%; holds 41h vs 84h — chandelier cuts the multi-day winners that carry expectancy).
  → Convex stays an evolvable gene, default OFF; evolution must earn it on validation + sealed data.
- WARNING: the validated set lost −33…−53% (max DD −70…−75%) over the earlier 42-day window and won +28…+49% on the latest 18 days;
  the same configuration moved by 20 points between two runs minutes apart (new bars shift every window) → returns are
  path-dependent and dominated by market beta. This is why the haircut (H=0.25), ECR ≥ 2 for live, sealed exams and drawdown
  states are now mandatory before real capital scales.
- Elite ranking in the Time Machine filters on holdout_return > 0 → that is holdout contamination; flagged for the
  sealed-window redesign (ranking must use selection only; validation is a gate, not a selector).

## 2026-10-06 — First evolutionary runs (25→60 USD markets; 1h×365d and 5m×60d; Intro fees 0.50/0.90%)
- Seeds on 5m: all net-negative; several have real GROSS edge (panic-wick +1.14%/trade, relative-strength +0.31%, vol-expansion +0.30%)
  that fees (~1.0–1.4% round trip) consume. 5m ATR stops (0.5–1%) are tighter than fees → horizon/barrier mutation needed.
- Bug found by diagnostics: ATR double-normalized in simulator (fixed). Diagnostics-first discipline pays.
- 1h search, 3,210 genomes: nothing passes holdout. Selection "best" (P=0.99, +2.3%/trade, n=24) lost −1.9%/trade on holdout → overfit caught.
- 5m search, 1,810 genomes: lineage momentum+breakout+trend_pullback reached holdout n=155, +3.03%/trade net, P=1.00, robust 1.00 — but random
  90h long holds earned +5.2% gross in the same window (BTC +24.6% over the selection period): it was market BETA, not alpha. Deflated Sharpe
  0.29 rejected it.
- LESSON → code: evaluator now measures alpha vs equal-weighted market drift over each trade's exact window; promotion requires
  P(alpha>0) ≥ 0.60 in addition to P(net>0) ≥ 0.90; fitness rewards alpha. Fitness min trades raised to 40.
- Implication: in a rising market, long beta *does* earn; FORGE may run an explicit, labeled "beta/trend-capture" sleeve whose job is to
  hold the market in up-regimes and exit in down-regimes — judged on regime timing vs buy-and-hold, not confused with alpha.

## 2026-10-07 — Why "+71%" and how to keep more of it (Time Machine)
- Selection window: equal-weight 60-coin index **+58%**, BTC +25%; portfolio +63% with beta 0.76 / corr 0.87 → mostly market rally + selection bias.
- Unseen window: index +32%, portfolio only **+2%**; every single strategy alone was positive (+3% … +34%) → portfolio construction was the leak.
- Deployment experiment (chosen on selection, judged unseen): top-3 strategies + full Kelly → **+22.0% unseen, PF 2.58, maxDD −10.2%**
  (vs +2.0% current). Over-aggressive (100%/pos) collapses. → Elite allocation adopted (hourly re-ranked by the Time Machine).
- Early profit locks: −20% vs +31% stops-only (unseen) → lock is an evolvable gene, default OFF.
- Simple market-trend entry filters did NOT generalize (selected thresholds gave +0.4…+8.8% unseen).
