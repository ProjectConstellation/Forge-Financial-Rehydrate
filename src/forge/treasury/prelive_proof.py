"""Pre-LIVE Proof — continuous PAPER validation before founder enables LIVE.

Does not flip LIVE. Publishes go/no-go from real PAPER/shadow evidence.
"""
from __future__ import annotations

import time
from typing import Any


class PreLiveProof:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()

        def shadow(rail: str, since: float):
            row = db.query(
                "SELECT COUNT(*) n, COALESCE(SUM(pnl_usd),0) net FROM shadow_trades WHERE rail=? AND ts>?",
                (rail, since),
            )
            r = (row or [{}])[0]
            return {"n": int(r.get("n") or 0), "net": float(r.get("net") or 0)}

        tri_4 = shadow("coinbase.stable_triangle", now - 4 * 3600)
        tri_24 = shadow("coinbase.stable_triangle", now - 86400)
        peg_24 = shadow("coinbase.stable_peg_mm", now - 86400)
        paper_net = float(db.scalar(
            "SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)),0) "
            "FROM positions WHERE book='paper' AND status='CLOSED'"
        ) or 0)
        vel = db.kv_get("velocity") or {}
        proven = float((vel.get("expected_usd_per_h") or {}).get("proven") or 0)
        hb = db.kv_get("agents.heartbeat") or {}
        stale = [r for r in (hb.get("roster") or []) if r.get("employment") == "STALE"]
        gates = {
            "stables_shadow_24h_positive": tri_24["net"] > 0.5,
            "stables_shadow_4h_nonnegative": tri_4["net"] >= 0,
            "spot_paper_not_bleeding_hard": paper_net > -5.0,
            "officers_not_stale": len(stale) == 0,
            "proven_usd_per_h_rising": proven >= 0.25,
        }
        go = all(gates.values())
        rep = {
            "ts": now,
            "verdict": "GO_MICRO_LIVE_STABLES" if go else "NO_GO",
            "gates": gates,
            "evidence": {
                "stable_triangle_4h": tri_4,
                "stable_triangle_24h": tri_24,
                "stable_peg_24h": peg_24,
                "paper_closed_net": paper_net,
                "proven_usd_per_h": proven,
                "stale_officers": [{"role": r.get("role"), "age_h": r.get("age_h")} for r in stale[:8]],
            },
            "note": "PAPER/shadow must prove edge before LIVE. Founder auth still required to flip FORGE_LIVE_TRADING.",
        }
        db.kv_set("lab.prelive_proof", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("prelive_proof")
            try:
                await asyncio.to_thread(self.tick)
            except Exception:
                pass
            await asyncio.sleep(300)
