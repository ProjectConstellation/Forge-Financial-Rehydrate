"""Statistics for evidence-before-confidence (DOSSIER §2.4, §30; OP-004 90% rule).

- P(edge > 0): Bayesian posterior on mean net return per trade with a skeptical (zero-centered)
  prior — shrinks small samples toward "no edge".
- Deflated Sharpe Ratio (Bailey & López de Prado): probability the observed Sharpe beats the
  expected maximum Sharpe of N independent trials → multiple-testing awareness.
- Power analysis: trades needed to detect an edge of a given size (pre-registered target).
Pure numpy/math (no scipy dependency).
"""

from __future__ import annotations

import math

import numpy as np

EULER = 0.5772156649015329


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Acklam's inverse normal CDF approximation (|rel err| < 1.2e-9)."""
    if not 0.0 < p < 1.0:
        return math.copysign(float("inf"), p - 0.5)
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02, 1.383577518672690e02,
         -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02, 6.680131188771972e01,
         -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00, -2.549732539343734e00,
         4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00]
    lo, hi = 0.02425, 1 - 0.02425
    if p < lo:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > hi:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _betacf(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(c) > 1e-300 else 1e300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c if abs(c) > 1e-300 else 1e300
        de = d * c
        h *= de
        if abs(de - 1.0) < 3e-12:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    bt = math.exp(lbt)
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t: float, df: float) -> float:
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    tail = 0.5 * betainc(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def edge_posterior(returns: np.ndarray, prior_trades: float = 10.0, prior_scale: float | None = None) -> dict[str, float]:
    """Posterior on mean per-trade net return μ with a skeptical prior centered at 0.

    Prior: μ ~ N(0, σ²/κ0) with κ0 = `prior_trades` pseudo-trades of zero edge.
    Returns P(μ>0), posterior mean, and a 90% lower bound.
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 2:
        return {"n": n, "p_positive": 0.0, "post_mean": 0.0, "lb90": -1.0, "mean": float(r.mean()) if n else 0.0,
                "std": 0.0}
    m, s = float(r.mean()), float(r.std(ddof=1))
    s = max(s, prior_scale or 1e-6, 1e-6)
    k0 = prior_trades
    post_mean = n * m / (n + k0)
    post_se = s / math.sqrt(n + k0)
    df = max(n - 1, 1)
    tstat = post_mean / post_se
    p = t_cdf(tstat, df)
    # 90% one-sided lower bound
    tq = _t_ppf(0.90, df)
    return {"n": n, "p_positive": p, "post_mean": post_mean, "lb90": post_mean - tq * post_se, "mean": m, "std": s}


def _t_ppf(p: float, df: float) -> float:
    lo, hi = -50.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sharpe(returns: np.ndarray) -> float:
    r = np.asarray(returns, dtype=float)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1))


def expected_max_sharpe(n_trials: int, sr_var: float) -> float:
    """E[max SR] across N independent zero-skill trials (per-trade Sharpe units)."""
    if n_trials <= 1:
        return 0.0
    return math.sqrt(sr_var) * ((1 - EULER) * norm_ppf(1 - 1 / n_trials) + EULER * norm_ppf(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(returns: np.ndarray, n_trials: int, sr_var: float | None = None) -> float:
    """Probability the true Sharpe exceeds the best Sharpe expected from luck across n_trials."""
    r = np.asarray(returns, dtype=float)
    n = len(r)
    if n < 5:
        return 0.0
    sr = sharpe(r)
    sk = float(((r - r.mean()) ** 3).mean() / (r.std() ** 3 + 1e-18))
    ku = float(((r - r.mean()) ** 4).mean() / (r.std() ** 4 + 1e-18))
    sr0 = expected_max_sharpe(n_trials, sr_var if sr_var is not None else 1.0 / n)
    denom = math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr * sr))
    return norm_cdf((sr - sr0) * math.sqrt(n - 1) / denom)


def trades_needed(edge: float, std: float, p_target: float = 0.90, power: float = 0.8) -> int:
    """Pre-registered sample size to detect mean `edge` with sd `std` at one-sided confidence p_target."""
    if edge <= 0 or std <= 0:
        return 10 ** 6
    z = norm_ppf(p_target) + norm_ppf(power)
    return int(math.ceil((z * std / edge) ** 2))


def max_drawdown(equity: np.ndarray) -> float:
    e = np.asarray(equity, dtype=float)
    if len(e) == 0:
        return 0.0
    peak = np.maximum.accumulate(e)
    return float(((e - peak) / peak).min())
