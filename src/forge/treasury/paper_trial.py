"""24h+ PAPER full-dress trial — continues past window; opens next $1/h constraint objective."""
from __future__ import annotations

import time
from typing import Any

PRIMARY_TARGET = 1.0
DIAGNOSTIC = 0.50


def start_trial(forge: Any, hours: float = 24.0) -> dict[str, Any]:
    now = time.time()
    vel = forge.db.kv_get("velocity") or {}
    st = {
        "status": "RUNNING",
        "mode": "PAPER_REAL_MARKET_SIM_MONEY",
        "started_ts": now,
        "ends_ts": now + hours * 3600,
        "target_usd_per_h": PRIMARY_TARGET,
        "diagnostic_progress_usd_per_h": DIAGNOSTIC,
        "start_treasury": (vel.get("treasury") or {}).get("total"),
        "start_metrics": {
            "proven": (vel.get("expected_usd_per_h") or {}).get("proven"),
            "potential": (vel.get("expected_usd_per_h") or {}).get("potential"),
            "realized_1h": ((vel.get("realized") or {}).get("1h") or {}).get("usd_per_h"),
        },
        "note": "Primary objective >= $1.00/h TRUE-NET. $0.50/h is diagnostic only. LIVE algorithmic trading OFF. Firm does not stop when the window ends.",
    }
    forge.db.kv_set("paper_trial", st)
    forge.db.kv_set("firm.state", {
        "ts": now, "mode": st["mode"], "trial": st,
        "target_usd_per_h": PRIMARY_TARGET, "diagnostic_progress_usd_per_h": DIAGNOSTIC,
    })
    return st


def snapshot(forge: Any) -> dict[str, Any]:
    st = forge.db.kv_get("paper_trial") or {}
    if not st:
        return {"status": "NOT_STARTED"}
    vel = forge.db.kv_get("velocity") or {}
    now = time.time()
    st["last_snap_ts"] = now
    st["elapsed_h"] = round((now - float(st.get("started_ts") or now)) / 3600, 3)
    st["current"] = {
        "treasury": (vel.get("treasury") or {}).get("total"),
        "realized_1h": ((vel.get("realized") or {}).get("1h") or {}).get("usd_per_h"),
        "realized_24h": ((vel.get("realized") or {}).get("24h") or {}).get("usd_per_h"),
        "proven": (vel.get("expected_usd_per_h") or {}).get("proven"),
        "potential": (vel.get("expected_usd_per_h") or {}).get("potential"),
        "below_target": vel.get("below_target"),
        "below_diagnostic": vel.get("below_diagnostic"),
        "priorities": (vel.get("priorities") or [])[:5],
        "diagnosis": vel.get("diagnosis"),
    }
    # Window elapsed: do NOT stop the firm — mark window done and open next constraint objective
    if now >= float(st.get("ends_ts") or 0) and st.get("status") == "RUNNING":
        st["status"] = "WINDOW_COMPLETE_CONTINUING"
        st["window_completed_ts"] = now
        try:
            from forge.treasury.profit_recovery import open_next_constraint_objective
            st["next_constraint"] = open_next_constraint_objective(forge, vel)
        except Exception as e:
            st["next_constraint_error"] = str(e)[:200]
        # Roll a new 24h measurement window immediately (continuous operation)
        st["ends_ts"] = now + 24 * 3600
        st["status"] = "RUNNING"
        st["rolled_windows"] = int(st.get("rolled_windows") or 0) + 1
    forge.db.kv_set("paper_trial", st)
    forge.db.kv_set("firm.state", {
        "ts": now,
        "mode": st.get("mode") or "PAPER_REAL_MARKET_SIM_MONEY",
        "target_usd_per_h": PRIMARY_TARGET,
        "diagnostic_progress_usd_per_h": DIAGNOSTIC,
        "recovery": bool((forge.db.kv_get("profit_recovery") or {}).get("status") == "ACTIVE"),
        "trial": {
            "status": st.get("status"),
            "mode": st.get("mode"),
            "started_ts": st.get("started_ts"),
            "ends_ts": st.get("ends_ts"),
            "target_usd_per_h": PRIMARY_TARGET,
            "diagnostic_progress_usd_per_h": DIAGNOSTIC,
            "rolled_windows": st.get("rolled_windows") or 0,
            "elapsed_h": st.get("elapsed_h"),
            "note": st.get("note") or "Primary objective >= $1.00/h TRUE-NET. $0.50/h diagnostic only.",
        },
    })
    return st


