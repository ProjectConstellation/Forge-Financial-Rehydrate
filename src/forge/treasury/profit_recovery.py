"""Profit Recovery Protocol — open institutional objectives when PAPER true-net lags floors.

PAPER_REAL_MARKET_SIM_MONEY only affects simulated capital allocation priorities until founder
authorizes LIVE. Never flips FORGE_LIVE_TRADING.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.profit_recovery")

COOLDOWN_S = 6 * 3600


def maybe_open_recovery(forge: Any, rep: dict[str, Any]) -> dict[str, Any] | None:
    if not rep.get("below_floor") and not rep.get("below_stretch"):
        return None
    db = forge.db
    st = db.kv_get("profit_recovery") or {}
    now = time.time()
    if now - float(st.get("last_open_ts") or 0) < COOLDOWN_S and st.get("status") == "ACTIVE":
        return st
    top = (rep.get("priorities") or [{}])[0]
    mode = rep.get("mode_label") or "PAPER_REAL_MARKET_SIM_MONEY"
    floor = float(rep.get("floor_usd_per_h") or 0.5)
    stretch = float(rep.get("stretch_usd_per_h") or 1.0)
    r1 = float(rep.get("realized", {}).get("1h", {}).get("usd_per_h") or 0)
    proven = float(rep.get("expected_usd_per_h", {}).get("proven") or 0)
    objective = (
        f"PROFIT RECOVERY ({mode}): PAPER true-net below floor ${floor:.2f}/h "
        f"(1h realized ${r1:+.3f}/h, proven ${proven:.3f}/h, stretch ${stretch:.2f}/h). "
        f"Top lever: {top.get('action', 'diagnose binding constraint')}. "
        "Sequence: Tess quantify → Ada verify decay vs variance → Vale throttle weak paper streams → "
        "Cyrus/Ellis reallocate paper capital to strongest fee-survivable rails (stables, Kalshi shadow) → "
        "Quinn invent challengers → Sloane expand Coinbase/Kalshi surface → measure. "
        "NEVER force trades; NEVER enable LIVE without founder auth."
    )
    # Prefer ops_objectives table if present
    try:
        open_id = db.scalar("SELECT id FROM ops_objectives WHERE status='ACTIVE' AND kind='grow_profit' ORDER BY id DESC LIMIT 1")
        if not open_id:
            db.execute(
                "INSERT INTO ops_objectives (ts, kind, objective, status, summary) VALUES (?, 'grow_profit', ?, 'ACTIVE', ?)",
                (now, objective, json.dumps({"source": "profit_recovery", "top_lever": top}, default=str)[:2000]),
            )
            open_id = db.scalar("SELECT last_insert_rowid()")
        # Directive to governor
        db.execute(
            "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
            (now, "governor", objective[:1900], "high", "OPEN", "profit_recovery"),
        )
    except Exception as e:
        log.warning("ops tables write failed: %s", e)
        open_id = None
    st = {
        "status": "ACTIVE",
        "last_open_ts": now,
        "objective_id": open_id,
        "mode": mode,
        "floor": floor,
        "stretch": stretch,
        "top_lever": top,
        "diagnosis": rep.get("diagnosis"),
    }
    db.kv_set("profit_recovery", st)
    db.kv_set("firm.state", {
        "ts": now,
        "mode": mode,
        "floor_usd_per_h": floor,
        "stretch_usd_per_h": stretch,
        "recovery": True,
        "trial": db.kv_get("paper_trial") or {},
    })
    return st
