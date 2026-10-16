"""Cost/result visibility and compact role contracts, shared by briefs, Luca, and dashboard."""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

QUESTIONS = {
    "ops": "Luca: close each authorized objective with an action receipt, measured result or named blocker; report net earnings/costs and the next owner.",
    "scout": "Tess: detect one fresh feasible anomaly; include quote age, liquidity, session and net-cost hurdle. Reuse failures; hand mechanisms to Quinn.",
    "alpha_inventor": "Quinn: specify one novel mechanism and executable algorithm, capacity, baseline, falsification and kill criteria; no blind parameter sweep.",
    "critic": "Ada: independently test causal data, leakage, trials and forward evidence. PASS requires independent data; rejection must change the next decision.",
    "adversary": "Vale: challenge ruin, correlation, leg/fill risk, settlement and stale data; give the concrete condition that would remove a veto.",
    "governor": "Cyrus: rank all eligible portfolios by marginal net value/capital-hour under common reserves, evidence and capacity; no permanent rail preference.",
    "treasury": "Ellis: reconcile real cash and locked capital separately from training NAV; check fees, deposits, settlement, and operating costs before allocation.",
    "execution": "Reid: demonstrate order eligibility, session, spread, fee, partial fills, idempotency, exit and reconciliation; propose only through deterministic gateway.",
    "prediction": "Nolan: calibrate on independent event clusters and official settlement rules; compare market baseline, subtract fees, and track correlated exposure.",
    "doctor": "Diagnose one reproducible root cause, create a repair ticket with acceptance checks, and verify it; repeated diagnosis without change is waste.",
    "architect": "Design the smallest missing capability that unlocks a specific economic decision, with costs, acceptance checks and rollback.",
    "intelligence": "Audit every paid call/job against decision and outcome; scale budgets from verified live net earnings; cache unchanged evidence and stop duplicate research.",
    "rail_hunter": "Discover an eligible funded executable rail or a specific unlock; separate data-only feeds from income; verify restrictions and opportunity cost.",
}


def role_contract(role: str) -> str:
    return (QUESTIONS.get(role, "Answer one actionable, testable economic question.") +
            " Every paid task: objective/workflow ID, evidence version, hypothesis, maximum incremental cost, artifact, "
            "decision, owner/deadline, measured outcome. EARNED means reconciled settled LIVE after all Forge costs; "
            "paper/shadow forecasts and avoided losses are separate. Useful learning/repairs count as work, never cash. "
            "24/7 monitoring uses deterministic tools; wake for new actionable evidence. "
            "For executable equity work use submit_paper_experiment with an objective, mechanism, symbol, lookback and hypothesis; "
            "the broker-paper engine trials it automatically and get_research_results exposes fills, reviews and the successor. "
            "Pro high is available when decision value and budget justify it. Stop unchanged failed experiments; mutate the mechanism or obtain new data. "
            "Alpaca: paper NAV cap, account/assets/calendar, eligible limit extended orders, cash/settlement restrictions, "
            "spread/slippage/fees. Kalshi: fee schedule, settlement rules/basis, independent clusters and maintenance. "
            "No live orders or transfers without existing owner gates.")


def research_board(db: Any) -> dict[str, Any]:
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    calls = db.query("SELECT agent,COUNT(*) calls,SUM(CAST(cost_usd AS REAL)) cost_usd,MAX(ts) last_call "
                     "FROM inference_calls WHERE ts>=? GROUP BY agent ORDER BY cost_usd DESC", (cutoff,))
    jobs = db.query("SELECT id,kind,status,est_cost_usd,ts_start,ts_end,error FROM compute_jobs "
                    "ORDER BY ts_start DESC LIMIT 8")
    validation = db.query("SELECT family,where_run,COUNT(*) candidates,SUM(passed_validation) passed_validation, "
                          "SUM(promoted) promoted,MAX(ts) latest FROM research_trials WHERE ts>=? "
                          "GROUP BY family,where_run ORDER BY candidates DESC LIMIT 12", (cutoff,))
    reservations = db.query("SELECT id,provider,owner,objective_id,max_cost_usd,actual_cost_usd,state,outcome_ref,cost_basis "
                            "FROM spend_reservations WHERE state IN ('RESERVED','UNCERTAIN') ORDER BY created_at DESC LIMIT 20")
    training: dict[str, Any] = {}
    p = Path("/srv/forge/var/alpaca_research.json")
    if p.exists():
        try:
            data = json.loads(p.read_text())
            training = {k: data.get(k) for k in ("ts", "status", "rail", "training_nav_usd", "live_ready")}
            evaluation = data.get("evaluation") or {}
            training["evaluation"] = {k: evaluation.get(k) for k in (
                "algorithm_version", "n_trades", "hypothetical_net_usd", "earned_usd", "evidence_verdict", "next_action")}
        except (OSError, ValueError):
            training = {"status": "ARTIFACT_UNREADABLE"}
    forward = {}
    try:
        forward = json.loads(Path("/srv/forge/var/alpaca_forward_trials.json").read_text())
        forward["history_count"] = len(forward.get("history") or [])
        forward["history"] = (forward.get("history") or [])[-8:]
    except (OSError, ValueError):
        pass
    broker_trials = {}
    try:
        broker_trials = json.loads(Path("/srv/forge/var/alpaca_broker_trials.json").read_text())
        broker_trials["fresh"] = 0 <= time.time()-float(broker_trials.get("ts") or 0) <= 180
    except (OSError, ValueError, TypeError):
        broker_trials = {"fresh": False}
    return {"ts": time.time(), "cost_by_role_24h": calls, "recent_paid_jobs": jobs,
            "validation_receipts_24h": validation,
            "outstanding_reservations": reservations, "modal_experiment": db.kv_get("modal.experiment"),
            "alpaca_training": training, "alpaca_automatic_trials": forward,
            "alpaca_broker_experiments": broker_trials,
            "last_local_research": db.kv_get("research.last_receipt"),
            "outcome_contract": "call/job→objective→artifact→decision→outcome; no claim inferred from narrative",
            "primary_target_usd_per_hour": 1., "progress_floor_usd_per_hour": .5}
