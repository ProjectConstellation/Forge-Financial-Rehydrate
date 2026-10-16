"""Bounded, preregistered equity research. No orders, search sweep, or claimed earned cash."""
from __future__ import annotations

import math
from typing import Any


def evaluate_residual_momentum(bars: list[dict[str, Any]], benchmark: list[dict[str, Any]],
                               bankroll: float, round_trip_bps: float = 20.) -> dict[str, Any]:
    """Fixed 20-day relative momentum; next-open entry, five-session hold, nonoverlapping trades.

    Parameters are fixed before viewing the forward partition. The last 20% is untouched
    selection evidence; retraining on it requires a new forward period, never re-labeling.
    """
    by_date = {str(b["t"])[:10]: b for b in benchmark}
    pairs = [(b, by_date[str(b["t"])[:10]]) for b in sorted(bars, key=lambda x: str(x["t"]))
             if str(b["t"])[:10] in by_date]
    clean = []
    for b, market in pairs:
        values = [float(b.get("o", 0)), float(b.get("c", 0)), float(market.get("c", 0))]
        if all(math.isfinite(v) and v > 0 for v in values):
            clean.append((b, market))
    if len(clean) < 80 or bankroll <= 0:
        return {"status": "INSUFFICIENT_DATA", "n_bars": len(clean), "earned_usd": 0}
    split = int(len(clean) * .8)
    trades = []
    i = split
    while i + 6 < len(clean):
        b, market = clean[i]
        prev, previous_market = clean[i - 20]
        residual = float(b["c"]) / float(prev["c"]) - float(market["c"]) / float(previous_market["c"])
        if residual > .01:
            entry, exit_bar = clean[i + 1][0], clean[i + 6][0]
            net_return = float(exit_bar["o"]) / float(entry["o"]) - 1 - round_trip_bps / 10000
            size = bankroll * .2
            trades.append({"signal_at": b["t"], "entry_at": entry["t"], "exit_at": exit_bar["t"],
                           "notional_usd": size, "hypothetical_net_usd": size * net_return})
            i += 6
        else:
            i += 1
    net = sum(t["hypothetical_net_usd"] for t in trades)
    buy_hold = bankroll * .2 * (float(clean[-1][0]["o"]) / float(clean[split][0]["o"]) - 1 - round_trip_bps / 10000)
    return {"status": "RESEARCH_ONLY", "algorithm_version": "relative_momentum_fixed_v1",
            "data_first": clean[0][0]["t"], "data_last": clean[-1][0]["t"], "feed": "iex",
            "n_bars": len(clean), "forward_start": clean[split][0]["t"], "n_trades": len(trades),
            "hypothetical_net_usd": net, "earned_usd": 0., "round_trip_cost_bps": round_trip_bps,
            "trades": trades, "evidence_verdict": "INSUFFICIENT_INDEPENDENT_EVIDENCE",
            "benchmarks": {"cash_net_usd": 0., "equal_sized_buy_hold_net_usd": buy_hold},
            "decision": "REJECT_CURRENT_MECHANISM" if net <= 0 else "PENDING_INDEPENDENT_PROOF",
            "next_action": "autonomous_equity timer executes preregistered future paper blocks and rotates failed mechanisms",
            "limitations": ["historical simulation", "fixed conservative spread/slippage assumption",
                            "regulatory fees require current account schedule", "no guaranteed fills",
                            "not approved for allocation or live", "research bankroll is simulated"]}


async def run_curriculum(client: Any, policy: Any) -> dict[str, Any]:
    import asyncio
    import time
    results = await asyncio.gather(client.bars("QQQ", limit=300), client.bars("SPY", limit=300),
                                   client.asset("QQQ"), client.account(), return_exceptions=True)
    if any(isinstance(r, Exception) for r in results):
        return {"ts": time.time(), "status": "DATA_BLOCKED", "earned_usd": 0,
                "next_action": "verify historical data entitlement and account/asset status"}
    qqq, spy, asset, account = results
    evaluation = evaluate_residual_momentum(qqq.get("bars") or [], spy.get("bars") or [], policy.bankroll_usd)
    return {"ts": time.time(), "rail": "alpaca.equities.paper", "evaluation": evaluation,
            "capabilities": {k: asset.get(k) for k in ("tradable", "fractionable", "status", "attributes")},
            "account_constraints": {k: account.get(k) for k in ("trading_blocked", "account_blocked", "multiplier",
                                                                  "pattern_day_trader", "daytrade_count")},
            "training_nav_usd": policy.bankroll_usd, "live_ready": False,
            "training_note": "commission-free eligibility does not remove spread/slippage/regulatory fees or risk"}
