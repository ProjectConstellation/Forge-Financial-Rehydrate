"""Agent heartbeat & employment state (blueprint §47–§49)."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.heartbeat")

ROLES = [
    "ops", "governor", "critic", "alpha_inventor", "scout", "adversary",
    "rail_hunter", "architect", "doctor", "eng",
]


class AgentHeartbeat:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def snapshot(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        roster = []
        for role in ROLES:
            last = db.query_one(
                "SELECT MAX(ts) ts, COUNT(*) n FROM role_reports WHERE role=? AND ts>=?",
                (role, now - 86400),
            ) or {}
            open_d = db.scalar(
                "SELECT COUNT(*) FROM ops_directives WHERE status='OPEN' AND role=?", (role,)) or 0
            age = (now - float(last["ts"])) if last.get("ts") else None
            state = "ACTIVE"
            if age is None:
                state = "QUIET"
            elif age > 12 * 3600 and role not in ("ops", "eng"):
                state = "STALE"
            elif age > 48 * 3600:
                state = "REVIEW"  # performance review — not auto-fire
            roster.append({
                "role": role,
                "reports_24h": last.get("n") or 0,
                "last_ts": last.get("ts"),
                "age_h": round(age / 3600, 2) if age is not None else None,
                "open_directives": int(open_d),
                "employment": state,
            })
        rep = {"ts": now, "roster": roster,
               "policy": "STALE→nudge Mira/Luke; REVIEW→prompt/benchmark before any 'firing'; never delete for silence alone"}
        db.kv_set("agents.heartbeat", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("agent_heartbeat")
            try:
                await asyncio.to_thread(self.snapshot)
            except Exception as e:
                log.warning("heartbeat: %s", e)
            await asyncio.sleep(120)
