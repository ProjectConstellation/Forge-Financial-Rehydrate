"""Research worker entry points (run in a low-priority subprocess locally, or inside a Modal container).

Pure function of (data, parents, fees, budget) → serializable results, so local and Modal execution are identical.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

HOLDOUT_FRAC = 0.20     # validation window (P0.4: selection 65% / validation 20% / sealed 15%)
SEALED_FRAC = 0.15      # one-time final-exam window; results go to the Research Trial Ledger only


def _limit_threads() -> None:
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(k, "1")


def _clean(m: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in m.items():
        if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
            out[k] = None if v != v else (1e9 if v > 0 else -1e9)
        else:
            out[k] = v
    return out


def search_on_raw(raw: dict[str, dict[str, Any]], interval: int, parents: list[dict[str, Any]], fees: dict[str, float],
                  budget_s: float, seed: int, generations: int = 60, children: int = 60, top: int = 12,
                  must_eval: list[dict[str, Any]] | None = None, prior_trials: int = 0,
                  sealed_seen: dict[str, bool] | None = None, sealed_exams_prior: int = 0) -> dict[str, Any]:
    _limit_threads()
    import time

    import numpy as np

    from forge.evolution.search import adjudicate, run_search
    from forge.research.backtest import CostModel
    from forge.research.evaluate import Dataset
    from forge.strategies.genome import Genome
    from forge.strategies.seeds import seed_genomes

    t0 = time.time()
    raw = {s: {k: np.asarray(v, dtype=float) for k, v in b.items()} for s, b in raw.items()}
    ds = Dataset.build(raw, interval, holdout_frac=HOLDOUT_FRAC, n_folds=4, sealed_frac=SEALED_FRAC)
    ds.trials = int(prior_trials)          # cumulative hypotheses already tested on this data → stricter deflated Sharpe
    if len(ds.symbols) < 5:
        return {"candidates": [], "evaluated": 0, "seconds": 0.0, "note": "insufficient data", "where": "local"}
    cost = CostModel(maker_fee=fees.get("maker", 0.005), taker_fee=fees.get("taker", 0.009))
    llm = [Genome.model_validate(p).model_copy(update={"interval_s": interval}) for p in (must_eval or [])]
    seeds = [Genome.model_validate(p) for p in parents] or seed_genomes()
    seeds = llm + seeds
    if len(seeds) < 6:
        extra = [g for g in seed_genomes() if g.id not in {s.id for s in seeds}]
        seeds += extra
    seeds = [g.model_copy(update={"interval_s": interval}) for g in seeds]
    res = run_search(seeds, ds, cost, generations=generations, children_per_gen=children, seed=seed,
                     time_budget_s=budget_s * 0.8, log=lambda *_: None)
    seen = dict(sealed_seen or {})
    n_ex0 = int(sealed_exams_prior)
    adj = adjudicate(res, ds, cost, top=top, seed=seed, sealed_seen=seen, sealed_exams_prior=n_ex0)
    done = {r["genome"].id for r in adj}
    if llm:   # LLM-designed genomes are always adjudicated explicitly (their predictions get scored)
        from forge.evolution.search import Elite, SearchResult
        from forge.research.evaluate import evaluate
        extra = {}
        for g in llm:
            if g.id in done:
                continue
            ev = evaluate(g, ds, cost, "selection")
            extra[("llm", g.id, "")] = Elite(g, ev, {"operator": "llm"})
        if extra:
            n_ex = n_ex0 + sum(1 for r in adj if r.get("sealed") and not r["sealed"].get("reused"))
            adj += adjudicate(SearchResult(extra, len(extra), 0.0), ds, cost, top=len(extra), seed=seed + 7,
                              sealed_seen=seen, sealed_exams_prior=n_ex)
    cands = []
    for r in adj:
        g = r["genome"]
        sel = {k: v for k, v in r["selection"].items() if k not in ("by_regime",)}
        hold = {k: v for k, v in r["holdout"].items() if k not in ("by_regime",)}
        cands.append({"genome": g.model_dump(mode="json"), "passed": r["passed"], "reasons": r["reasons"],
                      "sleeve": r.get("sleeve"),
                      "selection": _clean(sel), "holdout": _clean(hold), "robustness": r["robustness"],
                      "sealed": _clean(r["sealed"]) if r.get("sealed") else None,
                      "rationale": r["rationale"], "fitness": float(res.archive and max(
                          (e.ev.fitness for e in res.archive.values() if e.genome.id == g.id), default=0.0))})
    best = max((e.ev.fitness for e in res.archive.values()), default=0.0)
    return {"candidates": cands, "evaluated": res.evaluated, "seconds": time.time() - t0, "trials": ds.trials,
            "sealed_start_ts": ds.sealed_start_ts(), "dataset": {"symbols": len(ds.symbols), "selection_days": ds.days("selection"),
                                                                 "holdout_days": ds.days("holdout"), "sealed_days": ds.days("sealed")},
            "best_fitness": best, "operator_stats": res.operator_stats, "where": "local"}


def local_search(market_dir: str, interval: int, parents: list[dict[str, Any]], fees: dict[str, float],
                 budget_s: float, seed: int, must_eval: list[dict[str, Any]] | None = None, prior_trials: int = 0,
                 sealed_seen: dict[str, bool] | None = None, sealed_exams_prior: int = 0) -> dict[str, Any]:
    _limit_threads()
    try:
        os.nice(10)
    except OSError:
        pass
    from forge.market_data.history import CandleStore

    store = CandleStore(Path(market_dir))
    raw = {s: store.load(s, interval) for s in store.symbols(interval)}
    raw = {s: b for s, b in raw.items() if b is not None}
    return search_on_raw(raw, interval, parents, fees, budget_s, seed, must_eval=must_eval, prior_trials=prior_trials,
                         sealed_seen=sealed_seen, sealed_exams_prior=sealed_exams_prior)
