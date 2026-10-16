"""Event-rail verdict: a deterministic, data-driven gate on Forge's own prediction-market engine.

MEASURED 2026-10-11 (crossrail_calibration, n=45,852 settled):
    model Brier   0.12994
    market Brier  0.12856   <- lower is better; the MARKET beats our model
    stacked       0.12968
MEASURED (crossrail_signals, n=19,988 settled): total shadow pnl -$417.598, avg -$0.0209
    MAKE          n=32,860  -$250.29
    SURFACE_RV    n= 3,056  -$ 80.18
    TAKE          n= 3,430  -$ 27.93
    SETTLE_WINDOW n= 1,970  -$ 27.73
    TAKE_THRESH   n= 1,623  -$ 16.17
    MODEL_RAW     n= 4,696  -$ 15.30

So the event rail currently has a NEGATIVE measured edge and its model does not beat the market.
That is not a reason to abandon it — it is a reason to stop spending attention and simulated capital
on it until it earns, exactly as the funnel discipline requires: a measured negative edge benches.

The verdict is recomputed from live data, so it SELF-HEALS the moment the model starts beating the
market. No constant is hardcoded; nothing here needs an officer or an inference call.
"""
from __future__ import annotations

import time
from typing import Any

CACHE_S = 900.0            # recompute at most every 15 min; the data moves slowly
MIN_SETTLED_N = 200        # calibration rows needed before we may claim anything about model skill
MIN_SIGNALS_N = 200        # settled signals needed before we may claim anything about profitability

# A definitive verdict requires BOTH. Benching a rail on 10 calibration rows and one signal is the
# same sin as promoting a strategy on n<30: it launders a guess as evidence. When either side is thin
# the honest answer is INSUFFICIENT_EVIDENCE, and the rail stays in shadow (measured, not deployed).


def compute(db: Any) -> dict[str, Any]:
    """Recompute the event-rail verdict from settled calibration + signal rows."""
    out: dict[str, Any] = {"ts": time.time()}
    try:
        row = db.query_one(
            "SELECT AVG((p_model-outcome)*(p_model-outcome)) mb, "
            "AVG((p_market-outcome)*(p_market-outcome)) kb, "
            "AVG((p_stacked-outcome)*(p_stacked-outcome)) sb, COUNT(*) n "
            "FROM crossrail_calibration WHERE outcome IS NOT NULL")
    except Exception:
        row = None
    n = int((row or {}).get("n") or 0)
    out["n_settled"] = n
    if row and n >= MIN_SETTLED_N:
        mb, kb, sb = float(row["mb"]), float(row["kb"]), float(row["sb"])
        out.update({"brier_model": round(mb, 5), "brier_market": round(kb, 5),
                    "brier_stacked": round(sb, 5),
                    "model_beats_market": mb < kb, "stacked_beats_market": sb < kb,
                    "model_skill_vs_market": round(kb - mb, 6)})
    try:
        pnl = db.query_one(
            "SELECT COUNT(*) n, COALESCE(SUM(CAST(pnl AS REAL)),0) total, "
            "COALESCE(AVG(CAST(pnl AS REAL)),0) avg FROM crossrail_signals WHERE pnl IS NOT NULL")
    except Exception:
        pnl = None
    if pnl:
        out["signals_settled"] = int(pnl["n"] or 0)
        out["shadow_pnl_usd"] = round(float(pnl["total"] or 0.0), 4)
        out["shadow_avg_pnl_usd"] = round(float(pnl["avg"] or 0.0), 6)
        try:
            worst = db.query_one(
                "SELECT kind, COUNT(*) n, ROUND(SUM(CAST(pnl AS REAL)),4) total FROM crossrail_signals "
                "WHERE pnl IS NOT NULL GROUP BY kind ORDER BY total ASC LIMIT 1")
            if worst:
                out["worst_kind"] = {"kind": worst["kind"], "n": int(worst["n"]),
                                     "total_usd": float(worst["total"] or 0)}
        except Exception:
            pass

    # The verdict. Positive edge requires BOTH: model beats market on calibration AND shadow pnl > 0.
    # Either evidence side being thin => INSUFFICIENT_EVIDENCE (shadow_only), never a definitive call.
    have_skill = n >= MIN_SETTLED_N and "model_beats_market" in out
    have_pnl = int(out.get("signals_settled") or 0) >= MIN_SIGNALS_N
    beats = bool(out.get("model_beats_market"))
    profitable = float(out.get("shadow_pnl_usd") or 0.0) > 0
    if not (have_skill and have_pnl):
        verdict, action = "INSUFFICIENT_EVIDENCE", "shadow_only"
        out["evidence"] = {"calibration_rows": n, "calibration_required": MIN_SETTLED_N,
                           "settled_signals": int(out.get("signals_settled") or 0),
                           "signals_required": MIN_SIGNALS_N,
                           "missing": [k for k, ok in (("model_skill", have_skill),
                                                        ("profitability", have_pnl)) if not ok]}
    elif beats and profitable:
        verdict, action = "EARNING", "deploy"
    elif beats:
        # model has skill but the execution/fee path loses: fix costs before deploying
        verdict, action = "SKILL_BUT_UNPROFITABLE", "shadow_only"
    else:
        verdict, action = "NEGATIVE_EDGE", "bench"
    out["verdict"] = verdict
    out["action"] = action
    out["reopen_condition"] = ("model Brier < market Brier on >=%d settled calibration rows AND shadow "
                               "pnl > 0 over >=%d settled signals" % (MIN_SETTLED_N, MIN_SIGNALS_N))
    return out


def verdict(db: Any, *, force: bool = False) -> dict[str, Any]:
    """Cached verdict. Reads KV unless stale or forced."""
    if not force:
        try:
            cached = db.kv_get("event_rail.verdict") or {}
            if cached and (time.time() - float(cached.get("ts") or 0)) < CACHE_S:
                return cached
        except Exception:
            pass
    v = compute(db)
    try:
        db.kv_set("event_rail.verdict", v)
    except Exception:
        pass
    return v


def event_rail_tradeable(db: Any) -> bool:
    """The single boolean the funnel and allocators consult: may event-rail candidates proceed?"""
    return verdict(db).get("action") == "deploy"
