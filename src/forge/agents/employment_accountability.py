"""Employment Accountability Supervisor — RED ZONE 30m SLA, no silent STALE.

Blueprint §§8–9, 51. Deterministic loop (~5m):
  - maintain agent_heartbeats states
  - approaching SLA → nudge/wake
  - breach → force wake + page Casey + Luke
  - never mark directives DONE
"""
from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

log = logging.getLogger("forge.employment")

# Callsign → Hermes role id
CORE_RED = {
    "ops": ("ops", 30 * 60),
    "governor": ("governor", 30 * 60),
    "alpha_inventor": ("alpha_inventor", 30 * 60),
    "critic": ("critic", 30 * 60),
    "adversary": ("adversary", 30 * 60),
    "scout": ("scout", 30 * 60),
    "prediction": ("prediction", 45 * 60),  # Nolan
    "execution": ("execution", 45 * 60),    # Reid
    "treasury": ("treasury", 30 * 60),      # Ellis
    "doctor": ("doctor", 30 * 60),
}
SPECIAL = {
    "rail_hunter": ("rail_hunter", 2 * 3600),
    "architect": ("architect", 2 * 3600),
    "intelligence": ("intelligence", 2 * 3600),  # Mira
}
CRON_IDS = {
    "alpha_inventor": "c4e0a7346eb1",
    "governor": "cd8994146031",
    "adversary": "89bddc6f49e2",
    "critic": "7f899ce67a80",
    "doctor": "59ad26aee185",
    "rail_hunter": "96d6ac22e134",
    "scout": "106a359ab6db",
    "architect": "cef76dea5e32",
    # specialists filled after cron create
    "prediction": None,
    "execution": None,
    "treasury": None,
    "intelligence": None,
}

VALID_IDLE = {
    "WORKING", "MONITORING", "WAITING_DATA", "WAITING_DEPENDENCY",
    "IDLE_BY_DESIGN", "BLOCKED", "FAILED", "RECOVERING", "STALE_SLA_BREACH",
}


