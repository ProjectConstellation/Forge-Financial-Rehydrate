"""Earnings Escalator — when $/h is unacceptable, the firm MUST change behavior.

Founder rule: if we are stuck ~$0.05/h, officers are not doing their job.
Cycle (always-on, deterministic first): DETECT → DIAGNOSE → SKIP BLOCKED LEVERS →
IMPLEMENT actionable PAPER/research NOW → PAGE officers → MEASURE Δ$/h.

Never enables LIVE without founder auth. Never lowers the $1/h target.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

log = logging.getLogger("forge.earnings_escalator")

PRIMARY = 1.0
UNACCEPTABLE_USD_PER_H = 0.10
CYCLE_S = 600
OFFICER_PAGE_S = 1200


class EarningsEscalator:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _proven(self) -> float:
        vel = self.f.db.kv_get("velocity") or {}
        return float((vel.get("expected_usd_per_h") or {}).get("proven") or 0.0)

    def _actionable_levers(self) -> list[dict[str, Any]]:
        vel = self.f.db.kv_get("velocity") or {}
        ev = self.f.db.kv_get("lab.evidence_board") or {}
        works = ev.get("works") or []
        out: list[dict[str, Any]] = []
        for w in works:
            sid = str(w.get("strategy_id") or w.get("rail") or "")
            if "stable" in sid.lower() or "stable" in str(w.get("rail") or "").lower():
                out.append({
                    "action": f"IMPLEMENT_PAPER_NOW: maximize {sid} capital-hours (shadow→paper bridge, size up within $200–500 band)",
                    "why": f"evidence true_net={w.get('true_net')} — only clear +EV sleeve",
                    "blocked": False,
                })
        if os.environ.get("THE_ODDS_API_KEY"):
            out.append({
                "action": "TIGHTEN event PAPER: high edge only, fast settle, measure $/capital-hour; feed Nolan/Quinn models",
                "why": "Odds live; secret-sauce R&D on small book",
                "blocked": False,
            })
        if not os.environ.get("KALSHI_API_KEY_ID"):
            out.append({
                "action": "SKIP kalshi.* live levers until founder keys — do not wait on blocked FLOW",
                "why": "velocity top priority is blocked; escalate around it",
                "blocked": True,
            })
        out.append({
            "action": "MODAL CPU tournament: falsify stables microstructure challengers; promote only if OOS $/capital-hour rises",
            "why": "RED ZONE research intensity",
            "blocked": False,
        })
        for p in vel.get("priorities") or []:
            act = str(p.get("action") or "")
            if "kalshi" in act.lower() and not os.environ.get("KALSHI_API_KEY_ID"):
                continue
            if "add capital" in act.lower():
                out.append({**p, "blocked": False, "action": act + " (founder deposit — parallel, not an excuse to idle)"})
            elif act:
                out.append({**p, "blocked": False})
        return out

    def _implement_now(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        pl = getattr(self.f, "paper_lab", None)
        if pl:
            for name in (
                "ensure_stable_strategies",
                "bridge_stable_shadow_to_paper",
                "promote_paper_probes",
                "diversify_experimental",
                "promote_diversity_to_shadow",
                "kill_confirmed_drains",
            ):
                fn = getattr(pl, name, None)
                if callable(fn):
                    try:
                        actions.append({name: fn()})
                    except Exception as e:
                        actions.append({name: f"err:{e}"[:120]})
        self.f.db.kv_set("econ.prefer_rails", {
            "ts": time.time(),
            "order": ["coinbase.stable_triangle", "coinbase.stable_peg_mm", "odds.paper_h2h"],
            "aggression": "ESCALATED_UNDERPERFORMANCE",
            "note": "Team failure mode: <10¢/h — put capital-hours on evidenced stables NOW",
        })
        self.f.db.kv_set("modal.research_request", {
            "ts": time.time(),
            "reason": "earnings_escalator_unacceptable_usd_per_h",
            "workloads": ["stable_microstructure_sweep", "challenger_falsification", "portfolio_optimization"],
            "prefer_cpu": True,
            "consumed": False,
        })
        self.f.db.kv_set("membership.recommendation", {
            "ts": time.time(),
            "action": "CANCEL",
            "reason": "USDC yield on ~$23 ≈ $0.07/mo vs $4.99 membership; Advanced rebate=0; hurts RED ZONE NAV",
            "founder": "Cancel Coinbase One unless you personally need Simple Trade perks — FORGE Advanced API gets ~$0 from it.",
        })
        return actions

    def _page_team(self, proven: float, levers: list[dict[str, Any]]) -> None:
        now = time.time()
        last = float((self.f.db.kv_get("escalator.last_page") or {}).get("ts") or 0)
        if now - last < OFFICER_PAGE_S:
            return
        top = next((L for L in levers if not L.get("blocked")), levers[0] if levers else {})
        msg = (
            f"TEAM FAILURE MODE: proven ${proven:.3f}/h << ${PRIMARY:.2f}/h target (and << acceptable floor). "
            f"You are not done analyzing — IMPLEMENT. Top actionable lever: {top.get('action')}. "
            f"Protocol: DET→VERIFY→CUT drains→REALLOC→CHALLENGER→VALIDATE→MEASURE Δ$/h. "
            f"Do not wait on blocked Kalshi. Do not lower target."
        )
        for role, priority in (
            ("governor", "critical"),
            ("alpha_inventor", "critical"),
            ("scout", "critical"),
            ("critic", "high"),
            ("adversary", "high"),
        ):
            try:
                self.f.db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, role, msg[:1900], priority, "OPEN", "earnings_escalator"),
                )
            except Exception as e:
                log.debug("page %s: %s", role, e)
        try:
            self.f.db.execute(
                "INSERT INTO ops_objectives (ts, kind, objective, status, summary) VALUES (?,?,?,?,?)",
                (now, "earnings_escalation", msg[:2000], "ACTIVE",
                 json.dumps({"proven": proven, "top": top}, default=str)[:1800]),
            )
        except Exception:
            pass
        self.f.db.kv_set("escalator.last_page", {"ts": now, "proven": proven})

    def tick(self) -> dict[str, Any]:
        now = time.time()
        proven = self._proven()
        vel = self.f.db.kv_get("velocity") or {}
        unacceptable = proven < UNACCEPTABLE_USD_PER_H or bool(vel.get("below_target"))
        levers = self._actionable_levers()
        implemented: list[dict[str, Any]] = []
        if unacceptable:
            implemented = self._implement_now()
            self._page_team(proven, levers)
            try:
                from forge.treasury.profit_recovery import maybe_open_recovery
                rep = dict(vel)
                actionable = [L for L in levers if not L.get("blocked")]
                if actionable:
                    rep["priorities"] = [{"action": actionable[0]["action"], "delta_usd_per_h": None}] + list(rep.get("priorities") or [])
                maybe_open_recovery(self.f, rep)
            except Exception as e:
                log.debug("recovery: %s", e)
        rep = {
            "ts": now,
            "proven_usd_per_h": proven,
            "unacceptable": unacceptable,
            "floor_usd_per_h": UNACCEPTABLE_USD_PER_H,
            "target_usd_per_h": PRIMARY,
            "levers": levers[:8],
            "implemented_n": len(implemented),
            "implemented": implemented[:6],
            "membership": self.f.db.kv_get("membership.recommendation"),
            "policy": "If $/h not rising: analyze→skip blocked→implement actionable→page team→measure. No idle.",
        }
        self.f.db.kv_set("lab.earnings_escalator", rep)
        self.f.db.kv_set("econ.earnings_escalator", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("earnings_escalator")
            try:
                rep = await asyncio.to_thread(self.tick)
                if rep.get("unacceptable"):
                    top = ((rep.get("levers") or [{}])[0].get("action") or "")[:120]
                    await self.f.say(
                        "Earnings Escalator",
                        f"UNACCEPTABLE ${rep['proven_usd_per_h']:.3f}/h — forcing implement cycle "
                        f"({rep.get('implemented_n')} actions). Team paged. Top: {top}",
                        level="warn",
                    )
            except Exception as e:
                log.warning("earnings_escalator: %s", e, exc_info=True)
            await asyncio.sleep(CYCLE_S)