def start_8h_trial(forge: Any) -> dict[str, Any]:
    """Blueprint §64 — active 8-hour full-dress PAPER trial with scorecard (does not stop the firm)."""
    st = start_trial(forge, hours=8.0)
    st["trial_kind"] = "FULL_DRESS_8H"
    st["scorecard"] = empty_scorecard()
    st["note"] = (
        "8h FULL-DRESS PAPER trial. PRIMARY >= $1.00/h TRUE-NET. "
        "Operational pass ≠ economic pass. Continues after window; opens next constraint if below target."
    )
    forge.db.kv_set("paper_trial", st)
    forge.db.kv_set("trial.8h", {"status": "RUNNING", "started_ts": st["started_ts"], "ends_ts": st["ends_ts"]})
    return st


def empty_scorecard() -> dict[str, Any]:
    return {
        "treasury": {}, "strategy": {}, "reallocation": {}, "research": {},
        "agents": {}, "systems": {}, "objective": {"target_usd_per_h": 1.0, "hit": None},
    }


def update_8h_scorecard(forge: Any) -> dict[str, Any]:
    st = forge.db.kv_get("paper_trial") or {}
    if st.get("trial_kind") != "FULL_DRESS_8H" and not (forge.db.kv_get("trial.8h") or {}).get("status"):
        return {"status": "NO_8H_TRIAL"}
    vel = forge.db.kv_get("velocity") or {}
    truth = forge.db.kv_get("treasury.truth") or {}
    realloc = forge.db.kv_get("capital.reallocation") or {}
    decay = forge.db.kv_get("edge_decay") or {}
    factory = forge.db.kv_get("research.algo_factory") or {}
    hb = forge.db.kv_get("agents.heartbeat") or {}
    import time
    now = time.time()
    started = float(st.get("started_ts") or now)
    elapsed = (now - started) / 3600.0
    proven = float((vel.get("expected_usd_per_h") or {}).get("proven") or 0)
    realized_1h = float(((vel.get("realized") or {}).get("1h") or {}).get("usd_per_h") or 0)
    sc = {
        "ts": now,
        "elapsed_h": round(elapsed, 3),
        "treasury": {
            "nav": truth.get("treasury_nav") or (vel.get("treasury") or {}).get("total"),
            "red_zone": truth.get("red_zone"),
            "mode": truth.get("mode_label") or st.get("mode"),
        },
        "strategy": {
            "proven_usd_per_h": proven,
            "realized_1h": realized_1h,
            "decay_actions": len(decay.get("actions") or []),
            "decay_states": decay.get("by_state"),
        },
        "reallocation": {
            "actions": len(realloc.get("actions") or []),
            "top": ((realloc.get("ranking") or [{}])[0]).get("id"),
        },
        "research": {
            "families": len((factory.get("families") or [])),
            "binding_lever": factory.get("binding_lever"),
        },
        "agents": {
            "roster_n": len(hb.get("roster") or []),
            "stale": [r["role"] for r in (hb.get("roster") or []) if r.get("employment") == "STALE"],
        },
        "systems": {"ready": True},
        "objective": {
            "target_usd_per_h": 1.0,
            "hit": bool(proven >= 1.0 or realized_1h >= 1.0),
            "gap_usd_per_h": round(1.0 - proven, 4),
        },
        "operational_pass": None,  # filled at window end
        "economic_result": "PENDING",
    }
    st["scorecard"] = sc
    st["last_snap_ts"] = now
    # window end handling
    ends = float(st.get("ends_ts") or 0)
    if ends and now >= ends and st.get("status") == "RUNNING":
        sc["operational_pass"] = True  # if we got here loops lived
        sc["economic_result"] = "HIT_TARGET" if sc["objective"]["hit"] else "MISS_TARGET"
        st["scorecard"] = sc
        st["window_completed_ts"] = now
        if not sc["objective"]["hit"]:
            try:
                from forge.treasury.profit_recovery import open_next_constraint_objective
                st["next_constraint"] = open_next_constraint_objective(forge, vel)
            except Exception as e:
                st["next_constraint_error"] = str(e)[:200]
        # continue firm — roll another measurement window but keep 8h artifact
        forge.db.kv_set("trial.8h.report", {"completed_ts": now, "scorecard": sc, "trial": {
            k: st.get(k) for k in ("started_ts", "ends_ts", "mode", "trial_kind")
        }})
        st["ends_ts"] = now + 8 * 3600
        st["rolled_windows"] = int(st.get("rolled_windows") or 0) + 1
        st["status"] = "RUNNING"
    forge.db.kv_set("paper_trial", st)
    forge.db.kv_set("trial.8h", {"status": st.get("status"), "scorecard": sc,
                                  "started_ts": st.get("started_ts"), "ends_ts": st.get("ends_ts")})
    return sc