class EmploymentAccountability:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _red_zone(self) -> bool:
        nav = None
        try:
            t = self.f.db.kv_get("treasury.truth") or {}
            nav = t.get("nav") or t.get("equity_usd")
            if nav is None:
                board = self.f.db.kv_get("econ.treasury_board") or {}
                nav = board.get("nav")
        except Exception:
            pass
        try:
            return float(nav or 0) < 50.0
        except Exception:
            return True

    def _last_meaningful(self, role: str) -> float | None:
        db = self.f.db
        row = db.query_one("SELECT MAX(ts) ts FROM role_reports WHERE role=?", (role,))
        if row and row.get("ts"):
            return float(row["ts"])
        # specialist aliases may report under boot role names
        return None

    def _hermes_wake(self, role: str) -> bool:
        jid = CRON_IDS.get(role)
        # refresh from kv if specialists registered
        reg = self.f.db.kv_get("hermes.cron_ids") or {}
        jid = reg.get(role) or jid
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

    def _page(self, role: str, instruction: str, priority: str = "critical") -> None:
        now = time.time()
        try:
            self.f.db.execute(
                "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) "
                "VALUES (?,?,?,?,?,?)",
                (now, role, instruction[:1900], priority, "OPEN", "employment_accountability"),
            )
        except Exception as e:
            log.warning("page %s: %s", role, e)

    def _upsert_hb(self, role: str, state: str, **kw: Any) -> None:
        now = time.time()
        try:
            self.f.db.execute(
                "INSERT INTO agent_heartbeats(role,state,last_seen,last_meaningful_action,"
                "current_objective,next_wake,blocker,health,reason,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(role) DO UPDATE SET state=excluded.state, last_seen=excluded.last_seen, "
                "last_meaningful_action=excluded.last_meaningful_action, current_objective=excluded.current_objective, "
                "next_wake=excluded.next_wake, blocker=excluded.blocker, health=excluded.health, "
                "reason=excluded.reason, updated_at=excluded.updated_at",
                (role, state, kw.get("last_seen"), kw.get("last_meaningful_action"),
                 kw.get("current_objective"), kw.get("next_wake"), kw.get("blocker"),
                 kw.get("health", "ok"), kw.get("reason"), now),
            )
        except Exception as e:
            # table may not exist yet — KV fallback
            log.debug("hb upsert %s: %s", role, e)

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        red = self._red_zone()
        # refresh cron ids
        cron_kv = db.kv_get("hermes.cron_ids") or {}
        for k, v in cron_kv.items():
            if k in CRON_IDS:
                CRON_IDS[k] = v

        roster_out = []
        actions = []
        roles = {**CORE_RED, **SPECIAL}
        # Also include classic heartbeat roles without specialist aliases
        for role, (_hermes, sla) in roles.items():
            max_silence = sla if red else max(sla * 4, 2 * 3600)
            last = self._last_meaningful(role)
            # Map specialist report roles: prediction may file as nolan etc — check aliases
            if last is None and role in ("prediction", "execution", "treasury", "intelligence"):
                aliases = {
                    "prediction": ["prediction", "nolan"],
                    "execution": ["execution", "reid"],
                    "treasury": ["treasury", "ellis"],
                    "intelligence": ["intelligence", "mira", "architect"],
                }.get(role, [role])
                for a in aliases:
                    last = self._last_meaningful(a)
                    if last:
                        break
            hermes_role = {
                "prediction": "prediction",
                "execution": "execution",
                "treasury": "treasury",
                "intelligence": "intelligence",
            }.get(role, role)
            open_d = int(db.scalar(
                "SELECT COUNT(*) FROM ops_directives WHERE status IN ('OPEN','DISPATCHED') AND role=?",
                (hermes_role,),
            ) or 0)

            age = (now - last) if last else None
            pending_handoff = 0
            try:
                pending_handoff = int(db.scalar(
                    "SELECT COUNT(*) FROM agent_handoffs WHERE to_role=? AND status='PENDING'",
                    (hermes_role,),
                ) or 0)
            except Exception:
                pass

            state = "MONITORING"
            reason = "within_sla"
            if age is None:
                state = "IDLE_BY_DESIGN" if open_d == 0 and pending_handoff == 0 else "WAITING_DEPENDENCY"
                reason = "no_role_report_yet" if open_d == 0 else "open_work_no_report"
            elif open_d > 0 or pending_handoff > 0:
                if age > max_silence:
                    state = "STALE_SLA_BREACH"
                    reason = f"open_work age_s={int(age)} sla={max_silence}"
                elif age > max_silence * 0.6:
                    state = "WORKING"
                    reason = "approaching_sla_with_open_work"
                else:
                    state = "WORKING"
                    reason = "open_work"
            else:
                if age > max_silence * 2:
                    # no open work but long silence — still want IDLE explanation
                    state = "IDLE_BY_DESIGN"
                    reason = f"silent_no_open_work age_s={int(age)}"
                else:
                    state = "MONITORING"
                    reason = "deterministic_desk_covers"

            # Escalation
            if state == "STALE_SLA_BREACH" or (age is not None and open_d > 0 and age > max_silence):
                woke = self._hermes_wake(hermes_role)
                self._page(hermes_role,
                           f"STALE_SLA_BREACH RED={red}: file REAL role_report with results contract "
                           f"(ACTION_TAKEN|DECISION_MADE|NO_ACTION_JUSTIFIED). age_s={int(age or -1)} "
                           f"open_criticalish={open_d}. Do not narrate — act or justify.",
                           "critical")
                self._page("doctor",
                           f"Casey: role={hermes_role} STALE_SLA_BREACH. Diagnose cron/gate/provider. "
                           f"Recover wake path. Preserve OPEN directives.",
                           "critical")
                self._page("governor",
                           f"Luke/Cyrus: workforce SLA breach on {hermes_role}. Follow through until report.",
                           "high")
                actions.append({"role": hermes_role, "action": "FORCE_WAKE", "woke": woke, "age": age})
                state = "STALE_SLA_BREACH"
            elif age is not None and open_d > 0 and age > max_silence * 0.55:
                self._hermes_wake(hermes_role)
                actions.append({"role": hermes_role, "action": "PREWAKE", "age": age})

            self._upsert_hb(
                hermes_role, state,
                last_seen=now,
                last_meaningful_action=last,
                current_objective=f"open_directives={open_d} handoffs={pending_handoff}",
                next_wake=now + (300 if red else 900),
                blocker=None if state not in ("BLOCKED", "STALE_SLA_BREACH", "FAILED") else reason,
                reason=reason,
                health="degraded" if state == "STALE_SLA_BREACH" else "ok",
            )
            roster_out.append({
                "role": hermes_role,
                "state": state,
                "age_h": round(age / 3600, 2) if age is not None else None,
                "sla_s": max_silence,
                "open_directives": open_d,
                "pending_handoffs": pending_handoff,
                "reason": reason,
                "red_zone": red,
            })

        # Mirror slim roster into agents.heartbeat for PWA compatibility
        legacy = []
        for r in roster_out:
            emp = "ACTIVE"
            if r["state"] == "STALE_SLA_BREACH":
                emp = "STALE"
            elif r["state"] in ("IDLE_BY_DESIGN", "MONITORING"):
                emp = "ACTIVE" if (r["age_h"] is not None and r["age_h"] < 1) else ("STALE" if (r["age_h"] or 99) > 1 else "QUIET")
            elif r["state"] == "WORKING":
                emp = "ACTIVE"
            legacy.append({
                "role": r["role"],
                "employment": emp,
                "age_h": r["age_h"],
                "open_directives": r["open_directives"],
                "state": r["state"],
                "reason": r["reason"],
                "sla_s": r["sla_s"],
                "reports_24h": 0,
            })
        rep = {
            "ts": now,
            "red_zone": red,
            "max_silence_red_s": 1800,
            "roster": legacy,
            "detailed": roster_out,
            "actions": actions,
            "policy": "RED ZONE core ≤30m unexplained silence; IDLE_BY_DESIGN ok; never fake DONE",
        }
        db.kv_set("agents.heartbeat", rep)
        db.kv_set("agents.employment", rep)
        if actions:
            log.info("employment: %s", actions[:8])
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("employment_accountability")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("employment: %s", e, exc_info=True)
            await asyncio.sleep(300)
