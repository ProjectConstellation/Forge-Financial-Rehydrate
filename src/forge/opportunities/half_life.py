"""Opportunity half-life estimates — urgency must match decay (blueprint §78)."""
from __future__ import annotations

import math
import time
from typing import Any

# priors in seconds by family
PRIORS = {
    "microstructure": 90.0,
    "stable_triangle": 120.0,
    "stable_peg": 300.0,
    "prediction_take": 900.0,
    "crossrail": 180.0,
    "equity_event": 86400.0,
    "idle_yield": 7 * 86400.0,
    "default": 1800.0,
}


def estimate_half_life(family: str, samples: list[float] | None = None) -> dict[str, Any]:
    """samples: observed edge magnitudes over equal time steps; EWMA decay → half-life."""
    prior = PRIORS.get(family, PRIORS["default"])
    if not samples or len(samples) < 3:
        return {"family": family, "half_life_s": prior, "source": "prior", "urgency": urgency(prior)}
    # fit simple exponential decay on |edge|
    xs = [abs(x) + 1e-9 for x in samples]
    ratios = []
    for a, b in zip(xs, xs[1:]):
        if a > 0:
            ratios.append(b / a)
    if not ratios:
        return {"family": family, "half_life_s": prior, "source": "prior", "urgency": urgency(prior)}
    # geometric mean retention per step; assume step≈prior/10
    g = math.exp(sum(math.log(max(r, 1e-6)) for r in ratios) / len(ratios))
    step_s = max(prior / 10.0, 1.0)
    if g >= 0.999:
        hl = prior * 4
    elif g <= 0.01:
        hl = step_s
    else:
        hl = step_s * math.log(0.5) / math.log(g)
    hl = max(5.0, min(hl, 30 * 86400.0))
    # shrink to prior
    hl = 0.5 * hl + 0.5 * prior
    return {"family": family, "half_life_s": round(hl, 1), "source": "ewma+prior", "urgency": urgency(hl)}


def urgency(half_life_s: float) -> str:
    if half_life_s < 120:
        return "IMMEDIATE"
    if half_life_s < 900:
        return "FAST"
    if half_life_s < 86400:
        return "SAME_DAY"
    return "PATIENT"


class HalfLifeEngine:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def compute(self) -> dict[str, Any]:
        out = {k: estimate_half_life(k) for k in PRIORS if k != "default"}
        rep = {"ts": time.time(), "families": out}
        self.f.db.kv_set("opportunity.half_life", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("half_life")
            try:
                await asyncio.to_thread(self.compute)
            except Exception:
                pass
            await asyncio.sleep(300)
