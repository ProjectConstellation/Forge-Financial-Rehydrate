"""Live evidence board — what works, what doesn't, what's inconclusive (PAPER truth)."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.evidence_board")


class EvidenceBoard:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def compute(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        # Paper strategy outcomes
        rows = db.query(
            "SELECT strategy_id, COUNT(*) n, "
            "SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)) net, "
            "SUM(CASE WHEN CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL) > 0 THEN 1 ELSE 0 END) wins "
            "FROM positions WHERE book='paper' AND status='CLOSED' GROUP BY strategy_id"
        ) or []
        works, fails, thin = [], [], []
        for r in rows:
            n = int(r["n"] or 0)
            net = float(r["net"] or 0)
            wr = float(r["wins"] or 0) / n if n else 0
            card = {"strategy_id": r["strategy_id"], "n": n, "true_net": round(net, 4), "win_rate": round(wr, 3),
                    "source": "paper_positions"}
            if n < 5:
                thin.append(card)
            elif net > 0 and wr >= 0.45:
                works.append(card)
            elif net < 0:
                fails.append(card)
            else:
                thin.append(card)
        # Shadow rails (stables etc.)
        shadows = db.query(
            "SELECT rail, COUNT(*) n, SUM(CAST(pnl_usd AS REAL)) net FROM shadow_trades "
            "WHERE ts > ? GROUP BY rail", (now - 86400,)
        ) or []
        shadow_cards = []
        for r in shadows:
            n = int(r["n"] or 0)
            net = float(r["net"] or 0)
            card = {"rail": r["rail"], "n": n, "true_net_24h": round(net, 4), "source": "shadow_trades"}
            shadow_cards.append(card)
            if n >= 20 and net > 0:
                works.append({**card, "strategy_id": r["rail"], "true_net": round(net, 4), "win_rate": None})
            elif n >= 20 and net < 0:
                fails.append({**card, "strategy_id": r["rail"], "true_net": round(net, 4), "win_rate": None})
        # Population diversity
        pop = db.query(
            "SELECT family, population, COUNT(*) c FROM strategies "
            "WHERE population IN ('EXPERIMENTAL','SHADOW','CHALLENGER','PRODUCTION') "
            "GROUP BY 1,2"
        ) or []
        vel = db.kv_get("velocity") or {}
        tcs = db.kv_get("treasury.tcs") or {}
        works.sort(key=lambda x: -(x.get("true_net") or 0))
        fails.sort(key=lambda x: (x.get("true_net") or 0))

        # Family scoreboard — aggregate paper + bridged stable evidence
        fam_rows = db.query(
            "SELECT family, population, COUNT(*) c FROM strategies "
            "WHERE population IN ('EXPERIMENTAL','SHADOW','CHALLENGER','PRODUCTION') GROUP BY 1,2"
        ) or []
        family_scoreboard = {}
        for r in fam_rows:
            base = str(r["family"]).split("+")[0]
            slot = family_scoreboard.setdefault(base, {"experimental": 0, "shadow": 0, "challenger": 0, "production": 0})
            pop_key = str(r["population"]).lower()
            if pop_key in slot:
                slot[pop_key] += int(r["c"])
        stable_book = db.kv_get("lab.paper_stable_pnl") or {}
        if isinstance(stable_book, dict):
            for rail, br in (stable_book.get("by_rail") or {}).items():
                key = rail.replace("coinbase.", "")
                slot = family_scoreboard.setdefault(key, {"experimental": 0, "shadow": 0, "challenger": 0, "production": 0})
                slot["paper_bridged_net"] = round(float(br.get("net") or 0), 4)
                slot["paper_bridged_n"] = int(br.get("n") or 0)
        next_actions = []
        if works:
            next_actions.append(
                f"DOUBLE DOWN (PAPER): {works[0].get('strategy_id')} — only stream with sequential +EV so far"
            )
        if fails:
            next_actions.append(
                f"KILL/HIBERNATE after more evidence: {fails[0].get('strategy_id')} draining paper"
            )
        thin_fams = [
            f for f, v in family_scoreboard.items()
            if (v.get("experimental", 0) + v.get("shadow", 0)) < 5
        ]
        if thin_fams:
            next_actions.append(f"SPAWN more PAPER probes: {', '.join(thin_fams[:6])}")
        next_actions.append("Binding capital: +$10 raises proven frontier most (see trial/current)")

        rep = {
            "ts": now,
            "mode_label": "PAPER — REAL MARKET / SIMULATED MONEY",
            "works": works[:25],
            "doesnt_work": fails[:25],
            "inconclusive": thin[:25],
            "shadow_rails_24h": shadow_cards,
            "population": pop,
            "binding": ((vel.get("priorities") or [{}])[0]).get("action"),
            "proven_usd_per_h": (vel.get("expected_usd_per_h") or {}).get("proven"),
            "tcs_drains": (tcs.get("drains") or [])[:10],
            "lesson": (
                "PAPER aggressiveness: run many fee-aware families in parallel; "
                "kill drains with sequential evidence; promote only what clears fees."
            ),
            "family_scoreboard": family_scoreboard,
            "what_to_do_next": next_actions,
        }
        db.kv_set("lab.evidence_board", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("evidence_board")
            try:
                await asyncio.to_thread(self.compute)
            except Exception as e:
                log.warning("evidence_board: %s", e, exc_info=True)
            await asyncio.sleep(60)
