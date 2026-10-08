"""Nudge STALE Hermes roles — never auto-fire (blueprint §47–§49)."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.stale_nudge")
COOLDOWN = 6 * 3600


class StaleNudge:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        hb = db.kv_get("agents.heartbeat") or {}
        now = time.time()
        last = db.kv_get("agents.stale_nudge") or {"last_ts": 0, "nudged": []}
        if now - float(last.get("last_ts") or 0) < COOLDOWN:
            return {"skipped": "cooldown", **last}
        stale = [r for r in (hb.get("roster") or []) if r.get("employment") in ("STALE", "REVIEW")]
        actions = []
        for r in stale:
            role = r["role"]
            # map ops role names to hermes assign targets
            target = {"ops": "governor"}.get(role, role)
            try:
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, target,
                     f"STALE/REVIEW nudge: role={role} age_h={r.get('age_h')} reports_24h={r.get('reports_24h')}. "
                     f"File a short role report or SILENT with reason. Mira: consider prompt refresh if repeated.",
                     "normal", "OPEN", "stale_nudge"),
                )
                actions.append(role)
            except Exception as e:
                log.warning("nudge %s: %s", role, e)
        out = {"ts": now, "last_ts": now, "nudged": actions, "stale": [r["role"] for r in stale]}
        db.kv_set("agents.stale_nudge", out)
        return out

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("stale_nudge")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("stale_nudge: %s", e)
            await asyncio.sleep(900)
