"""Atomic paid-work admission. No role, urgency, or paper profit bypasses this gate."""
from __future__ import annotations

import math
import time
from datetime import UTC, datetime
from typing import Any

from forge.core.ids import new_id


def enabled(db: Any) -> bool:
    return bool((db.kv_get("intelligence.admission") or {}).get("enabled"))


def reserve(db: Any, *, provider: str, owner: str, objective_id: str,
            experiment_key: str, max_cost_usd: float, budget_usd: float,
            spent_usd: float, ttl_s: float = 3600) -> dict[str, Any]:
    values = (max_cost_usd, budget_usd, spent_usd, ttl_s)
    if not all(math.isfinite(v) for v in values) or max_cost_usd <= 0 or ttl_s <= 0:
        return {"allowed": False, "reason": "invalid_cost_bound"}
    if not objective_id or not experiment_key:
        return {"allowed": False, "reason": "missing_experiment_contract"}
    now = time.time()
    with db.transaction():
        # An expired reservation may have incurred charges: retain its bound until reconciled.
        db.execute("UPDATE spend_reservations SET state='UNCERTAIN' WHERE provider=? "
                   "AND state='RESERVED' AND expires_at<=?", (provider, now))
        duplicate = db.query_one("SELECT id FROM spend_reservations WHERE provider=? "
                                 "AND experiment_key=? AND state IN ('RESERVED','UNCERTAIN')",
                                 (provider, experiment_key))
        if duplicate:
            return {"allowed": False, "reason": "experiment_already_reserved"}
        outstanding = float(db.scalar("SELECT COALESCE(SUM(max_cost_usd),0) FROM spend_reservations "
                                      "WHERE provider=? AND state IN ('RESERVED','UNCERTAIN')", (provider,)) or 0)
        headroom = max(0., budget_usd - spent_usd - outstanding)
        if max_cost_usd > headroom + 1e-12:
            return {"allowed": False, "reason": "budget_exhausted", "headroom_usd": headroom,
                    "outstanding_usd": outstanding}
        rid = new_id("reserve")
        db.insert("spend_reservations", dict(id=rid, provider=provider, owner=owner,
                  objective_id=objective_id, experiment_key=experiment_key,
                  max_cost_usd=max_cost_usd, state="RESERVED", created_at=now,
                  expires_at=now + ttl_s))
        return {"allowed": True, "reservation_id": rid, "max_cost_usd": max_cost_usd,
                "headroom_usd": headroom - max_cost_usd}


def settle(db: Any, reservation_id: str, cost: float | None, outcome_ref: str,
           *, basis: str = "provider_usage") -> None:
    if cost is not None and (not math.isfinite(cost) or cost < 0):
        raise ValueError("invalid settlement cost")
    with db.transaction():
        db.execute("UPDATE spend_reservations SET state=?,actual_cost_usd=?,outcome_ref=?,cost_basis=? "
                   "WHERE id=? AND state IN ('RESERVED','UNCERTAIN')",
                   ("UNCERTAIN" if cost is None else "SETTLED", cost, outcome_ref, basis, reservation_id))


def inference_reserve(db: Any, *, owner: str, objective_id: str, experiment_key: str,
                      max_cost_usd: float, floor: float) -> dict[str, Any]:
    from forge.treasury.intelligence import profit_7d, spent_24h
    sentinel = db.kv_get("deepseek.sentinel") or {}
    try:
        age = time.time() - datetime.fromisoformat(sentinel["checked"]).timestamp()
        balance = float(sentinel["balance"])
        if age < 0 or age > 600 or not math.isfinite(balance):
            raise ValueError("stale")
    except (KeyError, TypeError, ValueError):
        return {"allowed": False, "reason": "provider_balance_unknown_or_stale"}
    policy = db.kv_get("intelligence.admission") or {}
    runway = inference_runway(db)
    budget = max(0., balance - floor) / runway
    # Reinvestment needs settled live profit after operating costs; paper is excluded.
    budget += max(0., profit_7d(db)) * min(.5, max(0., float(policy.get("reinvest_share", .25)))) / 7
    return reserve(db, provider="deepseek", owner=owner, objective_id=objective_id,
                   experiment_key=experiment_key, max_cost_usd=max_cost_usd,
                   budget_usd=budget, spent_usd=spent_24h(db))


def inference_runway(db: Any) -> float:
    """Scale throughput from settled LIVE net cost coverage, never deposits or simulated profits."""
    from forge.treasury.economic_truth import realized_window
    result = realized_window(db, time.time() - 7 * 86400, time.time())
    if result["net_usd"] <= 0:
        return 7.
    coverage = result["settled_income_usd"] / max(result["operating_cost_usd"], .01)
    return 1.5 if coverage >= 3 else 2.5 if coverage >= 1.5 else 4.
