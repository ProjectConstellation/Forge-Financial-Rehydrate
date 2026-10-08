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
