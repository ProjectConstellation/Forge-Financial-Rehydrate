"""Idempotent ops-directive emission.

FOUNDER-VISIBLE DEFECT (2026-10-10): 17,484 OPEN directives against 1,573 DONE \u2014 an 11:1 ratio.
The same EARNINGS_PUSH instruction was emitted 1,351 times without ever being closed, because
every emitter did a raw unconditional INSERT on each tick. Consequences measured:
  * every agent brief injected thousands of duplicate "critical" items (signal drowned);
  * the wake gate treated the pile as "urgent work", waking officers who then found nothing
    new to do \u2014 burning inference for zero output ("API inference burning, no results");
  * officers could not close what they were paged with, so accountability looked broken.

This module makes emission idempotent per (role, emitter, instruction signature). One OPEN
directive per distinct instruction per role; re-paging refreshes the existing row instead of
adding a new one, so the newest evidence survives without duplicating.

Nothing here deletes history \u2014 rows are only ever collapsed to a single OPEN representative
plus CANCELLED superseded copies, preserving the audit trail.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any

# How many OPEN rows per (role, emitter) to compare a new signature against. Must exceed the number of
# distinct instructions an emitter can have outstanding, or a signature ages out of the window and the
# same instruction is inserted twice.
SCAN_ROWS = 600

# Numbers in instructions vary every tick ($0.001/h vs $0.002/h) while the *instruction* is
# identical. Normalising them makes the signature stable so dedup actually matches.
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def signature(instruction: str) -> str:
    """Stable signature for an instruction: numbers/whitespace normalised, then hashed."""
    norm = _NUM.sub("#", str(instruction or "")).lower()
    norm = " ".join(norm.split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:24]


def emit(db: Any, role: str, instruction: str, priority: str = "critical",
         requested_by: str = "system", workflow_id: str | None = None) -> bool:
    """Emit a directive idempotently. Returns True only when a NEW row was created.

    If an OPEN directive with the same signature already exists for this role+emitter, refresh
    its timestamp/priority (so the newest evidence is what agents see) and return False.
    """
    instruction = (instruction or "")[:2000]
    sig = signature(instruction)
    now = time.time()

    # Signature is not a column, so match among this emitter's recent OPEN rows for the role.
    try:
        # Scan a wide-enough window that a signature cannot age out of it between ticks. It was 60,
        # which let 6 duplicates through in a 2h observation (74/80 distinct). Bounded and cheap:
        # the comparison is a dict lookup over at most SCAN_ROWS rows.
        rows = db.query(
            "SELECT id, instruction FROM ops_directives WHERE role=? AND status='OPEN' "
            "AND requested_by=? ORDER BY id DESC LIMIT ?",
            (role, requested_by, SCAN_ROWS),
        ) or []
    except Exception:
        try:
            rows = db.query(
                "SELECT id, instruction FROM ops_directives WHERE role=? AND status='OPEN' "
                "AND requested_by=? ORDER BY id DESC LIMIT 600",
                (role, requested_by),
            ) or []
        except Exception:
            rows = []

    dup_ids = [r["id"] for r in rows if signature(r.get("instruction") or "") == sig]
    if dup_ids:
        keep = dup_ids[0]
        try:
            # Refresh the survivor with the latest wording/priority and cancel its duplicates.
            db.execute(
                "UPDATE ops_directives SET ts=?, priority=?, instruction=? WHERE id=?",
                (now, priority, instruction, keep),
            )
            if len(dup_ids) > 1:
                extra = dup_ids[1:]
                marks = ",".join("?" * len(extra))
                db.execute(
                    "UPDATE ops_directives SET status='CANCELLED', done_ts=?, "
                    "result='superseded: duplicate signature collapsed by emit()' "
                    "WHERE id IN (" + marks + ")",
                    (now, *extra),
                )
        except Exception:
            pass
        return False

    try:
        db.execute(
            "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by,result) "
            "VALUES(?,?,?,?,?,?,?)",
            (now, role, instruction, priority, "OPEN", requested_by, None),
        )
    except Exception:
        # Older schema without a result column on insert path.
        try:
            db.execute(
                "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                "VALUES(?,?,?,?,?,?)",
                (now, role, instruction, priority, "OPEN", requested_by),
            )
        except Exception:
            return False

    if workflow_id:
        try:
            db.kv_set(f"directive.workflow.{workflow_id}", time.time())
        except Exception:
            pass
    return True


def emit_objective(db: Any, kind: str, objective: str, summary: str | None = None) -> bool:
    """Emit an ops_objective idempotently: at most ONE ACTIVE row per (kind, signature).

    The escalator created a new ACTIVE "TEAM FAILURE MODE" objective every page cycle and never
    closed any of them (153 ACTIVE, 146 identical), so Luca saw an objective "relaunching with
    zero progress" (149 -> 153). Refreshing one ACTIVE objective keeps a real running tally of
    attempts instead of a pile of zombies, and leaves the audit trail intact.
    """
    objective = (objective or "")[:2000]
    sig = signature(objective)
    now = time.time()
    try:
        rows = db.query(
            "SELECT id, objective FROM ops_objectives WHERE status='ACTIVE' AND kind=? "
            "ORDER BY id DESC LIMIT ?", (kind, SCAN_ROWS),
        ) or []
    except Exception:
        rows = []
    dup_ids = [int(r["id"]) for r in rows if signature(r.get("objective") or "") == sig]
    if dup_ids:
        keep = dup_ids[0]
        try:
            db.execute("UPDATE ops_objectives SET ts=?, summary=? WHERE id=?",
                       (now, (summary or "")[:1800], keep))
            for old_id in dup_ids[1:]:
                db.execute(
                    "UPDATE ops_objectives SET status='DONE', done_ts=?, "
                    "summary='superseded: duplicate ACTIVE objective collapsed by emit_objective()' "
                    "WHERE id=?", (now, old_id))
        except Exception:
            pass
        return False
    try:
        db.execute("INSERT INTO ops_objectives (ts, kind, objective, status, summary) VALUES (?,?,?,?,?)",
                   (now, kind, objective, "ACTIVE", (summary or "")[:1800]))
        return True
    except Exception:
        return False


def collapse_objectives(db: Any, dry_run: bool = False) -> dict[str, Any]:
    """Collapse the historical pile of duplicate ACTIVE objectives to one per (kind, signature).

    Superseded rows are marked DONE with an audit note — never deleted.
    """
    try:
        rows = db.query("SELECT id, kind, objective FROM ops_objectives WHERE status='ACTIVE' ORDER BY id DESC") or []
    except Exception:
        return {"error": "ops_objectives unreadable"}
    seen: dict[tuple[str, str], int] = {}
    close: list[int] = []
    for r in rows:
        key = (str(r.get("kind")), signature(r.get("objective") or ""))
        if key in seen:
            close.append(int(r["id"]))
        else:
            seen[key] = int(r["id"])
    out = {"active_scanned": len(rows), "distinct_kept": len(seen), "superseded_to_close": len(close)}
    if dry_run or not close:
        return out
    now = time.time()
    for i in range(0, len(close), 400):
        chunk = close[i:i + 400]
        marks = ",".join("?" * len(chunk))
        db.execute(
            "UPDATE ops_objectives SET status='DONE', done_ts=?, "
            "summary='backlog collapse: duplicate ACTIVE objective superseded' "
            "WHERE id IN (" + marks + ") AND status='ACTIVE'",
            (now, *chunk),
        )
    out["closed"] = len(close)
    return out


def collapse_backlog(db: Any, dry_run: bool = False) -> dict[str, Any]:
    """One-time cleanup of the historical flood.

    For each (role, requested_by, signature) keep the NEWEST OPEN row and cancel the rest as
    superseded. Rows are cancelled, never deleted, so the audit trail is intact and the
    immutable-ledger rule is respected. Returns counts for the report.
    """
    rows = db.query(
        "SELECT id, role, requested_by, instruction, ts FROM ops_directives "
        "WHERE status='OPEN' ORDER BY id DESC"
    ) or []
    seen: dict[tuple[str, str, str], int] = {}
    cancel: list[int] = []
    for r in rows:
        key = (str(r.get("role")), str(r.get("requested_by")), signature(r.get("instruction") or ""))
        if key in seen:
            cancel.append(int(r["id"]))
        else:
            seen[key] = int(r["id"])
    out = {"open_scanned": len(rows), "distinct_kept": len(seen), "superseded_to_cancel": len(cancel)}
    if dry_run or not cancel:
        return out
    now = time.time()
    BATCH = 400
    for i in range(0, len(cancel), BATCH):
        chunk = cancel[i:i + BATCH]
        marks = ",".join("?" * len(chunk))
        db.execute(
            "UPDATE ops_directives SET status='CANCELLED', done_ts=?, "
            "result='backlog collapse: duplicate signature superseded (idempotent emit now enforced)' "
            "WHERE id IN (" + marks + ") AND status='OPEN'",
            (now, *chunk),
        )
    out["cancelled"] = len(cancel)
    return out
