"""24h PAPER full-dress trial instrumentation (blueprint §59–§71)."""
from __future__ import annotations

import time
from typing import Any


def start_trial(forge: Any, hours: float = 24.0) -> dict[str, Any]:
    now = time.time()
    vel = forge.db.kv_get("velocity") or {}
    st = {
        "status": "RUNNING",
        "mode": "PAPER_REAL_MARKET_SIM_MONEY",
        "started_ts": now,
        "ends_ts": now + hours * 3600,
        "floor_usd_per_h": 0.50,
        "stretch_usd_per_h": 1.00,
        "start_treasury": (vel.get("treasury") or {}).get("total"),
        "start_metrics": {
            "proven": (vel.get("expected_usd_per_h") or {}).get("proven"),
            "potential": (vel.get("expected_usd_per_h") or {}).get("potential"),
            "realized_1h": ((vel.get("realized") or {}).get("1h") or {}).get("usd_per_h"),
        },
        "note": "Algorithmic LIVE money remains OFF. Trial tests firm + portfolio on real markets / simulated money.",
    }
    forge.db.kv_set("paper_trial", st)
    forge.db.kv_set("firm.state", {"ts": now, "mode": st["mode"], "trial": st, "floor_usd_per_h": 0.5, "stretch_usd_per_h": 1.0})
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
        "below_floor": vel.get("below_floor"),
        "priorities": (vel.get("priorities") or [])[:5],
        "diagnosis": vel.get("diagnosis"),
    }
    if now >= float(st.get("ends_ts") or 0) and st.get("status") == "RUNNING":
        st["status"] = "COMPLETE_PENDING_REPORT"
    forge.db.kv_set("paper_trial", st)
    return st
