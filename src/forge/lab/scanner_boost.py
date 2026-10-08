"""PAPER scanner boost — ensure underrepresented families stay in the funnel."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.scanner_boost")


class ScannerBoost:
    def __init__(self, forge: Any):
        self.f = forge

    def run(self) -> None:
        try:
            self._tick()
        except Exception as e:
            log.warning("scanner_boost: %s", e)

    def _tick(self) -> None:
        arena = self.f.db.kv_get("arena.state") or {}
        fam_counts: dict[str, int] = {}
        for sid, meta in (arena.get("strategies") or arena.get("by_id") or {}).items() if isinstance(arena, dict) else []:
            if not isinstance(meta, dict):
                continue
            fam = str(meta.get("family") or meta.get("genome_family") or "unknown")
            fam_counts[fam] = fam_counts.get(fam, 0) + 1
        # Also count from registry if present
        try:
            rows = self.f.db.query(
                "SELECT family, COUNT(*) c FROM strategies GROUP BY family"
            ) if hasattr(self.f.db, "query") else []
            for r in rows or []:
                fam = str(r["family"] if isinstance(r, dict) else r[0])
                c = int(r["c"] if isinstance(r, dict) else r[1])
                fam_counts[fam] = max(fam_counts.get(fam, 0), c)
        except Exception:
            pass
        bias = (self.f.db.kv_get("lab.regime") or {}).get("paper_bias") or []
        under = [f for f in bias if fam_counts.get(f, 0) < 2]
        out = {
            "ts": time.time(),
            "family_counts": fam_counts,
            "underrepresented_bias": under,
            "boost": True if under else False,
            "note": "PAPER: prefer spawning/promoting underrepresented families when boosting",
        }
        self.f.db.kv_set("lab.scanner_boost", out)
        # Hint for algo_factory / arena
        if under:
            self.f.db.kv_set("lab.spawn_priority_families", {"ts": time.time(), "families": under[:6]})
