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
    assert tp == CONVEX_NO_TP and abs(sl - 0.02) < 1e-12
    assert chandelier_k(g2, 0.9) == g2.exit.chand_k_hv and chandelier_k(g2, 0.2) == g2.exit.chand_k
