"""Mutation & crossover operators (DOSSIER §14, §29; DIRECTIVE §16).

Every operator returns (child, rationale). Thresholds for new conditions are drawn from the
dataset's *selection-period* feature quantiles (never the holdout) so mutations stay in realistic
ranges. The Mutation Planner chooses operators from diagnosed weaknesses; DeepSeek can supply
structured mutations through the same validation path.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from forge.core.ids import new_id
from forge.regime.engine import REGIMES
from forge.strategies.genome import ALLOWED_FEATURES, Condition, EntryLogic, Genome

OPERATORS = ("jitter", "jitter_exit", "add_condition", "remove_condition", "swap_feature",
             "regime_specialize", "regime_veto", "execution", "horizon")

# features that are informative for entry gating (skip pure-calendar ones by default)
ENTRY_POOL = sorted(ALLOWED_FEATURES - {"hour_sin", "hour_cos"})


def _child(g: Genome, rationale: dict[str, Any], **changes: Any) -> tuple[Genome, dict[str, Any]]:
    data = g.model_dump()
    data.update(changes)
    data["id"] = new_id("stg")
    data["parents"] = [g.id]
    data["generation"] = g.generation + 1
    data["origin"] = "mutation"
    child = Genome.model_validate(data)
    rationale = {"parent": g.id, **rationale}
    return child, rationale


def _quantile_value(ds: Any, feat: str, rng: np.random.Generator) -> float | None:
    q = getattr(ds, "feature_quantiles", {}).get(feat)
    if q is None or len(q) == 0:
        return None
    return float(q[rng.integers(2, len(q) - 2)])


def _jitter_val(v: float, rng: np.random.Generator, scale: float) -> float:
    if abs(v) < 1e-9:
        return float(rng.normal(0, 0.01))
    return float(v * math.exp(rng.normal(0, scale)))


def mutate(g: Genome, rng: np.random.Generator, ds: Any = None, operators: tuple[str, ...] = OPERATORS,
           scale: float = 0.2, weights: dict[str, float] | None = None) -> tuple[Genome, dict[str, Any]]:
    ops = list(operators)
    p = np.array([weights.get(o, 1.0) if weights else 1.0 for o in ops], dtype=float)
    op = ops[int(rng.choice(len(ops), p=p / p.sum()))]
    for _ in range(6):
        try:
            return _apply(op, g, rng, ds, scale)
        except (ValueError, IndexError):
            op = ops[int(rng.integers(len(ops)))]
    return _apply("jitter_exit", g, rng, ds, scale)


def _apply(op: str, g: Genome, rng: np.random.Generator, ds: Any, scale: float) -> tuple[Genome, dict[str, Any]]:
    entry = g.entry.model_dump()
    if op == "jitter":
        conds = entry["all"] + entry["any"]
        if not conds:
            raise ValueError
        k = int(rng.integers(len(conds)))
        target = "all" if k < len(entry["all"]) else "any"
        idx = k if target == "all" else k - len(entry["all"])
        c = dict(entry[target][idx])
        old = c["v"]
        c["v"] = _jitter_val(old, rng, scale)
        if c.get("v2") is not None:
            c["v2"] = max(c["v"] + 1e-6, _jitter_val(c["v2"], rng, scale))
        entry[target][idx] = c
        return _child(g, {"operator": op, "change": f"{c['f']} {c['op']} {old:.5g}→{c['v']:.5g}"},
                      entry=EntryLogic.model_validate(entry))
    if op == "jitter_exit":
        ex = g.exit.model_dump()
        key = str(rng.choice(["tp_atr", "sl_atr", "time_stop_bars", "tp_min_pct", "trail_atr", "be_trigger_pct", "lock_frac"]))
        old = ex.get(key)
        if key == "time_stop_bars":
            ex[key] = int(min(2016, max(2, round(old * math.exp(rng.normal(0, scale * 1.5))))))
        elif key == "trail_atr":
            ex[key] = None if (old and rng.random() < 0.3) else float(np.clip(_jitter_val(old or 2.0, rng, scale), 0.3, 15))
        elif key == "be_trigger_pct":
            ex[key] = 0.9 if rng.random() < 0.3 else float(np.clip(_jitter_val(old if old and old < 0.5 else 0.05, rng, scale), 0.006, 0.3))
        elif key == "lock_frac":
            ex[key] = float(np.clip((old or 0.5) + rng.normal(0, 0.12), 0.25, 0.95))
        elif key == "tp_min_pct":
            ex[key] = float(np.clip(_jitter_val(old, rng, scale), 0.008, 0.5))
        else:
            ex[key] = float(np.clip(_jitter_val(old, rng, scale), 0.3, 15 if key == "sl_atr" else 20))
        return _child(g, {"operator": op, "change": f"exit.{key} {old}→{ex[key]}"}, exit=ex)
    if op == "add_condition":
        if len(entry["all"]) + len(entry["any"]) >= 8:
            raise ValueError
        feat = str(rng.choice(ENTRY_POOL))
        v = _quantile_value(ds, feat, rng)
        if v is None:
            raise ValueError
        cop = str(rng.choice(["gt", "lt"]))
        entry["all"].append({"f": feat, "op": cop, "v": v, "v2": None, "lookback": 1})
        return _child(g, {"operator": op, "change": f"+ {feat} {cop} {v:.5g}"},
                      entry=EntryLogic.model_validate(entry))
    if op == "remove_condition":
        if len(entry["all"]) + len(entry["any"]) <= 1:
            raise ValueError
        target = "all" if entry["all"] and (not entry["any"] or rng.random() < 0.7) else "any"
        idx = int(rng.integers(len(entry[target])))
        removed = entry[target].pop(idx)
        return _child(g, {"operator": op, "change": f"- {removed['f']} {removed['op']} {removed['v']:.5g}"},
                      entry=EntryLogic.model_validate(entry))
    if op == "swap_feature":
        conds = entry["all"]
        if not conds:
            raise ValueError
        idx = int(rng.integers(len(conds)))
        feat = str(rng.choice(ENTRY_POOL))
        v = _quantile_value(ds, feat, rng)
        if v is None:
            raise ValueError
        old = conds[idx]["f"]
        conds[idx] = {**conds[idx], "f": feat, "v": v, "v2": None,
                      "op": conds[idx]["op"] if conds[idx]["op"] in ("gt", "lt") else "gt"}
        return _child(g, {"operator": op, "change": f"{old}→{feat} (v={v:.5g})"},
                      entry=EntryLogic.model_validate(entry))
    if op == "regime_specialize":
        r = str(rng.choice(REGIMES[:-1]))
        return _child(g, {"operator": op, "change": f"allow only {r}"}, regimes_allow=[r],
                      min_regime_prob=float(rng.uniform(0.2, 0.5)))
    if op == "regime_veto":
        r = str(rng.choice(REGIMES[:-1]))
        deny = sorted(set(g.regimes_deny) | {r})
        allow = [x for x in g.regimes_allow if x != r]
        return _child(g, {"operator": op, "change": f"veto {r}"}, regimes_deny=deny, regimes_allow=allow)
    if op == "execution":
        ex = g.execution.model_dump()
        if rng.random() < 0.3:
            ex["entry"] = "taker" if ex["entry"] == "maker" else "maker"
        ex["maker_offset_bps"] = float(np.clip(_jitter_val(max(ex["maker_offset_bps"], 1.0), rng, scale * 2), 0, 300))
        ex["maker_ttl_bars"] = int(np.clip(round(ex["maker_ttl_bars"] * math.exp(rng.normal(0, 0.4))), 1, 48))
        return _child(g, {"operator": op, "change": f"execution {ex['entry']} off={ex['maker_offset_bps']:.1f}bps ttl={ex['maker_ttl_bars']}"},
                      execution=ex)
    if op == "horizon":
        ex = g.exit.model_dump()
        k = float(math.exp(rng.normal(0.3, 0.4)))      # bias toward longer horizons / wider barriers
        ex["tp_atr"] = float(np.clip(ex["tp_atr"] * k, 0.3, 20))
        ex["sl_atr"] = float(np.clip(ex["sl_atr"] * k, 0.3, 15))
        ex["time_stop_bars"] = int(np.clip(round(ex["time_stop_bars"] * k), 2, 2016))
        ex["tp_min_pct"] = float(np.clip(ex["tp_min_pct"] * math.sqrt(k), 0.008, 0.5))
        return _child(g, {"operator": op, "change": f"horizon ×{k:.2f}"}, exit=ex)
    raise ValueError(op)


def crossover(a: Genome, b: Genome, rng: np.random.Generator) -> tuple[Genome, dict[str, Any]]:
    """Entry from A, exit/execution from B, regime filter from the better-specified parent."""
    data = a.model_dump()
    data["exit"] = b.exit.model_dump()
    data["execution"] = b.execution.model_dump() if rng.random() < 0.5 else a.execution.model_dump()
    if b.regimes_allow and (not a.regimes_allow or rng.random() < 0.5):
        data["regimes_allow"], data["min_regime_prob"] = list(b.regimes_allow), b.min_regime_prob
    data.update(id=new_id("stg"), parents=[a.id, b.id], generation=max(a.generation, b.generation) + 1,
                origin="crossover", family=a.family if a.family == b.family else f"{a.family}+{b.family}",
                hypothesis=f"Combine entry of {a.id} with exit/risk of {b.id}: {a.hypothesis[:120]}")
    return Genome.model_validate(data), {"operator": "crossover", "parents": [a.id, b.id],
                                         "change": "entry(A)+exit(B)"}
