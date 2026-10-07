"""Dynamic treasury regime (operator addendum 2026-10-07, OP-021).

BOOTSTRAP  (treasury high-water mark < $50): no fixed reserve — essentially the whole treasury is deployable when
           calibrated evidence justifies it; confidence tiers + Kelly + ruin math decide how much.
RESERVE    (HWM ≥ $50, latched — a later dip below $50 keeps the reserve): first $25 is protected survival capital;
           above HWM $100 the reserve grows to 25% of HWM (dynamic, never below $25).
Confidence tiers (evidence = independent clusters, posterior P(mean > 0)) map to fractional Kelly and per-cluster
concentration caps, so no single trade is forced to carry the hourly target.
"""

from __future__ import annotations

import os
import time
from typing import Any

BOOTSTRAP_EXIT_USD = float(os.environ.get("FORGE_BOOTSTRAP_EXIT_USD", "50"))
RESERVE_FLOOR_USD = float(os.environ.get("FORGE_RESERVE_FLOOR_USD", "25"))
RESERVE_GROWTH_FROM_USD = 100.0
RESERVE_GROWTH_SHARE = 0.25

# tier: (min clusters, min P(mean>0), min mean per unit-capital, Kelly fraction, max share of deployable per cluster)
TIERS: tuple[tuple[str, int, float, float, float, float], ...] = (
    ("EXCEPTIONAL", 40, 0.99, 0.02, 1.00, 0.90),
    ("HIGH", 20, 0.95, 0.03, 0.50, 0.50),
    ("MEDIUM", 10, 0.90, 0.02, 0.25, 0.25),
    ("LOW", 10, 0.80, 0.00, 0.10, 0.10),
)


def tier_for(n: int, p_pos: float, mean_rel: float, binary: bool = True, lcb: float = 0.0) -> dict[str, Any]:
    """mean_rel = mean P&L per cluster / mean capital per cluster (scale-free edge). Binary payoffs (event contracts) also
    need a minimum edge per unit capital (fee/settlement-model error margin); continuous low-variance streams (spread
    arbitrage) need a positive lower confidence bound instead for MEDIUM and above."""
    for name, need_n, need_p, need_m, kelly, share in TIERS:
        edge_ok = mean_rel >= need_m if binary else (mean_rel > 0 and (name == "LOW" or lcb > 0))
        if n >= need_n and p_pos >= need_p and edge_ok:
            return {"tier": name, "kelly": kelly, "share": share, "live_ok": True}
    return {"tier": "UNPROVEN", "kelly": 0.05, "share": 0.05, "live_ok": False}


def reserve_for(hwm: float) -> float:
    if hwm < BOOTSTRAP_EXIT_USD:
        return 0.0
    return max(RESERVE_FLOOR_USD, RESERVE_GROWTH_SHARE * hwm if hwm >= RESERVE_GROWTH_FROM_USD else RESERVE_FLOOR_USD)


def regime_for(treasury: float, hwm: float) -> dict[str, Any]:
    hwm = max(hwm, treasury)
    reserve = reserve_for(hwm)
    return {"regime": "BOOTSTRAP" if reserve == 0 else "RESERVE", "treasury": treasury, "hwm": hwm, "reserve": reserve,
            "deployable": max(0.0, treasury - reserve),
            # daily circuit breaker (model-failure protection, not a profit cap): bootstrap 35% of treasury,
            # reserve regime 50% of deployable — and never into the reserve
            "daily_loss_stop": 0.35 * treasury if reserve == 0 else 0.5 * max(0.0, treasury - reserve),
            "hourly_loss_stop": 0.15 * treasury if reserve == 0 else 0.2 * max(0.0, treasury - reserve)}


def current(db: Any, treasury: float) -> dict[str, Any]:
    """Latch the high-water mark (the reserve, once activated, stays) and return the live regime."""
    st = db.kv_get("treasury.regime") or {}
    hwm = max(float(st.get("hwm", 0.0)), treasury)
    r = regime_for(treasury, hwm)
    if r["regime"] == "RESERVE" and not st.get("reserve_since"):
        st["reserve_since"] = time.time()
    db.kv_set("treasury.regime", {**st, "hwm": hwm, "regime": r["regime"], "reserve": r["reserve"], "ts": time.time()})
    return {**r, "reserve_since": st.get("reserve_since")}
