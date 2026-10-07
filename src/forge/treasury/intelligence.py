"""Intelligence Treasury — autonomous compute ↔ money controller (OP-014/OP-015).

Intelligence (DeepSeek) is capital: it is spent to find money and is refilled by money. The controller sets the spend
PACE from three live inputs, with no human tuning:

  available   = balance − floor                                   (whatever credit exists right now is usable)
  runway_days = f(measured value-per-$):  unmeasured → 3 d;  value/$ ≥ 3 → 1.5 d (spend fast: it pays);
                                          value/$ < 1 (measured) → 7 d (conserve, still never zero)
  budget_24h  = available / runway_days  +  reinvest_share × max(0, realized net profit over 7 d) / 7

Spend is measured over a ROLLING 24 h window (no midnight bursts / dead zones). Throughput follows headroom:
cycle interval and the number of deep research sessions per cycle scale with budget headroom, so a deposit (detected
by the Balance Sentinel within ≤ 5 min) immediately WAKES the brain and raises its pace; earnings do the same.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class Pace:
    available_usd: float
    runway_days: float
    budget_24h: float
    spent_24h: float
    headroom: float
    cycle_s: float
    deep_sessions: int
    reason: str


def runway_for(value_per_usd: float, measured: bool) -> float:
    if not measured:
        return 3.0
    if value_per_usd >= 3.0:
        return 1.5
    if value_per_usd >= 1.5:
        return 2.5
    if value_per_usd >= 1.0:
        return 4.0
    return 7.0


def pace(balance: float | None, floor: float, value_per_usd: float, measured: bool, spent_24h: float,
         profit_7d: float, reinvest_share: float, deep_cost: float = 0.03) -> Pace:
    avail = max(0.0, (balance or 0.0) - floor)
    rw = runway_for(value_per_usd, measured)
    budget = avail / rw + reinvest_share * max(0.0, profit_7d) / 7.0
    head = budget - spent_24h
    frac = head / budget if budget > 0 else 0.0
    # more headroom → think more often and run more deep sessions (bounded by what the headroom can actually buy)
    cycle_s = 300.0 if frac > 0.6 else 600.0 if frac > 0.3 else 1200.0 if frac > 0.05 else 2700.0
    sessions = int(max(0, min(4, math.floor(max(head, 0.0) / max(deep_cost * 2, 1e-6)))))
    why = (f"avail ${avail:.2f} / runway {rw:.1f}d (value/$ {value_per_usd:.2f}{'' if measured else ' prior'}) "
           f"+ reinvest {reinvest_share:.0%} of 7d profit ${profit_7d:.2f} → ${budget:.2f}/24h; spent ${spent_24h:.2f}")
    return Pace(avail, rw, budget, spent_24h, head, cycle_s, sessions, why)


def spent_24h(db: Any) -> float:
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()       # ISO vs ISO
    return float(db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls WHERE ts >= ?",
                           (cutoff,)) or 0.0)


def profit_7d(db: Any) -> float:
    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    pos = float(db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) FROM positions "
                          "WHERE status='CLOSED' AND closed_at >= ?", (cutoff,)) or 0.0)
    return pos


class WakeSignal:
    """Set by the Balance Sentinel on a top-up (or by earnings); the brain loop sleeps on it instead of a fixed timer."""

    def __init__(self) -> None:
        self.ev = asyncio.Event()

    def wake(self) -> None:
        self.ev.set()

    async def sleep(self, seconds: float) -> bool:
        try:
            await asyncio.wait_for(self.ev.wait(), timeout=seconds)
            return True
        except TimeoutError:
            return False
        finally:
            self.ev.clear()
