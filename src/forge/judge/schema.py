"""Idempotent DDL for the judge subsystem. Safe to call on every boot; never drops data.

Tables:
    judge_verdicts      one row per committed judgement (the audit trail of every typed decision)
    judge_noul_pending  one row per noul awaiting its realized outcome (feeds the calibrator)
    funnel_bench        candidates benched by the CHECK that failed them, with a reason-specific TTL
    funnel_rejects      every rejection with its rung + check (drives the filter-health metric)
    role_salary         per-role inference cost vs attributed income, per window (the economy ledger)
"""
from __future__ import annotations

from typing import Any

_DDL = [
    """CREATE TABLE IF NOT EXISTS judge_verdicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        question_set TEXT NOT NULL,
        role TEXT,
        candidate_id TEXT,
        source TEXT,
        regime TEXT,
        verdict TEXT,
        size_factor REAL,
        answers TEXT,
        problems TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS judge_noul_pending (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        question_set TEXT NOT NULL,
        question TEXT NOT NULL,
        candidate_id TEXT,
        role TEXT,
        source TEXT,
        raw REAL,
        calibrated REAL,
        outcome INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS funnel_bench (
        id TEXT PRIMARY KEY,
        reason TEXT,
        until REAL
    )""",
    """CREATE TABLE IF NOT EXISTS funnel_rejects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        candidate_id TEXT,
        rail TEXT,
        family TEXT,
        rung INTEGER,
        reason TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS funnel_shadow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        opportunity_id TEXT,
        symbol TEXT,
        family TEXT,
        would_kill INTEGER,
        reason TEXT,
        rung INTEGER,
        actual_status TEXT,
        exp_net_bps REAL,
        cost_bp REAL
    )""",
    """CREATE TABLE IF NOT EXISTS role_salary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        role TEXT NOT NULL,
        window_h REAL,
        inference_cost_usd REAL,
        attributed_income_usd REAL,
        value_per_usd REAL,
        calls INTEGER,
        state TEXT,
        note TEXT
    )""",
]
_IDX = [
    "CREATE INDEX IF NOT EXISTS idx_jv_set ON judge_verdicts(question_set, ts)",
    "CREATE INDEX IF NOT EXISTS idx_jnp_outcome ON judge_noul_pending(question_set, question, outcome)",
    "CREATE INDEX IF NOT EXISTS idx_fr_ts ON funnel_rejects(ts)",
    "CREATE INDEX IF NOT EXISTS idx_rs_role_ts ON role_salary(role, ts)",
    "CREATE INDEX IF NOT EXISTS idx_fs_ts ON funnel_shadow(ts)",
]


def ensure_schema(db: Any) -> None:
    for stmt in _DDL:
        db.execute(stmt)
    for stmt in _IDX:
        db.execute(stmt)
