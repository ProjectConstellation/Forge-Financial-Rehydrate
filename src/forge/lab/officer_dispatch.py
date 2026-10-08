"""Officer Dispatch — keep firm goals alive 24/7 without burning inference 24/7.

Deterministic loop (~60s):
  - Consumes OPEN critical/high ops_directives (from Position Vigil etc.)
  - Event-wakes the matching Hermes officer *once* per family/role cooldown
  - Prefers local PAPER regen (no LLM) first; LLM only when a new strategy thesis is needed
  - Marks duplicate/stale directives DONE so the desk does not thrash Quinn every cut
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any

log = logging.getLogger("forge.officer_dispatch")

# Role → Hermes cron job id (active jobs on production)
CRON_IDS = {
    "alpha_inventor": "c4e0a7346eb1",
    "governor": "cd8994146031",
    "adversary": "89bddc6f49e2",
    "critic": "7f899ce67a80",
    "doctor": "59ad26aee185",
    "rail_hunter": "96d6ac22e134",
    "scout": "106a359ab6db",
    "architect": "cef76dea5e32",
}

# Do NOT invent a new thesis every cut — intelligent spacing
FAMILY_INVENT_COOLDOWN_S = 45 * 60   # 45m per family for Quinn
ROLE_WAKE_COOLDOWN_S = {
    "alpha_inventor": 20 * 60,
    "governor": 15 * 60,
    "adversary": 30 * 60,
    "doctor": 10 * 60,
    "scout": 30 * 60,
    "rail_hunter": 60 * 60,
    "critic": 6 * 3600,
    "architect": 12 * 3600,
}


class OfficerDispatch:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _wake_state(self) -> dict[str, Any]:
        return self.f.db.kv_get("dispatch.officer_wake") or {"roles": {}, "families": {}, "wakes": []}

    def _save_wake(self, st: dict[str, Any]) -> None:
        wakes = st.get("wakes") or []
        st["wakes"] = wakes[-40:]
        self.f.db.kv_set("dispatch.officer_wake", st)

    def _local_regen(self, family: str, why: str) -> dict[str, Any]:
        """No-LLM first response: rotate PAPER probes / diversity shadows."""
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
        jid = CRON_IDS.get(role)
        if not jid:
            return False
        try:
            subprocess.Popen(
                ["sudo", "-u", "forge-hermes", "env",
                 "HOME=/srv/forge/runtime/hermes/home",
                 "HERMES_HOME=/srv/forge/runtime/hermes/home",
                 "HERMES_ACCEPT_HOOKS=1",
                 "/srv/forge/runtime/hermes/app/venv/bin/hermes",
                 "cron", "run", jid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            log.warning("hermes wake %s: %s", role, e)
            return False

    def _extract_family(self, instruction: str) -> str:
        # "family=breakout" style from vigil
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
            "WHERE status='OPEN' AND priority IN ('critical','high') ORDER BY id ASC LIMIT 30"
        ) or []
        actions: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            role = d["role"]
            if role == "all":
                continue
            instr = d.get("instruction") or ""
            family = self._extract_family(instr)
            cool_role = ROLE_WAKE_COOLDOWN_S.get(role, 30 * 60)
            last_role = float((st.get("roles") or {}).get(role) or 0)
            # Dedupe: if same role woken recently, mark directive acknowledged without re-waking
            if now - last_role < cool_role:
                db.execute(
                    "UPDATE ops_directives SET status='DONE', result=?, done_ts=? WHERE id=? AND status='OPEN'",
                    (f"acked_cooldown: last wake {int(now-last_role)}s ago; local desk handling", now, d["id"]),
                )
                actions.append({"id": d["id"], "role": role, "action": "ACK_COOLDOWN"})
                continue

            if role == "alpha_inventor":
                last_fam = float((st.get("families") or {}).get(family) or 0)
                # Always do local regen (cheap); LLM invent only if family cooldown elapsed
                regen = self._local_regen(family, instr[:200])
                need_llm = (now - last_fam) >= FAMILY_INVENT_COOLDOWN_S
                woke = False
                if need_llm:
                    woke = self._hermes_wake(role)
                    st.setdefault("families", {})[family] = now
                    st.setdefault("roles", {})[role] = now
                    result = (
                        f"LOCAL_REGEN + HERMES_WAKE inventor family={family}. "
                        f"regen={json.dumps(regen, default=str)[:500]}"
                    )
                    action = "LOCAL+LLM_WAKE"
                else:
                    result = (
                        f"LOCAL_REGEN only (family={family} invent cooldown "
                        f"{int(FAMILY_INVENT_COOLDOWN_S - (now - last_fam))}s left). "
                        f"Avoid thrashing strategies. regen={json.dumps(regen, default=str)[:500]}"
                    )
                    action = "LOCAL_ONLY"
                    st.setdefault("roles", {})[role] = now  # still pace role
                db.execute(
                    "UPDATE ops_directives SET status='DONE', result=?, done_ts=? WHERE id=? AND status='OPEN'",
                    (result[:1900], now, d["id"]),
                )
                actions.append({"id": d["id"], "role": role, "family": family, "action": action, "woke": woke})
                st.setdefault("wakes", []).append({"ts": now, "role": role, "family": family, "action": action})
                continue

            # Other officers: wake once per role cooldown
            woke = self._hermes_wake(role)
            st.setdefault("roles", {})[role] = now
            db.execute(
                "UPDATE ops_directives SET status='DONE', result=?, done_ts=? WHERE id=? AND status='OPEN'",
                (f"HERMES_WAKE {role} (event-driven officer_dispatch)", now, d["id"]),
            )
            actions.append({"id": d["id"], "role": role, "action": "LLM_WAKE", "woke": woke})
            st.setdefault("wakes", []).append({"ts": now, "role": role, "action": "LLM_WAKE"})

        # Also honor vigil.wake_inventor flag if directive path missed
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

        rep = {
            "ts": now,
            "n_open_seen": len(rows),
            "actions": actions,
            "policy": {
                "family_invent_cooldown_s": FAMILY_INVENT_COOLDOWN_S,
                "role_wake_cooldown_s": ROLE_WAKE_COOLDOWN_S,
                "note": "24/7 goals via deterministic desk; LLM only on justified events + cooldowns",
            },
        }
        self._save_wake(st)
        db.kv_set("lab.officer_dispatch", rep)
        if actions:
            log.info("officer_dispatch: %s", actions)
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
                        "Event-woke officers for open directives (inference only when justified). "
                        + "; ".join(
                            f"{a.get('role', a.get('action'))}:{a.get('action')}"
                            for a in (rep.get("actions") or [])[:4]
                        ),
                        level="info",
                    )
            except Exception as e:
                log.warning("officer_dispatch: %s", e, exc_info=True)
            await asyncio.sleep(60)
