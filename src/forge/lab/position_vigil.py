"""Position Vigil — always-on desk that kills stuck/losing inventory and regenerates challengers.

Founder requirement: a real firm does not let capital rot in a dead strategy. Detect → exit →
hibernate drain → demand a CHALLENGER from Quinn / arena immediately.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.position_vigil")

# PAPER thresholds (aggressive learning)
MAX_HOLD_S = 6 * 3600
MAX_UNREALIZED_PCT = -0.04          # -4% mark → cut
RETIRED_POPS = frozenset({"RETIRED", "HIBERNATING", "QUARANTINED"})
COOLDOWN_CHALLENGER_S = 300
FAMILY_CHALLENGER_COOLDOWN_S = 45 * 60  # intelligent: one invent thesis per family / 45m


class PositionVigil:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _unrealized_pct(self, pos: dict[str, Any]) -> float | None:
        try:
            cost = float(pos.get("cost_usd") or 0)
            qty = float(pos.get("qty") or 0)
            if cost <= 0 or qty <= 0:
                return None
            entry = float(pos.get("entry_price") or (cost / qty))
            sym = pos["symbol"]
            bbo = None
            try:
                bbo = self.f.market.bbo(sym)
            except Exception:
                bbo = None
            px = float(bbo.bid) if bbo and getattr(bbo, "bid", None) else None
            if px is None:
                # marks
                try:
                    marks = self.f.market.marks()
                    px = float(marks.get(sym) or marks.get(sym.split("-")[0]) or 0) or None
                except Exception:
                    px = None
            if px is None or entry <= 0:
                return None
            return (px / entry) - 1.0
        except Exception:
            return None

    def _opened_age_s(self, pos: dict[str, Any]) -> float:
        try:
            meta = json.loads(pos.get("meta") or "{}")
            if meta.get("opened_ts"):
                return time.time() - float(meta["opened_ts"])
        except Exception:
            pass
        oa = pos.get("opened_at") or ""
        try:
            import datetime as dt
            return time.time() - dt.datetime.fromisoformat(oa.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _force_exit(self, pos_id: str, reason: str) -> None:
        self.f.db.kv_set(
            f"position.force_exit.{pos_id}",
            {"ts": time.time(), "reason": reason, "source": "position_vigil"},
        )

    def _hibernate(self, sid: str, reason: str) -> None:
        try:
            from forge.strategies.registry import State
            st = self.f.reg.state(sid)
            if st and st.value not in RETIRED_POPS:
                self.f.reg.transition(sid, State.HIBERNATING, f"position_vigil: {reason}")
        except Exception as e:
            log.warning("hibernate %s: %s", sid, e)

    def _demand_challenger(self, dead_sid: str, family: str, why: str) -> None:
        db = self.f.db
        now = time.time()
        last = float((db.kv_get("vigil.last_challenger_ts") or {}).get(dead_sid) or 0)
        if now - last < COOLDOWN_CHALLENGER_S:
            return
        fam_mark = db.kv_get("vigil.family_challenger_ts") or {}
        last_fam = float(fam_mark.get(family) or 0)
        # Still hibernate/exit always; only throttle LLM invent directives per family
        skip_invent_llm = (now - last_fam) < FAMILY_CHALLENGER_COOLDOWN_S
        instruction = (
            f"CHALLENGER REQUIRED NOW (Position Vigil). Dead/draining strategy {dead_sid} "
            f"family={family}. Reason: {why}. Invent/mutate a replacement genome; "
            f"do NOT revive the milched edge. Prefer fee-aware microstructure/stables if spot directional is draining. "
            f"PAPER first. Report challenger id."
        )
        try:
            if not skip_invent_llm:
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "alpha_inventor", instruction[:1900], "critical", "OPEN", "position_vigil"),
                )
                fam_mark[family] = now
                db.kv_set("vigil.family_challenger_ts", fam_mark)
            else:
                # Still page governor for realloc; invent waits for intelligent spacing
                log.info("vigil: skip inventor LLM for family=%s (cooldown)", family)
            db.execute(
                "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                (now, "governor",
                 f"REALLOCATE after vigil cut of {dead_sid} ({why}). Prefer higher marginal PAPER streams; keep investing under $1/h target.",
                 "high", "OPEN", "position_vigil"),
            )
            if not skip_invent_llm:
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "adversary",
                     f"Postmortem {dead_sid}: why did this drain? Fee? regime? false signal? One paragraph + kill criterion.",
                     "high", "OPEN", "position_vigil"),
                )
        except Exception as e:
            log.warning("directive: %s", e)
        # Local regen: spawn diversity probes for that family immediately
        try:
            pl = getattr(self.f, "paper_lab", None)
            if pl and hasattr(pl, "promote_diversity_to_shadow"):
                pl.promote_diversity_to_shadow()
            if pl and hasattr(pl, "diversify_experimental"):
                pl.diversify_experimental()
        except Exception as e:
            log.debug("local regen: %s", e)
        mark = db.kv_get("vigil.last_challenger_ts") or {}
        mark[dead_sid] = now
        db.kv_set("vigil.last_challenger_ts", mark)
        # Ping Hermes cron inventor if CLI available — best-effort via kv flag consumed by ops
        db.kv_set("vigil.wake_inventor", {"ts": now, "sid": dead_sid, "family": family, "why": why})

    def scan(self) -> dict[str, Any]:
        db = self.f.db
        book = getattr(self.f, "book", "paper")
        rows = db.query(
            "SELECT p.*, s.population, s.family FROM positions p "
            "LEFT JOIN strategies s ON s.id = p.strategy_id "
            "WHERE p.book=? AND p.status IN ('OPEN','OPENING','CLOSING')",
            (book,),
        ) or []
        actions: list[dict[str, Any]] = []
        for r in rows:
            pos = dict(r)
            pid, sid = pos["id"], pos.get("strategy_id") or ""
            pop = (pos.get("population") or "").upper()
            fam = (pos.get("family") or "unknown").split("+")[0]
            age = self._opened_age_s(pos)
            upct = self._unrealized_pct(pos)
            why = None
            if pop in RETIRED_POPS:
                why = f"strategy_{pop.lower()}_still_holding"
            elif age >= MAX_HOLD_S and book == "paper":
                why = f"paper_hold_{int(age)}s_exceeds_{MAX_HOLD_S}s"
            elif upct is not None and upct <= MAX_UNREALIZED_PCT:
                why = f"unrealized_{upct:.2%}_cut"
            elif pos.get("status") == "CLOSING":
                # stuck closing with rejected exits
                meta = {}
                try:
                    meta = json.loads(pos.get("meta") or "{}")
                except Exception:
                    pass
                ex = db.query_one("SELECT status FROM orders WHERE client_order_id=?", (meta.get("exit_cid"),)) if meta.get("exit_cid") else None
                if ex and ex["status"] in ("REJECTED", "CANCELLED", "EXPIRED") and int(meta.get("exit_attempts") or 0) >= 1:
                    why = "exit_rejected_stuck"
            if not why:
                continue
            self._force_exit(pid, f"vigil:{why}")
            if sid:
                self._hibernate(sid, why)
                self._demand_challenger(sid, fam, why)
            actions.append({"position_id": pid, "symbol": pos.get("symbol"), "strategy_id": sid,
                            "family": fam, "action": "FORCE_EXIT+HIBERNATE+CHALLENGER", "why": why})
            try:
                import asyncio
                # timeline note
                db.execute(
                    "INSERT INTO research_notes (id, ts, author, kind, title, body) VALUES (?,?,?,?,?,?)",
                    (f"vigil_{int(time.time()*1000)}", str(time.time()), "position_vigil", "vigil_cut",
                     f"cut {pos.get('symbol')}", json.dumps(actions[-1])[:1900]),
                )
            except Exception:
                pass
        rep = {"ts": time.time(), "book": book, "n_open": len(rows), "actions": actions,
               "policy": {"max_hold_s": MAX_HOLD_S, "max_unrealized_pct": MAX_UNREALIZED_PCT,
                          "note": "always-on: cut stuck/losing → hibernate → challenger NOW"}}
        db.kv_set("lab.position_vigil", rep)
        if actions:
            log.warning("vigil acted: %s", actions)
            try:
                # sync announce if event loop available later via forge.say from async run
                self.f.db.kv_set("vigil.last_actions", {"ts": time.time(), "actions": actions})
            except Exception:
                pass
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("position_vigil")
            try:
                rep = await asyncio.to_thread(self.scan)
                if rep.get("actions"):
                    await self.f.say(
                        "Position Vigil",
                        f"Cut {len(rep['actions'])} stuck/losing book(s) → hibernate → challenger demanded. "
                        + "; ".join(f"{a['symbol']} ({a['why']})" for a in rep["actions"][:4]),
                        level="warn",
                    )
                    # Best-effort: queue Hermes inventor job
                    try:
                        import subprocess
                        subprocess.Popen(
                            ["sudo", "-u", "forge-hermes", "env",
                             "HOME=/srv/forge/runtime/hermes/home",
                             "HERMES_HOME=/srv/forge/runtime/hermes/home",
                             "HERMES_ACCEPT_HOOKS=1",
                             "/srv/forge/runtime/hermes/app/venv/bin/hermes",
                             "cron", "run", "c4e0a7346eb1"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                    except Exception:
                        pass
            except Exception as e:
                log.warning("position_vigil: %s", e, exc_info=True)
            await asyncio.sleep(45)
