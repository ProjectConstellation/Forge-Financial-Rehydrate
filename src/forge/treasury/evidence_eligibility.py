"""Evidence failures invalidate income CLAIMS until independently verified evidence exists.

Scope matters. A marker written as claim-discipline ("do not label this proven yet; PAPER
capital-hours ALLOWED") must not remove the stream from measurement or allocation — doing so
silently starves the firm's best earner, which is the opposite of the author's intent.
Expired markers block nothing.
"""
from __future__ import annotations

import time
from typing import Any

# Marker statuses that are a HARD stop (the edge is dead/untradeable), not merely unproven.
HARD_STATUSES = ("KILLED", "BLOCKED", "NEGATIVE_AFTER_COSTS", "EXECUTION_INFEASIBLE")
# Statuses that only restrain CLAIMING proven income.
CLAIM_STATUSES = ("CONTAMINATED", "INSUFFICIENT_EVIDENCE")
CLAIM_SCOPE = "income_claim"


def income_block(db: Any, rail: str, family: str = "", *, hard_only: bool = False) -> dict[str, Any] | None:
    """Return the active marker blocking `rail`, or None.

    hard_only=True  -> only HARD statuses block (used for measurement/allocation, so
                       claim-discipline markers never suppress PAPER capital-hours).
    hard_only=False -> HARD statuses and claim-scoped markers both block (used for the
                       PROVEN tier, so nothing is claimed proven while contaminated).
    Expired markers (expires_at in the past) never block, matching
    opportunity_memory.blocks_income_claim().
    """
    if not db.scalar("SELECT 1 FROM sqlite_master WHERE name='opportunity_memory'"):
        return None
    now = time.time()
    fam = family or rail.rsplit(".", 1)[-1]
    statuses = HARD_STATUSES if hard_only else HARD_STATUSES + CLAIM_STATUSES
    marks = ",".join("?" * len(statuses))
    return db.query_one(
        "SELECT mem_id,status,scope,reason,created_at,expires_at FROM opportunity_memory "
        "WHERE kind='NEGATIVE' AND status IN (" + marks + ") AND (rail=? OR family=?) "
        "AND (expires_at IS NULL OR expires_at > ?) "
        "ORDER BY created_at DESC LIMIT 1",
        (*statuses, rail, fam, now),
    )
