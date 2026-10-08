"""Proprietary Algorithm Factory — seed/monitor FORGE-native strategy families (blueprint §36–§37).

External feeds are inputs only. Moat = our genomes/features/allocator/execution.
Does not spam spot genomes for activity.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.algo_factory")

FAMILIES = [
    {"id": "stable_triangle_v2", "family": "A.StablecoinMicrostructure", "rail": "coinbase.stable_triangle",
     "hypothesis": "Fee-aware triangular stable dislocation with queue-aware fills; recycle <2m",
     "mode": "PAPER_SHADOW", "priority": "HIGH"},
    {"id": "stable_peg_inventory", "family": "A.StablecoinMicrostructure", "rail": "coinbase.stable_peg_mm",
     "hypothesis": "Peg mean-reversion with inventory skew and adverse-selection filter",
     "mode": "PAPER_SHADOW", "priority": "HIGH"},
    {"id": "kalshi_take_thresh", "family": "B.PredictionSettlement", "rail": "kalshi.events",
     "hypothesis": "Settlement-window TAKE when model edge clears fees + half-life",
     "mode": "PAPER_BLOCKED_NO_KEY", "priority": "HIGH"},
    {"id": "crossrail_leadlag", "family": "C.CrossRailLeadLag", "rail": "crossrail",
     "hypothesis": "Coinbase microstructure leads Kalshi crypto event prices on short half-life",
     "mode": "PAPER_RESEARCH", "priority": "MEDIUM"},
    {"id": "equity_event_drift", "family": "D.EquityEvent", "rail": "coinbase.equity",
     "hypothesis": "8-K/10-Q residual drift after gap; SEC+intraday features",
     "mode": "PAPER_RESEARCH", "priority": "MEDIUM"},
    {"id": "regime_hibernator", "family": "E.RegimeConditioned", "rail": "multi",
     "hypothesis": "Hibernate trend/MR families outside favorable regime; reactivate on fit",
     "mode": "PAPER_META", "priority": "MEDIUM"},
    {"id": "execution_maker_edge", "family": "F.ExecutionAlpha", "rail": "coinbase",
     "hypothesis": "Maker-first entry with cancel/replace; capture spread vs taker baseline",
     "mode": "PAPER_RESEARCH", "priority": "MEDIUM"},
]


class AlgoFactory:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def snapshot(self) -> dict[str, Any]:
        db = self.f.db
        truth = db.kv_get("treasury.truth") or {}
        vel = db.kv_get("velocity") or {}
        red = bool(truth.get("red_zone"))
        items = []
        for fam in FAMILIES:
            # skip directional spot spam
            if "spot_breakout" in fam["id"]:
                continue
            status = fam["mode"]
            if fam["rail"] == "kalshi.events" and not (db.kv_get("kalshi.live") or {}).get("keyed"):
                status = "PAPER_BLOCKED_NO_KEY"
            items.append({**fam, "status": status})
        # binding constraint feeds next invention focus
        top = ((vel.get("priorities") or [{}])[0]).get("action")
        rep = {
            "ts": time.time(),
            "moat": "proprietary algorithms/features/allocator/execution/edge-decay",
            "red_zone_focus": "flow_discovery" if red else None,
            "binding_lever": top,
            "families": items,
            "note": "Seeds for Quinn/Ada validation — not LIVE. Spot directional remains PAPER until fee-aware +EV.",
        }
        db.kv_set("research.algo_factory", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("algo_factory")
            try:
                await asyncio.to_thread(self.snapshot)
            except Exception as e:
                log.warning("algo_factory: %s", e, exc_info=True)
            await asyncio.sleep(600)
