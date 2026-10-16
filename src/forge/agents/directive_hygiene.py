"""Directive hygiene: OPEN must mean actionable, not archaeology.

Founder-visible symptom (2026-10-10): 1,000 OPEN directives survived the duplicate collapse
because they were *distinct* instructions \u2014 but 457 of them were 1\u20137 days old. Stale OPEN
rows are worse than no rows: the wake gate treats OPEN critical/high as urgent work and wakes
officers, who then burn inference discovering there is nothing current to do. That is precisely
the "API inference burning with no results" the founder reported.

Policy (deliberately conservative \u2014 advice decays, incidents do not):
  * A critical/high directive older than STALE_CRITICAL_H is presumed superseded by newer
    telemetry and is expired.
  * A normal directive older than STALE_NORMAL_H is expired.
  * Directives carrying an explicit workflow linkage are left alone: an open workflow stage
    owns them and will close or advance them.
  * Rows are set to EXPIRED_STALE with an audit reason. Nothing is deleted.
"""
from __future__ import annotations

import time
from typing import Any

STALE_CRITICAL_H = 6.0
STALE_NORMAL_H = 12.0

# Priorities that decay fast because they are advice about a moving market.
FAST_PRIORITY = ("critical", "high")


def reap_stale(db: Any, now: float | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Expire OPEN directives that can no longer be acted on. Returns counts."""
    now = now or time.time()
    crit_cut = now - STALE_CRITICAL_H * 3600
    norm_cut = now - STALE_NORMAL_H * 3600

    rows = db.query(
        "SELECT id, priority, ts, instruction FROM ops_directives "
        "WHERE status='OPEN' AND ts < ? ORDER BY ts ASC LIMIT 5000",
        (norm_cut,),
    ) or []

    stale: list[int] = []
    for r in rows:
        pri = str(r.get("priority") or "normal").lower()
        ts = float(r.get("ts") or 0)
        instr = str(r.get("instruction") or "")
        # An instruction bound to a live workflow is owned by that stage; do not reap it.
        if "workflow=" in instr or "wf=" in instr or "handoff" in instr.lower():
            continue
        if pri in FAST_PRIORITY:
            if ts < crit_cut:
                stale.append(int(r["id"]))
        elif ts < norm_cut:
            stale.append(int(r["id"]))

    out = {"open_scanned": len(rows), "stale_found": len(stale),
           "policy": {"critical_high_h": STALE_CRITICAL_H, "normal_h": STALE_NORMAL_H}}
    if dry_run or not stale:
        return out

    BATCH = 400
    expired = 0
    for i in range(0, len(stale), BATCH):
        chunk = stale[i:i + BATCH]
        marks = ",".join("?" * len(chunk))
        try:
            db.execute(
                "UPDATE ops_directives SET status='EXPIRED_STALE', done_ts=?, "
                "result='expired by directive hygiene: older than the actionable window; "
                "superseded by newer telemetry. No work was lost \u2014 the underlying condition "
                "is re-detected and re-paged if it still holds.' "
                "WHERE id IN (" + marks + ") AND status='OPEN'",
                (now, *chunk),
            )
            expired += len(chunk)
        except Exception:
            # Older schema may lack a result column; fall back to status-only.
            try:
                db.execute(
                    "UPDATE ops_directives SET status='EXPIRED_STALE', done_ts=? "
                    "WHERE id IN (" + marks + ") AND status='OPEN'",
                    (now, *chunk),
                )
                expired += len(chunk)
            except Exception:
                pass
    out["expired"] = expired
    return out
