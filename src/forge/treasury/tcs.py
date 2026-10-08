"""Treasury Contribution Score — every strategy must pay the treasury (blueprint §32).

Improved vs naive PnL/hours:
  TCS = realized_true_net / capital_hours
        - attributable_opex_rate
        - opportunity_cost_penalty
  then contextualized with confidence, decay state, regime fit.
Sequential evidence gates prevent single-loss overreaction.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

log = logging.getLogger("forge.tcs")


def _f(x: Any, d: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else d
    except Exception:
        return d


class TreasuryContribution:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def score(self, strategy_id: str) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        closed = db.query(
            "SELECT realized_pnl_usd, fees_usd, cost_usd, opened_at, closed_at FROM positions "
            "WHERE strategy_id=? AND status='CLOSED' ORDER BY closed_at DESC LIMIT 100", (strategy_id,)) or []
        open_rows = db.query(
            "SELECT cost_usd, unrealized_pnl_usd FROM positions WHERE strategy_id=? AND status!='CLOSED'",
            (strategy_id,)) or []
        realized = sum(_f(r.get("realized_pnl_usd")) - _f(r.get("fees_usd")) for r in closed)
        fees = sum(_f(r.get("fees_usd")) for r in closed)
        # capital-hours approximation
        cap_h = 0.0
        for r in closed:
            try:
                import datetime as dt
                o = dt.datetime.fromisoformat(str(r.get("opened_at") or "").replace("Z", "+00:00")).timestamp()
                c = dt.datetime.fromisoformat(str(r.get("closed_at") or "").replace("Z", "+00:00")).timestamp()
                cap_h += max(0.0, (c - o) / 3600.0) * max(_f(r.get("cost_usd")), 0.01)
            except Exception:
                cap_h += max(_f(r.get("cost_usd")), 0.01) * 0.1
        for r in open_rows:
            cap_h += max(_f(r.get("cost_usd")), 0.01) * 0.25  # partial credit open
        unreal = sum(_f(r.get("unrealized_pnl_usd")) for r in open_rows)
        # opex attribution from inference (coarse)
        opex = 0.0
        try:
            opex = float(db.scalar(
                "SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls WHERE ts > datetime('now','-1 day')"
            ) or 0) * 0.01  # tiny share unless strategy-tagged
        except Exception:
            pass
        # opportunity cost: idle USDC APY ~ as penalty if capital locked poorly
        apy = float((db.kv_get("yield.usdc") or {}).get("apy") or 0.04)
        opp = (cap_h * (apy / 8760.0)) if cap_h else 0.0
        tcs = (realized / cap_h if cap_h > 0 else 0.0) - (opex / max(cap_h, 1.0)) - (opp / max(cap_h, 1.0))
        n = len(closed)
        conf = max(0.0, min(1.0, n / 30.0))
        decay = db.kv_get("edge_decay") or {}
        decay_s = 0.0
        for b in (decay.get("best") or []) + (decay.get("worst") or []):
            if b.get("strategy_id") == strategy_id:
                decay_s = _f(b.get("edge_decay_score"))
        return {
            "strategy_id": strategy_id,
            "ts": now,
            "tcs": round(tcs, 6),
            "realized_true_net": round(realized, 6),
            "unrealized": round(unreal, 6),
            "capital_hours": round(cap_h, 4),
            "fees": round(fees, 6),
            "opex_attrib": round(opex, 6),
            "opportunity_cost": round(opp, 6),
            "confidence": round(conf, 4),
            "edge_decay_score": decay_s,
            "n_closed": n,
            "contributing": bool(tcs > 0 and conf >= 0.1),
        }

    def evaluate_all(self) -> dict[str, Any]:
        db = self.f.db
        ids = [r["id"] for r in db.query(
            "SELECT id FROM strategies WHERE population IN ('SHADOW','CHALLENGER','PRODUCTION') LIMIT 200")] or []
        cards = [self.score(i) for i in ids]
        cards.sort(key=lambda c: -c["tcs"])
        rep = {
            "ts": time.time(),
            "n": len(cards),
            "contributors": [c for c in cards if c["contributing"]][:20],
            "drains": [c for c in cards if c["tcs"] < 0 and c["n_closed"] >= 3][:20],
            "best": cards[:10],
            "worst": list(reversed(cards[-10:])) if cards else [],
        }
        db.kv_set("treasury.tcs", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("tcs")
            try:
                await asyncio.to_thread(self.evaluate_all)
            except Exception as e:
                log.warning("tcs: %s", e, exc_info=True)
            await asyncio.sleep(180)
