# Cross-portfolio paper learning and next-upgrade plan

Updated: 2026-10-09T01:59:50Z. Scope: private, founder-owned Imagine Forge used to earn for Northstar Imagine and fund its technologies. Forge is not being designed as a SaaS product. This note records the requested cross-portfolio paper-testing upgrade and the verified runtime snapshot. Paper results are simulated evidence, never revenue.

## Outcome contract

Pursue a consistent combined net-income run rate of at least $0.50/hour, with $1/hour as the primary target. These are outcome objectives, not a trade quota. Do not force orders or report virtual P&L as money earned. Count an earning only after venue settlement, independent book reconciliation, and attribution of fees, losses, compute/inference and other Forge operating costs. Keep every paper bankroll and ledger isolated by rail; paper capital must never move to a LIVE account. The global STOPPED state and per-venue risk controls continue to block new simulated or live entries as configured.

## Verified paper coverage at this checkpoint

| Rail / mechanism | Observed state | Interpretation / next evidence |
|---|---|---|
| Cross-rail strategy evolution | 240 EXPERIMENTAL, 54 SHADOW, 7 CHALLENGER strategies; 46,117 RETIRED | Broad hypothesis exploration is running. Counts are not independent profitable trials; measure each version on fresh forward outcomes and costs. |
| Coinbase crypto paper | 49 recorded positions, all CLOSED at the latest inspected view | No open position in that view. Keep the strategy/evolution stream active; require source freshness, realistic fees/fills and net settled outcomes. |
| Kalshi / cross-rail shadow | Recent signal stream included MAKE, MODEL_RAW, SETTLE_WINDOW, SURFACE_RV, TAKE and TAKE_THRESH; settlement-window signals included both open and settled observations | Shadow signals are not fills. Preserve signal-to-market, settlement and counterfactual provenance; distinguish expired, quoted, filled, settled, and net P&L. Kalshi real balance was $0 and global PAPER blocked live execution at the prior verified account snapshot. |
| Sports event paper desk | 12 OPEN virtual bets (NHL 1, EPL 7, MLS 4), 16 VOID in the inspected book; latest lab tick found 44 candidate edges and placed 0 because the 12-open cap was reached | Lane is active and capacity constrained, not idle. Await settlements and use fresh event/odds timestamps. Verify odds-key/config source mapping (`THE_ODDS_API_KEY` vs capability reporting `ODDS_API_KEY`) and expose stale-feed state; do not infer that the feed is absent solely from the mismatched capability flag. |
| Alpaca equity broker-paper | `forge-alpaca-broker.service` and `forge-equity-forward.timer` active; broker trial artifact refreshed at 01:59 UTC; forward-trial artifact present from 01:16 UTC; paper account reconciled at prior read | Session was closed in the prior broker snapshot; no paper fills/open positions or earnings were claimed. Local future-only equity trials are separate modeled experiments, not broker fills. Recheck account, session and outcomes on next run. |

Services `forge.service`, `forge-alpaca-broker.service`, `forge-equity-forward.timer` and `forge-continuity.timer` were ACTIVE at 2026-10-09T01:59:50Z. The above is a point-in-time operational snapshot, not a profitability finding. No LIVE enablement, funding or transfers occurred. Historical observations from other checkpoints must not be presented as current without a refresh.

## Required next-upgrade build

1. **Shared opportunity and health feed.** Normalize each rail's timestamped prices, events, candidate opportunities, account/session capability, quota/auth state, and freshness deadline. Every observation carries source, fetch time, event/market identity, strategy/version, and failure reason. Expired/stale input blocks new paper entries and appears as an explicit degraded state; no silent cache reuse.
2. **One auditable experiment lifecycle.** Record hypothesis and preregistered rule, code/config version, data cutoff, baseline/no-trade control, paper book and capital limit, candidates, simulated order lifecycle (queue, partials, cancels, slippage, fees), settlement source, open/closed state, and next decision. Preserve immutable raw receipts and idempotent event IDs. Group overlapping signals by market/time/event so correlated copies do not inflate sample counts.
3. **Parallel exploration with disciplined promotion.** Run many independent bounded paper tests across supported rails and strategy families. Use chronological forward windows, regime/event clusters, minimum evidence and uncertainty intervals. Retain incumbent and challenger; continue, mutate, or retire automatically from preregistered net-of-cost criteria. Every research result must lead to an auditable next experiment or a reasoned hold/retire result. Do not promote to LIVE automatically from paper success.
4. **Portfolio-level competition and limits.** Rank eligible opportunities using expected conservative net return after fees, uncertainty, capital lockup, liquidity/capacity, correlation and operational/API cost. Enforce per-rail paper bankrolls, max exposure and loss controls. Global risk STOPPED blocks new entries. Candidate scarcity is valid; do not fabricate trades to make dashboards look busy.
5. **Outcome-oriented team and inference budget.** Tie every research/inference job to a specific question, expected decision change, compute/API cost ceiling, deadline and result receipt. Cache reusable analysis, batch deterministic data work, and reserve expensive reasoning for consequential decisions. Stop or redesign repeated work that produces no new evidence. Grade roles on settled/reconciled economic contribution and useful risk reduction, not token volume or activity counts.
6. **Always-on portfolio scorecard.** Per rail and combined: last successful data time, last candidate, last simulated fill, last settlement, independent sample count, open exposure, gross/net realized and unrealized paper P&L, all-in cost, drawdown, error/cooldown, mode and reconciliation status. Display 1h/24h/7d views and target gap. Label paper, modeled, broker-paper and LIVE distinctly; only reconciled LIVE contributes actual earnings.
7. **Automatic recovery and learning.** Detect dead timers, stale sources, auth/quota errors, stuck open positions, missing settlement and corrupt reconciliation. Retry with bounded backoff; alert Luke with concise evidence and recovery action. Quarantine a broken rail without stopping independent healthy paper rails. Continuity notes must record changed files, behavior, evidence, risks, rollback and next owner.

## Acceptance criteria for the next upgrade

- Every enabled rail reports fresh/stale/blocked plus last-success and last-event timestamps; stale data cannot create a new simulated order.
- Several independently versioned hypotheses can run in parallel within explicit per-rail virtual capital, and no rail can borrow another rail's simulated funds.
- Every simulated order can be traced from source observation through fill model, fees, settlement and final net result; open/void/expired/settled states reconcile exactly.
- Baseline/no-trade comparisons and independent forward sample counts prevent duplicate signals or historical training data from masquerading as new evidence.
- Research completion automatically records continue/mutate/retire/hold and schedules the next eligible experiment without requiring a human to copy results between agents.
- Role and inference cost reports connect spend to experiments, decisions and subsequent outcomes; unproductive repeated jobs are throttled or redesigned.
- Global STOPPED and paper/live separation tests pass; zero LIVE orders are submitted by paper workflows.
- Combined scorecard calculates actual earnings separately from paper evidence and subtracts attributable Forge costs before measuring the $0.50/$1 per-hour goals.

## Rehydration instructions

Read this plan with `CURRENT_STATE.md`, `WORK_QUEUE.md`, `TEAM_ECONOMICS.md`, the latest broker execution delivery and the latest session journal. Then refresh live runtime data before acting. Start implementation by reconciling the odds-feed capability key mapping and defining the common experiment event/result contract; next build freshness-gated normalized opportunity intake and per-rail scorecards. Use the existing isolated Forge staging workflow, preserve unrelated projects and dirty work, and do not deploy from a stale checkout.
