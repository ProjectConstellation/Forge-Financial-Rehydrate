"""Typed tool surface for DeepSeek (DOSSIER §18). Read tools return curated facts; action tools only queue validated
research artifacts. There is deliberately NO trade, transfer, risk-limit or emergency-stop tool (OP-009 §6)."""

from __future__ import annotations

import contextlib
import json
from typing import Any

from forge.core.ids import new_id
from forge.persistence.db import dumps
from forge.strategies.genome import Genome
from forge.strategies.registry import State


def _fn(name: str, desc: str, props: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required or [], "additionalProperties": False}}}


TOOLS = [
    _fn("get_system_state", "Treasury, capital regime, fees, mode, population counts, hurdle rate.", {}),
    _fn("get_market_state", "Live regime/feature snapshot for markets (latest bar).",
        {"symbols": {"type": "array", "items": {"type": "string"}}, "interval_s": {"type": "integer", "enum": [300, 3600]}}),
    _fn("list_strategies", "Strategies with state and evidence.",
        {"states": {"type": "array", "items": {"type": "string", "enum": [s.value for s in State]}}, "limit": {"type": "integer"}}),
    _fn("get_strategy", "Full genome, lineage, holdout/forward metrics and state history.", {"id": {"type": "string"}}, ["id"]),
    _fn("get_recent_failures", "Recent losing positions, demotions and gate failures with reasons.", {"limit": {"type": "integer"}}),
    _fn("get_missed_opportunities", "Counterfactual outcomes of rejected/observed opportunities (missed winners, avoided losers).",
        {"limit": {"type": "integer"}}),
    _fn("get_calibration", "Predicted-vs-actual reliability by prediction class.", {}),
    _fn("get_research_log", "Recent research notes/lessons (institutional memory).", {"limit": {"type": "integer"}}),
    _fn("submit_strategy_candidates", "Queue genomes for evaluation by the evolution engine (validated, backtested, gated).",
        {"candidates": {"type": "array", "items": {"type": "object"}}}, ["candidates"]),
    _fn("record_lesson", "Persist a structured lesson.", {"statement": {"type": "string"}, "confidence": {"type": "number"},
                                                          "family": {"type": "string"}}, ["statement", "confidence"]),
    _fn("request_research", "Ask the Improvement Loop to prioritize a horizon/focus next cycle.",
        {"interval_s": {"type": "integer", "enum": [300, 3600]}, "focus": {"type": "string"}}, ["focus"]),
    # OP-013 / Hermes dossier surfaces (shared by FORGE's brain and Hermes)
    _fn("get_opportunity_surface", "All income rails: status, executability, blockers, evidence-based score/day, allocator "
        "plan now vs if-unblocked, fixed costs (Coinbase One).", {}),
    _fn("get_crossrail_evidence", "Kalshi↔Coinbase prediction engine evidence: Brier model/market/stacked, settled shadow P&L by "
        "signal kind, lead/lag, edge half-life, RTI-proxy error, calibrator weights.", {}),
    _fn("get_shadow_rails", "Paper results of non-core rails (stable peg maker, stable triangle, listing discovery).", {}),
    _fn("get_listing_events", "Recent Coinbase product/listing/status/doc-page discovery events.", {"limit": {"type": "integer"}}),
    _fn("get_intelligence_budget", "Live DeepSeek balance, 24h pace/headroom, value-per-$ by role (incl. Hermes roles).", {}),
    # cognitive architecture (role briefs, structured reports, prompt genomes, blind panels)
    _fn("get_role_brief", "FIRST CALL OF EVERY RUN: your engineered role brief (constitution, mission, decision rights, "
        "evidence standard, output schema), live world state and your role's track record.", {"role": {"type": "string"}},
        ["role"]),
    _fn("submit_role_report", "LAST CALL OF EVERY RUN: structured role report (JSON object per your brief's output schema).",
        {"role": {"type": "string"}, "report": {"type": "object"}}, ["role", "report"]),
    _fn("get_recent_candidates", "LLM-designed strategy candidates with gate/sealed outcomes and inventor/adversary forecasts.",
        {"limit": {"type": "integer"}}),
    _fn("get_role_reports", "Recent structured reports of all roles (blind-panel verdicts hidden until reconciled).",
        {"limit": {"type": "integer"}, "role": {"type": "string"}}),
    _fn("get_prompt_performance", "Prompt genome versions per role with runs, KPI, cost, calibration and challenger status.",
        {"role": {"type": "string"}}),
    _fn("submit_prompt_variant", "Architect only: propose ONE challenger prompt variant (edit 1–3 sections) with a hypothesis.",
        {"role": {"type": "string"}, "parent_version": {"type": "integer"}, "hypothesis": {"type": "string"},
         "sections": {"type": "object"}}, ["role", "hypothesis", "sections"]),
    _fn("get_system_health", "Self-healing health: loop heartbeats, feed state, event-loop lag, quarantines, circuits, "
        "recent warnings/errors, memory.", {}),
    _fn("submit_research_lead", "Record a research lead (new rail, fee/rule change, market-structure anomaly, data source) with "
        "sources; it is triaged by FORGE and valued if it leads to income.",
        {"title": {"type": "string"}, "body": {"type": "string"}, "category": {"type": "string"},
         "sources": {"type": "array", "items": {"type": "string"}}, "expected_value_usd_month": {"type": "number"}},
        ["title", "body", "category"]),
]


