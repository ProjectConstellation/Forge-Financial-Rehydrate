"""OP-013 opportunity surface: fees, mapping, probability engine, signals, arbs, allocator, listing diff."""
import math

import numpy as np

from forge.opportunities.crossrail import (Signal, ladder_arbs, maker_filled, maker_quotes, map_series, range_arbs,
                                           scale_ok, taker_signals)
from forge.opportunities.kalshi import KalshiMarket, kalshi_fee
from forge.opportunities.probability import (StackedCalibrator, binary_kelly, fit_underlying, stack_features,
                                             student_t_sf)
from forge.opportunities.surface import ListingSentinel, Rail, RailEconomics, allocate


def mk(t, st="greater", floor=None, cap=None, yb=None, ya=None, ev="E1"):
    return KalshiMarket(t, ev, "S", st, floor, cap, 1e10, yb, ya, 10, 10, 100, 100, "active", "")


def test_kalshi_fee_matches_official_worked_example():
    # docs.kalshi.com fee_rounding: price $0.055, model fee $0.00363825 → ceil_6dp $0.003639; FCM rounds to the cent
    assert kalshi_fee(0.055, rounding_cents=False) == 0.003639
    assert kalshi_fee(0.055) == 0.01
    assert kalshi_fee(0.5, 100, rounding_cents=False) == 1.75
    assert kalshi_fee(0.4, maker=True) == 0.0 and kalshi_fee(0.4, fee_type="quadratic_with_maker_fees", maker=True) > 0


def test_series_mapping_is_discovered_and_scale_checked():
    bases = {"BTC", "ETH", "SOL", "XRP", "PAXG", "DOGE"}
    cf = [{"name": "CF Benchmarks"}]
    assert map_series({"ticker": "KXBTCD", "title": "Bitcoin price", "category": "Crypto", "settlement_sources": cf}, bases) == "BTC-USD"
    assert map_series({"ticker": "KXRIPPLE", "title": "Ripple range", "category": "Crypto", "settlement_sources": cf}, bases) == "XRP-USD"
    assert map_series({"ticker": "KXCRYPTOCOMP15M", "title": "x", "category": "Crypto", "settlement_sources": cf}, bases) is None
    assert map_series({"ticker": "KXGOLDH", "title": "Gold Hourly", "category": "Commodities",
                       "settlement_sources": [{"name": "Pyth - Gold"}]}, bases) == "PAXG-USD"
    assert map_series({"ticker": "KXBCH15M", "title": "Bitcoin Cash 15 Minute", "category": "Crypto", "settlement_sources": cf}, bases) is None
    assert map_series({"ticker": "KXWTI", "title": "WTI", "category": "Commodities", "settlement_sources": [{"name": "ICE"}]}, bases) is None
    assert scale_ok([83000, 84000, 85000], 84200) and not scale_ok([1.0, 2.0], 84200)


def test_student_t_tail():
    assert abs(student_t_sf(0.0) - 0.5) < 1e-12 and 0.11 < student_t_sf(1.0) < 0.12 and student_t_sf(3) > 0.006


def test_fhs_model_recovers_gbm_probabilities():
    rng = np.random.default_rng(1)
    n, sub, sig = 30000, 30, 0.0008
    lp = np.cumsum(rng.normal(0, sig * math.sqrt(5 / sub), (n, sub)).ravel()).reshape(n, sub) + math.log(100)
    c = np.exp(lp[:, -1]); o = np.r_[100, c[:-1]]
    h = np.maximum(np.exp(lp.max(1)), o); lo = np.minimum(np.exp(lp.min(1)), o)
    m = fit_underlying("X", {"ts": np.arange(n) * 300.0, "open": o, "high": h, "low": lo, "close": c})
    assert abs(m.sigma_min_now / sig - 1) < 0.10
    s = sig * math.sqrt(60 - 2 / 3)
    for k in (99.5, 100.0, 100.5):
        ana = 0.5 * math.erfc(math.log(k / 100) / (s * math.sqrt(2)))
        assert abs(m.prob_above(100, k, 0, 60) - ana) < 0.035
    assert abs(m.prob(100, 0, 60, "between", 99.5, 100.5) - (m.prob_above(100, 99.5, 0, 60) - m.prob_above(100, 100.5, 0, 60))) < 1e-12


