"""Aggressive PAPER laboratory — diversify, probe, score, kill, promote (no LIVE).

Founder mandate: with simulated money, test many investment kinds aggressively to learn
what works. Fee-aware — not activity theatre. Spot stays paper; stables paper-bridged.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.paper_lab")

# Paper-mode arena aggressiveness
PAPER_MAX_SHADOW = 80
PAPER_MAX_EXPERIMENTAL = 240
PAPER_MAX_CONCURRENT_POS = 16
DIVERSITY_FAMILIES_TARGET = 8


class PaperLab:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def ensure_stable_strategies(self) -> None:
        """Register stable rails as first-class PAPER strategies if missing."""
        db = self.f.db
        specs = [
            ("paper_stable_triangle", "stable_triangle", "Fee-aware USDT/USDC/USD triangular dislocation (PAPER bridge from pegmaker)"),
            ("paper_stable_peg_mm", "stable_peg_mm", "Maker peg inventory around USDT peg (PAPER bridge from pegmaker)"),
        ]
        for sid, fam, hypo in specs:
            exists = db.scalar("SELECT 1 FROM strategies WHERE id=?", (sid,))
            if exists:
                continue
            try:
                from forge.strategies.genome import Genome, EntryLogic, ExitLogic, Execution, Condition as C
                g = Genome(
                    id=sid, family=fam, hypothesis=hypo,
                    entry=EntryLogic(all=[C(f="ret_3", op="lt", v=0.0)]),  # placeholder DNA; execution is pegmaker
                    exit=ExitLogic(tp_atr=1.0, sl_atr=1.0, tp_min_pct=0.001, time_stop_bars=12),
                    execution=Execution(entry="maker", maker_offset_bps=1, maker_ttl_bars=1),
                    regimes_allow=["RANGE_LOW_VOL", "RANGE_HIGH_VOL"],
                )
                self.f.reg.upsert(g, __import__("forge.strategies.registry", fromlist=["State"]).State.SHADOW,
                                  "paper lab: stable rail bridge")
                db.kv_set(f"strategy.activated.{sid}", time.time())
            except Exception as e:
                log.warning("ensure stable %s: %s", sid, e)

    def diversify_experimental(self) -> dict[str, Any]:
        """Break single-family monopoly; mass-spawn underrepresented PAPER families."""
        import numpy as np
        from forge.strategies.mutation import mutate
        from forge.strategies.seeds import seed_genomes
        from forge.strategies.registry import State

        db = self.f.db
        rows = db.query(
            "SELECT family, COUNT(*) c FROM strategies WHERE population='EXPERIMENTAL' GROUP BY 1 ORDER BY c DESC"
        ) or []
        total = sum(int(r["c"]) for r in rows) or 1
        actions: list[dict[str, Any]] = []
        # Harder monopoly trim: top family >40% and >25 → retire oldest excess down toward 25% share
        if rows:
            top_fam, top_c = rows[0]["family"], int(rows[0]["c"])
            if top_c / total > 0.40 and top_c > 25:
                target_keep = max(25, int(total * 0.25))
                n_retire = min(top_c - target_keep, 100)
                excess = db.query(
                    "SELECT id FROM strategies WHERE population='EXPERIMENTAL' AND family=? "
                    "ORDER BY created_at ASC LIMIT ?",
                    (top_fam, n_retire),
                ) or []
                for r in excess:
                    try:
                        self.f.reg.transition(r["id"], State.RETIRED,
                                              "paper lab: diversity trim (family monopoly)")
                        actions.append({"retired": r["id"], "family": top_fam})
                    except Exception:
                        pass
        # Count by base family across active pops
        base_counts: dict[str, int] = {}
        for r in db.query(
            "SELECT family, COUNT(*) c FROM strategies "
            "WHERE population IN ('EXPERIMENTAL','SHADOW','CHALLENGER') GROUP BY 1"
        ) or []:
            base = str(r["family"]).split("+")[0]
            base_counts[base] = base_counts.get(base, 0) + int(r["c"])
        TARGET_PER_FAMILY = 12  # aggressive PAPER tournament depth
        PRIORITY = [
            "microstructure", "inventory", "carry_proxy", "cross_asset", "event_driven",
            "liquidity_provision", "volatility", "rotation", "breakout", "momentum",
            "stable_triangle", "stable_peg_mm",
        ]
        under = [f for f in PRIORITY if base_counts.get(f, 0) < TARGET_PER_FAMILY]
        db.kv_set("lab.spawn_priority_families", {"ts": time.time(), "families": under[:8], "target": TARGET_PER_FAMILY})
        seeds_by_fam: dict[str, list] = {}
        for g in seed_genomes():
            seeds_by_fam.setdefault(g.family.split("+")[0], []).append(g)
        rng = np.random.default_rng(int(time.time()) % (2**31))
        exp_n = int(db.scalar("SELECT COUNT(*) FROM strategies WHERE population='EXPERIMENTAL'") or 0)
        for fam in under:
            parents = seeds_by_fam.get(fam) or []
            if not parents:
                continue
            need = TARGET_PER_FAMILY - base_counts.get(fam, 0)
            spawned = 0
            for i in range(max(0, need)):
                if exp_n >= PAPER_MAX_EXPERIMENTAL:
                    break
                parent = parents[i % len(parents)]
                try:
                    # Ensure seed parent exists once
                    if self.f.reg.state(parent.id) is None:
                        self.f.reg.upsert(parent, State.EXPERIMENTAL, "paper lab: seed underrepresented family")
                        actions.append({"seeded": parent.id, "family": parent.family})
                        exp_n += 1
                        spawned += 1
                        base_counts[fam] = base_counts.get(fam, 0) + 1
                        continue
                    child, why = mutate(parent, rng, ds=None, scale=0.25)
                    # Keep family tag clean (no accidental crossover mash)
                    child = child.model_copy(update={"family": fam, "origin": "paper_lab_tournament"})
                    self.f.reg.upsert(child, State.EXPERIMENTAL,
                                      f"paper lab: tournament spawn {fam} ({why.get('operator')})")
                    actions.append({"spawned": child.id, "family": fam, "op": why.get("operator")})
                    exp_n += 1
                    spawned += 1
                    base_counts[fam] = base_counts.get(fam, 0) + 1
                except Exception as e:
                    log.debug("spawn %s: %s", fam, e)
            if spawned:
                log.info("paper_lab spawned %d for family %s", spawned, fam)
        # Raise paper arena caps
        try:
            self.f.arena.policy.max_shadow = PAPER_MAX_SHADOW
            self.f.arena.policy.max_experimental = PAPER_MAX_EXPERIMENTAL
        except Exception:
            pass
        rows = db.query(
            "SELECT family, COUNT(*) c FROM strategies WHERE population='EXPERIMENTAL' GROUP BY 1 ORDER BY c DESC"
        ) or []
        return {"actions": actions[:120], "families": rows, "underrepresented": under}

    def bridge_stable_shadow_to_paper(self) -> int:
        """Attribute recent profitable/finished shadow stable RTs onto paper evidence ledger (kv + optional positions meta)."""
        db = self.f.db
        now = time.time()
        last = float((db.kv_get("lab.stable_bridge") or {}).get("last_ts") or (now - 3600))
        rows = db.query(
            "SELECT ts, rail, symbol, pnl_usd, fee_usd, qty, entry, exit, hold_s FROM shadow_trades "
            "WHERE ts > ? AND rail IN ('coinbase.stable_triangle','coinbase.stable_peg_mm') ORDER BY ts ASC LIMIT 200",
            (last,),
        ) or []
        bridged = 0
        book = db.kv_get("lab.paper_stable_pnl") or {"net": 0.0, "n": 0, "by_rail": {}}
        for r in rows:
            rail = r["rail"]
            sid = "paper_stable_triangle" if "triangle" in rail else "paper_stable_peg_mm"
            pnl = float(r.get("pnl_usd") or 0)
            fee = float(r.get("fee_usd") or 0)
            book["net"] = float(book.get("net") or 0) + pnl
            book["n"] = int(book.get("n") or 0) + 1
            br = book.setdefault("by_rail", {}).setdefault(rail, {"net": 0.0, "n": 0})
            br["net"] += pnl
            br["n"] += 1
            # Append to lab trade log (append-only list capped)
            bridged += 1
            last = max(last, float(r["ts"]))
        book["ts"] = now
        db.kv_set("lab.paper_stable_pnl", book)
        db.kv_set("lab.stable_bridge", {"last_ts": last, "bridged": bridged, "ts": now})
        # Also write a compact episode into research_notes if available
        if bridged:
            try:
                db.execute(
                    "INSERT INTO research_notes (id, ts, author, kind, title, body) VALUES (?,?,?,?,?,?)",
                    (f"note_stable_{int(now)}", str(now), "paper_lab", "paper_stable_bridge",
                     "stable shadow→paper bridge", json.dumps({"bridged": bridged, "book": book}, default=str)[:1900]),
                )
            except Exception:
                pass
        return bridged

    def promote_paper_probes(self) -> list[dict[str, Any]]:
        """Aggressively admit fee-survivable near-misses into SHADOW for paper forward testing."""
        db = self.f.db
        near = db.kv_get("evolution.near_miss") or []
        out = []
        from forge.strategies.registry import State
        shadow_n = int(db.scalar("SELECT COUNT(*) FROM strategies WHERE population='SHADOW'") or 0)
        for item in near[:20]:
            if shadow_n >= PAPER_MAX_SHADOW:
                break
            sid = item.get("id")
            if not sid:
                continue
            st = self.f.reg.state(sid)
            if st != State.EXPERIMENTAL:
                continue
            # Only promote if sealed/holdout suggests fee survival
            hold = self.f.reg.latest_metrics(sid, "holdout") or {}
            n_hold = float(hold.get("n") or item.get("n") or 0)
            if n_hold < 8:
                continue
            # Aggressive PAPER: allow probes with promising p even if sealed exam pending/failed
            p_pos = float(hold.get("p_positive") or item.get("p") or 0)
            if p_pos < 0.7 and float(hold.get("mean") or hold.get("expectancy") or 0) <= 0:
                continue
            try:
                self.f.reg.transition(sid, State.SHADOW, "paper lab: aggressive probe — fee-aware near-miss → SHADOW")
                db.kv_set(f"strategy.activated.{sid}", time.time())
                shadow_n += 1
                out.append({"promoted": sid, "family": item.get("family")})
            except Exception as e:
                log.debug("promote %s: %s", sid, e)
        return out



    def promote_diversity_to_shadow(self) -> list[dict[str, Any]]:
        """PAPER tournament: lift underrepresented EXPERIMENTAL families into SHADOW for live-forward fee tests."""
        from forge.strategies.registry import State
        db = self.f.db
        shadow_rows = db.query(
            "SELECT family, COUNT(*) c FROM strategies WHERE population='SHADOW' GROUP BY 1"
        ) or []
        shadow_by = {}
        for r in shadow_rows:
            shadow_by[str(r["family"]).split("+")[0]] = int(r["c"])
        shadow_n = sum(shadow_by.values())
        want = [
            "microstructure", "inventory", "carry_proxy", "cross_asset", "event_driven",
            "liquidity_provision", "volatility", "rotation", "momentum", "mean_reversion",
            "stable_triangle", "stable_peg_mm",
        ]
        out = []
        PER_FAMILY = 3
        for fam in want:
            if shadow_n >= PAPER_MAX_SHADOW:
                break
            have = shadow_by.get(fam, 0)
            if have >= PER_FAMILY:
                continue
            need = PER_FAMILY - have
            # Prefer newest experimental of this family
            cands = db.query(
                "SELECT id, family FROM strategies WHERE population='EXPERIMENTAL' AND "
                "(family = ? OR family LIKE ?) ORDER BY created_at DESC LIMIT ?",
                (fam, fam + "+%", need * 3),
            ) or []
            for r in cands:
                if shadow_n >= PAPER_MAX_SHADOW or need <= 0:
                    break
                sid = r["id"]
                # Skip known drains
                drain = db.query_one(
                    "SELECT COUNT(*) n, SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)) net "
                    "FROM positions WHERE book='paper' AND status='CLOSED' AND strategy_id=?",
                    (sid,),
                )
                if drain and int(drain["n"] or 0) >= 5 and float(drain["net"] or 0) < 0:
                    continue
                try:
                    self.f.reg.transition(sid, State.SHADOW,
                                          f"paper lab: diversity SHADOW probe ({fam}) — fee-aware forward test")
                    db.kv_set(f"strategy.activated.{sid}", time.time())
                    out.append({"promoted_diversity": sid, "family": fam})
                    shadow_n += 1
                    need -= 1
                    shadow_by[fam] = shadow_by.get(fam, 0) + 1
                except Exception as e:
                    log.debug("div promote %s: %s", sid, e)
        return out

    def kill_confirmed_drains(self) -> list[dict[str, Any]]:
        """Hibernate PAPER strategies with sequential losing closes (n>=5, net<0, wr=0)."""
        from forge.strategies.registry import State
        db = self.f.db
        rows = db.query(
            "SELECT strategy_id, COUNT(*) n, "
            "SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)) net, "
            "SUM(CASE WHEN CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL) > 0 THEN 1 ELSE 0 END) wins "
            "FROM positions WHERE book='paper' AND status='CLOSED' GROUP BY strategy_id"
        ) or []
        out = []
        for r in rows:
            n, net, wins = int(r["n"] or 0), float(r["net"] or 0), int(r["wins"] or 0)
            if n < 5 or net >= 0 or wins > 0:
                continue
            sid = r["strategy_id"]
            st = self.f.reg.state(sid)
            if st in (State.EXPERIMENTAL, State.SHADOW, State.CHALLENGER):
                try:
                    self.f.reg.transition(sid, State.HIBERNATING,
                                          f"paper lab: confirmed drain n={n} net={net:.3f} wr=0")
                    out.append({"hibernated": sid, "n": n, "net": round(net, 4)})
                except Exception:
                    pass
        return out


    def reap_dead_positions(self) -> list[dict[str, Any]]:
        """Close PAPER positions whose strategy is RETIRED/HIBERNATING so capital recirculates."""
        db = self.f.db
        rows = db.query(
            "SELECT p.id, p.symbol, p.strategy_id, s.population FROM positions p "
            "LEFT JOIN strategies s ON s.id=p.strategy_id "
            "WHERE p.book='paper' AND p.status!='CLOSED' "
            "AND (s.population IN ('RETIRED','HIBERNATING','QUARANTINED') OR s.id IS NULL) LIMIT 20"
        ) or []
        out = []
        for r in rows:
            try:
                # Prefer gateway flatten if available
                gw = getattr(self.f, "gateway", None)
                if gw and hasattr(gw, "close_position"):
                    import asyncio
                    # sync path: mark for exit via kv flag consumed by exec loop
                    db.kv_set(f"position.force_exit.{r['id']}", {"ts": time.time(), "reason": "reap_dead", "population": r["population"]})
                else:
                    db.kv_set(f"position.force_exit.{r['id']}", {"ts": time.time(), "reason": "reap_dead", "population": r["population"]})
                out.append({"force_exit": r["id"], "symbol": r["symbol"], "strategy_id": r["strategy_id"]})
            except Exception as e:
                log.debug("reap %s: %s", r.get("id"), e)
        return out

    def tick(self) -> dict[str, Any]:
        self.ensure_stable_strategies()
        div = self.diversify_experimental()
        bridged = self.bridge_stable_shadow_to_paper()
        promoted = self.promote_paper_probes()
        promoted += self.promote_diversity_to_shadow()
        killed = self.kill_confirmed_drains()
        reaped = self.reap_dead_positions()
        # Signal runtime to allow more concurrent paper positions
        self.f.db.kv_set("lab.paper_aggression", {
            "ts": time.time(),
            "max_concurrent_positions": PAPER_MAX_CONCURRENT_POS,
            "max_shadow": PAPER_MAX_SHADOW,
            "probe_exposure_floor": 0.40,
            "note": "PAPER only — learn fast, fee-aware, no LIVE",
            "under_target_intensifies": True,
            "diagnostic_usd_per_h": 0.50,
            "primary_target_usd_per_h": 1.00,

        })
        rep = {
            "ts": time.time(),
            "diversity_actions": len(div.get("actions") or []),
            "stable_bridged": bridged,
            "promoted": promoted,
            "hibernated_drains": killed,
            "reaped": reaped,
            "stable_pnl": self.f.db.kv_get("lab.paper_stable_pnl"),
            "families": div.get("families"),
        }
        self.f.db.kv_set("lab.paper_lab", rep)
        return rep

    async def run(self) -> None:
        if not self.f.db.kv_get("lab.paper_aggression"):
            self.f.db.kv_set("lab.paper_aggression", {
                "probe_exposure_floor": 0.40,
                "max_concurrent_positions": 14,
                "promote_near_miss": True,
                "stable_bridge": True,
                "diversity_min_families": 8,
                "kill_after_n_losing_days": 5,
            })
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("paper_lab")
            try:
                await asyncio.to_thread(self.tick)
            except Exception as e:
                log.warning("paper_lab: %s", e, exc_info=True)
            await asyncio.sleep(90)
