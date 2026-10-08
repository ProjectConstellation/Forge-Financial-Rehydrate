"""Earnings Push — deterministic under-target actuation (PAPER only).

Puts capital-hours on evidenced stables, cuts spot drains, advances stuck
alpha workflows with a typed intelligence packet, and recycles event desk.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.earnings_push")


class EarningsPush:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _proven(self) -> float:
        vel = self.f.db.kv_get("velocity") or {}
        return float((vel.get("expected_usd_per_h") or {}).get("proven") or 0.0)

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        proven = self._proven()
        nav = float((db.kv_get("econ.treasury_board") or {}).get("nav") or 0)
        actions: list[dict[str, Any]] = []

        # Capital policy: hard-prefer stables band
        db.kv_set("lab.stable_capital_policy", {
            "target_band_usd": [200, 500],
            "multiplier": 5.0,
            "prefer": ["coinbase.stable_triangle", "coinbase.stable_peg_mm"],
            "mode": "EARNINGS_PUSH",
            "ts": now,
        })
        db.kv_set("econ.prefer_rails", {
            "order": ["coinbase.stable_triangle", "coinbase.stable_peg_mm", "odds.paper_h2h"],
            "paper_band_usd": [200, 500],
            "aggression": "EARNINGS_PUSH",
            "block_spot_challengers_when_proven_lt": 0.25,
            "ts": now,
        })
        actions.append({"prefer_rails": "stables_first"})

        # Force-exit losing / stagnant non-stable PAPER spot so capital recirculates
        rows = db.query(
            "SELECT id, symbol, strategy_id, cost_usd, meta, opened_at FROM positions "
            "WHERE book='paper' AND status!='CLOSED' LIMIT 30"
        ) or []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r.get("meta") or "{}")
            except Exception:
                pass
            fam = str(meta.get("family") or "")
            if "stable" in fam.lower():
                continue
            loss = float(meta.get("loss") or 0)
            opened = float(meta.get("opened_ts") or 0)
            age_h = (now - opened) / 3600 if opened else 99
            # Cut losers or any non-stable held > 2h while under $0.25/h proven
            if loss < -0.02 or (proven < 0.25 and age_h > 2.0):
                db.kv_set(f"position.force_exit.{r['id']}", {
                    "ts": now, "reason": "earnings_push_cut_drain",
                    "family": fam, "loss": loss, "age_h": round(age_h, 2),
                })
                actions.append({"force_exit": r["id"], "symbol": r["symbol"], "loss": loss})

        # Paper lab intensify
        pl = getattr(self.f, "paper_lab", None)
        if pl:
            for name in ("ensure_stable_strategies", "bridge_stable_shadow_to_paper",
                         "kill_confirmed_drains", "reap_dead_positions", "promote_paper_probes"):
                fn = getattr(pl, name, None)
                if callable(fn):
                    try:
                        actions.append({name: fn()})
                    except Exception as e:
                        actions.append({name: f"err:{e}"[:100]})

        # Settle / recycle event PAPER if possible
        pb = getattr(self.f, "paper_bets", None)
        if pb:
            for name in ("settle", "tick", "scan_and_place", "run_once"):
                fn = getattr(pb, name, None)
                if callable(fn):
                    try:
                        out = fn()
                        actions.append({f"paper_bets.{name}": out if not hasattr(out, "__await__") else "async"})
                        break
                    except TypeError:
                        continue
                    except Exception as e:
                        actions.append({f"paper_bets.{name}": f"err:{e}"[:100]})

        # Respect negative opportunity memory — do not spam stables income if CONTAMINATED
        try:
            from forge.agents.opportunity_memory import OpportunityMemory
            om = getattr(self.f, "opportunity_memory", None) or OpportunityMemory(self.f)
            blk = om.blocks_income_claim("stable_triangle", "coinbase.stable_triangle")
            if blk:
                db.kv_set("lab.earnings_push", {
                    "ts": now, "proven": proven, "nav": nav,
                    "actions": [{"blocked_by_memory": blk.get("mem_id"), "status": blk.get("status"),
                                 "reason": blk.get("reason")}],
                    "policy": "diagnostic_first_until_ledger_clean",
                })
                # Page Tess/Ada for diagnostic only once
                db.execute(
                    "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) VALUES(?,?,?,?,?,?)",
                    (now, "scout",
                     "EARNINGS_PUSH blocked by CONTAMINATED memory on stable_triangle. Run/finish DIAGNOSTIC ledger reconcile — do not claim proven income.",
                     "high", "OPEN", "earnings_push"))
                return {"ts": now, "blocked_by_memory": True, "proven": proven}
        except Exception as e:
            actions.append({"memory_check_err": str(e)[:120]})

        # Feed Tess evidence — NEVER auto-advance OPPORTUNITY_ORCHESTRATION past her proposal.
        # Only auto-advance ALPHA_GENERATION MARKET_INTELLIGENCE_PACKET if truly stuck (>25m).
        pending = db.query(
            "SELECT h.handoff_id, h.workflow_id, h.to_role, h.payload_type, h.created_at, w.type AS wf_type "
            "FROM agent_handoffs h LEFT JOIN agent_workflows w ON w.workflow_id=h.workflow_id "
            "WHERE h.status='PENDING' AND h.to_role='scout' LIMIT 8"
        ) or []
        stable = db.kv_get("lab.paper_stable_pnl") or {}
        tri = (stable.get("by_rail") or {}).get("coinbase.stable_triangle") or {}
        packet = {
            "trigger": "EARNINGS_PUSH",
            "rail": "coinbase.stable_triangle",
            "evidence": {
                "stable_triangle_net": tri.get("net"),
                "stable_triangle_n": tri.get("n"),
                "paper_stable_net": stable.get("net"),
                "proven_usd_per_h": proven,
                "nav": nav,
            },
            "recommendation": "MAXIMIZE_STABLES_PAPER_CAPITAL_HOURS",
            "next_action": "Quinn invents only fee-aware stables challengers; Ada gates; do not promote spot drains",
            "evidence_refs": ["lab.paper_stable_pnl", "shadow_trades:coinbase.stable_triangle", "velocity"],
            "economic_attribution": {"sleeve": "coinbase.stable_triangle", "mode": "PAPER_SHADOW"},
        }
        wf_engine = getattr(self.f, "workflow_engine", None)
        for h in pending:
            h = dict(h)
            wtype = h.get("wf_type") or ""
            ptype = h.get("payload_type") or ""
            # Opportunity masterpiece: leave for Tess; inject evidence into workflow inputs + directive
            if wtype == "OPPORTUNITY_ORCHESTRATION" or ptype in ("OPPORTUNITY_PROPOSAL", "MEASURE_RESULT"):
                db.kv_set("lab.scout_evidence_feed", {**packet, "ts": now, "for_workflow": h["workflow_id"]})
                db.execute(
                    "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                    "VALUES(?,?,?,?,?,?)",
                    (now, "scout",
                     f"EVIDENCE_FEED for {h['workflow_id']} ({ptype}): stables triangle n={tri.get('n')} "
                     f"net={tri.get('net')} proven={proven}/h nav={nav}. Propose fundable "
                     f"STRATEGY|ALGORITHM|INVESTMENT|REALLOCATION — do not skip risk/capital gates. "
                     f"role=scout only.",
                     "high", "OPEN", "earnings_push"),
                )
                actions.append({"scout_evidence_feed": h["workflow_id"]})
                continue
            # Alpha path only: auto-advance MARKET_INTELLIGENCE if stuck >25m
            age = now - float(h.get("created_at") or now)
            if ptype == "MARKET_INTELLIGENCE_PACKET" and age > 1500 and wf_engine and hasattr(wf_engine, "advance"):
                try:
                    out = wf_engine.advance(
                        h["workflow_id"], "scout", "MARKET_INTELLIGENCE_PACKET",
                        packet, result_type="DECISION_MADE", confidence=0.7,
                    )
                    actions.append({"workflow_advance": out})
                except Exception as e:
                    actions.append({"workflow_advance_err": str(e)[:120]})

        # Direct pages — IMPLEMENT not analyze
        if proven < 0.10:
            for role, instr in (
                ("governor", "EARNINGS_PUSH: allocate ALL marginal PAPER attention to coinbase.stable_triangle capital-hours. Cut spot challengers. Report Δ$/h."),
                ("alpha_inventor", "EARNINGS_PUSH: only stables microstructure challengers. No alt breakout genomes until proven≥$0.25/h."),
                ("execution", "EARNINGS_PUSH: Reid — ensure pegmaker/triangle path is the active execution sleeve; abort fee-toxic spot."),
                ("treasury", "EARNINGS_PUSH: Ellis — opportunity cost of $1 off stables is the binding constraint. Prefer stables band $200–500."),
                ("scout", "EARNINGS_PUSH: Tess — if OPPORTUNITY_PROPOSAL pending, propose fundable ask using stables evidence; else MEASURE_RESULT on capital-hours. role=scout."),
            ):
                db.execute(
                    "INSERT INTO ops_directives(ts,role,instruction,priority,status,requested_by) "
                    "VALUES(?,?,?,?,?,?)",
                    (now, role, instr, "critical", "OPEN", "earnings_push"),
                )
            actions.append({"paged": True})

        # Modal research on stables only
        db.kv_set("modal.research_request", {
            "ts": now,
            "reason": "earnings_push",
            "workloads": ["stable_microstructure_sweep", "stable_triangle_param_search"],
            "prefer_cpu": True,
            "consumed": False,
        })

        rep = {"ts": now, "proven": proven, "nav": nav, "actions": actions[:40],
               "policy": "stables_capital_hours_first_PAPER_only"}
        db.kv_set("lab.earnings_push", rep)
        if actions:
            log.info("earnings_push: %s", actions[:8])
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("earnings_push")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("earnings_push: %s", e, exc_info=True)
            await asyncio.sleep(120)