def test_stacked_calibrator_trusts_market_until_model_proves_itself():
    c = StackedCalibrator()
    p, lo, hi = c.predict(0.9, 0.4, 60)
    assert abs(p - 0.4) < 0.02 and lo < p < hi                    # prior: market price
    rng = np.random.default_rng(3)
    X, y = [], []
    for _ in range(1500):
        tl = rng.normal(0, 1.5)
        X.append(stack_features(1 / (1 + math.exp(-(tl + rng.normal(0, .3)))), 1 / (1 + math.exp(-(tl + rng.normal(0, .6)))), 60))
        y.append(float(rng.random() < 1 / (1 + math.exp(-tl))))
    c.fit(np.array(X), np.array(y))
    assert c.model_weight_share() > 0.3


def test_taker_maker_and_arbs():
    m = mk("T1", floor=100, yb=0.40, ya=0.45)
    s = taker_signals(m, 0.60, 0.62)
    assert s and s[0].side == "yes" and abs(s[0].edge - (0.60 - 0.45 - kalshi_fee(0.45))) < 1e-12
    assert not taker_signals(m, 0.46, 0.47)                       # edge below fee + margin → nothing
    q = maker_quotes(m, 0.60, 0.62)
    assert q and q[0].price == 0.41 and q[0].fee == 0.0           # inside the spread, zero maker fee
    assert maker_filled("yes", 0.41, mk("T1", floor=100, yb=0.35, ya=0.41)) and not maker_filled("yes", 0.41, m)
    lad = ladder_arbs([mk("A", floor=100, yb=0.20, ya=0.30), mk("B", floor=110, yb=0.50, ya=0.55)])
    assert lad and lad[0].kind == "LADDER_ARB" and lad[0].edge > 0
    ra = range_arbs([mk("R1", "between", 1, 2, 0.2, 0.25), mk("R2", "between", 2, 3, 0.2, 0.25), mk("R3", "between", 3, 4, 0.2, 0.25)], True)
    assert ra and ra[0].detail["type"] == "buy_all_yes"
    assert range_arbs([mk("R1", "between", 1, 2, 0.2, 0.25)], False) == []
    assert binary_kelly(0.6, 0.45, 0.02) > 0 and binary_kelly(0.4, 0.45, 0.02) == 0


def test_allocator_prefers_best_executable_and_reports_unlock_value():
    good_blocked = Rail("k", "K", "c", executable=False, economics=RailEconomics(0.05, 0.8, 1, 1, capacity_usd=10))
    spot = Rail("s", "S", "c", executable=True, economics=RailEconomics(0.01, 0.6, 2, 1, capacity_usd=100))
    bad = Rail("b", "B", "c", executable=True, economics=RailEconomics(0.001, 0.5, 1, 1, fees=0.01, capacity_usd=100))
    now = allocate([good_blocked, spot, bad], 28.0, 0.0)
    assert [p["rail"] for p in now["plan"]] == ["s"]
    unl = allocate([good_blocked, spot, bad], 28.0, 0.0, include_blocked=True)
    assert unl["plan"][0]["rail"] == "k" and unl["plan"][0]["usd"] == 10
    e = RailEconomics(0.01, 1.0, 1.0, lockup_days=2.0, compute_usd_day=0.28)
    assert abs(e.score_per_day(28.0, 0.001) - (0.01 - 0.002 - 0.01)) < 1e-12


def test_listing_diff():
    old = {"A-USD": ("online", False, False, False), "B-USD": ("online", True, False, False)}
    new = {"A-USD": ("online", False, False, False), "B-USD": ("online", False, False, False), "C-USD": ("online", False, True, False)}
    ev = {(p, k) for p, k, _, _ in ListingSentinel.diff(old, new)}
    assert ("C-USD", "NEW_PRODUCT") in ev and ("B-USD", "TRADING_ENABLED") in ev
    assert ListingSentinel.diff({}, new) == []                     # first snapshot is a baseline, not 900 "listings"
    assert ("A-USD", "DELISTED") in {(p, k) for p, k, _, _ in ListingSentinel.diff(new, {"B-USD": new["B-USD"], "C-USD": new["C-USD"]})}
