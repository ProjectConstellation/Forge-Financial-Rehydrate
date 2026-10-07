"""Evaluation harness: datasets with selection/holdout discipline, fold consistency, robustness.

DOSSIER §15, §30 / DIRECTIVE §18, §36:
- The newest `holdout_frac` of history is untouched during search (holdout discipline).
- Selection fitness requires consistency across chronological folds (walk-forward style).
- Parameter-perturbation robustness: neighbors must also work (prefer plateaus over spikes).
- Every result records its cost ruler, so verdicts can be re-adjudicated when costs change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from forge.features.engine import add_cross_asset, compute_features
from forge.market_data.bars import resample
from forge.regime.engine import regime_labels, regime_probs
from forge.research.backtest import CostModel, Trade, metrics, simulate
from forge.research.stats import deflated_sharpe
from forge.strategies.genome import Genome


@dataclass
class SymbolData:
    symbol: str
    bars: dict[str, np.ndarray]
    f: dict[str, np.ndarray]
    probs: dict[str, np.ndarray]
    labels: np.ndarray

    @property
    def n(self) -> int:
        return len(self.bars["ts"])


@dataclass
class Dataset:
    interval_s: int
    symbols: dict[str, SymbolData]
    holdout_frac: float = 0.3
    n_folds: int = 4
    trials: int = 0                      # hypotheses evaluated on this dataset (multiple-testing counter)
    feature_quantiles: dict[str, np.ndarray] = field(default_factory=dict)
    index_ts: np.ndarray = field(default_factory=lambda: np.array([]))
    index_log: np.ndarray = field(default_factory=lambda: np.array([]))   # equal-weighted universe log-index

    def market_return(self, t0: float, t1: float) -> float:
        """Equal-weighted universe return between two timestamps (drift benchmark)."""
        if len(self.index_ts) == 0:
            return 0.0
        i0 = min(np.searchsorted(self.index_ts, t0), len(self.index_ts) - 1)
        i1 = min(np.searchsorted(self.index_ts, t1), len(self.index_ts) - 1)
        return float(np.expm1(self.index_log[i1] - self.index_log[i0]))

    @classmethod
    def build(cls, raw: dict[str, dict[str, np.ndarray]], interval_s: int, src_interval_s: int | None = None,
              holdout_frac: float = 0.3, n_folds: int = 4, benchmark: str = "BTC-USD") -> Dataset:
        if src_interval_s and src_interval_s != interval_s:
            raw = {s: resample(b, src_interval_s, interval_s) for s, b in raw.items()}
        bench = raw.get(benchmark)
        out: dict[str, SymbolData] = {}
        for s, b in raw.items():
            if len(b["ts"]) < 300:
                continue
            f = compute_features(b, interval_s)
            add_cross_asset(f, b, bench if s != benchmark else None)
            p = regime_probs(f)
            out[s] = SymbolData(s, b, f, p, regime_labels(p))
        ds = cls(interval_s=interval_s, symbols=out, holdout_frac=holdout_frac, n_folds=n_folds)
        ds._quantiles()
        ds._index()
        return ds

    def _index(self) -> None:
        all_ts = np.unique(np.concatenate([sd.bars["ts"] for sd in self.symbols.values()]))
        acc = np.zeros(len(all_ts))
        cnt = np.zeros(len(all_ts))
        for sd in self.symbols.values():
            lc = np.log(np.asarray(sd.bars["close"], dtype=float))
            r = np.diff(lc, prepend=lc[0])
            idx = np.searchsorted(all_ts, sd.bars["ts"])
            acc[idx] += np.clip(r, -0.5, 0.5)
            cnt[idx] += 1
        self.index_ts = all_ts
        self.index_log = np.cumsum(np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0))

    def _quantiles(self) -> None:
        qs = np.linspace(0.02, 0.98, 25)
        acc: dict[str, list[np.ndarray]] = {}
        for sd in self.symbols.values():
            cut = int(sd.n * (1 - self.holdout_frac))
            for k, v in sd.f.items():
                vv = v[:cut]
                acc.setdefault(k, []).append(vv[np.isfinite(vv)])
        for k, parts in acc.items():
            allv = np.concatenate(parts) if parts else np.array([])
            self.feature_quantiles[k] = np.quantile(allv, qs) if len(allv) > 50 else np.array([])

    def split(self, sd: SymbolData, segment: str) -> tuple[int, int]:
        cut = int(sd.n * (1 - self.holdout_frac))
        if segment == "selection":
            return 0, cut
        if segment == "holdout":
            return cut, sd.n
        return 0, sd.n

    def days(self, segment: str) -> float:
        sd = next(iter(self.symbols.values()))
        a, b = self.split(sd, segment)
        return (b - a) * self.interval_s / 86400


@dataclass
class Evaluation:
    genome_id: str
    segment: str
    metrics: dict
    fold_means: list[float]
    fold_positive: float
    fitness: float
    trades: list[Trade]
    cost_ruler: dict


def evaluate(g: Genome, ds: Dataset, cost: CostModel, segment: str = "selection", keep_trades: bool = False,
             count_trial: bool = True) -> Evaluation:
    if count_trial:
        ds.trials += 1
    trades: list[Trade] = []
    for sym, sd in ds.symbols.items():
        if g.universe.symbols != "dynamic" and sym not in g.universe.symbols:
            continue
        a, b = ds.split(sd, segment)
        trades += simulate(g, sym, sd.bars, sd.f, sd.probs, cost, start=a, end=b, labels=sd.labels).trades
    days = ds.days(segment)
    m = metrics(trades, days)
    # alpha vs market drift (equal-weighted universe over the identical holding window)
    if trades:
        alpha = np.array([t.net - ds.market_return(t.entry_ts, t.exit_ts) for t in trades])
        from forge.research.stats import edge_posterior
        ap = edge_posterior(alpha)
        m["alpha_mean"], m["alpha_p_positive"] = float(alpha.mean()), ap["p_positive"]
        m["drift_mean"] = float(np.mean([ds.market_return(t.entry_ts, t.exit_ts) for t in trades]))
    else:
        m["alpha_mean"], m["alpha_p_positive"], m["drift_mean"] = 0.0, 0.0, 0.0
    # chronological folds (walk-forward consistency)
    fold_means: list[float] = []
    if trades:
        ts = np.array([t.entry_ts for t in trades])
        edges = np.quantile(ts, np.linspace(0, 1, ds.n_folds + 1))
        for i in range(ds.n_folds):
            sel = (ts >= edges[i]) & (ts <= edges[i + 1] if i == ds.n_folds - 1 else ts < edges[i + 1])
            rr = np.array([t.net for t, s in zip(trades, sel, strict=True) if s])
            fold_means.append(float(rr.mean()) if len(rr) else 0.0)
    fold_pos = float(np.mean([x > 0 for x in fold_means])) if fold_means else 0.0
    fit = fitness(m, fold_pos, g.complexity())
    return Evaluation(g.id, segment, m, fold_means, fold_pos, fit, trades if keep_trades else [], cost.ruler())


def fitness(m: dict, fold_pos: float, complexity: int, min_trades: int = 40, velocity_weight: float = 3.0,
            hurdle_per_day: float = 0.0096) -> float:
    """Multi-objective selection score (DOSSIER §14.5 + OP-008 velocity):
    per-trade growth × evidence × consistency + capital velocity vs hurdle − penalties."""
    n = m["n"]
    if n < min_trades:
        return -1.0 + n / (10 * min_trades)          # keep a gradient toward more evidence
    lb = m["lb90"]
    growth = m["log_growth"] / max(1.0, n) * 100     # mean log growth per trade, in %
    dd_pen = max(0.0, -m["max_dd"] - 0.25) * 2
    cx_pen = 0.02 * max(0, complexity - 4)
    alpha_term = 20 * m.get("alpha_mean", 0.0)
    vel = float(np.tanh((m.get("log_per_capital_day", 0.0) - hurdle_per_day) / max(hurdle_per_day, 1e-6)))
    return float(growth + 50 * lb + 0.5 * (fold_pos - 0.5) + 0.3 * min(1.0, m["p_positive"])
                 + 0.4 * velocity_weight * vel + alpha_term - dd_pen - cx_pen)


def robustness(g: Genome, ds: Dataset, cost: CostModel, mutate_fn, n: int = 8, seed: int = 0) -> dict:
    """Parameter-perturbation test: share of jittered neighbors with positive mean net (selection)."""
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n):
        child, _ = mutate_fn(g, rng, ds, operators=("jitter",), scale=0.12)
        ev = evaluate(child, ds, cost, "selection", count_trial=False)
        means.append(ev.metrics["mean_net"] if ev.metrics["n"] >= 10 else -1.0)
    arr = np.array(means)
    return {"neighbors": n, "positive_share": float((arr > 0).mean()), "median_mean_net": float(np.median(arr))}


def promotion_gate(ev_sel: Evaluation, ev_hold: Evaluation, rob: dict, n_trials: int,
                   p_required: float = 0.90, min_trades: int = 30,
                   alpha_required: float = 0.60) -> tuple[bool, list[str]]:
    """OP-004 90% rule + anti-self-deception checks. Returns (passed, reasons)."""
    reasons = []
    mh = ev_hold.metrics
    if mh["n"] < min_trades:
        reasons.append(f"holdout trades {mh['n']} < {min_trades}")
    if mh["p_positive"] < p_required:
        reasons.append(f"holdout P(edge>0)={mh['p_positive']:.3f} < {p_required}")
    if ev_sel.metrics["mean_net"] <= 0:
        reasons.append("selection mean net ≤ 0")
    if mh.get("alpha_p_positive", 0.0) < alpha_required:
        reasons.append(f"holdout alpha vs market drift P={mh.get('alpha_p_positive', 0.0):.2f} < {alpha_required} "
                       f"(net {mh['mean_net']:+.2%} vs drift {mh.get('drift_mean', 0.0):+.2%})")
    if ev_sel.fold_positive < 0.5:
        reasons.append(f"fold consistency {ev_sel.fold_positive:.2f} < 0.5")
    if rob.get("positive_share", 0) < 0.5:
        reasons.append(f"robustness {rob.get('positive_share', 0):.2f} < 0.5")
    rr = np.array([t.net for t in ev_hold.trades]) if ev_hold.trades else np.array([])
    if len(rr) >= 5:
        dsr = deflated_sharpe(rr, max(1, n_trials))
        if dsr < 0.5:
            reasons.append(f"deflated Sharpe {dsr:.2f} < 0.5 after {n_trials} trials")
    return (not reasons), reasons


def sleeve_of(reasons: list[str]) -> str | None:
    """'alpha' if fully passed; 'beta' if the ONLY failure is alpha-vs-drift (profitable trend/beta capture that must be
    regime-gated); None otherwise."""
    if not reasons:
        return "alpha"
    if all(r.startswith("holdout alpha vs market drift") for r in reasons):
        return "beta"
    return None
