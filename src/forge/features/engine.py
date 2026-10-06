"""Vectorized, strictly causal feature engine (DOSSIER §10, DIRECTIVE §12).

Every feature value at index t uses only bars ≤ t (no lookahead). Research computes features over
full histories; live recomputes over a trailing window and reads the last row — same code path.
Microstructure (order-book / trade-flow) features are live-only and merged at decision time.
"""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

NAN = np.nan


# ---- causal rolling primitives -------------------------------------------------------------------
def _pad(out: np.ndarray, n: int, w: int) -> np.ndarray:
    res = np.full(n, NAN)
    res[w - 1:] = out
    return res


def rmean(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    if n < w:
        return np.full(n, NAN)
    c = np.cumsum(np.insert(x, 0, 0.0))
    return _pad((c[w:] - c[:-w]) / w, n, w)


def rstd(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    if n < w:
        return np.full(n, NAN)
    c1 = np.cumsum(np.insert(x, 0, 0.0))
    c2 = np.cumsum(np.insert(x * x, 0, 0.0))
    m = (c1[w:] - c1[:-w]) / w
    v = np.maximum((c2[w:] - c2[:-w]) / w - m * m, 0.0)
    return _pad(np.sqrt(v * w / max(w - 1, 1)), n, w)


def rmax(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    return _pad(sliding_window_view(x, w).max(axis=1), n, w) if n >= w else np.full(n, NAN)


def rmin(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x)
    return _pad(sliding_window_view(x, w).min(axis=1), n, w) if n >= w else np.full(n, NAN)


def rsum(x: np.ndarray, w: int) -> np.ndarray:
    return rmean(x, w) * w


def ema(x: np.ndarray, span: int) -> np.ndarray:
    a = 2.0 / (span + 1.0)
    out = np.empty_like(x, dtype=float)
    acc = x[0] if len(x) else NAN
    for i, v in enumerate(x):
        acc = a * v + (1 - a) * acc if i else v
        out[i] = acc
    if len(x) >= span:
        out[: span - 1] = NAN
    else:
        out[:] = NAN
    return out


def shift(x: np.ndarray, k: int) -> np.ndarray:
    out = np.full(len(x), NAN)
    if k < len(x):
        out[k:] = x[:-k] if k else x
    return out


def rank_pct(x: np.ndarray, w: int) -> np.ndarray:
    """Percentile of x[t] within the trailing window (causal)."""
    n = len(x)
    if n < w:
        return np.full(n, NAN)
    win = sliding_window_view(x, w)
    last = win[:, -1:]
    with np.errstate(invalid="ignore"):
        pct = (win < last).sum(axis=1) / (w - 1)
    return _pad(pct, n, w)


def rslope(y: np.ndarray, w: int) -> np.ndarray:
    """OLS slope of y over trailing window (per bar)."""
    n = len(y)
    if n < w:
        return np.full(n, NAN)
    t = np.arange(w, dtype=float)
    tc = t - t.mean()
    denom = (tc * tc).sum()
    win = sliding_window_view(y, w)
    return _pad((win - win.mean(axis=1, keepdims=True)) @ tc / denom, n, w)


def rcorr(a: np.ndarray, b: np.ndarray, w: int) -> np.ndarray:
    ma, mb = rmean(a, w), rmean(b, w)
    cov = rmean(a * b, w) - ma * mb
    sa, sb = rstd(a, w), rstd(b, w)
    with np.errstate(invalid="ignore", divide="ignore"):
        return cov * w / max(w - 1, 1) / (sa * sb)


# ---- feature registry ----------------------------------------------------------------------------
FEATURE_DOCS: dict[str, str] = {}


def _doc(name: str, text: str) -> None:
    FEATURE_DOCS[name] = text


RET_H = (1, 3, 6, 12, 24, 48, 96, 288)
for _h in RET_H:
    _doc(f"ret_{_h}", f"log return over {_h} bars")
for _w in (12, 48, 288):
    _doc(f"vol_{_w}", f"realized volatility (std of 1-bar log returns) over {_w} bars")
_doc("vol_ratio", "vol_12 / vol_48 (>1 expansion, <1 compression)")
_doc("vol_pct", "percentile of vol_48 over trailing 500 bars")
_doc("z_20", "z-score of close vs 20-bar mean"); _doc("z_50", "z-score of close vs 50-bar mean")
_doc("vwap_dist_48", "close vs 48-bar VWAP (fraction)"); _doc("vwap_dist_288", "close vs 288-bar VWAP")
_doc("slope_24", "OLS slope of log price over 24 bars / vol_48"); _doc("slope_96", "OLS slope over 96 bars / vol_48")
_doc("accel_6", "ret_6 − previous ret_6 (acceleration)")
_doc("brk_hi_48", "close vs prior 48-bar high (fraction, >0 = breakout)"); _doc("brk_lo_48", "close vs prior 48-bar low")
_doc("brk_hi_288", "close vs prior 288-bar high"); _doc("range_pos_48", "position of close within 48-bar range [0,1]")
_doc("rvol_12", "volume last 12 bars / typical (288-bar mean ×12)")
_doc("rvol_1", "last bar volume / 288-bar mean volume")
_doc("rsi_14", "RSI(14) scaled to [0,1]")
_doc("er_24", "Kaufman efficiency ratio over 24 bars (trend quality)")
_doc("ac1_48", "lag-1 autocorrelation of returns over 48 bars")
_doc("dd_288", "drawdown from 288-bar high (≤0)")
_doc("ema_gap", "(EMA12 − EMA48) / close"); _doc("ema_gap_slow", "(EMA48 − EMA192) / close")
_doc("atr_14", "average true range (14) / close")
_doc("bb_width_pct", "percentile of 20-bar band width over 500 bars (squeeze detector)")
_doc("buy_ratio_12", "aggressor-buy share of volume over 12 bars (live/recorded only)")
_doc("hour_sin", "time of day (sin)"); _doc("hour_cos", "time of day (cos)")
_doc("rs_btc_48", "48-bar residual return vs BTC (beta-adjusted relative strength)")
_doc("corr_btc_96", "96-bar return correlation with BTC")


def compute_features(bars: dict[str, np.ndarray], interval_s: int = 300) -> dict[str, np.ndarray]:
    c = np.asarray(bars["close"], dtype=float)
    h = np.asarray(bars["high"], dtype=float)
    lo = np.asarray(bars["low"], dtype=float)
    v = np.nan_to_num(np.asarray(bars["volume"], dtype=float))
    ts = np.asarray(bars["ts"], dtype=float)
    n = len(c)
    f: dict[str, np.ndarray] = {}
    if n == 0:
        return {k: np.array([]) for k in FEATURE_DOCS}
    lc = np.log(np.maximum(c, 1e-12))
    r1 = np.diff(lc, prepend=lc[0])
    r1[0] = 0.0
    for k in RET_H:
        f[f"ret_{k}"] = lc - shift(lc, k)
    for w in (12, 48, 288):
        f[f"vol_{w}"] = rstd(r1, w)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["vol_ratio"] = f["vol_12"] / f["vol_48"]
        f["vol_pct"] = rank_pct(np.nan_to_num(f["vol_48"], nan=0.0), 500)
        for w in (20, 50):
            f[f"z_{w}"] = (c - rmean(c, w)) / rstd(c, w)
        pv = c * v
        for w in (48, 288):
            vw = rsum(pv, w) / rsum(v, w)
            f[f"vwap_dist_{w}"] = c / vw - 1.0
        vol48 = f["vol_48"]
        f["slope_24"] = rslope(lc, 24) / vol48
        f["slope_96"] = rslope(lc, 96) / vol48
        f["accel_6"] = f["ret_6"] - shift(f["ret_6"], 6)
        prev_hi48, prev_lo48 = shift(rmax(h, 48), 1), shift(rmin(lo, 48), 1)
        f["brk_hi_48"] = c / prev_hi48 - 1.0
        f["brk_lo_48"] = c / prev_lo48 - 1.0
        f["brk_hi_288"] = c / shift(rmax(h, 288), 1) - 1.0
        hi48, lo48 = rmax(h, 48), rmin(lo, 48)
        f["range_pos_48"] = (c - lo48) / (hi48 - lo48)
        mv288 = rmean(v, 288)
        f["rvol_12"] = rsum(v, 12) / (mv288 * 12)
        f["rvol_1"] = v / mv288
        up = np.maximum(r1, 0.0)
        dn = np.maximum(-r1, 0.0)
        au, ad = ema(up, 27), ema(dn, 27)          # Wilder(14) ≈ EMA(27)
        f["rsi_14"] = au / (au + ad)
        f["er_24"] = np.abs(lc - shift(lc, 24)) / rsum(np.abs(r1), 24)
        f["ac1_48"] = rcorr(r1, shift(r1, 1), 48)
        f["dd_288"] = c / rmax(h, 288) - 1.0
        e12, e48, e192 = ema(c, 12), ema(c, 48), ema(c, 192)
        f["ema_gap"] = (e12 - e48) / c
        f["ema_gap_slow"] = (e48 - e192) / c
        pc = shift(c, 1)
        tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
        tr[0] = h[0] - lo[0]
        f["atr_14"] = ema(tr, 27) / c
        bw = 4 * rstd(c, 20) / rmean(c, 20)
        f["bb_width_pct"] = rank_pct(np.nan_to_num(bw, nan=0.0), 500)
        bv = bars.get("buy_volume")
        if bv is not None and np.isfinite(np.asarray(bv, dtype=float)).any():
            bvv = np.nan_to_num(np.asarray(bv, dtype=float))
            f["buy_ratio_12"] = rsum(bvv, 12) / rsum(v, 12)
        else:
            f["buy_ratio_12"] = np.full(n, NAN)
    hour = (ts % 86400) / 86400 * 2 * np.pi
    f["hour_sin"], f["hour_cos"] = np.sin(hour), np.cos(hour)
    f["rs_btc_48"] = np.full(n, NAN)
    f["corr_btc_96"] = np.full(n, NAN)
    for k, arr in f.items():
        arr[~np.isfinite(arr)] = NAN
    return f


def add_cross_asset(f: dict[str, np.ndarray], bars: dict[str, np.ndarray],
                    btc_bars: dict[str, np.ndarray] | None) -> None:
    """Relative strength vs BTC, aligned on timestamps (causal)."""
    if btc_bars is None or len(btc_bars["ts"]) == 0:
        return
    ts = np.asarray(bars["ts"])
    idx = np.searchsorted(btc_bars["ts"], ts)
    ok = (idx < len(btc_bars["ts"])) & (btc_bars["ts"][np.minimum(idx, len(btc_bars["ts"]) - 1)] == ts)
    bc = np.full(len(ts), NAN)
    bc[ok] = np.asarray(btc_bars["close"])[idx[ok]]
    lc, lb = np.log(np.asarray(bars["close"], dtype=float)), np.log(bc)
    ra = np.diff(lc, prepend=lc[0])
    rb = np.diff(lb, prepend=lb[0])
    rb = np.nan_to_num(rb)
    with np.errstate(invalid="ignore", divide="ignore"):
        mb = rmean(rb, 96)
        cov = rmean(ra * rb, 96) - rmean(ra, 96) * mb
        var = rmean(rb * rb, 96) - mb * mb
        beta = np.clip(cov / var, -3, 3)
        res = ra - np.nan_to_num(beta) * rb
        f["rs_btc_48"] = rsum(res, 48)
        f["corr_btc_96"] = rcorr(ra, rb, 96)
    for k in ("rs_btc_48", "corr_btc_96"):
        f[k][~np.isfinite(f[k])] = NAN


def latest(f: dict[str, np.ndarray]) -> dict[str, float]:
    return {k: (float(v[-1]) if len(v) and np.isfinite(v[-1]) else NAN) for k, v in f.items()}


# ---- live microstructure features ----------------------------------------------------------------
MICRO_FEATURES = ("spread_bps", "imb_l1", "imb_5", "imb_25bps", "micro_disp_bps", "depth_50bps_usd",
                  "flow_imb_60s", "trade_rate_60s")
for _m in MICRO_FEATURES:
    _doc(_m, "live microstructure (order book / trade flow)")
