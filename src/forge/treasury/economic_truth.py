"""One realized economic result for Luca, APIs, and velocity. Paper never becomes cash income."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def paper_realized_window(db: Any, since: float, now: float,
                          deployable: float | None = None) -> dict[str, Any]:
    """Measured PAPER realized rate — the scoreboard for the milestone ladder.

    Strictly separate from realized_window(): cash TRUE-NET stays live-only ("paper never becomes
    cash income"). This function measures what the paper book is actually earning so the team can
    climb $0.25/h → $0.50/h → $1.00/h on EVIDENCE rather than on model expectations.

    Sources (all real, all already recorded):
      * paper book closed positions: realized_pnl_usd − fees_usd
      * shadow round-trips by rail (stable_peg_mm, stable_triangle): fee-modelled pnl_usd
    Cost side deliberately excludes subscription-covered inference (marginal cash $0) and reports
    compute separately so the rate is not penalised by a fixed prepaid plan.
    """
    iso = datetime.fromtimestamp(since, UTC).isoformat()
    seconds = max(1.0, now - since)

    spot = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)),0) "
        "FROM positions WHERE book='paper' AND status='CLOSED' AND closed_at>=?", (iso,)) or 0)
    spot_fees = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(fees_usd AS REAL)),0) FROM positions "
        "WHERE book='paper' AND status='CLOSED' AND closed_at>=?", (iso,)) or 0)
    spot_n = int(db.scalar(
        "SELECT COUNT(*) FROM positions WHERE book='paper' AND status='CLOSED' AND closed_at>=?", (iso,)) or 0)

    shadow_rows = db.query(
        "SELECT rail, COUNT(*) n, COALESCE(SUM(CAST(pnl_usd AS REAL)),0) pnl, "
        "COALESCE(SUM(CAST(fee_usd AS REAL)),0) fees FROM shadow_trades WHERE ts>=? GROUP BY rail",
        (since,)) or []
    shadow = float(sum(float(r.get("pnl") or 0) for r in shadow_rows))
    shadow_fees = float(sum(float(r.get("fees") or 0) for r in shadow_rows))
    shadow_n = int(sum(int(r.get("n") or 0) for r in shadow_rows))
    by_rail = {str(r.get("rail")): {"n": int(r.get("n") or 0),
                                     "pnl_usd": round(float(r.get("pnl") or 0), 6),
                                     "fees_usd": round(float(r.get("fees") or 0), 6)}
               for r in shadow_rows}

    # Fee semantics differ per source, and getting this wrong double-counts:
    #   positions.realized_pnl_usd is GROSS (the live realized_window subtracts fees separately),
    #   so `spot` above is already net because the SELECT does realized - fees.
    #   shadow_trades.pnl_usd is ALREADY fee-net (pegmaker: pnl = (price*qty - fee) - avg*qty with
    #   the buy fee inside avg; triangle: pnl = edge*qty where edge nets both legs' fees), so its
    #   fee_usd column is informational and must never be subtracted a second time.
    net = spot + shadow
    fees_total = spot_fees + shadow_fees           # disclosure only; already netted out of `net`
    gross = net + fees_total                       # true gross = net + all fees paid
    compute = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(amount_usd AS REAL)),0) FROM ledger_entries "
        "WHERE account='OPEX:COMPUTE' AND ts>=?", (iso,)) or 0)

    # Deployed capital basis, so the rate can be expressed per capital-hour (RATE-THEN-SCALE).
    # The ledger ASSET total is authoritative for what is actually held.
    deployed = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(amount_usd AS REAL)),0) FROM ledger_entries "
        "WHERE account LIKE 'ASSET%' AND book='paper'") or 0)
    # CAPITAL-HOURS is the honest utilization measure for high-velocity earners. A market maker holding
    # inventory ~2s per round-trip has an instantaneous ASSET balance near zero while genuinely putting
    # capital to work continuously — reporting only the snapshot reads as "nothing is working" and hides
    # real income. capital_hours = sum(notional * hold_seconds/3600) over completed round-trips.
    capital_hours = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(qty AS REAL)*CAST(entry AS REAL)*COALESCE(CAST(hold_s AS REAL),0)/3600.0),0) "
        "FROM shadow_trades WHERE ts>=? AND rail IN "
        "('coinbase.stable_triangle','coinbase.stable_peg_mm')", (since,)) or 0)
    window_hours = seconds / 3600.0
    # deployable MUST come from the caller. Reading it back from the `velocity` KV would be a
    # circular dependency: compute() writes `velocity` and also calls this function, so this would
    # consume its own previous-cycle output. When that prior value was stale (regime latched to a
    # $25 reserve off the real wallet's peak, deployable $0.0896) the utilization ratio came out
    # as 28.95 — an impossible >100% figure. Deriving from the active book's own equity instead.
    if deployable is None:
        book = db.scalar("SELECT value FROM kv_state WHERE key='firm.book'") or "paper"
        deployable = float(db.scalar(
            "SELECT COALESCE(equity_usd,0) FROM equity_series WHERE book=? ORDER BY ts DESC LIMIT 1",
            (book,)) or 0.0)
    deployable = max(float(deployable or 0.0), 0.0)

    return {
        "basis": "paper_realized_less_fees; cash income remains live-only and is never implied here",
        "book": "paper",
        "net_usd": net,
        "gross_usd": gross,
        "fees_usd": fees_total,
        "fee_semantics": {
            "positions": "realized_pnl_usd is GROSS; net computed as realized - fees",
            "shadow_trades": "pnl_usd is ALREADY fee-net; fee_usd is informational (not re-subtracted)",
        },
        "usd_per_h": net / seconds * 3600.0,
        "usd_per_h_per_deployed": (net / seconds * 3600.0) / deployable if deployable > 0 else None,
        "positions_closed": spot_n,
        "shadow_round_trips": shadow_n,
        "by_rail": by_rail,
        "compute_cost_usd": compute,
        "net_usd_after_compute": net - compute,
        "usd_per_h_after_compute": (net - compute) / seconds * 3600.0,
        "deployable_usd": deployable,
        "deployed_usd": deployed,
        "capital_hours": round(capital_hours, 6),
        "capital_hours_utilization": (round(capital_hours / (deployable * window_hours), 6)
                                      if deployable > 0 and window_hours > 0 else None),
        "utilization_basis": ("instantaneous deployed_usd is a snapshot and is legitimately ~0 for "
                              "sub-minute earners; capital_hours_utilization is the honest measure of "
                              "capital put to work over the window. It is deliberately NOT clamped to 1.0: "
                              "a value above 1.0 means notional per round-trip exceeded deployable, which is "
                              "a genuine over-deployment risk signal (it is how the phantom $300-433/book "
                              "sizing against a $28 paper book was caught), not a metric error."),
        "seconds": seconds, "since": since, "ts": now,
    }


def realized_window(db: Any, since: float, now: float) -> dict[str, Any]:
    iso = datetime.fromtimestamp(since, UTC).isoformat()
    seconds = max(1., now - since)
    spot = float(db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)),0) "
                           "FROM positions WHERE book='live' AND status='CLOSED' AND closed_at>=?", (iso,)) or 0)
    kalshi = float(db.scalar("SELECT COALESCE(SUM(pnl),0) FROM kalshi_live_orders "
                             "WHERE status='SETTLED' AND settled_ts>=?", (since,)) or 0)
    costs = {r["account"]: float(r["cost"] or 0) for r in db.query(
        "SELECT account,SUM(CAST(amount_usd AS REAL)) cost FROM ledger_entries "
        "WHERE account LIKE 'OPEX:%' AND ts>=? GROUP BY account", (iso,))}
    # Historical Hermes costing incorrectly treated some paid DeepSeek usage as free credit.
    # Preserve immutable ledger history and disclose the missing usage estimate without counting it twice.
    unposted = float(db.scalar("SELECT COALESCE(SUM(CAST(i.cost_usd AS REAL)),0) FROM inference_calls i "
                               "WHERE i.ts>=? AND i.model LIKE 'deepseek%' AND NOT EXISTS "
                               "(SELECT 1 FROM ledger_entries l WHERE l.account='OPEX:INFERENCE' AND l.ref_id=i.id)",
                               (iso,)) or 0)
    costs["OPEX:INFERENCE"] = costs.get("OPEX:INFERENCE", 0.) + unposted
    # Verified reward counters: no APY projection substituted for paid income.
    current = db.kv_get("yield.usdc") or {}
    base = db.query_one("SELECT ts,rewards_usdc FROM velocity_history WHERE ts<=? ORDER BY ts DESC LIMIT 1",
                        (since,))
    reward_known = bool(base and base.get("rewards_usdc") is not None and current.get("rewards_usdc") is not None)
    idle = max(0., float(current.get("rewards_usdc", 0)) - float(base["rewards_usdc"])) if reward_known else 0.
    # FQ0 disclosure: some OPEX:INFERENCE rows were posted for subscription-covered (prepaid Token Plan)
    # usage whose true marginal cash cost is $0. Immutable ledger history is preserved — never rewritten —
    # so the distortion is disclosed and an explicitly-labelled adjusted figure is provided alongside.
    misposted = float(db.scalar(
        "SELECT COALESCE(SUM(CAST(l.amount_usd AS REAL)),0) FROM ledger_entries l "
        "WHERE l.account='OPEX:INFERENCE' AND l.ts>=? AND EXISTS "
        "(SELECT 1 FROM inference_calls i WHERE i.id=l.ref_id AND i.model NOT LIKE 'deepseek%')",
        (iso,)) or 0)
    inference = costs.get("OPEX:INFERENCE", 0.)
    compute = costs.get("OPEX:COMPUTE", 0.)
    data = costs.get("OPEX:DATA", 0.)
    total_cost = sum(costs.values())
    gross = spot + kalshi + idle
    net = gross - total_cost
    adj_net = net + misposted
    return {"net_usd": net, "true_net_usd": net, "usd_per_h": net / seconds * 3600,
            "usd_per_hour": net / seconds * 3600,
            "true_net_excl_misposted_subscription_inference_usd": adj_net,
            "usd_per_h_excl_misposted_subscription_inference": adj_net / seconds * 3600,
            "misposted_subscription_inference_usd": misposted,
            "settled_income_usd": gross,
            "kalshi": kalshi, "spot": spot, "idle_yield": idle,
            "intelligence": -inference, "compute": -compute, "data": -data,
            "operating_cost_usd": total_cost, "costs": costs,
            "basis": "settled_live_income_less_all_recorded_forge_operating_costs",
            "idle_reward_coverage": "verified_counter" if reward_known else "unavailable",
            "compute_cost_basis": "internal_estimate_pending_provider_reconciliation",
            "unposted_historical_inference_estimate_usd": unposted,
            "excluded": ["deposits", "paper_profit", "shadow_forecasts", "unrealized_marks"],
            "seconds": seconds, "since": since, "ts": now}
