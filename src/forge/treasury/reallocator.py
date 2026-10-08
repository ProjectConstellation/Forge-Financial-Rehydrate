"""Capital Reallocation System — marginal value of the next dollar (blueprint §31, §52, §80).

Improvements:
- LCB of expected true-net per capital-hour
- persistence / liquidity / regime fit
- correlation penalty (same venue/family discount)
- hysteresis + min evidence window + transaction-cost threshold (anti-thrash)
- RED ZONE: prefer unlocking FLOW / research over upsizing one name
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any

log = logging.getLogger("forge.reallocator")

MIN_EVIDENCE_N = 5
HYSTERESIS = 1.15          # challenger must beat incumbent by 15% marginal value
TX_COST_USD = 0.02         # don't reshuffle for less than 2¢ expected improvement
CORRELATION_SAME_VENUE = 0.35


def _f(x: Any, d: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else d
    except Exception:
        return d


def marginal_value(card: dict[str, Any], *, corr_pen: float = 0.0) -> float:
    """MarginalValue = LCB(E[true-net/$/h]) * persist * liq * regime / (1 + risk + corr + lock)."""
    mu = _f(card.get("usd_per_h_per_dollar") or card.get("tcs") or card.get("expected_usd_per_h"))
    sd = _f(card.get("sd_per_h"), abs(mu) * 0.5 + 1e-6)
    n = max(int(card.get("n") or card.get("n_closed") or 0), 1)
    # one-sided LCB ~ mu - z*sd/sqrt(n)
    lcb = mu - 1.645 * sd / math.sqrt(n)
    persist = max(0.2, 1.0 - _f(card.get("edge_decay_score")))
    liq = max(0.2, min(1.0, _f(card.get("liquidity"), 0.7)))
    regime = max(0.2, min(1.0, _f(card.get("regime_fit"), 0.8)))
    risk = max(0.0, _f(card.get("risk_penalty"), 0.1))
    lock = max(0.0, _f(card.get("lock_penalty"), 0.05))
    return (lcb * persist * liq * regime) / (1.0 + risk + corr_pen + lock)


class CapitalReallocator:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def build_candidates(self) -> list[dict[str, Any]]:
        db = self.f.db
        vel = db.kv_get("velocity") or {}
        tcs = db.kv_get("treasury.tcs") or {}
        decay = db.kv_get("edge_decay") or {}
        decay_map = {b.get("strategy_id"): b for b in (decay.get("best") or []) + (decay.get("worst") or [])}
        tcs_map = {c["strategy_id"]: c for c in (tcs.get("best") or []) + (tcs.get("worst") or [])}
        cands: list[dict[str, Any]] = []
        # stream-level from velocity
        for s in vel.get("streams") or []:
            sid = s.get("id")
            if not sid:
                continue
            tc = tcs_map.get(sid, {})
            dc = decay_map.get(sid, {})
            card = {
                "id": sid,
                "venue": s.get("venue"),
                "tier": s.get("tier"),
                "n": s.get("n") or tc.get("n_closed") or 0,
                "usd_per_h_per_dollar": _f(s.get("usd_per_h")) / max(_f(s.get("locked_usd"), 1.0), 0.01) if s.get("usd_per_h") else _f(tc.get("tcs")),
                "expected_usd_per_h": _f(s.get("usd_per_h")),
                "sd_per_h": _f(s.get("sd"), abs(_f(s.get("usd_per_h"))) * 0.5),
                "edge_decay_score": _f(dc.get("edge_decay_score")),
                "liquidity": 0.8,
                "regime_fit": 0.85 if (s.get("tier") in ("EXCEPTIONAL", "HIGH", "PROVEN")) else 0.5,
                "risk_penalty": 0.05 if s.get("venue") == "coinbase" else 0.08,
                "lock_penalty": 0.05,
                "tcs": _f(tc.get("tcs")),
                "n_closed": tc.get("n_closed") or s.get("n") or 0,
                "state": dc.get("state") or "HEALTHY",
            }
            cands.append(card)
        # also surface rails unlock ranking
        alloc = db.kv_get("surface.allocation") or {}
        for u in alloc.get("unlock_value") or []:
            if isinstance(u, dict) and u.get("rail"):
                cands.append({
                    "id": u["rail"], "venue": "coinbase" if "coinbase" in u["rail"] else "kalshi",
                    "n": 30, "usd_per_h_per_dollar": _f(u.get("usd_per_day_if_unblocked")) / 24.0 / 26.0,
                    "expected_usd_per_h": _f(u.get("usd_per_day_if_unblocked")) / 24.0,
                    "sd_per_h": 0.01, "edge_decay_score": 0.0, "liquidity": 0.7, "regime_fit": 0.8,
                    "risk_penalty": 0.1, "lock_penalty": 0.05, "tcs": 0.0, "n_closed": 30,
                    "state": "SHADOW", "source": "unlock",
                })
        return cands

    def plan(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        truth = db.kv_get("treasury.truth") or {}
        red = bool(truth.get("red_zone") or (truth.get("treasury_nav") or 99) < 50)
        cands = self.build_candidates()
        # correlation penalties by venue crowding
        venue_n: dict[str, int] = {}
        for c in cands:
            venue_n[c.get("venue") or "?"] = venue_n.get(c.get("venue") or "?", 0) + 1
        scored = []
        for c in cands:
            v = c.get("venue") or "?"
            corr = CORRELATION_SAME_VENUE * max(0, venue_n.get(v, 1) - 1)
            # paused/weakening get crushed
            if c.get("state") in ("PAUSE", "REDUCE", "WEAKENING"):
                mv = marginal_value(c, corr_pen=corr) * 0.25
            else:
                mv = marginal_value(c, corr_pen=corr)
            if int(c.get("n") or 0) < MIN_EVIDENCE_N and c.get("source") != "unlock":
                mv *= 0.5  # immature
            scored.append({**c, "marginal_value": round(mv, 8), "corr_penalty": corr})
        scored.sort(key=lambda x: -x["marginal_value"])
        # propose moves with hysteresis
        actions = []
        if len(scored) >= 2:
            best, second = scored[0], scored[1]
            if best["marginal_value"] > second["marginal_value"] * HYSTERESIS and best["marginal_value"] > TX_COST_USD / 24:
                actions.append({
                    "type": "PREFER",
                    "to": best["id"],
                    "from": second["id"],
                    "reason": f"marginal LCB {best['marginal_value']:.6f} > {second['marginal_value']:.6f}×{HYSTERESIS}",
                    "paper_only": True,
                })
        # decay-driven reduces
        for c in scored:
            if c.get("state") in ("REDUCE", "PAUSE", "WEAKENING") or _f(c.get("edge_decay_score")) >= 0.55:
                actions.append({
                    "type": c.get("state") if c.get("state") in ("REDUCE", "PAUSE") else "REDUCE",
                    "strategy": c["id"],
                    "reason": f"decay/state={c.get('state')} score={c.get('edge_decay_score')}",
                    "paper_only": True,
                })
        if red:
            actions.insert(0, {
                "type": "RED_ZONE_POLICY",
                "reason": "NAV<$50: intensify independent FLOW discovery + research; do not upsize single names",
                "prefer": "flow_and_challengers",
            })
        nav = _f(truth.get("treasury_nav") or (db.kv_get("velocity") or {}).get("treasury", {}).get("total"))
        plan = {
            "ts": now,
            "nav": nav,
            "red_zone": red,
            "ranking": scored[:12],
            "actions": actions[:20],
            "note": "PAPER reallocation directives; LIVE requires founder auth",
        }
        db.kv_set("capital.reallocation", plan)
        # write directives for governor if material
        if actions and not red:
            try:
                top = actions[0]
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "governor",
                     f"REALLOCATE (PAPER): {top}",
                     "high", "OPEN", "capital_reallocator"),
                )
            except Exception:
                pass
        return plan

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("capital_reallocator")
            try:
                await asyncio.to_thread(self.plan)
            except Exception as e:
                log.warning("reallocator: %s", e, exc_info=True)
            await asyncio.sleep(120)
