"""Economic event taxonomy + routing — blueprint §§7, 55.

Deterministic emitters feed OPEN directives / workflow seeds without LLM.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

log = logging.getLogger("forge.econ_events")

ROUTING = {
    "edge_decay": ("scout", ["critic", "governor"]),
    "challenger_needed": ("alpha_inventor", ["critic"]),
    "candidate_ready": ("critic", ["adversary"]),
    "evidence_passed": ("adversary", ["governor"]),
    "capital_freed": ("treasury", ["governor"]),
    "founder_deposit": ("treasury", ["governor", "ops"]),
    "slippage_anomaly": ("execution", ["scout", "adversary"]),
    "risk_anomaly": ("adversary", ["governor", "ops"]),
    "stale_role": ("doctor", ["ops", "intelligence"]),
    "weak_prompt": ("intelligence", ["ops"]),
    "new_rail": ("rail_hunter", ["critic", "adversary", "architect"]),
    "engineering_defect": ("architect", ["doctor"]),
    "profit_velocity_collapse": ("ops", ["governor", "alpha_inventor", "critic", "adversary", "treasury"]),
    "modal_candidate": ("alpha_inventor", ["critic", "governor"]),
    "treasury_mismatch": ("treasury", ["doctor", "ops"]),
}


class EconomicEventRouter:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def emit(self, kind: str, payload: dict[str, Any], urgency: str = "high") -> str:
        db = self.f.db
        now = time.time()
        eid = f"ev_{uuid.uuid4().hex[:12]}"
        primary, secondary = ROUTING.get(kind, ("governor", []))
        try:
            db.execute(
                "INSERT INTO economic_events(event_id,kind,ts,primary_owner,secondary,payload_json,urgency,routed) "
                "VALUES(?,?,?,?,?,?,?,0)",
                (eid, kind, now, primary, json.dumps(secondary), json.dumps(payload)[:4000], urgency),
            )
        except Exception as e:
            log.warning("emit store: %s", e)
        # Dedup: same kind+owner open directive in last 20m
        recent = db.scalar(
            "SELECT COUNT(*) FROM ops_directives WHERE role=? AND status='OPEN' AND requested_by='econ_events' "
            "AND ts>?",
            (primary, now - 1200),
        ) or 0
        if int(recent) == 0:
            db.execute(
                "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                "VALUES(?,?,?,?,?,?)",
                (now, primary,
                 f"ECON_EVENT {kind} id={eid}: {json.dumps(payload)[:700]}. "
                 f"Route secondaries={secondary}. Results contract required.",
                 "critical" if urgency == "critical" else "high", "OPEN", "econ_events"),
            )
            for sec in secondary[:3]:
                db.execute(
                    "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                    "VALUES(?,?,?,?,?,?)",
                    (now, sec, f"ECON_EVENT secondary {kind} id={eid} primary={primary}",
                     "high", "OPEN", "econ_events"),
                )
        try:
            db.execute("UPDATE economic_events SET routed=1, consumed_at=? WHERE event_id=?", (now, eid))
        except Exception:
            pass
        return eid

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        emitted = []
        # Edge decay transitions
        ed = db.kv_get("edge_decay") or {}
        for a in (ed.get("actions") or [])[:5]:
            if str(a.get("action") or a.get("state") or "").upper() in (
                "REDUCE", "PAUSE", "HIBERNATE", "WEAKENING", "WATCH"
            ) or a.get("type") in ("REDUCE", "PAUSE", "HIBERNATE"):
                eid = self.emit("edge_decay", a, "critical")
                emitted.append(eid)
        # Velocity collapse
        vel = db.kv_get("velocity") or {}
        proven = float(vel.get("proven_usd_per_h") or 0)
        if proven < 0.10 and vel.get("below_target"):
            last = db.kv_get("econ_events.last_velocity") or {}
            if now - float(last.get("ts") or 0) > 900:
                eid = self.emit("profit_velocity_collapse",
                                {"proven_usd_per_h": proven, "diagnosis": vel.get("diagnosis")},
                                "critical")
                emitted.append(eid)
                db.kv_set("econ_events.last_velocity", {"ts": now, "event_id": eid})
        # Stale officers from employment
        emp = db.kv_get("agents.employment") or db.kv_get("agents.heartbeat") or {}
        for r in emp.get("detailed") or emp.get("roster") or []:
            if r.get("state") == "STALE_SLA_BREACH" or r.get("employment") == "STALE":
                if (r.get("age_h") or 0) > 0.5:
                    eid = self.emit("stale_role", {"role": r.get("role"), "age_h": r.get("age_h")}, "critical")
                    emitted.append(eid)
                    break  # one per tick
        # Seed DIAGNOSTIC if stables contaminated and no open diagnostic for that family
        try:
            from forge.agents.workflow_engine import WorkflowEngine
            eng = getattr(self.f, "workflow_engine", None) or WorkflowEngine(self.f)
            mem = getattr(self.f, "opportunity_memory", None)
            if mem:
                mem.tick()
            open_diag = db.scalar(
                "SELECT COUNT(*) FROM agent_workflows WHERE status='OPEN' AND "
                "(type='DIAGNOSTIC_ORCHESTRATION' OR proposal_class='DIAGNOSTIC')"
            ) or 0
            if int(open_diag) == 0 and proven < 0.50:
                wid = eng.start_diagnostic(
                    "ECON_EVENT: resolve economic uncertainty blocking proven $/h",
                    {"rail": "coinbase.stable_triangle", "family": "stable_triangle",
                     "mechanism_key": "ledger_contamination", "needs_safety_review": True,
                     "needs_early_exec": False, "max_diagnostic_usd": 50},
                )
                emitted.append(wid)
        except Exception as e:
            log.warning("diagnostic seed: %s", e)

        # Modal candidate
        modal = db.kv_get("econ.modal_research") or {}
        for j in (modal.get("recent_jobs") or [])[:2]:
            if j.get("status") in ("DONE", "completed") and j.get("decision_changed"):
                eid = self.emit("modal_candidate", j, "high")
                emitted.append(eid)
        rep = {"ts": now, "emitted": emitted}
        db.kv_set("lab.economic_events", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("economic_events")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("econ_events: %s", e, exc_info=True)
            await asyncio.sleep(180)
