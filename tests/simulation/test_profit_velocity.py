"""Profit-velocity frontier math, correlation clustering, treasury regime (OP-021) and confidence tiers."""
import math

from forge.treasury import regime as treg
from forge.treasury.profit_velocity import Stream, cluster_unit_pnls, clusters_from_signals, frontier


def _st(**kw):
    base = {"n": 100, "lam": 10.0, "mu_post": 0.01, "mu_lcb": 0.005, "sd": 0.1, "cap": 1.0, "hold_h": 0.01,
            "share": 1e9, "kelly": 1e9, "live_ok": True, "tier": "EXCEPTIONAL"}
    return base | kw


def test_frontier_matches_closed_form_when_risk_binds():
    s = Stream("x", "coinbase", live=True, binary=False)
    f = frontier([(s, _st())], W=28.0, reserve=0.0, idle_apy=0.0)
    m, v = 10 * 0.01, 10 * (0.1 ** 2 + 0.01 ** 2)
    expect = 2 * 28.0 * (m * m / v) / math.log(1 / 0.05)            # $/h_max = 2·D·S / ln(1/δ)
    assert f["binding"] == "RISK" and abs(f["usd_per_h"] - expect) / expect < 1e-6


def test_capital_and_caps_bind_and_reserve_shrinks_deployable():
    s = Stream("x", "kalshi", live=True, binary=True)
    slow = _st(hold_h=50.0)                                          # capital locked for 50 h → capital-bound
    assert frontier([(s, slow)], W=28.0, reserve=0.0, idle_apy=0.0)["binding"] == "CAPITAL"
    capped = Stream("y", "coinbase", live=True, binary=False, cap_units=2.0)
    f = frontier([(capped, _st())], W=28.0, reserve=0.0, idle_apy=0.0)
    assert f["streams"][0]["capped_by"] == "liquidity" and abs(f["trading_usd_per_h"] - 2 * 0.1) < 1e-9
    a = frontier([(s, _st())], W=60.0, reserve=0.0, idle_apy=0.0)["usd_per_h"]
    b = frontier([(s, _st())], W=60.0, reserve=25.0, idle_apy=0.0)["usd_per_h"]
    assert b < a                                                     # protected reserve is never deployed
    assert frontier([], W=28.0, reserve=0.0)["binding"] == "EVIDENCE"


def test_correlated_signals_collapse_to_one_cluster():
    rows = [{"ts": 100.0 + i, "ticker": f"KXBTCD-T{i}", "underlying": "BTC-USD", "close_ts": 3600.0, "side": "no",
             "price": 0.5, "fee": 0.02, "pnl": -0.52, "settled_ts": 3700.0} for i in range(8)]
    rows.append({"ts": 200.0, "ticker": "KXETHD-T1", "underlying": "ETH-USD", "close_ts": 3600.0, "side": "yes",
                 "price": 0.4, "fee": 0.02, "pnl": 0.58, "settled_ts": 3700.0})
    cl = clusters_from_signals(rows)
    assert len(cl) == 2 and abs(cl[0][1] - 8 * -0.52) < 1e-9
    assert cluster_unit_pnls(rows) == [-0.52, 0.58]


def test_treasury_regime_bootstrap_then_latched_reserve():
    r = treg.regime_for(28.0, 28.0)
    assert r["regime"] == "BOOTSTRAP" and r["reserve"] == 0 and r["deployable"] == 28.0
    assert treg.regime_for(49.9, 49.9)["regime"] == "BOOTSTRAP"
    r = treg.regime_for(50.0, 50.0)
    assert r["regime"] == "RESERVE" and r["reserve"] == 25.0 and r["deployable"] == 25.0
    r = treg.regime_for(40.0, 60.0)                                 # dipped below $50 after reaching it: reserve stays
    assert r["regime"] == "RESERVE" and r["deployable"] == 15.0
    assert treg.regime_for(75.0, 75.0)["deployable"] == 50.0
    assert treg.regime_for(200.0, 200.0)["reserve"] == 50.0         # dynamic: 25% of HWM above $100


def test_confidence_tiers():
    assert treg.tier_for(5, 0.99, 0.10)["tier"] == "UNPROVEN"
    assert treg.tier_for(12, 0.85, 0.01)["tier"] == "LOW"
    assert treg.tier_for(12, 0.92, 0.05)["tier"] == "MEDIUM"
    assert treg.tier_for(60, 0.999, 0.05)["tier"] == "EXCEPTIONAL"
    # low-variance spread arb: tiny edge but positive lower bound → can be exceptional (not held to the 2¢ binary rule)
    assert treg.tier_for(141, 1.0, 0.0001, binary=False, lcb=0.00008)["tier"] == "EXCEPTIONAL"
    assert treg.tier_for(141, 1.0, 0.0001, binary=True)["tier"] == "LOW"
