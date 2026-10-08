"""Economic Tournament Orchestrator — 8h PAPER full-dress + Modal research attribution."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.econ_orchestrator")


class EconOrchestrator:
    """Keeps the capital loop honest and drives Modal research during RED ZONE / 8h trial."""

    def __init__(self, forge: Any) -> None:
        self.f = forge

    def ensure_8h_trial(self) -> dict[str, Any]:
        from forge.treasury.paper_trial import start_8h_trial, snapshot, update_8h_scorecard
        st = self.f.db.kv_get("paper_trial") or {}
        if not st or st.get("trial_kind") != "FULL_DRESS_8H":
            st = start_8h_trial(self.f)
            log.warning("started FULL_DRESS_8H trial")
        else:
            snapshot(self.f)
            try:
                update_8h_scorecard(self.f)
            except Exception as e:
                log.debug("scorecard: %s", e)
        return self.f.db.kv_get("paper_trial") or st

    def treasury_board(self) -> dict[str, Any]:
        vel = self.f.db.kv_get("velocity") or {}
        realloc = self.f.db.kv_get("capital.reallocation") or {}
        decay = self.f.db.kv_get("edge_decay") or {}
        paper_bets = self.f.db.kv_get("lab.paper_bets") or {}
        evidence = self.f.db.kv_get("lab.evidence_board") or {}
        t = vel.get("treasury") or {}
        board = {
            "ts": time.time(),
            "nav": t.get("total") or t.get("nav"),
            "available": t.get("available") or t.get("free"),
            "deployed": t.get("deployed") or t.get("locked"),
            "locked": t.get("locked"),
            "paper_pnl": (vel.get("realized") or {}).get("24h"),
            "proven_usd_per_h": (vel.get("expected_usd_per_h") or {}).get("proven"),
            "potential_usd_per_h": (vel.get("expected_usd_per_h") or {}).get("potential"),
            "below_target": vel.get("below_target"),
            "below_diagnostic": vel.get("below_diagnostic"),
            "realloc_top": ((realloc.get("ranking") or [{}])[0]),
            "realloc_actions": len(realloc.get("actions") or []),
            "edge_decay_actions": len(decay.get("actions") or []),
            "paper_bets": {
                "open": paper_bets.get("open"),
                "realized_pnl": paper_bets.get("realized_pnl"),
                "bankroll": paper_bets.get("bankroll"),
                "edges_found": paper_bets.get("edges_found"),
            },
            "works": (evidence.get("works") or [])[:5],
            "marginal_next_dollar": (realloc.get("ranking") or [{}])[0].get("marginal_value"),
            "loop": "TREASURY→RANK→ALLOC→PAPER_EXEC→MONITOR→DECAY→REDUCE→RELEASE→REALLOC→REINVEST→GROWTH",
        }
        self.f.db.kv_set("econ.treasury_board", board)
        return board

    def maybe_modal_research(self) -> dict[str, Any]:
        """Queue / record Modal research intent; actual burst goes through ComputeGovernor when parents exist."""
        vel = self.f.db.kv_get("velocity") or {}
        red = bool(vel.get("below_diagnostic") or vel.get("below_target"))
        compute = getattr(self.f, "compute", None)
        out: dict[str, Any] = {"ts": time.time(), "red_zone_or_below_target": red, "launched": False}
        if not compute:
            out["status"] = "no_compute_governor"
            self.f.db.kv_set("econ.modal_research", out)
            return out
        # Prefer intensifying when below target
        try:
            summary = compute.summary() if hasattr(compute, "summary") else {}
            out["compute"] = summary
            # Flag for improvement loop / arena to burst
            flag = {
                "ts": time.time(),
                "reason": "econ_orchestrator_red_zone" if red else "econ_orchestrator_trial",
                "workloads": [
                    "strategy_genome_tournament",
                    "parameter_sweep",
                    "regime_clustering",
                    "challenger_falsification",
                    "portfolio_optimization",
                ],
                "prefer_cpu": True,
            }
            self.f.db.kv_set("modal.research_request", flag)
            out["request"] = flag
            out["status"] = "requested"
            # Attribute placeholder until burst completes
            hist = self.f.db.kv_get("econ.modal_attribution") or {"runs": []}
            runs = hist.get("runs") or []
            # Pull latest compute_jobs
            rows = self.f.db.query(
                "SELECT id, kind, status, est_cost_usd, duration_s, ts_start FROM compute_jobs ORDER BY ts_start DESC LIMIT 5"
            ) or []
            out["recent_jobs"] = [dict(r) for r in rows]
            for r in rows:
                if r["status"] == "DONE" and not any(x.get("id") == r["id"] for x in runs):
                    runs.append({
                        "id": r["id"], "kind": r["kind"], "cost": r["est_cost_usd"],
                        "duration_s": r["duration_s"], "ts": time.time(),
                        "decision_changed": "pending_evidence",
                        "estimated_econ_value": "measured_via_challenger_true_net",
                    })
            hist["runs"] = runs[-30:]
            self.f.db.kv_set("econ.modal_attribution", hist)
        except Exception as e:
            out["status"] = f"error:{e}"
            log.warning("modal research: %s", e)
        self.f.db.kv_set("econ.modal_research", out)
        return out

    def intensify_paper(self) -> dict[str, Any]:
        """Below $1/h: intensify fee-aware PAPER — never throttle."""
        actions = []
        pl = getattr(self.f, "paper_lab", None)
        if pl:
            for name in ("diversify_experimental", "promote_diversity_to_shadow", "bridge_stable_shadow_to_paper", "promote_paper_probes"):
                fn = getattr(pl, name, None)
                if callable(fn):
                    try:
                        actions.append({name: fn()})
                    except Exception as e:
                        actions.append({name: str(e)[:120]})
        # Prefer stables — evidence winner
        try:
            self.f.db.kv_set("econ.prefer_rails", {
                "ts": time.time(),
                "order": ["coinbase.stable_triangle", "coinbase.stable_peg_mm", "odds.paper_h2h", "twelve.equity_paper"],
                "note": "marginal capital prefers proven shadow + intelligent event PAPER",
            })
        except Exception:
            pass
        out = {"ts": time.time(), "actions": actions}
        self.f.db.kv_set("econ.intensify", out)
        return out

    def tick(self) -> dict[str, Any]:
        trial = self.ensure_8h_trial()
        board = self.treasury_board()
        modal = self.maybe_modal_research()
        intensify = {}
        if board.get("below_target") or board.get("below_diagnostic"):
            intensify = self.intensify_paper()
        # Officer directives for economic phase (cooldown via kv)
        now = time.time()
        last = float((self.f.db.kv_get("econ.last_officer_page") or {}).get("ts") or 0)
        if now - last > 1800 and (board.get("below_target")):
            try:
                self.f.db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "governor",
                     "ECON PHASE: below $1/h TRUE-NET. Reallocate marginal PAPER $ to highest LCB streams "
                     "(prefer stable_triangle evidence). Do not throttle investing.",
                     "critical", "OPEN", "econ_orchestrator"),
                )
                self.f.db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "alpha_inventor",
                     "ECON PHASE: invent/falsify proprietary challengers for stables microstructure + event PAPER probability. "
                     "Goal = higher true-net per capital-hour, not more strategies.",
                     "critical", "OPEN", "econ_orchestrator"),
                )
                self.f.db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "critic",
                     "Ada CDS: verify significance of any claimed +EV sleeve. Refuse promotion without OOS evidence.",
                     "high", "OPEN", "econ_orchestrator"),
                )
                self.f.db.kv_set("econ.last_officer_page", {"ts": now})
            except Exception as e:
                log.debug("page: %s", e)
        rep = {
            "ts": now,
            "trial": {
                "kind": trial.get("trial_kind"),
                "status": trial.get("status"),
                "elapsed_h": trial.get("elapsed_h"),
                "ends_ts": trial.get("ends_ts"),
            },
            "board": board,
            "modal": {"status": modal.get("status"), "recent": (modal.get("recent_jobs") or [])[:3]},
            "intensify_n": len(intensify.get("actions") or []),
        }
        self.f.db.kv_set("lab.econ_orchestrator", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("econ_orchestrator")
            try:
                rep = await asyncio.to_thread(self.tick)
                if rep.get("intensify_n"):
                    await self.f.say(
                        "Econ Orchestrator",
                        f"8h trial running · proven ${((rep.get('board') or {}).get('proven_usd_per_h') or 0):.3f}/h · "
                        f"intensified {rep['intensify_n']} PAPER actions · Modal {(rep.get('modal') or {}).get('status')}",
                        level="info",
                    )
            except Exception as e:
                log.warning("econ_orchestrator: %s", e, exc_info=True)
            await asyncio.sleep(300)
