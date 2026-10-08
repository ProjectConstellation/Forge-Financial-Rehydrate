"""Officer Dispatch — 24/7 goals, event wakes, NEVER fake-DONE.

Blueprint §11: only structured role_report closes directives.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any

log = logging.getLogger("forge.officer_dispatch")

CRON_IDS = {
    "alpha_inventor": "c4e0a7346eb1",
    "governor": "cd8994146031",
    "adversary": "89bddc6f49e2",
    "critic": "7f899ce67a80",
    "doctor": "59ad26aee185",
    "rail_hunter": "96d6ac22e134",
    "scout": "106a359ab6db",
    "architect": "cef76dea5e32",
    "prediction": None,
    "execution": None,
    "treasury": None,
    "intelligence": None,
    "ops": None,
}

FAMILY_INVENT_COOLDOWN_S = 45 * 60
ROLE_WAKE_COOLDOWN_S = {
    "alpha_inventor": 10 * 60,
    "governor": 10 * 60,
    "adversary": 15 * 60,
    "doctor": 10 * 60,
    "scout": 15 * 60,
    "rail_hunter": 30 * 60,
    "critic": 15 * 60,
    "architect": 30 * 60,
    "prediction": 15 * 60,
    "execution": 15 * 60,
    "treasury": 10 * 60,
    "intelligence": 30 * 60,
}


class OfficerDispatch:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _cron_id(self, role: str) -> str | None:
        reg = self.f.db.kv_get("hermes.cron_ids") or {}
        return reg.get(role) or CRON_IDS.get(role)

    def _wake_state(self) -> dict[str, Any]:
        return self.f.db.kv_get("dispatch.officer_wake") or {"roles": {}, "families": {}, "wakes": []}

    def _save_wake(self, st: dict[str, Any]) -> None:
        st["wakes"] = (st.get("wakes") or [])[-40:]
        self.f.db.kv_set("dispatch.officer_wake", st)

    def _local_regen(self, family: str, why: str) -> dict[str, Any]:
        out: dict[str, Any] = {"family": family, "why": why}
        pl = getattr(self.f, "paper_lab", None)
        if not pl:
            return out
        try:
            if hasattr(pl, "diversify_experimental"):
                out["diversify"] = pl.diversify_experimental()
            if hasattr(pl, "promote_diversity_to_shadow"):
                out["shadow"] = pl.promote_diversity_to_shadow()
            if hasattr(pl, "promote_paper_probes"):
                out["probes"] = pl.promote_paper_probes()
            if hasattr(pl, "bridge_stable_shadow_to_paper"):
                out["bridge"] = pl.bridge_stable_shadow_to_paper()
        except Exception as e:
            out["error"] = str(e)[:200]
            log.warning("local_regen: %s", e)
        return out

    def _hermes_wake(self, role: str) -> bool:
        jid = self._cron_id(role)
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
            log.warning("hermes wake %s: %s", role, e)
            return False

    def _extract_family(self, instruction: str) -> str:
        for part in instruction.replace(",", " ").split():
            if part.startswith("family="):
                return part.split("=", 1)[1].strip().lower()[:40]
        return "unknown"

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        st = self._wake_state()
        rows = db.query(
            "SELECT id, role, priority, instruction, requested_by, ts FROM ops_directives "
            "WHERE status='OPEN' AND priority IN ('critical','high') ORDER BY id ASC LIMIT 40"
        ) or []
        actions: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            role = d["role"]
            if role == "all":
                continue
            instr = d.get("instruction") or ""
            family = self._extract_family(instr)
            cool_role = ROLE_WAKE_COOLDOWN_S.get(role, 15 * 60)
            last_role = float((st.get("roles") or {}).get(role) or 0)
            # NEVER fake-complete. Cooldown only skips re-wake; leave OPEN for Hermes report.
            if now - last_role < cool_role:
                actions.append({"id": d["id"], "role": role, "action": "HOLD_OPEN_COOLDOWN"})
                # Critical: re-wake after 60s even inside cooldown if still OPEN
                if str(d.get("priority")).lower() == "critical" and now - last_role > 60:
                    self._hermes_wake(role)
                    st.setdefault("roles", {})[role] = now
                continue

            if role == "alpha_inventor":
                last_fam = float((st.get("families") or {}).get(family) or 0)
                regen = self._local_regen(family, instr[:200])
                need_llm = (now - last_fam) >= FAMILY_INVENT_COOLDOWN_S
                woke = False
                if need_llm:
                    woke = self._hermes_wake(role)
                    st.setdefault("families", {})[family] = now
                    st.setdefault("roles", {})[role] = now
                    action = "LOCAL+LLM_WAKE"
                    result = f"LOCAL_REGEN + HERMES_WAKE family={family}. regen={json.dumps(regen, default=str)[:500]}"
                else:
                    action = "LOCAL_ONLY"
                    result = (
                        f"LOCAL_REGEN only (family={family} invent cooldown "
                        f"{int(FAMILY_INVENT_COOLDOWN_S - (now - last_fam))}s left). "
                        f"regen={json.dumps(regen, default=str)[:500]}"
                    )
                    st.setdefault("roles", {})[role] = now
                db.execute(
                    "UPDATE ops_directives SET result=? WHERE id=? AND status='OPEN'",
                    (f"DISPATCHED:{action} {result}"[:1900], d["id"]),
                )
                actions.append({"id": d["id"], "role": role, "family": family, "action": action, "woke": woke})
                st.setdefault("wakes", []).append({"ts": now, "role": role, "family": family, "action": action})
                continue

            woke = self._hermes_wake(role)
            st.setdefault("roles", {})[role] = now
            db.execute(
                "UPDATE ops_directives SET result=? WHERE id=? AND status='OPEN'",
                (f"DISPATCHED:HERMES_WAKE {role} — awaiting officer report", d["id"]),
            )
            actions.append({"id": d["id"], "role": role, "action": "LLM_WAKE", "woke": woke})
            st.setdefault("wakes", []).append({"ts": now, "role": role, "action": "LLM_WAKE"})

        wake_flag = db.kv_get("vigil.wake_inventor")
        if wake_flag and float(wake_flag.get("ts") or 0) > now - 600:
            fam = str(wake_flag.get("family") or "unknown")
            last_fam = float((st.get("families") or {}).get(fam) or 0)
            if now - last_fam >= FAMILY_INVENT_COOLDOWN_S:
                self._local_regen(fam, str(wake_flag.get("why") or ""))
                self._hermes_wake("alpha_inventor")
                st.setdefault("families", {})[fam] = now
                st.setdefault("roles", {})["alpha_inventor"] = now
                actions.append({"action": "VIGIL_FLAG_WAKE", "family": fam})
                db.kv_set("vigil.wake_inventor", {**wake_flag, "dispatched": True, "dispatched_ts": now})

        # Repair any historical fake-DONE high that still say acked_cooldown with open work needed — leave history
        rep = {
            "ts": now,
            "n_open_seen": len(rows),
            "actions": actions,
            "policy": {
                "family_invent_cooldown_s": FAMILY_INVENT_COOLDOWN_S,
                "role_wake_cooldown_s": ROLE_WAKE_COOLDOWN_S,
                "fake_done": "FORBIDDEN",
                "note": "DONE only via submit_role_report evidence",
            },
        }
        self._save_wake(st)
        db.kv_set("lab.officer_dispatch", rep)
        if actions:
            log.info("officer_dispatch: %s", actions[:6])
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("officer_dispatch")
            try:
                rep = await asyncio.to_thread(self.tick)
                if any(a.get("action") in ("LOCAL+LLM_WAKE", "LLM_WAKE", "VIGIL_FLAG_WAKE") for a in rep.get("actions") or []):
                    await self.f.say(
                        "Officer Dispatch",
                        "Event-woke officers for open directives. "
                        + "; ".join(
                            f"{a.get('role', a.get('action'))}:{a.get('action')}"
                            for a in (rep.get("actions") or [])[:4]
                        ),
                        level="info",
                    )
            except Exception as e:
                log.warning("officer_dispatch: %s", e, exc_info=True)
            await asyncio.sleep(60)
