"""Evolution Arena — the Improvement Loop's lifecycle manager (OP-007, OP-004 thresholds, OP-009 §6).

    EXPERIMENTAL ──gate(holdout, alpha, robustness, DSR)──▶ SHADOW ──live-forward evidence──▶ CHALLENGER
        ▲                                                   │                                  │ combined P(edge>0) ≥ 0.90
        │ repair/mutate                                     ▼                                  ▼
    HIBERNATING ◀── regime absent ── PRODUCTION ◀────────────────────────────────────────── (promotion)
        │                              │ thresholds breached (posterior / drawdown / loss streak)
        └──── resurrection ◀─ RETIRED ◀┘  (never deleted; lineage + failure reasons retained)

Live-forward evidence = re-simulation of the genome over bars recorded *after* its activation (identical code to
research) plus real paper/live position outcomes. Backtest evidence is discounted by the learned backtest→live
haircut. Incumbents are never interrupted while their edge remains valid; challengers must beat them.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from forge.core.ids import new_id
from forge.persistence.db import Database, dumps
from forge.research.backtest import CostModel, metrics, simulate
from forge.research.stats import edge_posterior
from forge.strategies.genome import Genome
from forge.strategies.registry import ACTIVE_OBSERVING, State, StrategyRegistry
from forge.strategies.seeds import seed_genomes

log = logging.getLogger("forge.arena")


@dataclass
class StrategyEvidence:
    p_win: float
    avg_win: float
    avg_loss: float
    avg_hold_h: float
    n: int
    p_edge: float
    source: str


@dataclass
class ArenaPolicy:
    p_promote: float = 0.90               # OP-004 90% rule
    challenger_min_forward: int = 3       # shadow → challenger after ≥3 forward trades not contradicting history
    production_min_live: int = 8          # challenger → production needs real (paper/live) evidence
    demote_p_edge: float = 0.35           # incumbents demoted if posterior collapses
    demote_drawdown: float = 0.20         # strategy-level drawdown on its own trades
    loss_streak: int = 5
    backtest_weight: float = 0.5          # discount for historical evidence (learned haircut)
    max_shadow: int = 40
    max_experimental: int = 200
    hibernate_after_h: float = 72.0       # regime absent this long → hibernate


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Arena:
    def __init__(self, db: Database, registry: StrategyRegistry, policy: ArenaPolicy | None = None) -> None:
        self.db, self.reg = db, registry
        self.policy = policy or ArenaPolicy()

    # ---------------------------------------------------------------- bootstrap
    def bootstrap(self) -> int:
        n = 0
        for g in seed_genomes():
            if self.reg.state(g.id) is None:
                self.reg.upsert(g, State.EXPERIMENTAL, "seed population")
                n += 1
        return n

    # ---------------------------------------------------------------- research → shadow
    def admit(self, g: Genome, rationale: dict[str, Any], passed: bool, evidence: dict[str, Any],
              source: str = "evolution") -> str:
        """Insert a researched genome. Gate-passing ones enter SHADOW; others become EXPERIMENTAL stepping stones."""
        dup = self.reg.exists_dna(g.dna_hash())
        if dup:
            return dup
        if passed:
            same = self.db.scalar("SELECT COUNT(*) FROM strategies WHERE population IN ('SHADOW','CHALLENGER','PRODUCTION') "
                                  "AND family = ?", (g.family,)) or 0
            if same >= 6:          # diversity pressure: one family may not monopolize validated capital slots
                passed = False
                rationale = {**rationale, "diversity": f"family {g.family} already has {same} validated strategies"}
        state = State.SHADOW if passed else State.EXPERIMENTAL
        g = g.model_copy(update={"origin": g.origin})
        self.reg.upsert(g, state, "passed promotion gate" if passed else "archive elite (stepping stone)",
                        fitness=evidence.get("fitness"))
        self.reg.record_metrics(g.id, "holdout", evidence.get("holdout", {}))
        self.reg.record_metrics(g.id, "selection", evidence.get("selection", {}))
        for parent in g.parents:
            if self.reg.state(parent) is not None:
                edge = "CROSSOVER_OF" if rationale.get("operator") == "crossover" else "MUTATED_FROM"
                self.reg.add_lineage(parent, g.id, edge, rationale)
                self.reg.record_mutation(new_id("mut"), parent, g.id, str(rationale.get("operator")), source, rationale)
        if passed:
            self.db.kv_set(f"strategy.activated.{g.id}", time.time())
            self.reg.resolve_mutation(g.id, {"gate": "passed"}, True)
        self._trim()
        return g.id

    def _trim(self) -> None:
        """Population cap without killing newcomers (Hermes finding 2026-10-07: stale fitness from older datasets retired
        every fresh champion within seconds). Young strategies (< 12 h) are protected up to half the cap; the rest compete
        on fitness decayed by age (fitness values from different data windows are not comparable)."""
        now = datetime.now(UTC)
        for st, cap in ((State.SHADOW, self.policy.max_shadow), (State.EXPERIMENTAL, self.policy.max_experimental)):
            rows = self.db.query("SELECT id, fitness, created_at FROM strategies WHERE population = ?", (st.value,))
            if len(rows) <= cap:
                continue

            def age_d(r: dict[str, Any]) -> float:
                try:
                    return (now - datetime.fromisoformat(r["created_at"])).total_seconds() / 86400
                except (TypeError, ValueError):
                    return 99.0
            young = sorted((r for r in rows if age_d(r) < 0.5), key=lambda r: -(r["fitness"] if r["fitness"] is not None else -99))
            keep = {r["id"] for r in young[: cap // 2]}
            rest = sorted((r for r in rows if r["id"] not in keep),
                          key=lambda r: -((r["fitness"] if r["fitness"] is not None else -99) - 0.05 * age_d(r)))
            keep |= {r["id"] for r in rest[: cap - len(keep)]}
            for r in rows:
                if r["id"] not in keep:
                    self.reg.transition(r["id"], State.RETIRED, f"population cap ({st.value} > {cap}); lineage retained")

    # ---------------------------------------------------------------- evidence
    def forward_trades(self, g: Genome, bar_state: dict[str, Any], cost: CostModel) -> list[Any]:
        """Re-simulate the genome over bars recorded after activation (live-forward / shadow evidence)."""
        t0 = float(self.db.kv_get(f"strategy.activated.{g.id}", 0) or 0)
        trades = []
        for sym, st in bar_state.items():
            if not st.features or len(st.series) < 300:
                continue
            arr = {k: v[-len(st.features["atr_14"]):] for k, v in st.series.arrays().items()}
            ts = arr["ts"]
            start = int(np.searchsorted(ts, t0)) if t0 else len(ts)
            if start >= len(ts) - 1:
                continue
            res = simulate(g, sym, arr, st.features, st.probs, cost, start=max(start - 1, 0))
            trades += [t for t in res.trades if t.entry_ts >= t0]
        return trades

    def real_outcomes(self, sid: str) -> list[float]:
        rows = self.db.query("SELECT realized_pnl_usd, fees_usd, cost_usd FROM positions WHERE strategy_id = ? "
                             "AND status = 'CLOSED' AND CAST(cost_usd AS REAL) > 0", (sid,))
        return [(float(r["realized_pnl_usd"]) - float(r["fees_usd"])) / float(r["cost_usd"]) for r in rows]

    def evidence(self, sid: str) -> StrategyEvidence | None:
        """Combined evidence: real outcomes (full weight) + forward (shadow) + discounted holdout."""
        real = self.real_outcomes(sid)
        fwd = self.reg.latest_metrics(sid, "forward") or {}
        hold = self.reg.latest_metrics(sid, "holdout") or {}
        parts: list[tuple[dict[str, Any], float]] = [(hold, self.policy.backtest_weight), (fwd, 0.8)]
        n_eff, wsum = 0.0, 0.0
        pw = aw = al = hh = 0.0
        for m, w in parts:
            n = float(m.get("n", 0) or 0)
            if n <= 0:
                continue
            ww = n * w
            pw += m.get("win_rate", 0) * ww
            aw += m.get("avg_win", 0) * ww
            al += m.get("avg_loss", 0) * ww
            hh += m.get("avg_hold_h", 0) * ww
            n_eff += ww
            wsum += ww
        if real:
            r = np.array(real)
            ww = len(r) * 1.0
            pw += float((r > 0).mean()) * ww
            aw += float(r[r > 0].mean()) * ww if (r > 0).any() else 0.0
            al += float(r[r <= 0].mean()) * ww if (r <= 0).any() else 0.0
            n_eff += ww
            wsum += ww
        if wsum <= 0:
            return None
        p, W, L = pw / wsum, aw / wsum, al / wsum
        mean = p * W + (1 - p) * L
        std = math.sqrt(max(p * (W - mean) ** 2 + (1 - p) * (L - mean) ** 2, 1e-8))
        post = edge_posterior(np.random.default_rng(0).normal(mean, std, max(int(n_eff), 2)))
        return StrategyEvidence(p_win=p, avg_win=W, avg_loss=L, avg_hold_h=hh / wsum if wsum else 0.0,
                                n=int(n_eff), p_edge=post["p_positive"], source="combined")

    # ---------------------------------------------------------------- lifecycle review (Improvement Loop tick)
    def review(self, bar_states: dict[int, dict[str, Any]], cost: CostModel, regimes_now: dict[str, str]) -> list[dict[str, Any]]:
        """Update forward evidence; promote / demote / hibernate. Returns the list of transitions made."""
        changes: list[dict[str, Any]] = []
        present_regimes = set(regimes_now.values())
        for g, st, row in self.reg.list(ACTIVE_OBSERVING + (State.HIBERNATING,)):
            bars = bar_states.get(g.interval_s)
            if bars:
                fw = self.forward_trades(g, bars, cost)
                hours = (time.time() - float(self.db.kv_get(f"strategy.activated.{g.id}", time.time()) or time.time())) / 3600
                self.reg.record_metrics(g.id, "forward", metrics(fw, max(hours / 24, 1e-6)))
            ev = self.evidence(g.id)
            real = self.real_outcomes(g.id)
            fwd = self.reg.latest_metrics(g.id, "forward") or {}
            act = None
            if st == State.HIBERNATING:
                if not g.regimes_allow or set(g.regimes_allow) & present_regimes:
                    act = (State.SHADOW, "regime returned — resurrected to shadow")
                    self.db.kv_set(f"strategy.activated.{g.id}", time.time())
            elif st == State.SHADOW:
                if fwd.get("n", 0) >= self.policy.challenger_min_forward and fwd.get("mean_net", -1) > 0 and ev and ev.p_edge >= 0.75:
                    act = (State.CHALLENGER, f"forward n={fwd['n']} mean={fwd['mean_net']:+.2%}, combined P={ev.p_edge:.2f}")
                elif fwd.get("n", 0) >= 8 and fwd.get("mean_net", 0) < 0 and (ev is None or ev.p_edge < 0.5):
                    act = (State.EXPERIMENTAL, f"forward evidence contradicts history (n={fwd['n']}, mean={fwd['mean_net']:+.2%})")
                elif g.regimes_allow and not set(g.regimes_allow) & present_regimes and self._absent_long(g):
                    act = (State.HIBERNATING, f"allowed regimes {g.regimes_allow} absent")
            elif st == State.CHALLENGER:
                if len(real) >= self.policy.production_min_live and ev and ev.p_edge >= self.policy.p_promote:
                    act = (State.PRODUCTION, f"real n={len(real)} combined P(edge>0)={ev.p_edge:.2f} ≥ {self.policy.p_promote}")
                elif self._breached(real, ev):
                    act = (State.SHADOW, "challenger thresholds breached → back to shadow for repair")
            elif st == State.PRODUCTION:
                if self._breached(real, ev):
                    act = (State.SHADOW, "incumbent edge invalidated (posterior/drawdown/loss streak) → shadow + postmortem")
            if act:
                self.reg.transition(g.id, act[0], act[1], evidence={"evidence": ev.__dict__ if ev else None, "forward": fwd})
                changes.append({"strategy": g.id, "family": g.family, "from": st.value, "to": act[0].value, "why": act[1]})
        return changes

    def _breached(self, real: list[float], ev: StrategyEvidence | None) -> bool:
        if ev is not None and ev.n >= 10 and ev.p_edge < self.policy.demote_p_edge:
            return True
        if len(real) >= self.policy.loss_streak and all(x <= 0 for x in real[-self.policy.loss_streak:]):
            return True
        if real:
            eq = np.cumprod(1 + np.array(real))
            dd = float((eq / np.maximum.accumulate(eq) - 1).min())
            if dd <= -self.policy.demote_drawdown:
                return True
        return False

    def _absent_long(self, g: Genome) -> bool:
        k = f"strategy.regime_absent_since.{g.id}"
        since = self.db.kv_get(k)
        if since is None:
            self.db.kv_set(k, time.time())
            return False
        return (time.time() - float(since)) / 3600 >= self.policy.hibernate_after_h

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {"counts": self.reg.counts(), "active": []}
        for g, st, row in self.reg.list((State.PRODUCTION, State.CHALLENGER, State.SHADOW)):
            ev = self.evidence(g.id)
            out["active"].append({"id": g.id, "family": g.family, "state": st.value, "generation": g.generation,
                                  "fitness": row.get("fitness"), "regimes": g.regimes_allow,
                                  "evidence": ev.__dict__ if ev else None,
                                  "forward": self.reg.latest_metrics(g.id, "forward"),
                                  "allocation_usd": row.get("virtual_allocation_usd")})
        return out


def json_safe(x: Any) -> Any:
    return json.loads(dumps(x))
