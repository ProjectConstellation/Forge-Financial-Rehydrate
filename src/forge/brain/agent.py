"""The Brain: tiered intelligence escalation + Intelligence Attribution Ledger (OP-004, OP-006, OP-009 §1).

    deterministic detectors (ms) → Flash perception (continuous, cheap) → unusual/valuable/ambiguous?
      → Pro (max) scientist/diagnostician with real-time tools → candidates → Improvement Loop (local/Modal sims)
      → deterministic gate/risk → outcomes → attribution ledger → router learns where intelligence pays.

Optimize AI, don't minimize it: the router spends when expected value of information is positive, and spends more
when balance and measured ROI allow (budget-adaptive throughput). Runway tiers protect the organism:
NORMAL (Pro allowed) → LEAN (Flash; Pro only for critical events) → CRITICAL (no calls; deterministic only).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from forge.brain.deepseek import DeepSeekClient
from forge.brain.prompts import PROMPT_VERSION, system_prompt
from forge.brain.tools import TOOLS, ToolRouter
from forge.core.healing import Circuit
from forge.persistence.db import dumps

log = logging.getLogger("forge.brain")

ROLE_PRIOR_VALUE_PER_USD = {"perception": 3.0, "scientist": 5.0, "diagnostician": 2.0, "critic": 2.0,
                            # Hermes roles (OP-015): modest optimistic priors; measured value takes over with evidence
                            "hermes_governor": 2.0, "hermes_alpha_inventor": 3.0, "hermes_adversary": 2.0,
                            "hermes_critic": 1.5, "hermes_doctor": 1.5, "hermes_rail_hunter": 2.0, "hermes_architect": 1.5}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Brain:
    def __init__(self, forge: Any, client: DeepSeekClient) -> None:
        self.f = forge
        self.c = client
        self.balance: float | None = None
        self.balance_ts = 0.0
        self.last_scientist = 0.0
        self.last_escalation = 0.0
        self.last_diag = 0.0
        self.tier = "NORMAL"
        self.circuit = Circuit("deepseek", threshold=3, base_cooldown_s=300)
        from forge.treasury.intelligence import WakeSignal
        self.wake = WakeSignal()                       # Balance Sentinel / earnings wake the brain immediately

    async def _chat(self, *a: Any, **k: Any) -> Any:
        """Every LLM call goes through the circuit breaker: AI is never a single point of failure (OP-012 layer 4)."""
        if not self.circuit.allow():
            raise RuntimeError(f"DeepSeek circuit OPEN (cooling down {self.circuit.cooldown_s:.0f}s) — work queued for retry")
        try:
            res = await self.c.chat(*a, **k)
        except Exception as e:
            self.circuit.failure(str(e))
            if self.circuit.state == "OPEN":
                await self.f.say("Self-Healing", f"DeepSeek unavailable ({str(e)[:80]}) → circuit OPEN; deterministic engine continues, "
                                                 f"AI work queued; retry in {self.circuit.cooldown_s:.0f}s", level="warn")
            raise
        self.circuit.success()
        return res

    def _queue(self, kind: str, payload: dict[str, Any]) -> None:
        q = self.f.db.kv_get("brain.pending", []) or []
        if not any(x["kind"] == kind and x.get("key") == payload.get("key") for x in q):
            q.append({"kind": kind, "ts": time.time(), **payload})
        self.f.db.kv_set("brain.pending", q[-30:])

    async def _drain_pending(self) -> None:
        q = self.f.db.kv_get("brain.pending", []) or []
        if not q or not self.circuit.allow():
            return
        item = q.pop(0)
        self.f.db.kv_set("brain.pending", q)
        try:
            if item["kind"] == "rebuild":
                await self.rebuild(item["key"], item.get("report", {}), critical=item.get("critical", False), mode=item.get("mode", "rebuild"))
            elif item["kind"] == "escalate":
                await self.escalate(self.f, item.get("reason", "queued escalation"), item.get("data", {}))
        except Exception:
            self._queue(item["kind"], item)                        # still failing → keep it queued

    # ------------------------------------------------------------------ budget / router
    def set_balance(self, b: float) -> None:
        """Called by the Balance Sentinel (every 5 min): the pace follows the real credit balance immediately."""
        old = self.balance
        self.balance, self.balance_ts = b, time.time()
        self._retier()
        if old is not None and b > old + 0.25:
            self.wake.wake()

    async def refresh_balance(self) -> None:
        if time.time() - self.balance_ts < 300 and self.balance is not None:
            self._retier()
            return
        b = await self.c.balance()
        if b is not None:
            self.balance, self.balance_ts = b, time.time()
        self._retier()

    def _retier(self) -> None:
        reserve = float(self.f.s.deepseek.min_balance_reserve_usd)
        if self.balance is None:
            self.tier = "LEAN"
        elif self.balance <= reserve:
            self.tier = "CRITICAL"
        elif self.balance < reserve * 3:
            self.tier = "LEAN"
        else:
            self.tier = "NORMAL"
        self.f.status("DeepSeek Brain", f"tier {self.tier} · balance ${self.balance if self.balance is not None else '?'} · "
                                        f"session spend ${self.c.spent_session:.4f}")

    def roi(self, role: str) -> float:
        """Measured value per $ for a role (attribution ledger), shrunk toward an optimistic exploration prior."""
        r = self.f.db.query_one("SELECT COALESCE(SUM(CAST(a.value_usd AS REAL)),0) v, COUNT(DISTINCT a.call_id) n "
                                "FROM intel_artifacts a WHERE a.role = ?", (role,)) or {"v": 0, "n": 0}
        cost = self.f.db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls WHERE agent = ?", (role,)) or 0.0
        prior = ROLE_PRIOR_VALUE_PER_USD.get(role, 1.0)
        n = r["n"] or 0
        observed = (r["v"] / cost) if cost > 0 else prior
        w = n / (n + 40.0)
        return (1 - w) * prior + w * observed

    def pace(self) -> Any:
        """OP-015 Intelligence Treasury: spend pace from live balance × measured value-per-$ × earnings (rolling 24 h)."""
        from forge.treasury.intelligence import pace, profit_7d, spent_24h
        roi = max(self.roi(r) for r in ROLE_PRIOR_VALUE_PER_USD)
        measured = (self.f.db.scalar("SELECT COUNT(DISTINCT call_id) FROM intel_artifacts WHERE valued_at IS NOT NULL") or 0) >= 20
        return pace(self.balance, float(self.f.s.deepseek.min_balance_reserve_usd), roi, measured, spent_24h(self.f.db),
                    profit_7d(self.f.db), float(self.f.s.treasury.ops_profit_share_default))

    def daily_budget(self) -> float:
        return self.pace().budget_24h

    def spent_today(self) -> float:
        from forge.treasury.intelligence import spent_24h
        return spent_24h(self.f.db)

    def allow(self, role: str, est_cost: float, critical: bool = False) -> bool:
        if self.tier == "CRITICAL":
            return False
        if critical:
            return True
        if self.spent_today() + est_cost > self.daily_budget():
            return False
        return self.roi(role) >= 1.0                                   # EVI ≥ cost (value-per-$ ≥ 1)

    # ------------------------------------------------------------------ main loop
    async def run(self, forge: Any) -> None:
        await asyncio.sleep(90)
        while not forge.stop_event.is_set():
            forge.sup.beat("brain")
            try:
                await asyncio.wait_for(self._cycle(forge), timeout=2400)
            except TimeoutError:
                await forge.say("DeepSeek Brain", "research cycle exceeded 40 min — aborted (meltdown guard)", level="warn")
            forge.sup.beat("brain")
            p = self.pace()
            self.f.db.kv_set("brain.pace", {"budget_24h": p.budget_24h, "spent_24h": p.spent_24h, "runway_days": p.runway_days,
                                            "cycle_s": p.cycle_s, "deep_sessions": p.deep_sessions, "why": p.reason,
                                            "balance": self.balance, "ts": time.time()})
            if await self.wake.sleep(p.cycle_s):
                await forge.say("DeepSeek Brain", f"Woken by new funds — pace now: {self.pace().reason}")

    async def _cycle(self, forge: Any) -> None:
        if True:
            try:
                await self._drain_pending()
                await self.refresh_balance()
                if self.tier != "CRITICAL":
                    view = await self.perceive()
                    want = view.get("escalate") if view else False
                    near = len(self.f.db.kv_get("evolution.near_miss", []) or [])
                    p = self.pace()
                    # research when there is a reason (escalation, near-miss lineages) or unused headroom; the number of
                    # deep sessions per cycle scales with what the headroom can buy (more money → more thinking)
                    gap = 1800 if p.headroom < 0.25 else 600
                    due = (near > 0 or p.headroom > 0.06) and time.time() - self.last_scientist > gap
                    if want or due:
                        for k in range(max(1, p.deep_sessions) if (want or due) else 0):
                            if not self.allow("scientist", 0.03, critical=False):
                                break
                            self.last_scientist = 0.0 if k else self.last_scientist
                            foci = [(view or {}).get("research_focus") or [], ["repair the closest near-miss lineages"],
                                    ["new families: residual (BTC-neutral) momentum resid_z_24/72, breadth rotation "
                                     "mkt_breadth_24h, panic absorption after capitulation"],
                                    ["exits & execution: convex exits on 1h genomes, maker-first entries, no-progress stops"]]
                            await self.scientist(reason=(view or {}).get("escalate_reason") or
                                                 ("scheduled research cycle" if k == 0 else f"headroom session {k + 1}"),
                                                 focus=foci[k % len(foci)])
                await self.value_artifacts()
            except Exception as e:
                log.exception("brain cycle failed")
                await forge.say("DeepSeek Brain", f"cycle error (engine unaffected): {str(e)[:200]}", level="warn")

    def _situation(self) -> dict[str, Any]:
        f = self.f
        eng = f.bars[3600]
        regimes: dict[str, int] = {}
        movers = []
        for s, st in eng.state.items():
            if not st.features:
                continue
            regimes[st.regime] = regimes.get(st.regime, 0) + 1
            r = st.features["ret_24"][-1]
            if r == r:
                movers.append((s, float(r), st.regime, round(st.regime_conf, 2)))
        movers.sort(key=lambda x: -abs(x[1]))
        recent = f.db.query("SELECT symbol, family, status, probability, outcome FROM opportunities WHERE outcome IS NOT NULL "
                            "ORDER BY ts_ns DESC LIMIT 15")
        return {"utc": _now(), "regime_breadth_1h": regimes, "top_movers_24h": movers[:12],
                "population": f.reg.counts(), "treasury": {k: f.treasury.get(k) for k in ("equity_usd", "true_net_usd", "daily_pnl_usd")},
                "capital_regime": (f.treasury.get("regime") or {}).get("name"), "recent_scored_opportunities": recent}

    def _work(self, what: str, count: int = 1) -> None:
        self.f.workers["brain"] = {"what": what, "count": count, "since": time.time(), "where": "DeepSeek API"}

    async def perceive(self) -> dict[str, Any] | None:
        tri = None
        s1 = getattr(self.f, "systemone", None)
        if s1 is not None:
            sit = self._situation()
            tri = await s1.triage({k: sit[k] for k in ("regime_breadth_1h", "top_movers_24h", "population", "capital_regime")}
                                  | {"regimes": sit["regime_breadth_1h"], "top_movers": sit["top_movers_24h"],
                                     "alerts": [b["code"] for b in self.f.breakers.snapshot()]})
            if tri and s1.mode == "GATE" and (tri["escalate"] or 0) < 0.2 and (tri["anomaly"] or 0) < 0.3:
                self.f.status("DeepSeek Brain", f"System One triage: routine ({tri['latency_ms']:.0f} ms) — Flash call skipped")
                return {"escalate": False}
        self._work("Flash perception: reading the market")
        fo = getattr(self.f, "jev_failover", None)
        if not self.circuit.allow() and fo is not None:
            # INTELLIGENCE SELF-HEALING: direct DeepSeek is down → independent path via OpenRouter Jev Router
            try:
                res = await fo.chat_json(system_prompt("perception"), "SITUATION PACK:\n" + json.dumps(self._situation(), default=str))
            except Exception as e:
                await self.f.say("Self-Healing", f"DeepSeek AND Jev failover unavailable ({str(e)[:80]}) — deterministic engine continues",
                                 level="warn")
                return None
            from decimal import Decimal
            cid = f"jevfo_{int(time.time() * 1000)}"
            self.f.ledger.record_opex(self.f.book if self.f.book in ("live", "paper") else "paper", "INFERENCE",
                                      Decimal(f"{res['cost_usd']:.8f}"), cid, memo=f"jev-router failover → {res['routed_model']}")
            self._artifact(cid, "perception", f"jev-router:{res['routed_model']}", "failover_perception", None, None,
                           {"latency_ms": res["latency_ms"], "cost": res["cost_usd"]})
            await self.f.say("Self-Healing", f"DeepSeek circuit open → perception served by Jev Router failover "
                                             f"({res['routed_model']}, {res['latency_ms']:.0f} ms, ${res['cost_usd']:.4f})")
            return res["json"]
        msgs = [{"role": "system", "content": system_prompt("perception")},
                {"role": "user", "content": "SITUATION PACK:\n" + json.dumps(self._situation(), default=str)}]
        res = await self._chat(msgs, agent="perception", purpose="market_perception", effort="low", json_mode=True,
                                max_tokens=1500, prompt_version=PROMPT_VERSION)
        try:
            view = res.json()
        except Exception:
            return None
        if s1 is not None and tri is not None:
            s1.record_reference(bool(view.get("escalate")))
        for rc in (view.get("regime_calls") or [])[:20]:
            self._artifact(res.call_id, "perception", res.model, "regime_call", rc.get("symbol"), rc.get("p"), rc)
        self.f.status("DeepSeek Brain", f"Flash perception: {str(view.get('market_view', ''))[:120]}")
        self._work("idle — next perception in ≤15 min", 0)
        await self.f.say("DeepSeek Brain", f"Flash perception (${res.cost_usd:.5f}): {str(view.get('market_view', ''))[:240]}"
                                           + (f" → ESCALATE: {view.get('escalate_reason')}" if view.get("escalate") else ""))
        return view

    async def scientist(self, reason: str, focus: list[str] | None = None, critical: bool = False) -> None:
        self.last_scientist = time.time()
        self._work(f"V4 Pro scientist: designing strategies ({reason[:60]})")
        await self.f.say("DeepSeek Brain", f"Escalating to {self.f.s.deepseek.deep_model} (effort {self.f.s.deepseek.deep_effort if critical else 'high'}) — {reason}")
        user = ("Research mandate: find strategy genomes that clear FORGE's fee hurdle with alpha vs market drift and high "
                f"capital velocity. Reason for this session: {reason}. Focus hints: {focus or []}. "
                "Inspect evidence with tools first (system state, strategies incl. EXPERIMENTAL elites, failures, missed "
                "opportunities, calibration, market state 300s and 3600s). Then submit 4–10 candidates via "
                "submit_strategy_candidates and record lessons. Finish with the JSON described in your role.")
        # scheduled research: Pro @ high; critical escalations: Pro @ max (OP-009 §1 — escalate when value warrants)
        await self._tool_session("scientist", user, deep=True, effort=self.f.s.deepseek.deep_effort if critical else "high",
                                 max_rounds=8)

    async def _tool_session(self, role: str, user: str, deep: bool, effort: str, max_rounds: int = 6,
                            strategy_id: str | None = None) -> dict[str, Any] | None:
        msgs: list[dict[str, Any]] = [{"role": "system", "content": system_prompt(role)}, {"role": "user", "content": user}]
        router = None
        total = 0.0
        final: dict[str, Any] | None = None
        first_id = None
        for _ in range(max_rounds):
            res = await self._chat(msgs, agent=role, purpose=f"{role}_session", deep=deep, effort=effort, tools=TOOLS,
                                    max_tokens=32000 if deep else 8000, strategy_id=strategy_id, prompt_version=PROMPT_VERSION)
            first_id = first_id or res.call_id
            router = router or ToolRouter(self.f, first_id, role)
            total += res.cost_usd
            if not res.tool_calls:
                if not res.content.strip():
                    # thinking consumed the budget: ask for the final answer only (prefix-cached → cheap)
                    msgs.append({"role": "assistant", "content": ""})
                    msgs.append({"role": "user", "content": "Output ONLY the final JSON object for your role now."})
                    res = await self._chat(msgs, agent=role, purpose=f"{role}_finalize", deep=deep, effort="low",
                                            json_mode=True, max_tokens=12000, strategy_id=strategy_id,
                                            prompt_version=PROMPT_VERSION)
                    total += res.cost_usd
                try:
                    final = res.json()
                except Exception:
                    final = {"text": res.content[:2000]}
                break
            assistant = {"role": "assistant", "content": res.content or "", "tool_calls": res.tool_calls}
            if res.reasoning:
                assistant["reasoning_content"] = res.reasoning
            msgs.append(assistant)
            for tc in res.tool_calls:
                out = await router.dispatch(tc["function"]["name"], tc["function"].get("arguments", "{}"))
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
        if final and router is not None:
            for c in (final.get("candidates") or [])[:10]:
                await router.dispatch("submit_strategy_candidates", json.dumps({"candidates": [c]}))
            for les in (final.get("lessons") or [])[:5]:
                if isinstance(les, dict) and les.get("statement"):
                    await router.dispatch("record_lesson", json.dumps({"statement": les["statement"],
                                                                       "confidence": float(les.get("confidence", 0.5))}))
            self.f.db.insert("research_notes", {"id": f"note_{first_id}", "ts": _now(), "author": role, "kind": "postmortem"
                                                if role == "diagnostician" else "hypothesis", "strategy_id": strategy_id,
                                                "title": f"{role} session", "body": json.dumps(final, default=str)[:20000]},
                             or_ignore=True)
        if router is not None:
            model = self.f.s.deepseek.deep_model if deep else self.f.s.deepseek.model
            for a in router.artifacts:
                pred = None
                if a["kind"] == "genome":
                    q = [x for x in (self.f.db.kv_get("brain.candidate_queue", []) or []) if x["genome"]["id"] == a["ref_id"]]
                    pred = q[0].get("predicted_p") if q else None
                self._artifact(first_id or "?", role, model, a["kind"], a["ref_id"], pred, None)
            n_g = sum(1 for a in router.artifacts if a["kind"] == "genome")
            self._work("idle", 0)
            await self.f.say("DeepSeek Brain", f"{role} session done (${total:.4f}): {n_g} candidate genomes queued for "
                                               f"evaluation; {str((final or {}).get('diagnosis', ''))[:200]}")
        return final

    async def rebuild(self, sid: str, report: dict[str, Any], critical: bool = False, mode: str = "rebuild") -> None:
        """Analyst-triggered: rebuild a failing algorithm, repair a drifting one, or amplify a thriving one.
        Successor genomes carry `parents=[sid]` so lineage and attribution flow back to this decision."""
        key = f"last_{mode}"
        if time.time() - getattr(self, key, 0.0) < (900 if mode == "rebuild" else 2700):
            return
        await self.refresh_balance()
        if not self.circuit.allow():
            self._queue("rebuild", {"key": sid, "report": report, "critical": critical, "mode": mode})
            return
        if not self.allow("scientist", 0.12, critical=critical):
            self._queue("rebuild", {"key": sid, "report": report, "critical": critical, "mode": mode})
            await self.f.say("DeepSeek Brain", f"{mode} of {sid[:18]} queued for evolution (AI budget tier {self.tier}); "
                                               "Modal evolution continues mutating its lineage meanwhile")
            q = self.f.db.kv_get("evolution.near_miss", []) or []
            g = self.f.reg.get(sid)
            if g is not None:
                q.insert(0, {"id": sid, "interval": g.interval_s, "p": 0.99, "n": report.get("trades"), "reasons": [mode]})
                self.f.db.kv_set("evolution.near_miss", q[:20])
            return
        setattr(self, key, time.time())
        g = self.f.reg.get(sid)
        if g is None:
            return
        goal = {"rebuild": "This incumbent is FAILING live versus its validation evidence. Diagnose why (regime change, fee drag, "
                           "entry timing, exits, overfit) and design 4–8 successor genomes that fix the diagnosed cause.",
                "repair": "This algorithm is DRIFTING below expectation. Diagnose the drift and design 3–6 targeted repairs.",
                "amplify": "This algorithm is THRIVING. Keep it earning; design 3–6 upgraded challengers that could earn MORE "
                           "(better exits/profit locks, regime specialization, wider universe, faster capital velocity)."}[mode]
        user = (f"{goal}\nIncumbent genome id {sid}: {json.dumps(g.model_dump(mode='json'))[:6000]}\n"
                f"Live analyst report: {json.dumps(report, default=str)[:3000]}\n"
                "Use tools for evidence (get_strategy, get_recent_failures, get_missed_opportunities, get_market_state). "
                f'Every candidate genome MUST include "parents": ["{sid}"]. Submit via submit_strategy_candidates.')
        self._work(f"V4 Pro {mode}: {g.family} {sid[:14]}")
        await self._tool_session("scientist", user, deep=True, effort="max" if critical else "high", max_rounds=6, strategy_id=sid)

    # ------------------------------------------------------------------ event hooks
    async def on_loss(self, forge: Any, info: dict[str, Any]) -> None:
        if time.time() - self.last_diag < 600 or not self.allow("diagnostician", 0.002):
            return
        self.last_diag = time.time()
        user = "Diagnose this closed losing position. Use tools for strategy context.\n" + json.dumps(
            {k: v for k, v in info.items() if k != "meta"}, default=str)
        await self._tool_session("diagnostician", user, deep=False, effort="high", max_rounds=4, strategy_id=info.get("strategy_id"))

    async def escalate(self, forge: Any, reason: str, data: dict[str, Any]) -> None:
        if time.time() - self.last_escalation < 1800:
            return
        self.last_escalation = time.time()
        await self.refresh_balance()
        if not self.allow("diagnostician", 0.05, critical=True):
            return
        self.last_scientist = 0.0          # critical events also unlock an immediate research session
        if not self.circuit.allow():
            self._queue("escalate", {"key": reason, "reason": reason, "data": data})
            return
        user = f"CRITICAL EVENT: {reason}. Data: {json.dumps(data, default=str)[:6000]}. Diagnose root cause with tools, " \
               "propose repaired/successor genomes (submit_strategy_candidates) and lessons."
        await self._tool_session("diagnostician", user, deep=True, effort="max", max_rounds=6)

    # ------------------------------------------------------------------ attribution ledger
    def _artifact(self, call_id: str, role: str, model: str, kind: str, ref_id: Any, pred: Any, detail: Any) -> None:
        self.f.db.insert("intel_artifacts", {"ts": _now(), "call_id": call_id, "role": role, "model": model, "kind": kind,
                                             "ref_id": str(ref_id) if ref_id is not None else None,
                                             "prediction": float(pred) if isinstance(pred, int | float) else None,
                                             "detail": dumps(detail) if detail else None})

    async def value_artifacts(self) -> None:
        """Credit downstream economic value back to the calls that produced it (direct + enabling)."""
        db = self.f.db
        for a in db.query("SELECT id, ref_id, prediction FROM intel_artifacts WHERE kind = 'genome'"):
            sid = a["ref_id"]
            st = self.f.reg.state(sid) if sid else None
            if st is None:
                continue
            # realized net P&L of the strategy and its descendants (lineage), plus option value for reaching SHADOW+
            ids = [sid] + [r["child_id"] for r in db.query("SELECT child_id FROM lineage_edges WHERE parent_id = ?", (sid,))]
            q = ",".join("?" * len(ids))
            pnl = db.scalar(f"SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) FROM positions "
                            f"WHERE status='CLOSED' AND strategy_id IN ({q})", ids) or 0.0
            option = {"SHADOW": 0.02, "CHALLENGER": 0.05, "PRODUCTION": 0.10}.get(st.value, 0.0)
            val = float(pnl) + option
            db.execute("UPDATE intel_artifacts SET value_usd = ?, value_basis = ?, valued_at = ? WHERE id = ?",
                       (f"{val:.8f}", f"state={st.value} lineage_pnl={pnl:.6f} option={option}", _now(), a["id"]))
            if a["prediction"] is not None and st.value != "EXPERIMENTAL":
                pass
        # LLM prediction calibration: genome predicted holdout P vs gate outcome
        for a in db.query("SELECT id, ref_id, prediction, role FROM intel_artifacts WHERE kind='genome' AND prediction IS NOT NULL "
                          "AND (detail IS NULL OR detail NOT LIKE '%scored%')"):
            st = self.f.reg.state(a["ref_id"])
            if st is None:
                continue
            self.f.calib.record(f"llm:{a['role']}", float(a["prediction"]), st.value in ("SHADOW", "CHALLENGER", "PRODUCTION"),
                                "backtest", a["ref_id"])
            db.execute("UPDATE intel_artifacts SET detail = ? WHERE id = ?", (dumps({"scored": True}), a["id"]))

    def spend_summary(self) -> dict[str, Any]:
        db = self.f.db
        rows = db.query("SELECT agent, model, COUNT(*) n, COALESCE(SUM(CAST(cost_usd AS REAL)),0) cost FROM inference_calls "
                        "GROUP BY agent, model")
        value = {r["role"]: r["v"] for r in db.query("SELECT role, COALESCE(SUM(CAST(value_usd AS REAL)),0) v FROM intel_artifacts GROUP BY role")}
        today = db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls WHERE ts > date('now')") or 0.0
        return {"available": True, "tier": self.tier, "balance_usd": self.balance, "today_usd": today,
                "daily_budget_usd": round(self.daily_budget(), 4),
                "by_role": rows, "attributed_value_usd": value,
                "roi_estimates": {r: round(self.roi(r), 3) for r in ROLE_PRIOR_VALUE_PER_USD}}


def attach_brain(forge: Any) -> None:
    from forge.brain.systemone import SystemOneTriage, make_provider
    from forge.brain.systemone import make_failover
    prov = make_provider()
    forge.systemone = SystemOneTriage(forge, prov) if prov is not None else None
    forge.jev_failover = make_failover()
    key = forge.s.secrets.deepseek_api_key
    if key is None:
        raise RuntimeError("DEEPSEEK_API_KEY not configured (CONFIG_REQUIRED)")
    client = DeepSeekClient(forge.s.deepseek, key.get_secret_value(), forge.db, forge.ledger,
                            forge.book if forge.book in ("live", "paper") else "paper")
    forge.brain = Brain(forge, client)
