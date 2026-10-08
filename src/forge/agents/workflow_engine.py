"""Institutional Workflow Engine — Tess→Quinn→Ada→Vale→Cyrus/Ellis→Reid→Tess→Luke.

Blueprint §§15–17, 32–33. Durable handoffs; no fake completion.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

log = logging.getLogger("forge.workflow")

ALPHA_CHAIN = [
    ("scout", "MARKET_INTELLIGENCE_PACKET"),
    ("alpha_inventor", "ALPHA_CANDIDATE"),
    ("critic", "EVIDENCE_GATE"),
    ("adversary", "RISK_GATE"),
    ("governor", "ALLOCATION_DECISION"),  # Cyrus; Ellis via treasury role when present
    ("execution", "EXECUTION_PLAN"),
    ("scout", "POST_ACTION_ECONOMIC_RESULT"),
    ("ops", "EXECUTIVE_FOLLOWTHROUGH"),
]


class WorkflowEngine:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def start_alpha_cycle(self, trigger: str, inputs: dict[str, Any] | None = None,
                          due_s: float = 1800) -> str:
        db = self.f.db
        now = time.time()
        wid = self._id("wf")
        stage_owner, payload_type = ALPHA_CHAIN[0]
        db.execute(
            "INSERT INTO agent_workflows(workflow_id,objective_id,type,stage,owner,status,"
            "created_at,due_at,inputs_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (wid, None, "ALPHA_GENERATION", payload_type, stage_owner, "OPEN",
             now, now + due_s, json.dumps({"trigger": trigger, **(inputs or {})})),
        )
        hid = self._id("ho")
        db.execute(
            "INSERT INTO agent_handoffs(handoff_id,workflow_id,from_role,to_role,payload_type,"
            "payload_json,due_at,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (hid, wid, "system", stage_owner, payload_type,
             json.dumps({"trigger": trigger, **(inputs or {})}), now + due_s, "PENDING", now),
        )
        # Open directive for first owner
        db.execute(
            "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
            "VALUES(?,?,?,?,?,?)",
            (now, stage_owner,
             f"WORKFLOW {wid} stage={payload_type}: {trigger}. Produce typed {payload_type} "
             f"handoff. Results contract required. workflow_id={wid}",
             "critical", "OPEN", "workflow_engine"),
        )
        db.kv_set("lab.workflow_latest", {"workflow_id": wid, "ts": now, "trigger": trigger})
        return wid

    def advance(self, workflow_id: str, from_role: str, payload_type: str,
                payload: dict[str, Any], result_type: str = "DECISION_MADE",
                confidence: float = 0.5, skip_reason: str | None = None) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        wf = db.query_one("SELECT * FROM agent_workflows WHERE workflow_id=?", (workflow_id,))
        if not wf:
            return {"error": "unknown_workflow"}
        # Complete pending handoff to this role
        db.execute(
            "UPDATE agent_handoffs SET status='DONE', completed_at=? "
            "WHERE workflow_id=? AND to_role=? AND status='PENDING'",
            (now, workflow_id, from_role),
        )
        # Find next stage
        idx = next((i for i, (r, p) in enumerate(ALPHA_CHAIN) if p == payload_type or r == from_role), None)
        if idx is None:
            idx = 0
        next_idx = idx + 1
        rid = self._id("ar")
        db.execute(
            "INSERT INTO agent_results(report_id,role,objective_id,workflow_id,action_type,summary,"
            "evidence_refs,economic_attribution,next_action,next_owner,next_review_at,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, from_role, wf.get("objective_id"), workflow_id, result_type,
             json.dumps(payload)[:2000], json.dumps(payload.get("evidence_refs") or []),
             json.dumps(payload.get("economic_attribution") or {}),
             payload.get("next_action"), None, now + 1800, now),
        )
        if next_idx >= len(ALPHA_CHAIN) or result_type == "NO_ACTION_JUSTIFIED" and payload.get("terminal"):
            db.execute(
                "UPDATE agent_workflows SET status='DONE', completed_at=?, result_type=?, "
                "confidence=?, outputs_json=?, skip_reason=? WHERE workflow_id=?",
                (now, result_type, confidence, json.dumps(payload)[:4000], skip_reason, workflow_id),
            )
            return {"workflow_id": workflow_id, "status": "DONE"}

        next_role, next_payload = ALPHA_CHAIN[next_idx]
        # Optional Ellis parallel on allocation
        db.execute(
            "UPDATE agent_workflows SET stage=?, owner=?, outputs_json=? WHERE workflow_id=?",
            (next_payload, next_role, json.dumps(payload)[:4000], workflow_id),
        )
        hid = self._id("ho")
        db.execute(
            "INSERT INTO agent_handoffs(handoff_id,workflow_id,from_role,to_role,payload_type,"
            "payload_json,due_at,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (hid, workflow_id, from_role, next_role, next_payload,
             json.dumps(payload)[:8000], now + 1800, "PENDING", now),
        )
        db.execute(
            "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
            "VALUES(?,?,?,?,?,?)",
            (now, next_role,
             f"HANDOFF {hid} workflow={workflow_id} type={next_payload} from={from_role}. "
             f"Consume payload, produce next gate/decision. Results contract required.",
             "critical", "OPEN", "workflow_engine"),
        )
        if next_payload == "ALLOCATION_DECISION":
            # Also page Ellis (treasury) if role exists
            db.execute(
                "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                "VALUES(?,?,?,?,?,?)",
                (now, "treasury",
                 f"Ellis: capital decision for workflow {workflow_id}. Coordinate with Cyrus. "
                 f"Marginal $/capital-hour + opportunity cost required.",
                 "high", "OPEN", "workflow_engine"),
            )
        return {"workflow_id": workflow_id, "next_role": next_role, "next_payload": next_payload, "handoff_id": hid}

    def pending_for(self, role: str) -> list[dict[str, Any]]:
        try:
            rows = self.f.db.query(
                "SELECT * FROM agent_handoffs WHERE to_role=? AND status='PENDING' ORDER BY created_at ASC LIMIT 20",
                (role,),
            ) or []
            return [dict(r) for r in rows]
        except Exception:
            return []

    def tick(self) -> dict[str, Any]:
        """Watchdog: overdue handoffs → escalate; seed recovery cycle if under $/h and no open alpha wf."""
        db = self.f.db
        now = time.time()
        actions = []
        try:
            overdue = db.query(
                "SELECT * FROM agent_handoffs WHERE status='PENDING' AND due_at IS NOT NULL AND due_at<? LIMIT 20",
                (now,),
            ) or []
        except Exception as e:
            return {"error": str(e)[:200]}
        for h in overdue:
            d = dict(h)
            db.execute(
                "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                "VALUES(?,?,?,?,?,?)",
                (now, d["to_role"],
                 f"OVERDUE HANDOFF {d['handoff_id']} type={d['payload_type']} workflow={d['workflow_id']}. "
                 f"Complete or BLOCKED with evidence.",
                 "critical", "OPEN", "workflow_engine"),
            )
            actions.append({"overdue": d["handoff_id"], "role": d["to_role"]})

        vel = db.kv_get("velocity") or {}
        proven = float(vel.get("proven_usd_per_h") or vel.get("frontier_usd_per_h") or 0)
        open_wf = db.scalar(
            "SELECT COUNT(*) FROM agent_workflows WHERE type='ALPHA_GENERATION' AND status='OPEN'") or 0
        if proven < 0.10 and int(open_wf) == 0:
            wid = self.start_alpha_cycle(
                "PROFIT_RECOVERY: proven under floor — run alpha generation chain",
                {"proven_usd_per_h": proven},
            )
            actions.append({"started": wid, "reason": "under_floor"})

        rep = {"ts": now, "actions": actions, "open_workflows": int(open_wf)}
        db.kv_set("lab.workflow_engine", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("workflow_engine")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("workflow: %s", e, exc_info=True)
            await asyncio.sleep(120)
