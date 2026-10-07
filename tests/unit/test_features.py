import numpy as np

from forge.features.engine import FEATURE_DOCS, compute_features


def _bars(n=1500, seed=1):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, 0.004, n)
    c = 100 * np.exp(np.cumsum(r))
    h = c * (1 + np.abs(rng.normal(0, 0.002, n)))
    lo = c * (1 - np.abs(rng.normal(0, 0.002, n)))
    o = np.concatenate([[c[0]], c[:-1]])
    return {"ts": np.arange(n) * 300.0 + 1.7e9, "open": o, "high": h, "low": lo, "close": c,
            "volume": rng.uniform(10, 100, n), "buy_volume": np.full(n, np.nan)}


def test_no_lookahead():
    """Causality: features at t computed from a prefix equal those computed from the full series."""
    b = _bars()
    full = compute_features(b)
    for cut in (700, 1000, 1499):
        pre = compute_features({k: v[:cut] for k, v in b.items()})
        for name, arr in pre.items():
            a, f = arr[cut - 1], full[name][cut - 1]
            assert (np.isnan(a) and np.isnan(f)) or abs(a - f) < 1e-9 * max(1, abs(f)), (name, cut, a, f)


def test_all_registered_features_present():
    f = compute_features(_bars(600))
    missing = set(FEATURE_DOCS) - set(f) - {"spread_bps", "imb_l1", "imb_5", "imb_25bps", "micro_disp_bps",
                                            "depth_50bps_usd", "flow_imb_60s", "trade_rate_60s"}
    assert not missing


def test_cross_asset_and_market_features_causal():
    """resid_z_* and mkt_breadth/trend at t must not depend on data after t."""
    from forge.features.engine import add_cross_asset, add_market_features
    syms = {f"S{i}": _bars(1200, seed=10 + i) for i in range(6)}
    btc = _bars(1200, seed=99)

    def build(cut):
        out = {}
        for s, b in syms.items():
            bb = {k: v[:cut] for k, v in b.items()}
            f = compute_features(bb)
            add_cross_asset(f, bb, {k: v[:cut] for k, v in btc.items()})
            out[s] = (bb, f)
        add_market_features(out, horizon=288)
        return out
    full = build(1200)
    for cut in (800, 1100):
        pre = build(cut)
        for s in syms:
            for name in ("resid_z_24", "resid_z_72", "mkt_breadth_24h", "mkt_trend_24h", "mkt_breadth_chg", "ext_atr_ema20"):
                a, f = pre[s][1][name][cut - 1], full[s][1][name][cut - 1]
                assert (np.isnan(a) and np.isnan(f)) or abs(a - f) < 1e-9 * max(1, abs(f)), (s, name, cut, a, f)
    v = full["S0"][1]["mkt_breadth_24h"]
    assert np.nanmin(v) >= 0 and np.nanmax(v) <= 1 and np.isfinite(v[-1])


def test_convex_barriers():
    from forge.strategies.genome import CONVEX_NO_TP, barrier_pcts, chandelier_k
    from forge.strategies.seeds import seed_genomes
    g = seed_genomes()[0]
    g2 = g.model_copy(update={"exit": g.exit.model_copy(update={"convex": True, "cat_atr": 2.0})})
    tp, sl = barrier_pcts(g2, 0.01)
    unit = 0.01 * (3600 / g2.interval_s) ** 0.5            # hour-equivalent ATR (5m → ×√12)
    assert tp == CONVEX_NO_TP and abs(sl - min(2.0 * unit, g2.exit.sl_max_pct)) < 1e-12
    assert chandelier_k(g2, 0.9) == g2.exit.chand_k_hv and chandelier_k(g2, 0.2) == g2.exit.chand_k


