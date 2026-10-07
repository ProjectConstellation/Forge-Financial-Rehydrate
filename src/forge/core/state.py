"""Global trading state + emergency stop (DIRECTIVE §29). PROTECTED CORE.

STOP ALL TRADING:
 1. atomically set global state STOPPED (DB, survives restarts)
 2. reject all new order requests (RiskGovernor checks this state)
 3. cancel eligible pending orders (executed by the runtime on observing the flag)
 4. close positions only per explicit safe-stop policy (default: keep protective exits active, no panic liquidation)
 5. persist state  6. emit audit event  7. displayed prominently  8. resume requires deliberate operator action
The flag is read from the DB on every risk decision, so `forge stop-all` from any process takes effect immediately.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from forge.audit.journal import AuditJournal
from forge.persistence.db import Database
from forge.risk.governor import TRADING_OBSERVE, TRADING_RUNNING, TRADING_STOPPED

KEY = "trading.state"
SAFE_STOP_POLICIES = ("keep_exits", "flatten_when_safe")


def get_state(db: Database) -> dict[str, Any]:
    return db.kv_get(KEY) or {"state": TRADING_RUNNING, "since": None, "by": "default", "reason": "",
                              "safe_stop_policy": "keep_exits"}


def trading_state(db: Database) -> str:
    return str(get_state(db)["state"])


def stop_all(db: Database, audit: AuditJournal, actor: str, reason: str,
             safe_stop_policy: str = "keep_exits") -> dict[str, Any]:
    if safe_stop_policy not in SAFE_STOP_POLICIES:
        raise ValueError(f"safe_stop_policy must be one of {SAFE_STOP_POLICIES}")
    st = {"state": TRADING_STOPPED, "since": datetime.now(UTC).isoformat(), "by": actor, "reason": reason,
          "safe_stop_policy": safe_stop_policy, "cancel_requested": True}
    with db.transaction():
        db.kv_set(KEY, st)
    audit.append("EMERGENCY_STOP", {"actor": actor, "reason": reason, "policy": safe_stop_policy}, actor=actor)
    return st


def resume(db: Database, audit: AuditJournal, actor: str, confirm: str) -> dict[str, Any]:
    """Deliberate operator action: caller must pass confirm == 'RESUME TRADING'."""
    if confirm != "RESUME TRADING":
        raise PermissionError("resume requires the exact confirmation phrase 'RESUME TRADING'")
    st = {"state": TRADING_RUNNING, "since": datetime.now(UTC).isoformat(), "by": actor, "reason": "operator resume",
          "safe_stop_policy": "keep_exits"}
    db.kv_set(KEY, st)
    audit.append("TRADING_RESUMED", {"actor": actor}, actor=actor)
    return st


def observe_only(db: Database, audit: AuditJournal, reason: str) -> None:
    """Automatic protective mode (loss limits / breakers). Auto-clears only via the runtime's daily reset."""
    cur = get_state(db)
    if cur["state"] == TRADING_STOPPED:
        return                                    # operator stop has precedence
    db.kv_set(KEY, {"state": TRADING_OBSERVE, "since": datetime.now(UTC).isoformat(), "by": "risk", "reason": reason,
                    "safe_stop_policy": "keep_exits"})
    audit.append("OBSERVE_ONLY", {"reason": reason}, actor="risk")


def clear_observe(db: Database, audit: AuditJournal, reason: str) -> None:
    if trading_state(db) == TRADING_OBSERVE:
        db.kv_set(KEY, {"state": TRADING_RUNNING, "since": datetime.now(UTC).isoformat(), "by": "risk",
                        "reason": reason, "safe_stop_policy": "keep_exits"})
        audit.append("OBSERVE_CLEARED", {"reason": reason}, actor="risk")
