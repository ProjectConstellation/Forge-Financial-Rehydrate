# Research log (institutional memory; newest first)

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
