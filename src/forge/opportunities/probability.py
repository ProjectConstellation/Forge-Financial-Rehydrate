"""FORGE probability engine for price-threshold event contracts (Kalshi crypto/commodity ladders vs Coinbase prices).

Layers (each one exists to make money, each one is calibration-gated so it cannot fool FORGE):

1. VOLATILITY FORECAST — HAR-RV style blend (Corsi 2009) of short / medium / long realized variance built from
   Garman–Klass range estimators (≈5–7× more efficient than close-to-close), multiplied by an INTRADAY SEASONALITY
   profile integrated over the contract's exact remaining window (crypto vol is strongly time-of-day dependent).
2. DISTRIBUTION — FILTERED HISTORICAL SIMULATION: the full history of vol-standardized, demeaned horizon returns
   z = r_h / (σ_t·√h) (σ_t causal) captures real fat tails and skew; a Gaussian-kernel-smoothed CDF table makes every
   lookup O(1). Falls back to a Student-t(ν=4) when history is short — never to a thin-tailed normal.
3. SETTLEMENT MECHANICS — CF Benchmarks RTI settles on a 60 s average: terminal variance shrinks (τ_eff = τ − ⅔·60 s).
4. STACKED CALIBRATION — online Bayesian logistic regression on
   [1, logit p_model, logit p_market, longshot(p_market<0.30)·logit p_market, √τ·(logit p_model − logit p_market)]
   with a Gaussian prior centred on "the market is right" (w_market = 1, all else 0). The model only earns weight if
   settled outcomes prove it carries information the market price lacks. Signals use the LOWER confidence bound.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

HORIZONS_MIN = (5, 10, 15, 30, 60, 120, 240, 480, 960, 1440)
SETTLE_AVG_S = 60.0
_EPS = 1e-6


def logit(p: float) -> float:
    p = min(max(p, _EPS), 1 - _EPS)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 60.0), -60.0)))


# ------------------------------------------------------------------ volatility
def garman_klass_var(o: np.ndarray, h: np.ndarray, lo: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Per-bar Garman–Klass variance estimate (log units)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        hl = np.log(h / lo)
        co = np.log(c / o)
        v = 0.5 * hl ** 2 - (2 * math.log(2) - 1) * co ** 2
    v[~np.isfinite(v)] = np.nan
    return np.clip(v, 0.0, None)


def ewma(x: np.ndarray, halflife: float) -> np.ndarray:
    a = 1 - math.exp(math.log(0.5) / max(halflife, 1e-9))
    out = np.empty_like(x)
    m = np.nan
    for i, v in enumerate(x):
        if np.isfinite(v):
            m = v if not np.isfinite(m) else (1 - a) * m + a * v
        out[i] = m
    return out


def seasonality_profile(ts: np.ndarray, var: np.ndarray, bins: int = 48) -> np.ndarray:
    """Relative variance by half-hour of day (mean 1.0), shrunk 50% toward flat for robustness."""
    slot = ((ts % 86400) // (86400 / bins)).astype(int)
    prof = np.ones(bins)
    ok = np.isfinite(var)
    tot = np.nanmean(var[ok]) if ok.any() else 0.0
    if tot <= 0:
        return prof
    for b in range(bins):
        sel = ok & (slot == b)
        if sel.sum() > 20:
            prof[b] = float(np.mean(var[sel]) / tot)
    prof = 0.5 * prof + 0.5
    return prof / prof.mean()


def window_seasonality(profile: np.ndarray, start_ts: float, minutes: float) -> float:
    """Average seasonal variance multiplier over [start, start+minutes]."""
    bins = len(profile)
    step = 86400 / bins
    n = max(1, int(math.ceil(minutes * 60 / step)))
    idx = [int(((start_ts + k * step) % 86400) // step) for k in range(n)]
    return float(np.mean(profile[idx]))


# ------------------------------------------------------------------ distribution
@dataclass
class HorizonCDF:
    grid: np.ndarray            # standardized thresholds
    sf: np.ndarray              # P(Z > x) smoothed
    n: int


def build_cdf(z: np.ndarray, bw_frac: float = 0.15) -> HorizonCDF:
    z = z[np.isfinite(z)]
    z = z - np.mean(z)                                        # driftless: never bake in the sample's trend
    z = z / max(np.std(z), 1e-9)                              # unit variance: vol forecast carries the scale
    grid = np.linspace(-8, 8, 801)
    zs = np.sort(z)
    bw = bw_frac * 1.06 * len(zs) ** (-0.2) * 5               # smoothing ~ Silverman-scaled, gentle
    # kernel-smoothed survival via convolution of the empirical survival with a Gaussian kernel
    emp = 1.0 - np.searchsorted(zs, grid, side="right") / len(zs)
    k = np.exp(-0.5 * (np.linspace(-4, 4, 81) * bw / 0.1) ** 2) if bw > 0 else np.array([1.0])
    k = k / k.sum()
    sm = np.convolve(np.pad(emp, (40, 40), mode="edge"), k, mode="valid")[: len(grid)]
    return HorizonCDF(grid, np.clip(sm, 0.0, 1.0), len(zs))


def student_t_sf(x: float, nu: float = 4.0) -> float:
    """Survival of a unit-VARIANCE Student-t(4) (fat-tailed fallback when history is short).
    Closed form for ν=4: F(t) = ½ + ⅜·u·(1 − t²/(12(1+t²/4))), u = t/√(1+t²/4)."""
    t = x / math.sqrt((nu - 2) / nu)                          # rescale unit-variance x to standard t units
    q = 1 + t * t / 4
    cdf = 0.5 + 0.375 * (t / math.sqrt(q)) * (1 - t * t / (12 * q))
    return float(min(max(1.0 - cdf, 0.0), 1.0))


@dataclass
class UnderlyingModel:
    """Fitted per Coinbase product from its bar history (5m bars; refit periodically)."""
    product: str
    sigma_min_now: float                                       # HAR forecast, per √minute, before seasonality
    seasonality: np.ndarray
    sigma_min_lr: float = 0.0                                  # long-run (30 d) level the variance mean-reverts to
    mr_minutes: float = 720.0                                  # variance mean-reversion time constant
    cdfs: dict[int, HorizonCDF] = field(default_factory=dict)
    fitted_ts: float = 0.0
    n_bars: int = 0

    def horizon_cdf(self, minutes: float) -> HorizonCDF | None:
        if not self.cdfs:
            return None
        h = min(self.cdfs, key=lambda k: abs(math.log(k / max(minutes, 1.0))))
        return self.cdfs[h]

    def sigma_window(self, now_ts: float, minutes: float) -> float:
        """Average per-minute σ over the window: exponential mean reversion of variance toward the long-run level
        (GARCH/HAR term structure), times the intraday seasonality integrated over the exact window."""
        v_now, v_lr = self.sigma_min_now ** 2, (self.sigma_min_lr or self.sigma_min_now) ** 2
        x = max(minutes, 1e-6) / self.mr_minutes
        v = v_lr + (v_now - v_lr) * (1 - math.exp(-x)) / x
        return math.sqrt(max(v, 0.0) * window_seasonality(self.seasonality, now_ts, minutes))

    def prob_above(self, spot: float, strike: float, now_ts: float, minutes: float, averaging_s: float = SETTLE_AVG_S) -> float:
        t_eff = max(minutes - (2.0 / 3.0) * averaging_s / 60.0, 0.25)
        s = self.sigma_window(now_ts, minutes) * math.sqrt(t_eff)
        if s <= 0:
            return 1.0 if spot > strike else 0.0
        x = math.log(strike / spot) / s                       # standardized threshold
        cdf = self.horizon_cdf(minutes)
        if cdf is None or cdf.n < 500:
            return student_t_sf(x)
        return float(np.interp(x, cdf.grid, cdf.sf))

    def prob(self, spot: float, now_ts: float, minutes: float, strike_type: str, floor: float | None,
             cap: float | None) -> float | None:
        if strike_type == "greater" and floor:
            return self.prob_above(spot, floor, now_ts, minutes)
        if strike_type == "less" and cap:
            return 1.0 - self.prob_above(spot, cap, now_ts, minutes)
        if strike_type == "between" and floor and cap and cap > floor:
            return max(0.0, self.prob_above(spot, floor, now_ts, minutes) - self.prob_above(spot, cap, now_ts, minutes))
        return None


def fit_underlying(product: str, bars: dict[str, np.ndarray], bar_s: int = 300,
                   recent_1m: dict[str, np.ndarray] | None = None) -> UnderlyingModel | None:
    ts = np.asarray(bars["ts"], dtype=float)
    o, h, lo, c = (np.asarray(bars[k], dtype=float) for k in ("open", "high", "low", "close"))
    if len(c) < 600:
        return None
    gk = garman_klass_var(o, h, lo, c)                        # per bar
    # range estimators are biased low on discretely sampled (trade-built) bars → rescale by the asset's own long-run
    # close-to-close / GK variance ratio (unbiased on average, keeps GK's efficiency)
    cc = np.diff(np.log(c))
    ratio = float(np.nanvar(cc[np.isfinite(cc)]) / max(np.nanmean(gk[1:]), 1e-18))
    gk = gk * min(max(ratio, 0.5), 2.5)
    per_min = gk / (bar_s / 60.0)
    # causal σ_t for standardization: EWMA (half-life ~ 1 day of bars)
    sig_t = np.sqrt(ewma(per_min, halflife=86400 / bar_s))
    # HAR-RV forecast now: short (1h), medium (6h), long (24h) realized variance per minute
    def rv(bars_back: int) -> float:
        seg = per_min[-bars_back:]
        seg = seg[np.isfinite(seg)]
        return float(np.mean(seg)) if len(seg) else float("nan")
    short = rv(max(1, 3600 // bar_s))
    if recent_1m is not None and len(recent_1m.get("close", [])) >= 30:
        v1 = garman_klass_var(*(np.asarray(recent_1m[k], dtype=float) for k in ("open", "high", "low", "close")))
        v1 = v1[np.isfinite(v1)][-60:]
        if len(v1) >= 20:
            short = float(np.mean(v1))                         # 1-minute bars: sharper short-horizon estimate
    med, lng = rv(6 * 3600 // bar_s), rv(86400 // bar_s)
    parts = [(0.40, short), (0.35, med), (0.25, lng)]
    num = sum(w * v for w, v in parts if math.isfinite(v))
    den = sum(w for w, v in parts if math.isfinite(v))
    if den <= 0 or num <= 0:
        return None
    prof = seasonality_profile(ts, per_min)
    # de-seasonalize the forecast (seasonality re-applied over the contract window)
    now_slot = window_seasonality(prof, ts[-1] - 3600, 60)
    sigma_now = math.sqrt(num / den / max(now_slot, 0.25))
    lr = per_min[-30 * 86400 // bar_s:]
    lr = lr[np.isfinite(lr)]
    sigma_lr = math.sqrt(float(np.mean(lr))) if len(lr) else sigma_now
    m = UnderlyingModel(product, sigma_now, prof, sigma_min_lr=sigma_lr, n_bars=len(c))
    lc = np.log(c)
    for hm in HORIZONS_MIN:
        k = max(1, int(round(hm * 60 / bar_s)))
        if len(c) <= k + 300:
            continue
        r = lc[k:] - lc[:-k]
        s = sig_t[:-k] * math.sqrt(hm)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = r / s
        z = z[300:]                                            # EWMA warm-up
        z = z[np.isfinite(z)]
        if len(z) >= 500:
            m.cdfs[hm] = build_cdf(z)
    return m


# ------------------------------------------------------------------ stacked calibration (online Bayesian logistic)
FEATURES = ("bias", "model_minus_market", "market", "longshot_market", "disagree_sqrt_tau")
PRIOR_MEAN = np.array([0.0, 0.0, 1.0, 0.0, 0.0])               # prior belief: the market price is calibrated
PRIOR_SD = np.array([0.25, 0.30, 0.12, 0.15, 0.15])            # tight around "market"; data must earn model weight


def stack_features(p_model: float, p_market: float, minutes: float) -> np.ndarray:
    """Parameterized on the DISAGREEMENT (logit model − logit market) so prior uncertainty does not explode in the tails."""
    lm, lk = logit(p_model), logit(p_market)
    d = max(min(lm - lk, 6.0), -6.0)
    return np.array([1.0, d, lk, lk * (1.0 if p_market < 0.30 else 0.0),
                     math.sqrt(min(max(minutes, 1.0), 1440.0) / 60.0) * d / 4.0])


@dataclass
class StackedCalibrator:
    w: np.ndarray = field(default_factory=lambda: PRIOR_MEAN.copy())
    cov: np.ndarray = field(default_factory=lambda: np.diag(PRIOR_SD ** 2))
    n: int = 0

    def fit(self, X: np.ndarray, y: np.ndarray, iters: int = 25) -> None:
        """MAP logistic regression with Gaussian prior (Newton/IRLS) + Laplace posterior covariance."""
        P = np.diag(1.0 / PRIOR_SD ** 2)
        w = PRIOR_MEAN.copy()
        for _ in range(iters):
            z = np.clip(X @ w, -30, 30)
            p = 1.0 / (1.0 + np.exp(-z))
            g = X.T @ (p - y) + P @ (w - PRIOR_MEAN)
            H = (X * (p * (1 - p))[:, None]).T @ X + P
            step = np.linalg.solve(H, g)
            w = w - step
            if float(np.max(np.abs(step))) < 1e-8:
                break
        z = np.clip(X @ w, -30, 30)
        p = 1.0 / (1.0 + np.exp(-z))
        H = (X * (p * (1 - p))[:, None]).T @ X + P
        self.w, self.cov, self.n = w, np.linalg.inv(H), len(y)

    def predict(self, p_model: float, p_market: float, minutes: float) -> tuple[float, float, float]:
        """(p_stacked, p_lower, p_upper) — 90% band from the Laplace posterior (model-uncertainty aware)."""
        x = stack_features(p_model, p_market, minutes)
        mu = float(x @ self.w)
        sd = math.sqrt(max(float(x @ self.cov @ x), 0.0))
        return sigmoid(mu), sigmoid(mu - 1.645 * sd), sigmoid(mu + 1.645 * sd)

    def model_weight_share(self) -> float:
        """How much the stack trusts FORGE's model vs the market (0 = pure market)."""
        a, b = abs(self.w[1]) + abs(self.w[4]) / 4.0, abs(self.w[2])
        return a / max(a + b, 1e-9)


# ------------------------------------------------------------------ binary-contract sizing (for when the rail is funded)
def binary_kelly(p: float, price: float, fee: float) -> float:
    """Kelly fraction of bankroll for buying a $1 binary at `price` (+fee) with win probability p."""
    cost = price + fee
    if cost <= 0 or cost >= 1:
        return 0.0
    b = (1 - cost) / cost
    return max(0.0, (p * b - (1 - p)) / b)
