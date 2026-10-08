"""Institutional Opportunity Orchestration — INCOME / DIAGNOSTIC / INFRASTRUCTURE.

Tess DETECTS anomalies → Quinn FORMULATES strategy+algorithm (income) →
early Reid when microstructure matters → Ada evidence → Vale risk →
Cyrus allocate → Ellis commit → Reid execute → Tess measure → Luke close/learn.

Structural enforcement: persistent workflows, mandatory handoffs, dedupe keys,
proposal classes, lifecycle, capacity gate, no fake economic success without MEASURE.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any

log = logging.getLogger("forge.workflow")

PROPOSAL_CLASSES = ("INCOME", "DIAGNOSTIC", "INFRASTRUCTURE")

# INCOME: Tess detects; Quinn invents; optional early Reid; Ada; Vale; Cyrus; Ellis; Reid; Tess; Luke
INCOME_CHAIN = [
    ("scout", "ANOMALY_DETECT"),
    ("alpha_inventor", "STRATEGY_ALGORITHM"),
    ("execution", "EARLY_EXEC_FEASIBILITY"),
    ("critic", "EVIDENCE_GATE"),
    ("adversary", "RISK_GATE"),
    ("governor", "CAPITAL_ALLOCATION"),
    ("treasury", "CAPITAL_COMMIT"),
    ("execution", "EXECUTION_PLAN"),
    ("scout", "MEASURE_RESULT"),
    ("ops", "CLOSE_LEARN"),
]

# DIAGNOSTIC: shorter path to economic answer
DIAGNOSTIC_CHAIN = [
    ("scout", "UNCERTAINTY_IDENTIFY"),
    ("critic", "TEST_DESIGN"),
    ("adversary", "SAFETY_REVIEW"),
    ("execution", "MEASUREMENT_FIDELITY"),
    ("scout", "MEASURE_INTERPRET"),
    ("ops", "MEMORY_UPDATE"),
]

# INFRASTRUCTURE / RESEARCH capability unlocks
INFRA_CHAIN = [
    ("scout", "CAPABILITY_ASK"),
    ("architect", "DESIGN"),
    ("governor", "PRIORITY"),
    ("ops", "TRACK"),
]

# Legacy aliases kept for in-flight workflows
LEGACY_OPPORTUNITY = [
    ("scout", "OPPORTUNITY_PROPOSAL"),
    ("critic", "EVIDENCE_SCREEN"),
    ("adversary", "RISK_ANALYSIS"),
    ("governor", "CAPITAL_ALLOCATION"),
    ("treasury", "CAPITAL_COMMIT"),
    ("execution", "EXECUTION_PLAN"),
    ("scout", "MEASURE_RESULT"),
    ("ops", "EXECUTIVE_FOLLOWTHROUGH"),
]

ALPHA_CHAIN = [
    ("scout", "MARKET_INTELLIGENCE_PACKET"),
    ("alpha_inventor", "ALPHA_CANDIDATE"),
    ("critic", "EVIDENCE_GATE"),
    ("adversary", "RISK_GATE"),
    ("governor", "ALLOCATION_DECISION"),
    ("execution", "EXECUTION_PLAN"),
    ("scout", "POST_ACTION_ECONOMIC_RESULT"),
    ("ops", "EXECUTIVE_FOLLOWTHROUGH"),
]

CHAINS = {
    "INCOME_ORCHESTRATION": INCOME_CHAIN,
    "DIAGNOSTIC_ORCHESTRATION": DIAGNOSTIC_CHAIN,
    "INFRASTRUCTURE_ORCHESTRATION": INFRA_CHAIN,
    "OPPORTUNITY_ORCHESTRATION": LEGACY_OPPORTUNITY,  # migrate in-flight
    "ALPHA_GENERATION": ALPHA_CHAIN,
}

LIFECYCLE = (
    "OBSERVED", "DIAGNOSTIC", "HYPOTHESIS", "STRATEGY_FORMULATED", "ALGORITHM_FORMULATED",
    "EXECUTION_FEASIBLE", "EVIDENCE_PASS", "RISK_PASS", "PAPER_ALLOCATED", "EXECUTED",
    "MEASURED", "SCALE", "REDUCE", "HIBERNATE", "RETIRE", "MUTATE",
)

STAGE_BRIEF = {
    "ANOMALY_DETECT": "Tess: DETECT economic anomaly only — do NOT invent full STRATEGY+ALGORITHM. Class INCOME|DIAGNOSTIC|INFRASTRUCTURE. Hand to Quinn if income invention needed.",
    "STRATEGY_ALGORITHM": "Quinn: convert observation → proprietary STRATEGY + ALGORITHM (both required for INCOME). Mechanism, persistence, capacity, falsification, decay.",
    "EARLY_EXEC_FEASIBILITY": "Reid EARLY: can theoretical edge survive spreads/fees/queue/latency/partials? PASS|FAIL|NARROW.",
    "EVIDENCE_GATE": "Ada: prove or disprove with tool-cited numbers. PASS|FAIL|NARROW.",
    "RISK_GATE": "Vale: survivability / ruin / fee traps. PASS|VETO|RESIZE.",
    "CAPITAL_ALLOCATION": "Cyrus: marginal next-dollar value + opportunity cost + CAPACITY analysis. No bypass of deterministic risk.",
    "CAPITAL_COMMIT": "Ellis: treasury truth, liquidity, release size. Minimum sensible for diagnostics.",
    "EXECUTION_PLAN": "Reid FINAL: execution plan preserving alpha through microstructure.",
    "MEASURE_RESULT": "Tess: MEASURE Δ TRUE-NET $/h vs proposal. Workflow cannot claim economic success without this.",
    "CLOSE_LEARN": "Luke: close loop; update positive/negative/uncertainty memory; escalate blockers; compound.",
    "UNCERTAINTY_IDENTIFY": "Tess: name the economically important uncertainty (not an income pitch).",
    "TEST_DESIGN": "Ada: design minimum-information-value falsification test + abort criteria.",
    "SAFETY_REVIEW": "Vale: safety if capital/material risk. PASS_TO_MEASURE|VETO|BLOCKED.",
    "MEASUREMENT_FIDELITY": "Reid: can we obtain valid quotes/instruments/fills for the test?",
    "MEASURE_INTERPRET": "Tess(+Ada): PASS|FAIL|INCONCLUSIVE|BLOCKED + next rational action + memory update.",
    "MEMORY_UPDATE": "Luke: write institutional memory; page Quinn if INCOME work now justified.",
    "CAPABILITY_ASK": "Tess/ops: infrastructure ask with capability unlocked / decision improved.",
    "DESIGN": "Mira/architect: design the capability change.",
    "PRIORITY": "Cyrus: priority vs other research.",
    "TRACK": "Luke: track to completion.",
    # legacy
    "OPPORTUNITY_PROPOSAL": "Legacy Tess proposal — reclassify to INCOME/DIAGNOSTIC.",
    "EVIDENCE_SCREEN": "Ada evidence screen (legacy).",
    "RISK_ANALYSIS": "Vale risk analysis (legacy).",
    "EXECUTIVE_FOLLOWTHROUGH": "Luke followthrough (legacy).",
}

OPTIONAL_SKIP = {
    # stage → skip if predicate key in inputs is falsy
    "EARLY_EXEC_FEASIBILITY": "needs_early_exec",
    "SAFETY_REVIEW": "needs_safety_review",
}

_DIRECTIVE_COALESCE_S = 600
_HANDOFF_DUE_S = 1800


class WorkflowEngine:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        try:
            from forge.agents.opportunity_memory import OpportunityMemory
            self.memory = getattr(forge, "opportunity_memory", None) or OpportunityMemory(forge)
        except Exception:
            self.memory = None

    def _id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _chain(self, wf_type: str) -> list[tuple[str, str]]:
        return CHAINS.get(wf_type, INCOME_CHAIN)

    def _dedupe_key(self, inputs: dict[str, Any]) -> str:
        raw = "|".join([
            str(inputs.get("rail") or ""),
            str(inputs.get("family") or inputs.get("strategy_family") or ""),
            str(inputs.get("mechanism_key") or inputs.get("mechanism") or "")[:80],
            str(inputs.get("instrument") or inputs.get("regime") or ""),
            str(inputs.get("proposal_class") or ""),
        ])
        return hashlib.sha256(raw.encode()).hexdigest()[:16] if raw.strip("|") else self._id("dk")[:16]

    def _directive(self, db: Any, role: str, instruction: str, priority: str = "critical",
                   workflow_id: str | None = None) -> bool:
        now = time.time()
        if workflow_id:
            existing = db.scalar(
                "SELECT id FROM ops_directives WHERE role=? AND status='OPEN' AND requested_by='workflow_engine' "
                "AND instruction LIKE ? AND ts > ? LIMIT 1",
                (role, f"%{workflow_id}%", now - _DIRECTIVE_COALESCE_S),
            )
            if existing:
                return False
        db.execute(
            "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
            "VALUES(?,?,?,?,?,?)",
            (now, role, instruction[:2000], priority, "OPEN", "workflow_engine"),
        )
        return True

    def _wake_role(self, role: str) -> None:
        """Event-wake: mark urgent so cron gate allows immediate fire."""
        try:
            db = self.f.db
            db.kv_set(f"lab.wake_urgent.{role}", {"ts": time.time(), "reason": "orchestration_handoff"})
            # employment / officer_dispatch hooks
            for attr in ("officer_dispatch", "employment"):
                obj = getattr(self.f, attr, None)
                if obj and hasattr(obj, "force_wake"):
                    try:
                        obj.force_wake(role)
                    except Exception:
                        pass
        except Exception:
            pass

    def start(
        self,
        proposal_class: str,
        trigger: str,
        inputs: dict[str, Any] | None = None,
        due_s: float = _HANDOFF_DUE_S,
    ) -> str:
        pc = (proposal_class or "DIAGNOSTIC").upper()
        if pc not in PROPOSAL_CLASSES:
            pc = "DIAGNOSTIC"
        wf_type = {
            "INCOME": "INCOME_ORCHESTRATION",
            "DIAGNOSTIC": "DIAGNOSTIC_ORCHESTRATION",
            "INFRASTRUCTURE": "INFRASTRUCTURE_ORCHESTRATION",
        }[pc]
        return self._start(wf_type, trigger, {**(inputs or {}), "proposal_class": pc}, due_s)

    def start_opportunity_cycle(self, trigger: str, inputs: dict[str, Any] | None = None,
                                due_s: float = _HANDOFF_DUE_S) -> str:
        """Compat: default DIAGNOSTIC unless inputs declare INCOME."""
        pc = str((inputs or {}).get("proposal_class") or "DIAGNOSTIC").upper()
        return self.start(pc, trigger, inputs, due_s)

    def start_alpha_cycle(self, trigger: str, inputs: dict[str, Any] | None = None,
                          due_s: float = _HANDOFF_DUE_S) -> str:
        return self._start("ALPHA_GENERATION", trigger, inputs, due_s)

    def start_income(self, trigger: str, inputs: dict[str, Any] | None = None) -> str:
        return self.start("INCOME", trigger, inputs)

    def start_diagnostic(self, trigger: str, inputs: dict[str, Any] | None = None) -> str:
        return self.start("DIAGNOSTIC", trigger, inputs)

    def _start(self, wf_type: str, trigger: str, inputs: dict[str, Any] | None,
               due_s: float) -> str:
        db = self.f.db
        now = time.time()
        inp = dict(inputs or {})
        inp.setdefault("trigger", trigger)
        # Defaults for optional stages
        pc = str(inp.get("proposal_class") or (
            "INCOME" if wf_type == "INCOME_ORCHESTRATION" else
            "DIAGNOSTIC" if wf_type == "DIAGNOSTIC_ORCHESTRATION" else
            "INFRASTRUCTURE" if wf_type == "INFRASTRUCTURE_ORCHESTRATION" else "DIAGNOSTIC"
        )).upper()
        inp["proposal_class"] = pc
        if "needs_early_exec" not in inp:
            # Auto: microstructure-sensitive families need early Reid on INCOME
            fam = str(inp.get("family") or inp.get("strategy_family") or "").lower()
            rail = str(inp.get("rail") or "").lower()
            micro = any(k in fam or k in rail for k in (
                "mm", "market_make", "spread", "arb", "triangle", "peg", "micro", "event", "kalshi",
            ))
            inp["needs_early_exec"] = bool(pc == "INCOME" and micro)
        if "needs_safety_review" not in inp:
            size = float(inp.get("paper_size_usd") or inp.get("test_size_usd") or 0)
            inp["needs_safety_review"] = bool(size > 0 or pc == "INCOME")

        dk = str(inp.get("dedupe_key") or self._dedupe_key(inp))
        inp["dedupe_key"] = dk

        # One active workflow per dedupe key (not one global)
        existing = db.query_one(
            "SELECT workflow_id, stage, owner, status FROM agent_workflows "
            "WHERE status='OPEN' AND (dedupe_key=? OR inputs_json LIKE ?) "
            "ORDER BY created_at DESC LIMIT 1",
            (dk, f"%{dk}%"),
        )
        if existing:
            return existing["workflow_id"]

        # Block INCOME starts that claim proven on CONTAMINATED rails
        if pc == "INCOME" and self.memory:
            blk = self.memory.blocks_income_claim(
                str(inp.get("family") or "unknown"), str(inp.get("rail") or "unknown"),
            )
            if blk and not inp.get("override_negative_memory"):
                # Redirect to diagnostic reopen
                inp["proposal_class"] = "DIAGNOSTIC"
                inp["redirected_from_income"] = blk.get("mem_id")
                inp["reason_redirect"] = blk.get("reason")
                wf_type = "DIAGNOSTIC_ORCHESTRATION"
                pc = "DIAGNOSTIC"

        chain = self._chain(wf_type)
        wid = self._id("wf")
        stage_owner, payload_type = chain[0]
        lifecycle = "OBSERVED" if pc != "DIAGNOSTIC" else "DIAGNOSTIC"
        db.execute(
            "INSERT INTO agent_workflows(workflow_id,objective_id,type,stage,owner,status,"
            "created_at,due_at,inputs_json,class,dedupe_key,lifecycle,proposal_class) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (wid, None, wf_type, payload_type, stage_owner, "OPEN",
             now, now + due_s, json.dumps(inp)[:8000], pc, dk, lifecycle, pc),
        )
        self._insert_handoff(
            db, wid, "system", stage_owner, payload_type, inp, now + due_s,
            decision=f"Produce typed {payload_type}",
            success=f"{payload_type} filed with evidence",
            fail="NO_ACTION_JUSTIFIED or BLOCKED with evidence",
            next_owner=chain[1][0] if len(chain) > 1 else "ops",
        )
        self._directive(
            db, stage_owner,
            f"ORCHESTRATION {wid} class={pc} type={wf_type} stage={payload_type} dedupe={dk}: {trigger}. "
            f"{STAGE_BRIEF.get(payload_type, '')} Results contract required. workflow_id={wid}",
            "critical", wid,
        )
        self._wake_role(stage_owner)
        db.kv_set("lab.workflow_latest", {
            "workflow_id": wid, "ts": now, "trigger": trigger, "type": wf_type,
            "proposal_class": pc, "dedupe_key": dk,
        })
        # Scorecard timing
        timings = db.kv_get("lab.workflow_timings") or {}
        timings[wid] = {"t0": now, "stages": {payload_type: now}, "proposal_class": pc}
        db.kv_set("lab.workflow_timings", timings)
        return wid

    def _insert_handoff(
        self, db: Any, wid: str, from_role: str, to_role: str, payload_type: str,
        payload: dict[str, Any], due_at: float, *, decision: str, success: str,
        fail: str, next_owner: str,
    ) -> str:
        hid = self._id("ho")
        now = time.time()
        try:
            db.execute(
                "INSERT INTO agent_handoffs(handoff_id,workflow_id,from_role,to_role,payload_type,"
                "payload_json,due_at,status,created_at,decision_required,success_condition,"
                "fail_condition,next_owner,deadline_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (hid, wid, from_role, to_role, payload_type, json.dumps(payload)[:8000],
                 due_at, "PENDING", now, decision[:500], success[:500], fail[:500],
                 next_owner[:40], due_at),
            )
        except Exception:
            db.execute(
                "INSERT INTO agent_handoffs(handoff_id,workflow_id,from_role,to_role,payload_type,"
                "payload_json,due_at,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (hid, wid, from_role, to_role, payload_type, json.dumps(payload)[:8000],
                 due_at, "PENDING", now),
            )
        return hid

    def _next_lifecycle(self, wf_type: str, payload_type: str, result_type: str) -> str:
        m = {
            "ANOMALY_DETECT": "OBSERVED",
            "UNCERTAINTY_IDENTIFY": "DIAGNOSTIC",
            "STRATEGY_ALGORITHM": "STRATEGY_FORMULATED",
            "EARLY_EXEC_FEASIBILITY": "EXECUTION_FEASIBLE",
            "EVIDENCE_GATE": "EVIDENCE_PASS",
            "EVIDENCE_SCREEN": "EVIDENCE_PASS",
            "RISK_GATE": "RISK_PASS",
            "RISK_ANALYSIS": "RISK_PASS",
            "SAFETY_REVIEW": "RISK_PASS",
            "CAPITAL_ALLOCATION": "PAPER_ALLOCATED",
            "CAPITAL_COMMIT": "PAPER_ALLOCATED",
            "EXECUTION_PLAN": "EXECUTED",
            "MEASURE_RESULT": "MEASURED",
            "MEASURE_INTERPRET": "MEASURED",
        }
        if result_type in ("VETO", "REJECTED", "FAIL"):
            return "RETIRE"
        return m.get(payload_type, "HYPOTHESIS")

    def _income_ready(self, payload: dict[str, Any]) -> tuple[bool, str]:
        """INCOME cannot reach capital without STRATEGY + ALGORITHM."""
        strat = payload.get("strategy") or (payload.get("opportunity") or {}).get("strategy")
        algo = payload.get("algorithm") or (payload.get("opportunity") or {}).get("algorithm")
        if not strat:
            return False, "missing STRATEGY (mechanism, inefficiency, counterparty, regime, invalidation)"
        if not algo:
            return False, "missing ALGORITHM (data, signals, entry/exit, fees, kill criteria)"
        return True, "ok"

    def _capacity_ok(self, payload: dict[str, Any]) -> tuple[bool, str]:
        cap = payload.get("capacity") or (payload.get("opportunity") or {}).get("capacity")
        if not cap:
            return False, "missing CAPACITY analysis (size→fill→slippage→marginal TRUE-NET)"
        return True, "ok"

    def advance(self, workflow_id: str, from_role: str, payload_type: str,
                payload: dict[str, Any], result_type: str = "DECISION_MADE",
                confidence: float = 0.5, skip_reason: str | None = None) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        wf = db.query_one("SELECT * FROM agent_workflows WHERE workflow_id=?", (workflow_id,))
        if not wf:
            return {"error": "unknown_workflow"}
        wf = dict(wf)
        chain = self._chain(wf.get("type") or "INCOME_ORCHESTRATION")
        inputs = {}
        try:
            inputs = json.loads(wf.get("inputs_json") or "{}")
        except Exception:
            inputs = {}
        pc = str(wf.get("proposal_class") or wf.get("class") or inputs.get("proposal_class") or "DIAGNOSTIC").upper()

        db.execute(
            "UPDATE agent_handoffs SET status='DONE', completed_at=? "
            "WHERE workflow_id=? AND to_role=? AND status='PENDING'",
            (now, workflow_id, from_role),
        )

        idx = next((i for i, (_r, p) in enumerate(chain) if p == payload_type), None)
        if idx is None:
            return {
                "error": "payload_type_not_in_chain",
                "workflow_id": workflow_id,
                "wf_type": wf.get("type"),
                "payload_type": payload_type,
                "expected": [p for _r, p in chain],
            }

        # Structural gates
        if pc == "INCOME" and payload_type == "STRATEGY_ALGORITHM":
            ok, why = self._income_ready(payload)
            if not ok and result_type not in ("NO_ACTION_JUSTIFIED", "VETO", "REJECTED"):
                # Bounce to Quinn — do not advance
                self._directive(
                    db, "alpha_inventor",
                    f"STRUCTURAL GATE {workflow_id}: {why}. Re-file STRATEGY_ALGORITHM with both sections.",
                    "critical", workflow_id,
                )
                return {"error": "income_requires_strategy_and_algorithm", "why": why, "workflow_id": workflow_id}

        if pc == "INCOME" and payload_type == "CAPITAL_ALLOCATION":
            ok, why = self._capacity_ok(payload)
            if not ok and result_type not in ("NO_ACTION_JUSTIFIED", "VETO", "REJECTED"):
                self._directive(
                    db, "governor",
                    f"CAPACITY GATE {workflow_id}: {why}. Cyrus must estimate marginal next-dollar value.",
                    "critical", workflow_id,
                )
                return {"error": "income_requires_capacity", "why": why, "workflow_id": workflow_id}

        # Diagnostics cannot silently become income capital
        if pc == "DIAGNOSTIC" and payload_type in ("CAPITAL_ALLOCATION", "CAPITAL_COMMIT"):
            size = float(payload.get("paper_size_usd") or payload.get("commit_usd") or 0)
            max_diag = float(inputs.get("max_diagnostic_usd") or 50)
            if size > max_diag:
                return {"error": "diagnostic_capital_cap", "max": max_diag, "asked": size}

        next_idx = idx + 1
        rid = self._id("ar")
        db.execute(
            "INSERT INTO agent_results(report_id,role,objective_id,workflow_id,action_type,summary,"
            "evidence_refs,economic_attribution,next_action,next_owner,next_review_at,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, from_role, wf.get("objective_id"), workflow_id, result_type,
             json.dumps(payload)[:2000], json.dumps(payload.get("evidence_refs") or []),
             json.dumps(payload.get("economic_attribution") or {}),
             payload.get("next_action"), None, now + _HANDOFF_DUE_S, now),
        )

        # timings
        timings = db.kv_get("lab.workflow_timings") or {}
        t = timings.get(workflow_id) or {"t0": now, "stages": {}}
        t.setdefault("stages", {})[payload_type] = now
        timings[workflow_id] = t
        db.kv_set("lab.workflow_timings", timings)

        lifecycle = self._next_lifecycle(wf.get("type") or "", payload_type, result_type)
        try:
            db.execute(
                "UPDATE agent_workflows SET lifecycle=?, outputs_json=? WHERE workflow_id=?",
                (lifecycle, json.dumps(payload)[:4000], workflow_id),
            )
        except Exception:
            pass

        measure_stages = ("MEASURE_RESULT", "MEASURE_INTERPRET")
        close_stages = ("CLOSE_LEARN", "MEMORY_UPDATE", "EXECUTIVE_FOLLOWTHROUGH", "TRACK")
        # Measure must always reach Luke close/memory — FAIL is a measured answer, not a skip
        veto = (
            result_type in ("VETO", "REJECTED", "FAIL", "BLOCKED")
            and payload.get("terminal", result_type in ("VETO", "REJECTED", "FAIL"))
            and payload_type not in measure_stages
        )
        # Skip optional stages
        while next_idx < len(chain):
            nr, np = chain[next_idx]
            skip_key = OPTIONAL_SKIP.get(np)
            if skip_key and not inputs.get(skip_key, True):
                next_idx += 1
                continue
            # Skip SAFETY_REVIEW if Vale not needed
            if np == "SAFETY_REVIEW" and not inputs.get("needs_safety_review", True):
                next_idx += 1
                continue
            break

        if veto or next_idx >= len(chain):
            # Economic success only if a measure stage ran
            stages_seen = set(((timings.get(workflow_id) or {}).get("stages") or {}).keys())
            measured = payload_type in measure_stages or bool(stages_seen & set(measure_stages))
            final_rt = result_type
            if payload_type in close_stages and measured:
                # Prefer measure verdict already recorded
                prior = db.query_one(
                    "SELECT action_type, summary FROM agent_results WHERE workflow_id=? AND "
                    "action_type IN ('PASS','FAIL','INCONCLUSIVE','BLOCKED','ACTION_TAKEN','DECISION_MADE') "
                    "ORDER BY created_at DESC LIMIT 5",
                    (workflow_id,),
                )
                # Keep CLOSE result but mark measured completion
                if final_rt == "INCOMPLETE_NO_MEASURE":
                    final_rt = "MEASURED"
                # If ops closes after measure PASS/FAIL, use that economic answer
                mrow = db.query_one(
                    "SELECT action_type FROM agent_results WHERE workflow_id=? ORDER BY created_at DESC LIMIT 20",
                    (workflow_id,),
                )
                # Scan results for measure stage via timings
                if "MEASURE_RESULT" in stages_seen or "MEASURE_INTERPRET" in stages_seen:
                    # Find last measure-ish result
                    rows = db.query(
                        "SELECT action_type, summary FROM agent_results WHERE workflow_id=? ORDER BY created_at ASC",
                        (workflow_id,),
                    ) or []
                    for r in rows:
                        # last non-close result wins if PASS/FAIL
                        if r["action_type"] in ("PASS", "FAIL", "INCONCLUSIVE", "BLOCKED"):
                            final_rt = r["action_type"]
            elif next_idx >= len(chain) and not measured and result_type not in (
                "VETO", "REJECTED", "FAIL", "BLOCKED", "NO_ACTION_JUSTIFIED",
            ):
                final_rt = "INCOMPLETE_NO_MEASURE"
            life = "MEASURED" if measured else lifecycle
            db.execute(
                "UPDATE agent_workflows SET status='DONE', completed_at=?, result_type=?, "
                "confidence=?, outputs_json=?, skip_reason=?, lifecycle=? WHERE workflow_id=?",
                (now, final_rt, confidence, json.dumps(payload)[:4000], skip_reason,
                 life, workflow_id),
            )
            self._on_complete(wf, payload, final_rt, pc, inputs)
            return {"workflow_id": workflow_id, "status": "DONE", "result_type": final_rt}

        # If advancing past measure into CLOSE — ok
        next_role, next_payload = chain[next_idx]

        # After STRATEGY_ALGORITHM on INCOME, if early exec skipped, loop already handled
        db.execute(
            "UPDATE agent_workflows SET stage=?, owner=?, outputs_json=? WHERE workflow_id=?",
            (next_payload, next_role, json.dumps(payload)[:4000], workflow_id),
        )
        brief = STAGE_BRIEF.get(next_payload, "Produce next gate/decision.")
        hid = self._insert_handoff(
            db, workflow_id, from_role, next_role, next_payload, payload, now + _HANDOFF_DUE_S,
            decision=f"{brief}",
            success=f"Typed {next_payload} with evidence",
            fail="VETO/FAIL/BLOCKED with evidence or NO_ACTION_JUSTIFIED",
            next_owner=chain[next_idx + 1][0] if next_idx + 1 < len(chain) else "ops",
        )
        self._directive(
            db, next_role,
            f"HANDOFF {hid} workflow={workflow_id} class={pc} type={next_payload} from={from_role}. {brief} "
            f"Results contract required.",
            "critical", workflow_id,
        )
        self._wake_role(next_role)

        if next_payload in ("CAPITAL_ALLOCATION", "ALLOCATION_DECISION"):
            self._directive(
                db, "treasury",
                f"Ellis: coordinate capital with Cyrus for {workflow_id} class={pc}. "
                f"Treasury truth + marginal $/capital-hour + size. Diagnostics = minimum sensible test capital only.",
                "high", workflow_id,
            )
            self._wake_role("treasury")

        # Parallel Ada note on MEASURE_INTERPRET
        if next_payload == "MEASURE_INTERPRET":
            self._directive(
                db, "critic",
                f"Ada: co-interpret MEASURE for {workflow_id}. PASS|FAIL|INCONCLUSIVE|BLOCKED + next action.",
                "high", workflow_id,
            )

        return {
            "workflow_id": workflow_id,
            "next_role": next_role,
            "next_payload": next_payload,
            "handoff_id": hid,
            "proposal_class": pc,
        }

    def _on_complete(self, wf: dict[str, Any], payload: dict[str, Any], result_type: str,
                     pc: str, inputs: dict[str, Any]) -> None:
        db = self.f.db
        now = time.time()
        wid = wf["workflow_id"]
        timings = (db.kv_get("lab.workflow_timings") or {}).get(wid) or {}
        t0 = float(timings.get("t0") or wf.get("created_at") or now)
        elapsed = now - t0
        family = str(inputs.get("family") or (payload.get("opportunity") or {}).get("family") or "unknown")
        rail = str(inputs.get("rail") or (payload.get("opportunity") or {}).get("rail") or "unknown")
        delta = None
        try:
            delta = float((payload.get("economic_attribution") or {}).get("delta_usd_per_h")
                          or payload.get("delta_usd_per_h"))
        except Exception:
            delta = None

        if self.memory and result_type in (
            "PASS", "FAIL", "INCONCLUSIVE", "BLOCKED", "ACTION_TAKEN", "DECISION_MADE",
            "VETO", "REJECTED", "MEASURED",
        ):
            try:
                self.memory.learn_from_measure(
                    proposal_class=pc, family=family, rail=rail,
                    result=str(payload.get("measure_verdict") or result_type),
                    summary=str(payload.get("summary") or result_type)[:500],
                    delta_usd_per_h=delta, owner="ops",
                )
            except Exception as e:
                log.warning("learn_from_measure: %s", e)

        # Money-moving scorecard
        sc = db.kv_get("lab.money_scorecard") or {"workflows": [], "totals": {}}
        sc.setdefault("workflows", []).append({
            "workflow_id": wid, "class": pc, "result_type": result_type,
            "elapsed_s": elapsed, "delta_usd_per_h": delta, "ts": now,
            "family": family, "rail": rail,
        })
        sc["workflows"] = sc["workflows"][-50:]
        tot = sc.setdefault("totals", {})
        tot["n_complete"] = int(tot.get("n_complete") or 0) + 1
        tot["sum_delta_usd_per_h"] = float(tot.get("sum_delta_usd_per_h") or 0) + float(delta or 0)
        tot["sum_time_to_answer_s"] = float(tot.get("sum_time_to_answer_s") or 0) + elapsed
        sc["ts"] = now
        db.kv_set("lab.money_scorecard", sc)
        db.kv_set("lab.luke_orchestration", {
            "ts": now,
            "last_closed": wid,
            "result_type": result_type,
            "class": pc,
            "elapsed_s": elapsed,
            "delta_usd_per_h": delta,
            "open": self.board_for_luke(),
        })

    def board_for_luke(self) -> dict[str, Any]:
        db = self.f.db
        open_wf = db.query(
            "SELECT workflow_id,type,stage,owner,status,proposal_class,class,dedupe_key,lifecycle,"
            "created_at,due_at FROM agent_workflows WHERE status='OPEN' ORDER BY created_at DESC LIMIT 30"
        ) or []
        overdue = db.query(
            "SELECT handoff_id,workflow_id,to_role,payload_type,due_at FROM agent_handoffs "
            "WHERE status='PENDING' AND due_at IS NOT NULL AND due_at<? LIMIT 20",
            (time.time(),),
        ) or []
        return {
            "open_workflows": [dict(r) for r in open_wf],
            "overdue_handoffs": [dict(r) for r in overdue],
            "scorecard": db.kv_get("lab.money_scorecard"),
            "memory": db.kv_get("lab.opportunity_memory"),
        }

    def pending_for(self, role: str) -> list[dict[str, Any]]:
        try:
            rows = self.f.db.query(
                "SELECT * FROM agent_handoffs WHERE to_role=? AND status='PENDING' "
                "ORDER BY created_at ASC LIMIT 20",
                (role,),
            ) or []
            return [dict(r) for r in rows]
        except Exception:
            return []

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        actions: list[dict[str, Any]] = []
        if self.memory:
            try:
                self.memory.ensure_schema()
                self.memory.tick()
            except Exception as e:
                actions.append({"memory_err": str(e)[:120]})

        try:
            overdue = db.query(
                "SELECT * FROM agent_handoffs WHERE status='PENDING' AND due_at IS NOT NULL AND due_at<? LIMIT 20",
                (now,),
            ) or []
        except Exception as e:
            return {"error": str(e)[:200]}

        for h in overdue:
            d = dict(h)
            inserted = self._directive(
                db, d["to_role"],
                f"OVERDUE HANDOFF {d['handoff_id']} type={d['payload_type']} "
                f"workflow={d['workflow_id']}. Complete or BLOCKED with evidence. Luke tracking.",
                "critical", d["workflow_id"],
            )
            if inserted:
                actions.append({"overdue": d["handoff_id"], "role": d["to_role"]})
                self._wake_role(d["to_role"])
            # Page Luke
            self._directive(
                db, "ops",
                f"Luke: overdue {d['handoff_id']} owner={d['to_role']} wf={d['workflow_id']} "
                f"stage={d['payload_type']}. Follow to RESULT|BLOCKER|FOUNDER DECISION.",
                "high", d["workflow_id"],
            )

        vel = db.kv_get("velocity") or {}
        proven = float(vel.get("proven_usd_per_h") or vel.get("frontier_usd_per_h") or 0)
        # Seed diagnostic on contaminated stables if none open for that dedupe
        if self.memory and proven < 0.50:
            blk = self.memory.blocks_income_claim("stable_triangle", "coinbase.stable_triangle")
            if not blk:
                # Ensure contamination memory exists while ledger disputed
                try:
                    self.memory.record_negative(
                        family="stable_triangle",
                        rail="coinbase.stable_triangle",
                        status="CONTAMINATED",
                        reason="Do not claim proven income until peg-specific ledger is reconciled",
                        reopen_condition="clean instrument-specific fee/fill evidence exists",
                        superseding_test="DIAGNOSTIC peg ledger reconciliation",
                        owner="critic",
                        confidence=0.85,
                        ttl_h=72,
                    )
                except Exception:
                    pass

        open_n = db.scalar("SELECT COUNT(*) FROM agent_workflows WHERE status='OPEN'") or 0
        board = self.board_for_luke()
        rep = {
            "ts": now,
            "actions": actions,
            "open_workflows": int(open_n),
            "proven_usd_per_h": proven,
            "luke": {"n_open": len(board.get("open_workflows") or []),
                     "n_overdue": len(board.get("overdue_handoffs") or [])},
        }
        db.kv_set("lab.workflow_engine", rep)
        db.kv_set("lab.luke_orchestration", {**(db.kv_get("lab.luke_orchestration") or {}), **board, "ts": now})
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("workflow_engine")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("workflow: %s", e, exc_info=True)
            await asyncio.sleep(90)
