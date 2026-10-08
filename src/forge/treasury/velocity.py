"""Capital Velocity Score + Opportunity Cost Engine (OP-008).

Core idea: capital has a *time price*. Let h = hurdle rate (expected net return per capital-hour that
FORGE's opportunity set can currently deliver). An opportunity that locks capital C for T hours
must beat the value that capital would otherwise earn:

    opportunity_cost      = C · h · T · utilization_pressure
    velocity-adjusted EV  = C · E[r_net] − opportunity_cost
    velocity (per hour)   = E[log(1 + r_net)] / (T + t_liquidity)

h is *learned* (EWMA of realized and shadow-expected net yield per capital-hour) and scaled by the
capital regime's hurdle multiplier (SURVIVAL prefers fast recycling). Utilization pressure measures
whether capital is actually scarce: if plenty is idle and nothing better is queued, locking it costs
little — so exceptional long-duration opportunities are never rejected by rule, only priced.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from forge.persistence.db import Database

DEFAULT_HURDLE_PER_HOUR = 0.0004      # 0.04%/h ≈ 1%/day prior; replaced by learned rate as evidence accrues


@dataclass(frozen=True)
class VelocityAssessment:
    expected_return: float            # E[r_net] per unit capital
    expected_hold_h: float
    velocity_per_h: float             # E[log(1+r)] / (T + t_liq)
    velocity_per_day: float
    hurdle_per_h: float
    opportunity_cost_frac: float      # h·T·pressure, as fraction of capital
    adjusted_return: float            # E[r] − opportunity cost (per unit capital)
    capital_velocity_score: float     # normalized 0..1 for ranking/allocation
    rationale: str


class OpportunityCostEngine:
    """Learns the hurdle rate h from realized + shadow outcomes; persists across restarts."""

    KEY = "velocity.hurdle"

    def __init__(self, db: Database | None = None, halflife_obs: float = 50.0) -> None:
        self.db = db
        self.alpha = 1 - 0.5 ** (1 / halflife_obs)
        st = (db.kv_get(self.KEY) if db else None) or {}
        self.rate = float(st.get("rate", DEFAULT_HURDLE_PER_HOUR))
        self.n = int(st.get("n", 0))

    def observe(self, net_return: float, hold_hours: float, weight: float = 1.0) -> None:
        """Feed realized trades (weight 1) and shadow/expected outcomes (weight < 1)."""
        if hold_hours <= 0:
            return
        r = max(-0.5, min(0.5, net_return)) / max(hold_hours, 0.25)
        a = self.alpha * weight
        # only positive-yield deployments define the *alternative* use of capital
        self.rate = (1 - a) * self.rate + a * max(r, 0.0)
        self.n += 1
        if self.db and self.n % 10 == 0:
            self.db.kv_set(self.KEY, {"rate": self.rate, "n": self.n})

    def hurdle(self, regime_multiplier: float = 1.0) -> float:
        prior_w = 1.0 / (1.0 + self.n / 30.0)        # shrink toward prior until evidence accumulates
        h = prior_w * DEFAULT_HURDLE_PER_HOUR + (1 - prior_w) * self.rate
        return h * regime_multiplier

    def flush(self) -> None:
        if self.db:
            self.db.kv_set(self.KEY, {"rate": self.rate, "n": self.n})


def utilization_pressure(free_capital: float, queued_demand: float) -> float:
    """≈1 when capital is the binding constraint; →0.25 when most capital is idle with nothing queued."""
    if free_capital <= 0:
        return 1.5
    return float(min(1.5, max(0.25, queued_demand / free_capital)))


def assess(p_win: float, win_return: float, loss_return: float, expected_hold_h: float,
           hurdle_per_h: float, pressure: float = 1.0, liquidity_delay_h: float = 0.05) -> VelocityAssessment:
    """win/loss returns are NET of all costs (fractions). p_win must be calibrated."""
    p = min(max(p_win, 0.0), 1.0)
    er = p * win_return + (1 - p) * loss_return
    elog = p * math.log1p(max(win_return, -0.99)) + (1 - p) * math.log1p(max(loss_return, -0.99))
    t = max(expected_hold_h, 0.05) + liquidity_delay_h
    vel_h = elog / t
    oc = hurdle_per_h * expected_hold_h * pressure
    adj = er - oc
    # squash velocity into 0..1 relative to the hurdle (score 0.5 == exactly the hurdle)
    _z = -(vel_h - hurdle_per_h) / max(hurdle_per_h, 1e-6)
    _z = max(-60.0, min(60.0, float(_z)))  # prevent OverflowError on extreme paper probes
    score = 1 / (1 + math.exp(_z))
    why = (f"E[r]={er:+.3%} over ~{expected_hold_h:.1f}h → {vel_h * 24:+.3%}/day vs hurdle {hurdle_per_h * 24:.3%}/day; "
           f"opportunity cost {oc:.3%} (pressure {pressure:.2f}) → adjusted {adj:+.3%}")
    return VelocityAssessment(er, expected_hold_h, vel_h, vel_h * 24, hurdle_per_h, oc, adj, score, why)
