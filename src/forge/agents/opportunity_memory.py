"""Institutional Opportunity Memory — negative / positive / uncertainty.

Blueprint §8–9, §16. Prevents ghost rediscovery without permanent blacklists;
feeds Tess/Quinn briefs with what works and what not to waste time on.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

log = logging.getLogger("forge.opp_memory")

NEGATIVE_STATUSES = (
    "KILLED", "BLOCKED", "CONTAMINATED", "SATURATED", "INSUFFICIENT_EVIDENCE",
    "EXECUTION_INFEASIBLE", "NEGATIVE_AFTER_COSTS", "WAITING_DEPENDENCY", "REGIME_INACTIVE",
)


class OpportunityMemory:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.ensure_schema()

    def ensure_schema(self) -> None:
        db = self.f.db
        db.execute(
            """CREATE TABLE IF NOT EXISTS opportunity_memory (
                mem_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                family TEXT,
                rail TEXT,
                scope TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                evidence_json TEXT,
                created_at REAL NOT NULL,
                expires_at REAL,
                reopen_condition TEXT,
                superseding_test TEXT,
                owner TEXT,
                confidence REAL,
                payload_json TEXT
            )"""
        )
        try:
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_opp_mem_kind_status "
                "ON opportunity_memory(kind, status, expires_at)"
            )
        except Exception:
            pass
        # Workflow enrichment columns (idempotent)
        for col, typ in (
            ("class", "TEXT"),
            ("dedupe_key", "TEXT"),
            ("lifecycle", "TEXT"),
            ("proposal_class", "TEXT"),
        ):
            try:
                db.execute(f"ALTER TABLE agent_workflows ADD COLUMN {col} {typ}")
            except Exception:
                pass
        for col, typ in (
            ("decision_required", "TEXT"),
            ("success_condition", "TEXT"),
            ("fail_condition", "TEXT"),
            ("next_owner", "TEXT"),
            ("deadline_at", "REAL"),
        ):
            try:
                db.execute(f"ALTER TABLE agent_handoffs ADD COLUMN {col} {typ}")
            except Exception:
                pass

    def _id(self) -> str:
        return f"om_{uuid.uuid4().hex[:12]}"

    def record_negative(
        self,
        *,
        family: str,
        rail: str,
        status: str,
        reason: str,
        evidence: list[Any] | dict[str, Any] | None = None,
        scope: str = "income_claim",
        expires_at: float | None = None,
        reopen_condition: str = "",
        superseding_test: str = "",
        owner: str = "ops",
        confidence: float = 0.7,
        ttl_h: float = 168.0,
    ) -> str:
        now = time.time()
        mid = self._id()
        st = status if status in NEGATIVE_STATUSES else "BLOCKED"
        self.f.db.execute(
            "INSERT INTO opportunity_memory(mem_id,kind,family,rail,scope,status,reason,evidence_json,"
            "created_at,expires_at,reopen_condition,superseding_test,owner,confidence,payload_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid, "NEGATIVE", family[:120], rail[:120], scope[:120], st, reason[:1000],
                json.dumps(evidence or [])[:4000], now,
                expires_at if expires_at is not None else now + ttl_h * 3600,
                reopen_condition[:500], superseding_test[:500], owner[:40], float(confidence),
                json.dumps({"status": st})[:1000],
            ),
        )
        return mid

    def record_positive(
        self,
        *,
        family: str,
        rail: str,
        reason: str,
        evidence: list[Any] | dict[str, Any] | None = None,
        scope: str = "working",
        owner: str = "ops",
        confidence: float = 0.7,
        capacity_note: str = "",
        ttl_h: float = 336.0,
    ) -> str:
        now = time.time()
        mid = self._id()
        self.f.db.execute(
            "INSERT INTO opportunity_memory(mem_id,kind,family,rail,scope,status,reason,evidence_json,"
            "created_at,expires_at,reopen_condition,superseding_test,owner,confidence,payload_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid, "POSITIVE", family[:120], rail[:120], scope[:120], "VALIDATED", reason[:1000],
                json.dumps(evidence or [])[:4000], now, now + ttl_h * 3600,
                "", "", owner[:40], float(confidence),
                json.dumps({"capacity_note": capacity_note})[:1000],
            ),
        )
        return mid

    def record_uncertainty(
        self,
        *,
        family: str,
        rail: str,
        reason: str,
        evidence: list[Any] | dict[str, Any] | None = None,
        owner: str = "scout",
        resolve_with: str = "",
        confidence: float = 0.5,
        ttl_h: float = 72.0,
    ) -> str:
        now = time.time()
        mid = self._id()
        self.f.db.execute(
            "INSERT INTO opportunity_memory(mem_id,kind,family,rail,scope,status,reason,evidence_json,"
            "created_at,expires_at,reopen_condition,superseding_test,owner,confidence,payload_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                mid, "UNCERTAINTY", family[:120], rail[:120], "unresolved", "OPEN", reason[:1000],
                json.dumps(evidence or [])[:4000], now, now + ttl_h * 3600,
                resolve_with[:500], resolve_with[:500], owner[:40], float(confidence), "{}",
            ),
        )
        return mid

    def active(self, kind: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
        now = time.time()
        if kind:
            rows = self.f.db.query(
                "SELECT * FROM opportunity_memory WHERE kind=? AND (expires_at IS NULL OR expires_at>?) "
                "ORDER BY created_at DESC LIMIT ?",
                (kind, now, limit),
            ) or []
        else:
            rows = self.f.db.query(
                "SELECT * FROM opportunity_memory WHERE (expires_at IS NULL OR expires_at>?) "
                "ORDER BY created_at DESC LIMIT ?",
                (now, limit),
            ) or []
        return [dict(r) for r in rows]

    def blocks_income_claim(self, family: str, rail: str) -> dict[str, Any] | None:
        """Return active CONTAMINATED/KILLED/etc that blocks claiming proven income."""
        now = time.time()
        row = self.f.db.query_one(
            "SELECT * FROM opportunity_memory WHERE kind='NEGATIVE' AND family=? AND rail=? "
            "AND status IN ('KILLED','BLOCKED','CONTAMINATED','NEGATIVE_AFTER_COSTS','EXECUTION_INFEASIBLE') "
            "AND (expires_at IS NULL OR expires_at>?) ORDER BY created_at DESC LIMIT 1",
            (family, rail, now),
        )
        return dict(row) if row else None

    def brief_for_scout(self) -> dict[str, Any]:
        neg = self.active("NEGATIVE", 20)
        pos = self.active("POSITIVE", 15)
        unc = self.active("UNCERTAINTY", 15)
        return {
            "do_not_propose": [
                {
                    "family": n.get("family"), "rail": n.get("rail"), "status": n.get("status"),
                    "reason": n.get("reason"), "reopen_condition": n.get("reopen_condition"),
                    "expires_at": n.get("expires_at"),
                }
                for n in neg
            ],
            "what_is_working": [
                {
                    "family": p.get("family"), "rail": p.get("rail"), "reason": p.get("reason"),
                    "capacity": (json.loads(p.get("payload_json") or "{}") or {}).get("capacity_note"),
                }
                for p in pos
            ],
            "uncertainties": [
                {
                    "family": u.get("family"), "rail": u.get("rail"), "reason": u.get("reason"),
                    "resolve_with": u.get("reopen_condition"), "owner": u.get("owner"),
                }
                for u in unc
            ],
        }

    def learn_from_measure(
        self,
        *,
        proposal_class: str,
        family: str,
        rail: str,
        result: str,
        summary: str,
        delta_usd_per_h: float | None = None,
        owner: str = "scout",
    ) -> list[str]:
        """Update memories after MEASURE_RESULT / MEASURE_INTERPRET."""
        ids: list[str] = []
        r = (result or "").upper()
        if r in ("FAIL", "VETO", "REJECTED", "NEGATIVE"):
            ids.append(self.record_negative(
                family=family, rail=rail, status="NEGATIVE_AFTER_COSTS" if (delta_usd_per_h or 0) < 0 else "KILLED",
                reason=summary[:500], owner=owner,
                reopen_condition="new independent evidence or regime change",
            ))
        elif r in ("PASS", "POSITIVE", "SCALE"):
            ids.append(self.record_positive(
                family=family, rail=rail, reason=summary[:500], owner=owner,
                capacity_note=f"delta_usd_per_h={delta_usd_per_h}",
            ))
        elif r in ("INCONCLUSIVE", "BLOCKED"):
            ids.append(self.record_uncertainty(
                family=family, rail=rail, reason=summary[:500], owner=owner,
                resolve_with="obtain missing evidence named in measure",
            ))
        if proposal_class == "DIAGNOSTIC" and r == "PASS":
            # Clear contamination reopen path note
            ids.append(self.record_uncertainty(
                family=family, rail=rail,
                reason="Diagnostic PASS — Quinn may formulate INCOME strategy if edge survives clean ledger",
                owner="alpha_inventor",
                resolve_with="Quinn STRATEGY+ALGORITHM on clean instruments",
            ))
        return ids

    def tick(self) -> dict[str, Any]:
        brief = self.brief_for_scout()
        self.f.db.kv_set("lab.opportunity_memory", {"ts": time.time(), **brief,
                                                     "n_neg": len(brief["do_not_propose"]),
                                                     "n_pos": len(brief["what_is_working"]),
                                                     "n_unc": len(brief["uncertainties"])})
        return brief

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("opportunity_memory")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("opp_memory: %s", e, exc_info=True)
            await asyncio.sleep(180)