def test_allocation_gates():
    from forge.treasury.allocation import (breadth_multiplier, drawdown_state, ecr_tier, edge_coverage_ratio,
                                           haircut_probability, retention_haircut, risk_at_stop_cap, volatility_multiplier)
    # ECR: 50% win, +3% / −2% gross, 1% / 1.4% costs → E[gross]=0.5%, E[cost]=1.2% → 0.42 → REJECT
    e = edge_coverage_ratio(0.5, 0.02, -0.034, 0.01, 0.014)
    assert abs(e - 0.005 / 0.012) < 1e-9 and ecr_tier(e) == "REJECT"
    assert ecr_tier(1.7) == "SHADOW_ONLY" and ecr_tier(2.5) == "SMALL_LIVE" and ecr_tier(4.2) == "CONCENTRATION_CANDIDATE"
    # haircut scales EV exactly by H
    p, w, l = 0.55, 0.03, -0.02
    ph = haircut_probability(p, w, l, 0.25)
    assert abs((ph * w + (1 - ph) * l) - 0.25 * (p * w + (1 - p) * l)) < 1e-12
    assert retention_haircut(0.01, None, 0) == 0.25
    assert retention_haircut(0.01, 0.01, 1000) > 0.95 and retention_haircut(0.01, -0.01, 1000) < 0.01
    # exposure tiers
    assert breadth_multiplier(0.7, "momentum") == 1.0 and breadth_multiplier(0.2, "liquidity_provision") == 1.0
    assert 0.5 <= breadth_multiplier(0.5, "momentum") <= 0.75 and breadth_multiplier(0.1, "momentum") < 0.25
    assert volatility_multiplier(0.95, False) == 0.5 and volatility_multiplier(0.98, False) == 0.0 and volatility_multiplier(0.98, True) == 1.0
    assert drawdown_state(94, 100).multiplier == 0.75 and drawdown_state(89, 100).postmortem_required
    assert drawdown_state(84, 100).generic_live_paused and drawdown_state(100, 100).state == "NORMAL"
    # risk-at-stop: 5% of $28 at a 4% stop → ≤ $35; aggregate budget exhausted → 0
    rc = risk_at_stop_cap(28.0, 0.04, 0.8, 0.0)
    assert abs(rc.max_notional - 28 * 0.05 / 0.04) < 1e-9
    assert risk_at_stop_cap(28.0, 0.04, 0.8, 2.8).max_notional < 1e-9


def test_sealed_split_is_disjoint_and_ordered():
    from forge.research.evaluate import Dataset
    syms = {f"S{i}-USD": _bars(1000, seed=i) for i in range(6)}
    ds = Dataset.build(syms, 300, holdout_frac=0.20, sealed_frac=0.15)
    sd = next(iter(ds.symbols.values()))
    s0, s1 = ds.split(sd, "selection")
    h0, h1 = ds.split(sd, "holdout")
    z0, z1 = ds.split(sd, "sealed")
    assert s0 == 0 and s1 == h0 and h1 == z0 and z1 == sd.n          # contiguous, chronological, disjoint
    assert abs((z1 - z0) / sd.n - 0.15) < 0.01 and abs((h1 - h0) / sd.n - 0.20) < 0.01
    legacy = Dataset.build(syms, 300, holdout_frac=0.3)
    assert legacy.split(next(iter(legacy.symbols.values())), "holdout")[1] == sd.n   # sealed_frac=0 → unchanged behaviour
    assert ds.sealed_start_ts() == float(sd.bars["ts"][z0])


def test_sealed_exam_rules():
    from types import SimpleNamespace as NS

    from forge.evolution.search import sealed_exam
    good = NS(metrics={"n": 20, "mean_net": 0.01, "p_positive": 0.8}, trades=[NS(net=x) for x in [0.02, 0.01, -0.005] * 7])
    assert sealed_exam(good, 1)[0]
    assert not sealed_exam(NS(metrics={"n": 3, "mean_net": 0.05, "p_positive": 0.9}, trades=[]), 1)[0]
    assert not sealed_exam(NS(metrics={"n": 20, "mean_net": -0.001, "p_positive": 0.4}, trades=[]), 1)[0]
