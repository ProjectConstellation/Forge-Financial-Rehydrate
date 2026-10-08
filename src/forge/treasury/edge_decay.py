"""Real-time edge decay + capital rotation (founder correction §5).

Tracks per-strategy health; on material sequential degradation runs:
DETECT→VERIFY→REDUCE/PAUSE→DIAGNOSE→REALLOCATE→CHALLENGER→VALIDATE→PROMOTE→MONITOR.
Does not overreact to a single losing trade.
"""
from __future__ import annotations

import json
import logging
import math
import time
from typing import Any

log = logging.getLogger("forge.edge_decay")

# sequential evidence: need multiple adverse windows before pause
ADVERSE_WINDOWS_TO_PAUSE = 3
ROLLING_H = (1.0, 4.0, 24.0)


def _safe(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


class EdgeDecayMonitor:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def scorecard(self, strategy_id: str) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        # positions + fills attribution if available
        open_n = db.scalar(
            "SELECT COUNT(*) FROM positions WHERE strategy_id=? AND status!='CLOSED'", (strategy_id,)) or 0
        closed = db.query(
            "SELECT realized_pnl_usd, fees_usd, opened_at, closed_at, meta FROM positions "
            "WHERE strategy_id=? AND status='CLOSED' ORDER BY closed_at DESC LIMIT 50", (strategy_id,))
        pnls = [_safe(r.get("realized_pnl_usd")) for r in closed]
        fees = [_safe(r.get("fees_usd")) for r in closed]
        n = len(pnls)
        realized = sum(pnls)
        fee_sum = sum(fees)
        # simple sequential: last 5 vs prior 5
        recent = pnls[:5]
        prior = pnls[5:10]
        recent_m = sum(recent) / len(recent) if recent else 0.0
        prior_m = sum(prior) / len(prior) if prior else 0.0
        decay = 0.0
        if prior and recent:
            # positive decay score => degrading
            if prior_m > 0 and recent_m < prior_m * 0.5:
                decay = min(1.0, (prior_m - recent_m) / max(abs(prior_m), 1e-6))
            elif prior_m > 0 and recent_m < 0:
                decay = min(1.0, 0.6 + abs(recent_m) / max(abs(prior_m), 1e-6) * 0.4)
        # registry state if present
        st_row = db.query_one(
            "SELECT population, fitness, status_reason, updated_at FROM strategies WHERE id=?", (strategy_id,)) or {}
        card = {
            "strategy_id": strategy_id,
            "ts": now,
            "expected_edge": _safe(st_row.get("fitness")),
            "realized_edge": recent_m,
            "true_net_pnl": realized - fee_sum,
            "rolling_usd_per_h": None,  # filled when hold times known
            "slippage": None,
            "fees": fee_sum,
            "confidence": max(0.0, min(1.0, n / 30.0)),
            "regime": "UNKNOWN",
            "drawdown": min(0.0, min(pnls) if pnls else 0.0),
            "capital_efficiency": (realized - fee_sum) / max(fee_sum + abs(realized) * 0.01, 1e-6),
            "edge_decay_score": round(decay, 4),
            "open_positions": int(open_n),
            "n_closed": n,
            "population": st_row.get("population"),
            "status_reason": st_row.get("status_reason"),
        }
        # rough $/h from last 24h closes
        day_pnl = 0.0
        for r in closed:
            try:
                import datetime as dt
                ca = r.get("closed_at") or ""
                # ISO
                if ca and (now - dt.datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()) <= 86400:
                    day_pnl += _safe(r.get("realized_pnl_usd")) - _safe(r.get("fees_usd"))
            except Exception:
                pass
        card["rolling_usd_per_h"] = round(day_pnl / 24.0, 6)
        return card

    def evaluate_all(self) -> dict[str, Any]:
        db = self.f.db
        # active observing populations
        ids = [r["id"] for r in db.query(
            "SELECT id FROM strategies WHERE population IN ('SHADOW','CHALLENGER','PRODUCTION') LIMIT 200")]
        cards = [self.scorecard(i) for i in ids]
        actions = []
        hist = db.kv_get("edge_decay.history") or {}
        for c in cards:
            sid = c["strategy_id"]
            h = hist.get(sid) or {"adverse": 0}
            if c["edge_decay_score"] >= 0.45 and c["n_closed"] >= 6:
                h["adverse"] = int(h.get("adverse") or 0) + 1
            else:
                h["adverse"] = max(0, int(h.get("adverse") or 0) - 1)
            h["last"] = c
            hist[sid] = h
            if h["adverse"] >= ADVERSE_WINDOWS_TO_PAUSE and c["population"] in ("SHADOW", "CHALLENGER", "PRODUCTION"):
                actions.append(self._rotate(sid, c, h["adverse"]))
        db.kv_set("edge_decay.history", hist)
        report = {"ts": time.time(), "n": len(cards), "actions": actions,
                  "worst": sorted(cards, key=lambda x: -x["edge_decay_score"])[:10],
                  "best": sorted(cards, key=lambda x: -(_safe(x.get("rolling_usd_per_h"))))[:10]}
        db.kv_set("edge_decay", report)
        return report

    def _rotate(self, sid: str, card: dict[str, Any], adverse: int) -> dict[str, Any]:
        """DETECT verified → REDUCE/PAUSE population to EXPERIMENTAL + request challenger research."""
        db = self.f.db
        prev = card.get("population")
        action = {
            "strategy_id": sid, "phase": "DETECT→VERIFY→REDUCE/PAUSE→DIAGNOSE→REALLOCATE→CHALLENGER",
            "from": prev, "to": "EXPERIMENTAL", "adverse_windows": adverse,
            "edge_decay_score": card["edge_decay_score"], "true_net_pnl": card["true_net_pnl"],
        }
        try:
            db.execute(
                "UPDATE strategies SET population='EXPERIMENTAL', status_reason=?, updated_at=? WHERE id=?",
                (f"edge_decay pause score={card['edge_decay_score']:.2f} adverse={adverse}",
                 time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), sid),
            )
            # handoff: research focus toward replacement
            q = db.kv_get("research.queue") or []
            q.append({"ts": time.time(), "kind": "challenger", "replace": sid,
                      "why": f"edge decay {card['edge_decay_score']:.2f}", "priority": "high"})
            db.kv_set("research.queue", q[-50:])
            db.execute(
                "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                (time.time(), "alpha_inventor",
                 f"CHALLENGER NEEDED: strategy {sid} paused for edge decay "
                 f"(score={card['edge_decay_score']:.2f}, true_net={card['true_net_pnl']:.4f}). "
                 f"Invent fee-aware replacement; Ada/Vale must falsify before promotion. Spot stays PAPER.",
                 "high", "OPEN", "edge_decay"),
            )
        except Exception as e:
            action["error"] = str(e)[:200]
            log.warning("rotate %s: %s", sid, e)
        return action

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("edge_decay")
            try:
                await asyncio.to_thread(self.evaluate_all)
            except Exception as e:
                log.warning("edge_decay: %s", e, exc_info=True)
            await asyncio.sleep(300)
