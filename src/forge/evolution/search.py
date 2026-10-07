"""Quality-diversity evolutionary search (Improvement Loop core; EDGE PLAN L3/L4; OP-007).

MAP-Elites archive keyed by behavior niche (family × holding-horizon bucket × regime focus) keeps a
diverse bench of specialists — stepping stones are retained even when they are not the global best.
Each generation: select parents (fitness-proportional within niches, plus novelty), mutate/crossover,
evaluate on the SELECTION segment only, insert into the archive. The holdout is touched only by the
promotion gate. Runs locally (bounded CPU) or as a Modal burst (same code).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from forge.research.backtest import CostModel
from forge.research.evaluate import Dataset, Evaluation, evaluate, promotion_gate, robustness, sleeve_of
from forge.strategies.genome import Genome
from forge.strategies.mutation import OPERATORS, crossover, mutate


def niche(g: Genome, ev: Evaluation) -> tuple[str, str, str]:
    h = ev.metrics.get("avg_hold_h", 0.0) or 0.0
    hb = "≤4h" if h <= 4 else "≤24h" if h <= 24 else "≤72h" if h <= 72 else ">72h"
    reg = g.regimes_allow[0] if len(g.regimes_allow) == 1 else ("ANY" if not g.regimes_allow else "MULTI")
    return (g.family.split("+")[0], hb, reg)


@dataclass
class Elite:
    genome: Genome
    ev: Evaluation
    rationale: dict[str, Any]


@dataclass
class SearchResult:
    archive: dict[tuple[str, str, str], Elite]
    evaluated: int
    seconds: float
    history: list[dict[str, Any]] = field(default_factory=list)
    operator_stats: dict[str, list[int]] = field(default_factory=dict)   # op -> [attempts, improvements]

    def ranked(self) -> list[Elite]:
        return sorted(self.archive.values(), key=lambda e: e.ev.fitness, reverse=True)


def run_search(seeds: list[Genome], ds: Dataset, cost: CostModel, generations: int = 10, children_per_gen: int = 60,
               seed: int = 0, time_budget_s: float | None = None, velocity_weight: float = 1.0,
               log=print) -> SearchResult:
    rng = np.random.default_rng(seed)
    t0 = time.time()
    archive: dict[tuple[str, str, str], Elite] = {}
    op_stats: dict[str, list[int]] = {o: [0, 0] for o in (*OPERATORS, "crossover")}
    evaluated = 0

    def consider(g: Genome, rationale: dict[str, Any]) -> bool:
        nonlocal evaluated
        ev = evaluate(g, ds, cost, "selection")
        evaluated += 1
        key = niche(g, ev)
        cur = archive.get(key)
        if cur is None or ev.fitness > cur.ev.fitness:
            archive[key] = Elite(g, ev, rationale)
            return True
        return False

    for g in seeds:
        consider(g, {"operator": "seed"})
    history = []
    for gen in range(generations):
        if time_budget_s and time.time() - t0 > time_budget_s:
            break
        elites = list(archive.values())
        fit = np.array([e.ev.fitness for e in elites])
        w = np.exp((fit - fit.max()) / 0.5)
        w /= w.sum()
        # adaptive operator weights: favor operators that have produced archive improvements
        op_w = {o: (1 + s[1]) / (2 + s[0]) for o, s in op_stats.items() if o != "crossover"}
        improved = 0
        for _ in range(children_per_gen):
            if len(elites) >= 2 and rng.random() < 0.15:
                a, b = rng.choice(len(elites), size=2, replace=False, p=w)
                child, why = crossover(elites[a].genome, elites[b].genome, rng)
                op = "crossover"
            else:
                pidx = int(rng.choice(len(elites), p=w)) if rng.random() < 0.85 else int(rng.integers(len(elites)))
                child, why = mutate(elites[pidx].genome, rng, ds, weights=op_w)
                op = why["operator"]
            op_stats[op][0] += 1
            if consider(child, why):
                op_stats[op][1] += 1
                improved += 1
        best = max(archive.values(), key=lambda e: e.ev.fitness)
        history.append({"gen": gen, "archive": len(archive), "improved": improved,
                        "best_fitness": best.ev.fitness, "best_mean": best.ev.metrics["mean_net"],
                        "best_n": best.ev.metrics["n"], "evaluated": evaluated})
        log(f"gen {gen:2d}: archive={len(archive):3d} improved={improved:3d} best fit={best.ev.fitness:+.3f} "
            f"mean={best.ev.metrics['mean_net'] * 100:+.3f}% n={best.ev.metrics['n']} "
            f"P={best.ev.metrics['p_positive']:.2f} ({best.genome.family}) [{time.time() - t0:.0f}s]")
    return SearchResult(archive, evaluated, time.time() - t0, history, op_stats)


def adjudicate(res: SearchResult, ds: Dataset, cost: CostModel, top: int = 12, seed: int = 1) -> list[dict[str, Any]]:
    """Run the promotion gate (holdout + robustness + deflated Sharpe) on the best elites."""
    out = []
    rng_seed = seed
    for el in res.ranked()[:top]:
        hold = evaluate(el.genome, ds, cost, "holdout", keep_trades=True, count_trial=False)
        rob = robustness(el.genome, ds, cost, mutate, n=8, seed=rng_seed)
        ok, reasons = promotion_gate(el.ev, hold, rob, n_trials=ds.trials)
        out.append({"genome": el.genome, "selection": el.ev.metrics, "fold_positive": el.ev.fold_positive,
                    "holdout": hold.metrics, "robustness": rob, "passed": ok, "reasons": reasons,
                    "sleeve": sleeve_of(reasons),
                    "rationale": el.rationale})
        rng_seed += 1
    return out
