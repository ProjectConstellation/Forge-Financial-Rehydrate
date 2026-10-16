"""Persistent forward-only, local equity paper experiments. Never submits broker orders.

Completed daily IEX bars model next-open fills, with 20bps round-trip costs. This is
an independently capped simulation, not broker execution, live evidence or income.
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MECHANISMS = ("relative_momentum", "dip_reversion", "trend_following")


def signal(mechanism: str, history: list[tuple[dict, dict]]) -> bool:
    if len(history) < 21:
        return False
    close = [float(b[0]["c"]) for b in history]
    market = [float(b[1]["c"]) for b in history]
    if mechanism == "relative_momentum":
        return close[-1] / close[-21] - market[-1] / market[-21] > .01
    if mechanism == "dip_reversion":
        return close[-1] / close[-4] - 1 < -.02 and market[-1] > sum(market[-20:]) / 20
    if mechanism == "trend_following":
        return close[-1] > sum(close[-20:]) / 20 and market[-1] > sum(market[-20:]) / 20
    raise ValueError("unknown mechanism")


def new_trial(index: int, generation: int, after: str, allocation: float) -> dict:
    mechanism = MECHANISMS[index % len(MECHANISMS)]
    return {"id": f"equity-{index}-{generation}-{after}", "mechanism": mechanism,
            "generation": generation, "after": after, "state": "READY",
            "allocation_usd": allocation, "net_usd": 0., "trades": [], "position": None,
            "sessions": 0, "first_open": None, "last_close": None,
            "contract": {"signal_lookback_sessions": 20, "hold_sessions": 5,
                         "next_open_execution": True, "round_trip_cost_bps": 20,
                         "stop_close_return": -.05, "max_trial_loss_usd": allocation * .1,
                         "review_sessions": 20, "min_closed_trades": 3,
                         "selection": "net > 0 and net exceeds equal-capital buy-and-hold",
                         "live_promotion": False}}


def advance(state: dict | None, bars: list[dict], benchmark: list[dict], *,
            today: str, now: float, running: bool, bankroll: float,
            max_open: float, max_order: float) -> dict:
    """Replay new completed sessions only; registration excludes all historical bars.

    Allocation is frozen at registration, never inflated by broker fake equity or paper
    profits. Two disjoint slots share the open-exposure budget. No outcome changes on
    repeat invocation. New hypotheses start strictly after their preceding review.
    """
    limits = [bankroll, max_open, max_order]
    if not all(math.isfinite(v) and v > 0 for v in limits):
        raise ValueError("finite positive paper limits required")
    by_date = {str(b["t"])[:10]: b for b in benchmark}
    pairs = []
    for bar in sorted(bars, key=lambda b: str(b["t"])):
        date = str(bar["t"])[:10]
        market = by_date.get(date)
        if market is None or date >= today:
            continue
        values = [float(bar.get("o", 0)), float(bar.get("c", 0)), float(market.get("c", 0))]
        if all(math.isfinite(v) and v > 0 for v in values):
            pairs.append((bar, market))
    if state is None:
        allocation = min(bankroll * .2, max_open / 2, max_order)
        state = {"schema": 1, "mode": "LOCAL_FORWARD_PAPER", "registered_at": now,
                 "registered_after": today, "bankroll_usd": bankroll,
                 "trials": [new_trial(i, 1, today, allocation) for i in range(2)],
                 "history": [], "earned_usd": 0., "live_ready": False}
    state["checked_at"] = now
    state["blocked"] = None if running else "GLOBAL_TRADING_NOT_RUNNING"
    state["data_last"] = str(pairs[-1][0]["t"]) if pairs else None
    if sum(t["allocation_usd"] for t in state["trials"]) > min(max_open, bankroll):
        state["blocked"] = "EXPERIMENT_CAP_EXCEEDS_CURRENT_POLICY"
        return state
    if not running or len(pairs) < 21:
        state["blocked"] = state["blocked"] or "INSUFFICIENT_DATA"
        return state
    if (datetime.fromisoformat(today) - datetime.fromisoformat(str(pairs[-1][0]["t"])[:10])).days > 7:
        state["blocked"] = "STALE_MARKET_DATA"
        return state
    # Never retrospectively simulate sessions that occurred while explicitly stopped.
    paused_after = state.pop("paused_after", None)
    if paused_after:
        for trial in state["trials"]:
            trial["after"] = max(trial["after"], paused_after)
    for slot in range(len(state["trials"])):
        trial = state["trials"][slot]
        for i in range(21, len(pairs)):
            bar, _ = pairs[i]
            date = str(bar["t"])[:10]
            if date <= trial["after"]:
                continue
            # A discontinuity cannot be silently marked as a timely forward observation.
            if trial.get("last_session") and (datetime.fromisoformat(date) -
                    datetime.fromisoformat(trial["last_session"])).days > 7:
                trial["data_gap"] = True
            price = float(bar["o"])
            trial["state"] = "RUNNING"
            trial["sessions"] += 1
            trial["first_open"] = trial["first_open"] or price
            trial["last_close"] = float(bar["c"])
            position = trial["position"]
            if position:
                previous_close = float(pairs[i - 1][0]["c"])
                position["held_sessions"] += 1
                stop = previous_close / position["entry_price"] - 1 <= -.05
                if position["held_sessions"] >= 5 or stop or trial["sessions"] >= 20:
                    net = position["notional_usd"] * (price / position["entry_price"] - 1 - .002)
                    trial["trades"].append({**position, "exit_at": date, "exit_price": price,
                                            "net_usd": net, "exit_reason": "STOP" if stop else "TIME"})
                    trial["net_usd"] += net
                    trial["position"] = None
            realized_total = sum(t["net_usd"] for t in state["history"] + state["trials"])
            if (trial["position"] is None and trial["sessions"] < 20
                    and realized_total > -state["bankroll_usd"] * .1
                    and trial["net_usd"] > -trial["allocation_usd"] * .1
                    and signal(trial["mechanism"], pairs[:i])):
                # The signal uses only bars preceding this modeled next-open fill.
                trial["position"] = {"entry_at": date, "signal_at": str(pairs[i-1][0]["t"]),
                                     "entry_price": price, "notional_usd": trial["allocation_usd"],
                                     "held_sessions": 0}
            trial["after"] = date
            trial["last_session"] = date
            loss = trial["net_usd"] <= -trial["allocation_usd"] * .1
            if (trial["sessions"] >= 20 or loss) and trial["position"] is None:
                baseline = trial["allocation_usd"] * (price / trial["first_open"] - 1 - .002)
                keep = (not loss and not trial.get("data_gap") and len(trial["trades"]) >= 3
                        and trial["net_usd"] > max(0, baseline))
                trial.update(state="RETAINED" if keep else "RETIRED", measured_at=now,
                             benchmark_net_usd=baseline,
                             decision_reason="POSITIVE_AFTER_COST_AND_BASELINE" if keep else
                             "LOSS_LIMIT" if loss else "INSUFFICIENT_OR_NEGATIVE_FORWARD_EVIDENCE")
                state["history"].append(trial)
                # Retained hypotheses are continuously challenged in a NEW future block.
                index = MECHANISMS.index(trial["mechanism"]) + (0 if keep else 1)
                trial = new_trial(index, trial["generation"] + 1, date, trial["allocation_usd"])
                state["trials"][slot] = trial
    state["simulated_closed_net_usd"] = sum(t["net_usd"] for t in state["history"] + state["trials"])
    state["paper_balance_usd"] = state["bankroll_usd"] + state["simulated_closed_net_usd"]
    if state["simulated_closed_net_usd"] <= -state["bankroll_usd"] * .1:
        state["blocked"] = "SHARED_SIMULATION_LOSS_LIMIT"
    state["live_ready"] = False
    state["earned_usd"] = 0.
    state["limitations"] = ["IEX daily bar local simulation, not actual broker fills",
                            "next-open price modeled after session; gaps can exceed stop budget",
                            "20bps costs assumed; real execution needs spread, fees and reconciliation",
                            "one positive review window is not proof of a durable edge"]
    return state


async def run_once() -> dict[str, Any]:
    from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy, read_runtime_state
    from forge.venues.alpaca import AlpacaClient
    root = Path(os.environ.get("FORGE_HOME", "/srv/forge/var"))
    target = root / "alpaca_forward_trials.json"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "alpaca_forward_trials.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "ALREADY_RUNNING"}
        state = json.loads(target.read_text()) if target.exists() else None
        policy = PaperBankrollPolicy.from_env()
        client = AlpacaClient(paper=True)
        now = time.time()
        today = datetime.fromtimestamp(now, UTC).date().isoformat()
        trading = read_runtime_state("trading.state") or {}
        running = trading.get("state") == "RUNNING"
        try:
            qqq, spy = await asyncio.gather(client.bars("QQQ", limit=300), client.bars("SPY", limit=300))
            state = advance(state, qqq.get("bars") or [], spy.get("bars") or [],
                            today=today, now=now, running=running, bankroll=policy.bankroll_usd,
                            max_open=policy.max_open_usd, max_order=policy.max_per_order_usd)
            if not running:
                state["paused_after"] = today
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, indent=2) + "\n")
            os.replace(temporary, target)
            return {"status": "CHECKED", "mode": state["mode"], "blocked": state["blocked"],
                    "trials": [{k: t[k] for k in ("id", "mechanism", "state", "sessions", "net_usd")}
                               for t in state["trials"]], "earned_usd": 0}
        finally:
            await client.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_once())))
