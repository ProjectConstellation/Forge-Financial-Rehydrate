"""Probabilistic regime engine (DOSSIER §10.5, DIRECTIVE §12/§21F).

Deterministic, vectorized, causal: computes evidence scores from features, converts them into a
probability distribution over regimes (softmax), and smooths with an EWMA for hysteresis.
The DeepSeek perception layer may add its own regime calls (logged to the Intelligence
Attribution Ledger); this engine is the always-on, millisecond baseline.
"""

from __future__ import annotations

import numpy as np

REGIMES = ("TREND_UP", "TREND_DOWN", "RANGE_LOW_VOL", "RANGE_HIGH_VOL", "BREAKOUT_EXPANSION",
           "PANIC_SELLING", "EUPHORIA_BUYING", "TRANSITION")


def _z(x: np.ndarray) -> np.ndarray:
    return np.nan_to_num(x, nan=0.0)


def regime_scores(f: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    slope = _z(f["slope_96"])                 # vol-normalized trend slope
    er = _z(f["er_24"])                       # trend efficiency 0..1
    gap = _z(f["ema_gap_slow"]) / np.maximum(_z(f["vol_48"]), 1e-4)
    volp = np.nan_to_num(f["vol_pct"], nan=0.5)
    vratio = np.nan_to_num(f["vol_ratio"], nan=1.0)
    squeeze = 1.0 - np.nan_to_num(f["bb_width_pct"], nan=0.5)
    rvol = np.nan_to_num(f["rvol_12"], nan=1.0)
    vol48 = np.maximum(_z(f["vol_48"]), 1e-4)
    shock = _z(f["ret_12"]) / (vol48 * np.sqrt(12))   # 12-bar move in sigma units
    brk = _z(f["brk_hi_48"]) / vol48
    trend = 0.6 * np.tanh(slope / 3) + 0.4 * np.tanh(gap / 4)
    s = {
        "TREND_UP": 2.5 * np.maximum(trend, 0) + 1.5 * er - 0.5,
        "TREND_DOWN": 2.5 * np.maximum(-trend, 0) + 1.5 * er - 0.5,
        "RANGE_LOW_VOL": 1.8 * (1 - np.abs(trend)) + 1.5 * (1 - volp) - 1.2 * er - 0.6,
        "RANGE_HIGH_VOL": 1.8 * (1 - np.abs(trend)) + 1.5 * volp - 1.2 * er - 0.8,
        "BREAKOUT_EXPANSION": 1.2 * np.tanh(np.maximum(vratio - 1, 0) * 2) + 1.0 * np.tanh(np.maximum(brk, 0))
                              + 0.6 * np.tanh(np.maximum(rvol - 1, 0)) + 0.4 * squeeze - 1.2,
        "PANIC_SELLING": 1.5 * np.tanh(np.maximum(-shock - 2, 0)) + 0.8 * np.tanh(np.maximum(rvol - 1.5, 0)) - 0.6,
        "EUPHORIA_BUYING": 1.5 * np.tanh(np.maximum(shock - 2, 0)) + 0.8 * np.tanh(np.maximum(rvol - 1.5, 0)) - 0.6,
        "TRANSITION": np.full(len(slope), 0.0),
    }
    return s


def regime_probs(f: dict[str, np.ndarray], temperature: float = 0.6, smooth: int = 3) -> dict[str, np.ndarray]:
    s = regime_scores(f)
    m = np.vstack([s[r] for r in REGIMES]) / temperature
    m -= m.max(axis=0, keepdims=True)
    p = np.exp(m)
    p /= p.sum(axis=0, keepdims=True)
    if smooth > 1:                                   # causal EWMA hysteresis
        a = 2.0 / (smooth + 1)
        for j in range(1, p.shape[1]):
            p[:, j] = a * p[:, j] + (1 - a) * p[:, j - 1]
        p /= p.sum(axis=0, keepdims=True)
    return {r: p[i] for i, r in enumerate(REGIMES)}


def regime_labels(probs: dict[str, np.ndarray]) -> np.ndarray:
    m = np.vstack([probs[r] for r in REGIMES])
    return np.array(REGIMES)[m.argmax(axis=0)]


def latest_regime(probs: dict[str, np.ndarray]) -> tuple[str, dict[str, float], float]:
    """(label, distribution, confidence) at the last bar; confidence = top prob − second prob."""
    last = {r: float(probs[r][-1]) for r in REGIMES}
    ordered = sorted(last.items(), key=lambda kv: -kv[1])
    label = ordered[0][0]
    conf = ordered[0][1] - ordered[1][1]
    if conf < 0.08:
        label = "TRANSITION"
    return label, last, conf
