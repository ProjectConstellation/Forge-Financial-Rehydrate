"""PAPER scanner boost — ensure underrepresented families stay in the funnel."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.scanner_boost")


class ScannerBoost:
    def __init__(self, forge: Any):
        self.f = forge

    def _tick(self) -> None:
        fam_counts: dict[str, int] = {}
        try:
            rows = self.f.db.query(
                "SELECT family, COUNT(*) c FROM strategies "
                "WHERE population IN ('EXPERIMENTAL','SHADOW','CHALLENGER') GROUP BY family"
            ) or []
            for r in rows:
                fam = str(r["family"]).split("+")[0]
                fam_counts[fam] = fam_counts.get(fam, 0) + int(r["c"])
        except Exception as e:
            log.debug("fam counts: %s", e)
        bias = (self.f.db.kv_get("lab.regime") or {}).get("paper_bias") or [
            "microstructure", "inventory", "carry_proxy", "cross_asset", "event_driven",
        ]
        under = [f for f in bias if fam_counts.get(f, 0) < 6]
        out = {
            "ts": time.time(),
            "family_counts": fam_counts,
            "underrepresented_bias": under,
            "boost": bool(under),
            "note": "PAPER: prefer spawning/promoting underrepresented families when boosting",
        }
        self.f.db.kv_set("lab.scanner_boost", out)
        if under:
            self.f.db.kv_set("lab.spawn_priority_families", {"ts": time.time(), "families": under[:6]})

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("scanner_boost")
            try:
                await asyncio.to_thread(self._tick)
            except Exception as e:
                log.warning("scanner_boost: %s", e)
            await asyncio.sleep(1200)
