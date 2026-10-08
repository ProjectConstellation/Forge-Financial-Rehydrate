"""Profit Recovery — open institutional objectives when PAPER true-net lags the PRIMARY $1/h target.

$0.50/h is diagnostic progress only — never the optimization target.
Capital follows evidence-ranked rails/strategies; no hard-coded asset-class preference.
Never flips FORGE_LIVE_TRADING.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.profit_recovery")
COOLDOWN_S = 6 * 3600
PRIMARY_TARGET = 1.0


def maybe_open_recovery(forge: Any, rep: dict[str, Any]) -> dict[str, Any] | None:
    # Primary trigger: below $1/h target (proven or 24h realized)
    if not rep.get("below_target"):
        return None
    db = forge.db
    st = db.kv_get("profit_recovery") or {}
    now = time.time()
    if now - float(st.get("last_open_ts") or 0) < COOLDOWN_S and st.get("status") == "ACTIVE":
        return st
    top = (rep.get("priorities") or [{}])[0]
    mode = rep.get("mode_label") or "PAPER_REAL_MARKET_SIM_MONEY"
    target = float(rep.get("target_primary_usd_per_h") or rep.get("operator_min_usd_per_h") or PRIMARY_TARGET)
    diagnostic = float(rep.get("diagnostic_progress_usd_per_h") or 0.5)
    r1 = float(rep.get("realized", {}).get("1h", {}).get("usd_per_h") or 0)
    r24 = float(rep.get("realized", {}).get("24h", {}).get("usd_per_h") or 0)
    proven = float(rep.get("expected_usd_per_h", {}).get("proven") or 0)
    objective = (
        f"PROFIT RECOVERY ({mode}): below PRIMARY target ${target:.2f}/h TRUE-NET "
        f"(1h ${r1:+.3f}/h, 24h ${r24:+.3f}/h, proven ${proven:.3f}/h; diagnostic progress mark ${diagnostic:.2f}/h). "
        f"Largest evidence-supported lever NOW: {top.get('action', 'diagnose binding constraint')} "
        f"(not a permanent asset-class preference — re-rank continuously). "
        "Protocol: DETECT→VERIFY→REDUCE/PAUSE→DIAGNOSE→REALLOCATE→CHALLENGER→VALIDATE→PROMOTE→MONITOR. "
        "Spot crypto stays PAPER until fee-aware forward +EV. Never force trades. Never enable LIVE without founder auth. "
        "Moat = proprietary algorithms/features/allocator/execution — external feeds are inputs only."
    )
    try:
        open_id = db.scalar(
            "SELECT id FROM ops_objectives WHERE status='ACTIVE' AND kind='grow_profit' ORDER BY id DESC LIMIT 1")
        if not open_id:
            db.execute(
                "INSERT INTO ops_objectives (ts, kind, objective, status, summary) VALUES (?, 'grow_profit', ?, 'ACTIVE', ?)",
                (now, objective, json.dumps({"source": "profit_recovery", "target": target, "top_lever": top}, default=str)[:2000]),
            )
            open_id = db.scalar("SELECT last_insert_rowid()")
        db.execute(
            "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
            (now, "governor", objective[:1900], "high", "OPEN", "profit_recovery"),
        )
    except Exception as e:
        log.warning("ops tables write failed: %s", e)
        open_id = None
    st = {
        "status": "ACTIVE", "last_open_ts": now, "objective_id": open_id, "mode": mode,
        "target_usd_per_h": target, "diagnostic_usd_per_h": diagnostic, "top_lever": top,
        "diagnosis": rep.get("diagnosis"),
    }
    db.kv_set("profit_recovery", st)
    db.kv_set("firm.state", {
        "ts": now, "mode": mode, "target_usd_per_h": target,
        "diagnostic_progress_usd_per_h": diagnostic, "recovery": True,
        "trial": db.kv_get("paper_trial") or {},
    })
    return st


def open_next_constraint_objective(forge: Any, rep: dict[str, Any] | None = None) -> dict[str, Any]:
    """After a trial window: identify largest constraint to $1/h and open the next objective (never stop the firm)."""
    rep = rep or forge.db.kv_get("velocity") or {}
    top = (rep.get("priorities") or [{"action": "diagnose binding constraint to $1/h true-net"}])[0]
    diag = "; ".join(rep.get("diagnosis") or [])[:500]
    now = time.time()
    objective = (
        f"NEXT CONSTRAINT (primary target $1.00/h TRUE-NET): {top.get('action')}. "
        f"Evidence: {diag or 'see velocity.priorities'}. "
        "Continue PAPER_REAL_MARKET_SIM_MONEY; capital follows continuous re-ranking; "
        "build/validate proprietary challengers; do not hard-code rails."
    )
    try:
        forge.db.execute(
            "INSERT INTO ops_objectives (ts, kind, objective, status, summary) VALUES (?, 'next_constraint', ?, 'ACTIVE', ?)",
            (now, objective, json.dumps({"top": top, "source": "trial_continue"}, default=str)[:2000]),
        )
        oid = forge.db.scalar("SELECT last_insert_rowid()")
    except Exception as e:
        log.warning("next_constraint objective failed: %s", e)
        oid = None
    out = {"ts": now, "objective_id": oid, "action": top.get("action"), "target_usd_per_h": 1.0}
    forge.db.kv_set("firm.next_constraint", out)
    return out
