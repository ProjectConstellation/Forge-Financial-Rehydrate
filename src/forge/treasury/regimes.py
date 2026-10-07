"""Capital Regime Engine (OP-008).

Treasury size → a smooth, learnable policy surface. Anchors (SURVIVAL < $100 ≤ GROWTH < $500 ≤ EXPANSION)
are starting parameters; boundaries and per-parameter multipliers are stored in kv_state and can be
adjusted by the Strategist / meta-learning loop as drawdowns, costs and demonstrated performance evolve.
Policy values interpolate in log-equity space so there are no cliff edges between regimes.

Hard constraints that regimes can never relax: reserve fraction ∈ [5%, 20%] below $100 (RESOLUTIONS #4),
$25 hard floor at ≥ $100 (sticky), no leverage.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from forge.persistence.db import Database


@dataclass(frozen=True)
class RegimePolicy:
    name: str
    equity_usd: float
    reserve_fraction: float          # of equity, on top of hard floor
    reserve_floor_usd: float
    max_position_fraction: float     # of deployable capital per position
    max_concurrent_positions: int
    target_hold_hours: float         # preferred (not a cap): drives velocity hurdle
    hurdle_multiplier: float         # scales opportunity-cost rate (higher = prefer fast recycling)
    research_intensity: float        # multiplier on inference/compute spend rate
    min_liquidity_usd_24h: float
    min_strategy_diversity: int      # distinct families with capital
    max_family_fraction: float       # concentration cap per strategy family
    exploration_capital_fraction: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


ANCHORS: dict[str, dict[str, float]] = {
    "SURVIVAL": dict(reserve_fraction=0.10, max_position_fraction=0.60, max_concurrent_positions=2,
                     target_hold_hours=12, hurdle_multiplier=1.6, research_intensity=1.5,
                     min_liquidity_usd_24h=1_000_000, min_strategy_diversity=1, max_family_fraction=1.0,
                     exploration_capital_fraction=0.05),
    "GROWTH": dict(reserve_fraction=0.10, max_position_fraction=0.45, max_concurrent_positions=4,
                   target_hold_hours=36, hurdle_multiplier=1.2, research_intensity=1.25,
                   min_liquidity_usd_24h=2_000_000, min_strategy_diversity=2, max_family_fraction=0.7,
                   exploration_capital_fraction=0.08),
    "EXPANSION": dict(reserve_fraction=0.15, max_position_fraction=0.30, max_concurrent_positions=8,
                      target_hold_hours=120, hurdle_multiplier=1.0, research_intensity=1.0,
                      min_liquidity_usd_24h=5_000_000, min_strategy_diversity=3, max_family_fraction=0.5,
                      exploration_capital_fraction=0.10),
}
DEFAULT_BOUNDS = {"growth_at": 100.0, "expansion_at": 500.0}
INT_KEYS = {"max_concurrent_positions", "min_strategy_diversity"}


class CapitalRegimeEngine:
    def __init__(self, db: Database | None = None, hard_floor_usd: float = 25.0, floor_threshold_usd: float = 100.0) -> None:
        self.db = db
        self.hard_floor_usd = hard_floor_usd
        self.floor_threshold_usd = floor_threshold_usd

    # learnable state ------------------------------------------------------------------------------
    def bounds(self) -> dict[str, float]:
        b = dict(DEFAULT_BOUNDS)
        if self.db:
            b.update(self.db.kv_get("capital_regime.bounds", {}) or {})
        return b

    def multipliers(self) -> dict[str, float]:
        return (self.db.kv_get("capital_regime.multipliers", {}) or {}) if self.db else {}

    def adjust(self, key: str, multiplier: float, actor: str, reason: str) -> None:
        """Learned adjustment (bounded 0.5×–2×), recorded in config history."""
        if not self.db:
            return
        m = self.multipliers()
        m[key] = float(min(2.0, max(0.5, multiplier)))
        self.db.kv_set("capital_regime.multipliers", m)
        self.db.insert("config_history", {"ts": _now(), "actor": actor,
                                          "change": {"capital_regime_multiplier": {key: m[key]}, "reason": reason}})

    def floor_active(self, equity: float) -> bool:
        if equity >= self.floor_threshold_usd:
            if self.db and not self.db.kv_get("reserve.floor_activated", False):
                self.db.kv_set("reserve.floor_activated", True)     # sticky (RESOLUTIONS #4)
            return True
        return bool(self.db and self.db.kv_get("reserve.floor_activated", False))

    # policy ----------------------------------------------------------------------------------------
    def policy(self, equity_usd: float | Decimal) -> RegimePolicy:
        e = max(float(equity_usd), 0.01)
        b = self.bounds()
        g_at, x_at = b["growth_at"], b["expansion_at"]
        if e < g_at:
            name = "SURVIVAL"
            vals = dict(ANCHORS["SURVIVAL"])
        elif e < x_at:
            name = "GROWTH"
            t = (math.log(e) - math.log(g_at)) / (math.log(x_at) - math.log(g_at))   # 0→1 across GROWTH
            vals = {k: _lerp(ANCHORS["GROWTH"][k], ANCHORS["EXPANSION"][k], t) for k in ANCHORS["GROWTH"]}
        else:
            name = "EXPANSION"
            vals = dict(ANCHORS["EXPANSION"])
            decades = max(0.0, math.log10(e / x_at))
            vals["reserve_fraction"] = min(0.30, vals["reserve_fraction"] + 0.02 * decades)
            vals["max_concurrent_positions"] = min(40, int(vals["max_concurrent_positions"] * (1 + decades)))
            vals["target_hold_hours"] = vals["target_hold_hours"] * (1 + 0.5 * decades)
            vals["min_liquidity_usd_24h"] = vals["min_liquidity_usd_24h"] * (1 + decades * 2)
        for k, m in self.multipliers().items():
            if k in vals:
                vals[k] = vals[k] * m
        # hard constraints (never relaxed by learning)
        if name == "SURVIVAL" and not self.floor_active(e):
            vals["reserve_fraction"] = min(0.20, max(0.05, vals["reserve_fraction"]))
            floor = 0.0
        else:
            floor = self.hard_floor_usd if self.floor_active(e) else 0.0
        for k in INT_KEYS:
            vals[k] = int(max(1, round(vals[k])))
        vals["max_position_fraction"] = min(1.0, max(0.05, vals["max_position_fraction"]))
        return RegimePolicy(name=name, equity_usd=e, reserve_floor_usd=floor, **vals)  # type: ignore[arg-type]

    def reserve_usd(self, equity_usd: float, exceptional: bool = False) -> float:
        p = self.policy(equity_usd)
        frac = p.reserve_fraction
        if exceptional and p.name == "SURVIVAL" and not self.floor_active(equity_usd):
            frac = 0.05                                             # floor of the 5–20% band, never 0
        return max(p.reserve_floor_usd, equity_usd * frac)


def _lerp(a: float, b: float, t: float) -> float:
    t = min(1.0, max(0.0, t))
    return a + (b - a) * t


def _now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
