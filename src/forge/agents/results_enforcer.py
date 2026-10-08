"""Results Enforcer — real-time workforce QA for money generation.

Blueprint spirit: no decorative roles, no fake work, no report-only theater.
Every ~3 minutes:
  1) Score recent role_reports: ACTION vs narrative fluff
  2) Check collaboration (handoffs accepted/completed, chain progress)
  3) Detect missed fires (open critical work + silence / cron without report)
  4) Attribute short-window Δ proven $/h and stables PnL
  5) Page / FORCE_WAKE report-only or missing officers
  6) Queue prompt-genome tweaks when a role is chronically non-economic
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

log = logging.getLogger("forge.results_enforcer")

CORE_ROLES = (
    "ops", "governor", "alpha_inventor", "critic", "adversary", "scout",
    "prediction", "execution", "treasury", "doctor", "architect",
    "intelligence", "rail_hunter",
)

# Words that smell like theater without actuation
FLUFF = re.compile(
    r"\b(monitoring|continue to (watch|monitor)|standing by|as discussed|"
    r"will (revisit|consider)|noted|acknowledged|in progress)\b",
    re.I,
)
ACTION_CUES = re.compile(
    r"\b(allocated|reallocated|force[_\s-]?exit|bridged|promoted|hibernated|"
    r"submitted\s+\d+|implemented|cut|sized|placed|settled|advanced|"
    r"workflow|handoff|challenger|capital-hours|ABORT|PASS|ALLOCATE)\b",
    re.I,
)


class ResultsEnforcer:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    # ------------------------------------------------------------------ scoring
    def _parse_report(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            return {"summary": str(raw)[:500]}

    def score_report(self, role: str, status: str, report: dict[str, Any],
                     proven_before: float | None = None, proven_after: float | None = None,
                     closed_directives: int = 0, handoffs_out: int = 0) -> dict[str, Any]:
        rt = str(report.get("result_type") or "").upper()
        summary = str(report.get("summary") or report.get("report") or "")
        st = str(status or report.get("status") or "").upper()

        score = 0.0
        tags: list[str] = []

        if st == "SILENT":
            score -= 2.0
            tags.append("SILENT")
        if rt == "ACTION_TAKEN":
            score += 3.0
            tags.append("ACTION_TAKEN")
        elif rt == "DECISION_MADE":
            score += 2.0
            tags.append("DECISION_MADE")
        elif rt == "NO_ACTION_JUSTIFIED":
            # Valid only with evidence + next trigger
            if report.get("evidence") or report.get("evidence_refs") or "because" in summary.lower():
                score += 1.0
                tags.append("NO_ACTION_JUSTIFIED_OK")
            else:
                score -= 1.5
                tags.append("NO_ACTION_UNJUSTIFIED")
        else:
            score -= 0.5
            tags.append("MISSING_RESULT_TYPE")

        if ACTION_CUES.search(summary):
            score += 1.5
            tags.append("ACTION_LANGUAGE")
        if FLUFF.search(summary) and not ACTION_CUES.search(summary):
            score -= 2.0
            tags.append("FLUFF")

        # Economic artifacts
        arts = report.get("artifacts") or report.get("evidence_refs") or []
        if arts:
            score += min(1.5, 0.3 * len(arts))
            tags.append("ARTIFACTS")
        if report.get("economic_attribution") or report.get("metrics_after") or report.get("metrics_before"):
            score += 1.0
            tags.append("ECON_ATTR")
        if closed_directives:
            score += min(2.0, 0.5 * closed_directives)
            tags.append(f"CLOSED_DIR_{closed_directives}")
        if handoffs_out:
            score += min(2.0, 1.0 * handoffs_out)
            tags.append(f"HANDOFFS_OUT_{handoffs_out}")

        # Money delta in window (if provided)
        if proven_before is not None and proven_after is not None:
            d = proven_after - proven_before
            if d > 0.001:
                score += 3.0
                tags.append("PROVEN_UP")
            elif d < -0.001:
                score -= 1.0
                tags.append("PROVEN_DOWN")

        # Spot-drain invention while under floor = anti-money
        if role == "alpha_inventor" and re.search(r"\b(breakout|alt|spot)\b", summary, re.I):
            if not re.search(r"stable", summary, re.I):
                score -= 2.0
                tags.append("SPOT_WHILE_UNDERPERFORMING")

        # Classify
        if score >= 4.0:
            grade = "EARNER"
        elif score >= 2.0:
            grade = "CONTRIBUTOR"
        elif score >= 0.0:
            grade = "MIXED"
        else:
            grade = "REPORT_ONLY"

        return {
            "role": role,
            "score": round(score, 2),
            "grade": grade,
            "result_type": rt or None,
            "tags": tags,
            "summary_head": summary[:160],
        }

    # ------------------------------------------------------------------ ticks
    def _proven(self) -> float:
        vel = self.f.db.kv_get("velocity") or {}
        return float((vel.get("expected_usd_per_h") or {}).get("proven") or 0.0)

    def _page(self, role: str, instruction: str, priority: str = "critical") -> None:
        try:
            self.f.db.execute(
                "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) "
                "VALUES (?,?,?,?,?,?)",
                (time.time(), role, instruction[:1900], priority, "OPEN", "results_enforcer"),
            )
        except Exception as e:
            log.warning("page %s: %s", role, e)

    def _wake(self, role: str) -> bool:
        for attr in ("employment", "officer_dispatch"):
            obj = getattr(self.f, attr, None)
            if obj and hasattr(obj, "_hermes_wake"):
                try:
                    if obj._hermes_wake(role):
                        return True
                except Exception:
                    pass
        # Direct fallback (forge may sudo to forge-hermes)
        import subprocess
        jid = (self.f.db.kv_get("hermes.cron_ids") or {}).get(role)
        if not jid:
            return False
        try:
            subprocess.Popen(
                ["sudo", "-u", "forge-hermes", "env",
                 "HOME=/srv/forge/runtime/hermes/home",
                 "HERMES_HOME=/srv/forge/runtime/hermes/home",
                 "HERMES_ACCEPT_HOOKS=1",
                 "/srv/forge/runtime/hermes/app/venv/bin/hermes",
                 "cron", "run", str(jid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            log.warning("wake %s: %s", role, e)
            return False

    def _prompt_tweak(self, role: str, diagnosis: str) -> dict[str, Any] | None:
        pg = getattr(self.f, "prompt_genomes", None)
        if not pg:
            return None
        # Rate-limit: one tweak per role per 6h
        last = (self.f.db.kv_get("results_enforcer.prompt_tweaks") or {}).get(role) or 0
        if time.time() - float(last) < 6 * 3600:
            return {"skipped": "cooldown"}
        champ = pg.champion(role)
        if not champ:
            return None
        try:
            sections = json.loads(champ["sections"]) if isinstance(champ.get("sections"), str) else (champ.get("sections") or {})
        except Exception:
            sections = {}
        # Inject hard results contract overlay
        overlay = (
            "\n\n## RESULTS ENFORCER OVERRIDE (money-first)\n"
            "You are graded on ECONOMIC ACTUATION, not prose.\n"
            "Every wake MUST end as ACTION_TAKEN | DECISION_MADE | NO_ACTION_JUSTIFIED with evidence.\n"
            "Required: close ≥1 open directive OR emit a typed handoff OR change a capital/strategy KV.\n"
            "Forbidden: monitoring essays, acknowledgements, 'will revisit' without a trigger condition.\n"
            f"Diagnosis that triggered this tweak: {diagnosis}\n"
            "Primary OKR: raise proven TRUE-NET $/h via stables PAPER capital-hours while LIVE off.\n"
        )
        mission = (sections.get("mission") or sections.get("Mission") or "") + overlay
        # Keep key section names stable
        key = "mission" if "mission" in sections else ("Mission" if "Mission" in sections else "mission")
        new_sections = {**sections, key: mission[-4000:]}
        try:
            out = pg.submit_variant(
                role,
                champ.get("version"),
                f"results_enforcer: cure REPORT_ONLY — {diagnosis[:200]}",
                new_sections,
                author="results_enforcer",
            )
            tweaks = self.f.db.kv_get("results_enforcer.prompt_tweaks") or {}
            tweaks[role] = time.time()
            self.f.db.kv_set("results_enforcer.prompt_tweaks", tweaks)
            return out
        except TypeError:
            # signature may differ — try minimal
            try:
                out = pg.submit_variant(role, None, diagnosis[:200], new_sections, author="results_enforcer")
                return out
            except Exception as e:
                return {"error": str(e)[:160]}
        except Exception as e:
            return {"error": str(e)[:160]}

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        proven = self._proven()
        stable = db.kv_get("lab.paper_stable_pnl") or {}
        prev = db.kv_get("results_enforcer.prev") or {}
        proven_before = float(prev.get("proven") or proven)
        stable_before = float((prev.get("stable_net") or stable.get("net") or 0))

        # Score last 2h reports (latest per role + all for averages)
        rows = db.query(
            "SELECT id, ts, role, status, report FROM role_reports WHERE ts >= ? ORDER BY ts DESC LIMIT 80",
            (now - 7200,),
        ) or []

        per_role: dict[str, list[dict[str, Any]]] = {}
        scored: list[dict[str, Any]] = []
        for r in rows:
            rep = self._parse_report(r.get("report"))
            # directives closed by this report
            closed = int(db.scalar(
                "SELECT COUNT(*) FROM ops_directives WHERE report_id=? AND status='DONE'",
                (r["id"],),
            ) or 0)
            # handoffs created near this report (±5m) by role
            handoffs_out = int(db.scalar(
                "SELECT COUNT(*) FROM agent_handoffs WHERE from_role=? AND created_at BETWEEN ? AND ?",
                (r["role"], float(r["ts"]) - 60, float(r["ts"]) + 300),
            ) or 0)
            s = self.score_report(
                r["role"], r.get("status") or "", rep,
                proven_before=proven_before, proven_after=proven,
                closed_directives=closed, handoffs_out=handoffs_out,
            )
            s["ts"] = r["ts"]
            s["report_id"] = r["id"]
            scored.append(s)
            per_role.setdefault(r["role"], []).append(s)

        roster: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        report_only: list[str] = []
        missing: list[str] = []

        for role in CORE_ROLES:
            open_d = int(db.scalar(
                "SELECT COUNT(*) FROM ops_directives WHERE status='OPEN' AND role=? AND priority IN ('critical','high')",
                (role,),
            ) or 0)
            pending_h = int(db.scalar(
                "SELECT COUNT(*) FROM agent_handoffs WHERE to_role=? AND status='PENDING'",
                (role,),
            ) or 0)
            last = (per_role.get(role) or [None])[0]
            last_ts = float(last["ts"]) if last else None
            age_s = (now - last_ts) if last_ts else None
            grades = [x["grade"] for x in (per_role.get(role) or [])[:5]]
            avg_score = (
                sum(x["score"] for x in (per_role.get(role) or [])[:5]) / max(1, len((per_role.get(role) or [])[:5]))
                if per_role.get(role) else None
            )

            # Missed fire: open critical work and no report in SLA window
            sla = 1800 if role not in ("architect", "intelligence", "rail_hunter") else 7200
            missed = bool((open_d > 0 or pending_h > 0) and (age_s is None or age_s > sla))
            chronic_report_only = bool(grades) and all(g == "REPORT_ONLY" for g in grades[:3]) and len(grades) >= 2
            latest_grade = last["grade"] if last else ("MISSING" if missed else "QUIET")

            entry = {
                "role": role,
                "latest_grade": latest_grade,
                "avg_score_5": round(avg_score, 2) if avg_score is not None else None,
                "age_s": int(age_s) if age_s is not None else None,
                "open_directives": open_d,
                "pending_handoffs": pending_h,
                "missed_fire": missed,
                "last_result_type": (last or {}).get("result_type"),
                "last_tags": (last or {}).get("tags"),
                "last_summary": (last or {}).get("summary_head"),
            }
            roster.append(entry)

            if missed:
                missing.append(role)
                woke = self._wake(role)
                self._page(
                    role,
                    f"RESULTS ENFORCER MISSED_FIRE: open_work={open_d} handoffs={pending_h} "
                    f"silence_s={int(age_s or -1)}. ACT now — ACTION_TAKEN with evidence or "
                    f"NO_ACTION_JUSTIFIED with trigger. Money OKR: raise proven $/h via stables PAPER.",
                    "critical",
                )
                actions.append({"role": role, "action": "MISSED_FIRE_WAKE", "woke": woke})

            if last and last["grade"] == "REPORT_ONLY" and (open_d > 0 or pending_h > 0):
                report_only.append(role)
                self._page(
                    role,
                    f"RESULTS ENFORCER REPORT_ONLY: your last wake scored {last['score']} "
                    f"(tags={last['tags']}). Do NOT write another essay. Close a directive, "
                    f"emit a typed handoff, or change capital/strategy state. Measure Δ$/h.",
                    "critical",
                )
                self._wake(role)
                actions.append({"role": role, "action": "REPORT_ONLY_PAGE", "score": last["score"]})

            if chronic_report_only:
                tw = self._prompt_tweak(role, f"chronic REPORT_ONLY grades={grades}")
                actions.append({"role": role, "action": "PROMPT_TWEAK", "result": tw})

        # Collaboration health
        ho_pending = int(db.scalar("SELECT COUNT(*) FROM agent_handoffs WHERE status='PENDING'") or 0)
        ho_done_2h = int(db.scalar(
            "SELECT COUNT(*) FROM agent_handoffs WHERE status='DONE' AND completed_at >= ?",
            (now - 7200,),
        ) or 0)
        ho_created_2h = int(db.scalar(
            "SELECT COUNT(*) FROM agent_handoffs WHERE created_at >= ?",
            (now - 7200,),
        ) or 0)
        wf_open = db.query(
            "SELECT workflow_id, stage, owner, status FROM agent_workflows WHERE status='OPEN'"
        ) or []

        # Stale pending handoffs > 45m → escalate to owner + Casey
        stale_ho = db.query(
            "SELECT handoff_id, to_role, payload_type, created_at FROM agent_handoffs "
            "WHERE status='PENDING' AND created_at < ?",
            (now - 2700,),
        ) or []
        for h in stale_ho[:8]:
            self._page(
                h["to_role"],
                f"RESULTS ENFORCER STALE_HANDOFF {h['handoff_id']} type={h['payload_type']}: "
                f"accept and complete with typed payload. Collaboration failure blocks income.",
                "critical",
            )
            self._wake(h["to_role"])
            actions.append({"action": "STALE_HANDOFF", "to": h["to_role"], "id": h["handoff_id"]})

        delta_proven = proven - proven_before
        delta_stable = float(stable.get("net") or 0) - stable_before

        # Firm-level grade
        earners = sum(1 for r in roster if r["latest_grade"] == "EARNER")
        report_only_n = sum(1 for r in roster if r["latest_grade"] == "REPORT_ONLY")
        if delta_proven > 0.002 or delta_stable > 0.01:
            firm_grade = "EARNING"
        elif earners >= 3 and report_only_n == 0:
            firm_grade = "ACTUATING"
        elif missing or report_only_n >= 3:
            firm_grade = "THEATER_RISK"
        else:
            firm_grade = "MIXED"

        # Luke/ops digest
        if firm_grade in ("THEATER_RISK",) or missing:
            self._page(
                "ops",
                f"RESULTS ENFORCER firm_grade={firm_grade}: missing={missing} report_only={report_only} "
                f"Δproven={delta_proven:.4f} Δstable_net={delta_stable:.4f}. "
                f"Intervene on non-earners; keep stables capital-hours primary.",
                "high",
            )

        board = {
            "ts": now,
            "firm_grade": firm_grade,
            "proven_usd_per_h": proven,
            "delta_proven_usd_per_h": round(delta_proven, 5),
            "stable_net": float(stable.get("net") or 0),
            "delta_stable_net": round(delta_stable, 5),
            "collaboration": {
                "handoffs_pending": ho_pending,
                "handoffs_done_2h": ho_done_2h,
                "handoffs_created_2h": ho_created_2h,
                "completion_rate_2h": round(ho_done_2h / max(1, ho_created_2h), 3),
                "open_workflows": wf_open,
                "stale_handoffs": len(stale_ho),
            },
            "roster": roster,
            "recent_scores": scored[:20],
            "report_only_roles": report_only,
            "missed_fire_roles": missing,
            "actions": actions[:30],
            "policy": {
                "grades": ["EARNER", "CONTRIBUTOR", "MIXED", "REPORT_ONLY", "MISSING"],
                "money_okr": "raise proven TRUE-NET $/h via evidenced sleeves (stables PAPER while LIVE off)",
                "report_only": "FORBIDDEN when open work exists",
                "prompt_tweaks": "auto after 2+ consecutive REPORT_ONLY",
            },
        }
        db.kv_set("lab.results_enforcer", board)
        db.kv_set("agents.results_scorecard", board)  # PWA/API alias
        db.kv_set("results_enforcer.prev", {
            "proven": proven,
            "stable_net": float(stable.get("net") or 0),
            "ts": now,
        })
        # Mirror slim grades into employment snapshot if present
        emp = db.kv_get("agents.employment") or {}
        if isinstance(emp, dict) and emp.get("roster"):
            by = {r["role"]: r for r in roster}
            for row in emp["roster"]:
                g = by.get(row.get("role"))
                if g:
                    row["results_grade"] = g["latest_grade"]
                    row["results_score"] = g["avg_score_5"]
                    row["missed_fire"] = g["missed_fire"]
            emp["results_firm_grade"] = firm_grade
            emp["results_ts"] = now
            db.kv_set("agents.employment", emp)

        if actions:
            log.info("results_enforcer: firm=%s actions=%s", firm_grade, actions[:6])
        return board

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("results_enforcer")
            try:
                board = await asyncio.to_thread(self.tick)
                if board.get("firm_grade") in ("THEATER_RISK", "EARNING") or board.get("actions"):
                    await self.f.say(
                        "Results Enforcer",
                        f"firm={board.get('firm_grade')} Δproven={board.get('delta_proven_usd_per_h')} "
                        f"report_only={board.get('report_only_roles')} missed={board.get('missed_fire_roles')}",
                        level="info" if board.get("firm_grade") != "THEATER_RISK" else "warn",
                    )
            except Exception as e:
                log.warning("results_enforcer: %s", e, exc_info=True)
            await asyncio.sleep(180)
