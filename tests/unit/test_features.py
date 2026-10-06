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