class ToolRouter:
    def __init__(self, forge: Any, call_id: str, role: str) -> None:
        self.f, self.call_id, self.role = forge, call_id, role
        self.artifacts: list[dict[str, Any]] = []

    async def dispatch(self, name: str, args_json: str) -> str:
        try:
            args = json.loads(args_json or "{}")
        except ValueError:
            return json.dumps({"error": "invalid JSON arguments"})
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            out = fn(**args)
        except TypeError as e:
            out = {"error": f"bad arguments: {e}"}
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        return json.dumps(out, default=str)[:30000]

    # ---------------- read tools
    def t_get_system_state(self) -> dict[str, Any]:
        f = self.f
        t = f.treasury
        return {"mode": f.s.mode.value, "book": f.book, "treasury": {k: t.get(k) for k in (
            "equity_usd", "cash_usd", "deployed_usd", "true_net_usd", "fees_usd", "opex_inference_usd", "opex_compute_usd",
            "daily_pnl_usd", "reserve_usd")}, "capital_regime": t.get("regime"),
            "fees": {"maker": float(f.fees.maker), "taker": float(f.fees.taker)},
            "population": f.reg.counts(), "hurdle_per_day": f.hurdle.hurdle(1.0) * 24, "universe": f.universe}

    def t_get_market_state(self, symbols: list[str] | None = None, interval_s: int = 3600) -> dict[str, Any]:
        eng = self.f.bars.get(interval_s) or self.f.bars[3600]
        out = {}
        keys = ("ret_12", "ret_48", "ret_288", "vol_48", "vol_pct", "rvol_12", "er_24", "z_50", "rs_btc_48", "dd_288", "atr_14")
        for s in (symbols or self.f.universe)[:40]:
            st = eng.state.get(s)
            if not st or not st.features:
                continue
            out[s] = {"regime": st.regime, "regime_conf": round(st.regime_conf, 3),
                      "features": {k: round(float(st.features[k][-1]), 5) for k in keys if k in st.features
                                   and st.features[k][-1] == st.features[k][-1]}}
        return {"interval_s": interval_s, "markets": out}

    def t_list_strategies(self, states: list[str] | None = None, limit: int = 30) -> list[dict[str, Any]]:
        sts = tuple(State(s) for s in states) if states else None
        rows = self.f.reg.list(sts)
        rows.sort(key=lambda r: -(r[2].get("fitness") or -9))
        out = []
        for g, st, row in rows[: max(1, min(limit, 60))]:
            ev = self.f.arena.evidence(g.id)
            out.append({"id": g.id, "family": g.family, "state": st.value, "gen": g.generation, "fitness": row.get("fitness"),
                        "hypothesis": g.hypothesis[:200], "interval_s": g.interval_s,
                        "holdout": _short(self.f.reg.latest_metrics(g.id, "holdout")),
                        "evidence": ev.__dict__ if ev else None})
        return out

    def t_get_strategy(self, id: str) -> dict[str, Any]:
        g = self.f.reg.get(id)
        if g is None:
            return {"error": "not found"}
        return {"genome": g.model_dump(mode="json"), "state": self.f.reg.state(id), "lineage": self.f.reg.lineage(id, 3),
                "holdout": _short(self.f.reg.latest_metrics(id, "holdout")), "forward": _short(self.f.reg.latest_metrics(id, "forward"))}

    def t_get_recent_failures(self, limit: int = 20) -> dict[str, Any]:
        db = self.f.db
        return {"losing_positions": db.query("SELECT symbol, strategy_id, exit_reason, realized_pnl_usd, fees_usd, cost_usd, "
                                             "opened_at, closed_at FROM positions WHERE status='CLOSED' AND "
                                             "CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL) < 0 ORDER BY closed_at DESC LIMIT ?", (limit,)),
                "demotions": db.query("SELECT strategy_id, ts, from_population, to_population, reason FROM strategy_events "
                                      "WHERE to_population IN ('SHADOW','EXPERIMENTAL','RETIRED','HIBERNATING') ORDER BY id DESC LIMIT ?", (limit,))}

    def t_get_missed_opportunities(self, limit: int = 40) -> list[dict[str, Any]]:
        rows = self.f.db.query("SELECT symbol, family, strategy_id, status, reason, probability, outcome FROM opportunities "
                               "WHERE outcome IS NOT NULL ORDER BY ts_ns DESC LIMIT ?", (limit,))
        for r in rows:
            r["outcome"] = json.loads(r["outcome"])
        return rows

    def t_get_calibration(self) -> list[dict[str, Any]]:
        return [{k: v for k, v in self.f.calib.reliability(c).items() if k != "table"} for c in self.f.calib.classes()]

    def t_get_research_log(self, limit: int = 15) -> list[dict[str, Any]]:
        return self.f.db.query("SELECT ts, author, kind, title, substr(body,1,600) AS body FROM research_notes "
                               "ORDER BY ts DESC LIMIT ?", (limit,))

    # ---------------- action tools (research artifacts only)
    def t_submit_strategy_candidates(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        ok, bad = [], []
        queue = self.f.db.kv_get("brain.candidate_queue", []) or []
        for c in candidates[:12]:
            raw = c.get("genome", c)
            try:
                raw = {**raw, "id": new_id("stg"), "origin": "llm", "generation": int(raw.get("generation", 0)),
                       "parents": raw.get("parents", [])}
                g = Genome.model_validate(raw)
            except Exception as e:
                bad.append({"error": str(e)[:300]})
                continue
            queue.append({"genome": g.model_dump(mode="json"), "rationale": c.get("rationale", {}),
                          "predicted_p": c.get("predicted_holdout_p_positive"), "call_id": self.call_id, "role": self.role})
            ok.append(g.id)
            self.artifacts.append({"kind": "genome", "ref_id": g.id, "prediction": c.get("predicted_holdout_p_positive")})
        self.f.db.kv_set("brain.candidate_queue", queue[-60:])
        return {"queued": ok, "rejected": bad}

    def t_record_lesson(self, statement: str, confidence: float, family: str | None = None) -> dict[str, Any]:
        lid = new_id("les")
        self.f.db.insert("lessons", {"id": lid, "statement": statement[:1000], "family": family,
                                     "confidence": float(min(max(confidence, 0), 1)), "created_at": _now()})
        self.artifacts.append({"kind": "lesson", "ref_id": lid})
        return {"lesson_id": lid}

    # ---------------- cognitive architecture
    def _pg(self) -> Any:
        from forge.agents.genome import PromptGenomes
        return PromptGenomes(self.f)

    def _session(self) -> str:
        return self.call_id.split(":", 1)[1] if ":" in self.call_id else self.call_id

    def t_get_role_brief(self, role: str) -> dict[str, Any]:
        return self._pg().brief(role, self._session())

    def t_submit_role_report(self, role: str, report: dict[str, Any]) -> dict[str, Any]:
        out = self._pg().submit_report(role, self._session(), report if isinstance(report, dict) else {"raw": str(report)})
        self.artifacts.append({"kind": "role_report", "ref_id": out.get("prompt_id")})
        return out

    def t_get_recent_candidates(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._pg().recent_candidates(limit)

    def t_get_role_reports(self, limit: int = 20, role: str | None = None) -> list[dict[str, Any]]:
        return self._pg().role_reports(self.role.replace("hermes_", ""), limit, role)

    def t_get_prompt_performance(self, role: str | None = None) -> list[dict[str, Any]]:
        return self._pg().performance(role)

    def t_submit_prompt_variant(self, role: str, hypothesis: str, sections: dict[str, str],
                                parent_version: int | None = None) -> dict[str, Any]:
        if not self.role.endswith("architect"):
            return {"error": "only the architect role may propose prompt variants"}
        out = self._pg().submit_variant(role, parent_version, hypothesis, sections, author=self.role)
        if out.get("prompt_id"):
            self.artifacts.append({"kind": "prompt_variant", "ref_id": out["prompt_id"]})
        return out

    def t_get_system_health(self) -> dict[str, Any]:
        f = self.f
        h = getattr(f, "health", None)
        warn = self.f.db.query("SELECT ts, agent, level, substr(message,1,240) AS message FROM timeline WHERE level IN "
                               "('warn','error') ORDER BY id DESC LIMIT 15")
        return {"score": h.score() if h else None, "loops": f.sup.snapshot() if hasattr(f.sup, "snapshot") else None,
                "quarantined": [r["key"].split(".", 1)[1] for r in self.f.db.query(
                    "SELECT key FROM kv_state WHERE key LIKE 'quarantine.%' AND value != 'null'")],
                "recent_warnings": warn, "bad_ticks_repaired_24h": self.f.db.scalar(
                    "SELECT COUNT(*) FROM listing_events WHERE event='BAD_TICK_REPAIRED' AND ts > ?",
                    (datetime_iso_hours_ago(24),))}

    def t_get_opportunity_surface(self) -> dict[str, Any]:
        db = self.f.db
        rails = db.query("SELECT id, category, status, executable, blockers, economics FROM rail_registry ORDER BY id")
        a = db.kv_get("surface.allocation") or {}
        return {"rails": [{**dict(r), "blockers": json.loads(r["blockers"] or "[]"),
                           "economics": json.loads(r["economics"] or "{}")} for r in rails],
                "now": a.get("now"), "unlock_value": a.get("unlock_value"), "fixed_costs": a.get("fixed_costs_usd_per_day"),
                "membership": db.kv_get("membership.coinbase_one")}

    def t_get_crossrail_evidence(self) -> dict[str, Any]:
        sc = self.f.db.kv_get("crossrail.scorecard") or {}
        return {**sc, "calibrator": self.f.db.kv_get("crossrail.calibrator"),
                "mapping": (self.f.db.kv_get("crossrail.mapping") or {}).get("mapped")}

    def t_get_shadow_rails(self) -> dict[str, Any]:
        rows = self.f.db.query("SELECT rail, COUNT(*) n, SUM(pnl_usd) pnl, AVG(pnl_usd / (entry * qty)) mean_ret, "
                               "AVG(hold_s) hold_s FROM shadow_trades GROUP BY rail")
        return {"rails": rows, "pegmaker": self.f.db.kv_get("pegmaker.state")}

    def t_get_listing_events(self, limit: int = 30) -> list[dict[str, Any]]:
        return self.f.db.query("SELECT ts, product_id, product_type, event, after FROM listing_events ORDER BY id DESC LIMIT ?",
                               (min(int(limit), 200),))

    def t_get_intelligence_budget(self) -> dict[str, Any]:
        b = getattr(self.f, "brain", None)
        roles = self.f.db.query("SELECT agent, COUNT(*) n, SUM(CAST(cost_usd AS REAL)) usd FROM inference_calls GROUP BY agent")
        return {"pace": self.f.db.kv_get("brain.pace"), "balance": getattr(b, "balance", None),
                "spend_by_agent": roles, "roi": {r: b.roi(r) for r in ("perception", "scientist", "hermes_governor",
                                                                     "hermes_alpha_inventor", "hermes_adversary", "hermes_rail_hunter")} if b else None}

    def t_submit_research_lead(self, title: str, body: str, category: str, sources: list[str] | None = None,
                               expected_value_usd_month: float | None = None) -> dict[str, Any]:
        lid = new_id("lead")
        self.f.db.insert("research_notes", {"id": lid, "ts": _now(), "author": self.role, "kind": f"lead:{category[:40]}",
                                            "title": title[:200], "body": json.dumps({"body": body[:4000], "sources": (sources or [])[:10],
                                                                                      "ev_usd_month": expected_value_usd_month})})
        self.artifacts.append({"kind": "lead", "ref_id": lid})
        if category.startswith(("report", "operator_action", "incident", "new_rail", "fee_change")):
            import asyncio
            agent = "Hermes" if self.role.startswith("hermes") else "DeepSeek Brain"
            msg = f"[{category}] {title[:120]}" + (f" — {body[:600]}" if category.startswith("report") else "")
            with contextlib.suppress(RuntimeError):
                asyncio.get_running_loop().create_task(self.f.say(agent, msg))
        return {"lead_id": lid}

    def t_request_research(self, focus: str, interval_s: int | None = None) -> dict[str, Any]:
        self.f.db.kv_set("brain.research_focus", {"focus": focus[:300], "interval_s": interval_s, "by": self.call_id})
        self.artifacts.append({"kind": "research_focus", "ref_id": focus[:60]})
        return {"ok": True}


def _short(m: dict[str, Any] | None) -> dict[str, Any] | None:
    if not m:
        return None
    keep = ("n", "mean_net", "win_rate", "p_positive", "alpha_mean", "alpha_p_positive", "drift_mean", "avg_hold_h",
            "log_per_capital_day", "max_dd", "profit_factor")
    return {k: m.get(k) for k in keep if k in m}


def _now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()


__all__ = ["TOOLS", "ToolRouter", "dumps"]


def datetime_iso_hours_ago(h: float) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) - timedelta(hours=h)).isoformat()
