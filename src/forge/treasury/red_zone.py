"""RED ZONE policy — NAV < $50 intensifies FLOW/research, never reckless size (blueprint §34)."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.red_zone")
THRESHOLD = 50.0


class RedZoneGovernor:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        truth = db.kv_get("treasury.truth") or {}
        nav = float(truth.get("treasury_nav") or (db.kv_get("velocity") or {}).get("treasury", {}).get("total") or 0)
        active = nav < THRESHOLD
        now = time.time()
        out = {
            "active": active,
            "ts": now,
            "nav": nav,
            "threshold": THRESHOLD,
            "policy": "intensify_flow_research_not_size",
        }
        if active:
            # Prefer research focus on binding FLOW lever; soft Modal boost signal (hours capped)
            vel = db.kv_get("velocity") or {}
            top = ((vel.get("priorities") or [{}])[0]).get("action") or "diagnose FLOW constraint to $1/h"
            db.kv_set("brain.research_focus", {
                "interval_s": 300,
                "focus": f"RED ZONE NAV ${nav:.2f}<$50: unlock independent FLOW — {top}. "
                         f"Do not upsize single names. Challenger + rail evidence only.",
                "by": "red_zone",
                "ts": now,
            })
            # Ask Modal only if already enabled and not in hard circuit — flag for compute governor
            boost = db.kv_get("ops.compute_boost") or {}
            until = float(boost.get("until") or 0)
            if until < now:
                db.kv_set("ops.compute_boost", {
                    "until": now + 2 * 3600,
                    "by": "red_zone",
                    "hours": 2,
                    "why": "RED ZONE research intensity (FLOW discovery)",
                })
            out["research_focus"] = top
            out["compute_boost_h"] = 2
        db.kv_set("treasury.red_zone", out)
        return out

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("red_zone")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("red_zone: %s", e)
            await asyncio.sleep(120)
