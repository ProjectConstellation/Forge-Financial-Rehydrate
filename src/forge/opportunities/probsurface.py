"""Implied probability surface, cross-rail lead/lag, edge half-life (Hermes dossier §9–§11; deterministic, tested).

1. SURFACE — a ladder of "≥ K" contracts on one underlying/expiry IS a market-implied survival curve P(S_T ≥ K). We fit the
   best NON-INCREASING curve to the quoted mids (weighted isotonic regression, pool-adjacent-violators, weights 1/spread²).
   A strike whose executable quote disagrees with the smoothed surface of its neighbours is stale or mispriced — a
   RELATIVE-VALUE edge that does not need any directional view (SURFACE_RV signals). The residual between FORGE's own
   model and the smoothed market surface (SURFACE_RESIDUAL) is stored for research.
2. LEAD/LAG — per underlying, Coinbase mid vs the Kalshi ladder's implied median (strike where the surface crosses 0.5)
   sampled every fast-lane scan. Lagged correlations corr(Δspot_t, Δimplied_{t+k}) estimate how long Kalshi takes to
   reprice after Coinbase moves (LeadScore with n and t-stat; trusted only when significant).
3. EDGE HALF-LIFE — every taker signal is re-measured on later scans; t50 = time until the remaining edge falls below half
   of the first sighting. Short t50 → cross immediately or never; long t50 → patient maker quoting is viable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def isotonic_decreasing(y: list[float], w: list[float]) -> list[float]:
    """Weighted least-squares fit constrained non-increasing in index order (PAV on the negated sequence)."""
    blocks: list[list[float]] = []                 # [value, weight, count]
    for yi, wi in zip(y, w, strict=True):
        blocks.append([-yi, max(wi, 1e-12), 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, c2 = blocks.pop()
            v1, w1, c1 = blocks.pop()
            blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, c1 + c2])
    out: list[float] = []
    for v, _, c in blocks:
        out += [-v] * int(c)
    return out


@dataclass(frozen=True)
class SurfacePoint:
    ticker: str
    strike: float
    bid: float | None
    ask: float | None
    mid: float
    fitted: float
    residual: float          # mid − fitted


def fit_surface(points: list[tuple[str, float, float | None, float | None]]) -> list[SurfacePoint]:
    """points = [(ticker, strike, yes_bid, yes_ask)] for 'greater' contracts of ONE event. Needs ≥ 3 two-sided quotes."""
    q = sorted((p for p in points if p[2] is not None and p[3] is not None and p[3] > p[2]), key=lambda p: p[1])
    if len(q) < 3:
        return []
    mids = [0.5 * (b + a) for _, _, b, a in q]                         # type: ignore[operator]
    w = [1.0 / max((a - b) ** 2, 1e-4) for _, _, b, a in q]            # type: ignore[operator]
    fit = isotonic_decreasing(mids, w)
    return [SurfacePoint(t, k, b, a, m, f, m - f) for (t, k, b, a), m, f in zip(q, mids, fit, strict=True)]


def implied_median(surface: list[SurfacePoint]) -> float | None:
    """Strike where the fitted survival curve crosses 0.5 (linear interpolation)."""
    for a, b in zip(surface[:-1], surface[1:], strict=False):
        if a.fitted >= 0.5 >= b.fitted and a.fitted > b.fitted:
            return a.strike + (b.strike - a.strike) * (a.fitted - 0.5) / (a.fitted - b.fitted)
    return None


def surface_rv_candidates(surface: list[SurfacePoint], min_gap: float = 0.03) -> list[tuple[str, str, float, float]]:
    """(ticker, side, ask, fair_from_neighbours) where the executable ask is below the neighbour-implied value.
    The fitted value is recomputed WITHOUT the strike itself (leave-one-out) so a stale quote cannot defend itself."""
    out = []
    for i, p in enumerate(surface):
        others = surface[:i] + surface[i + 1:]
        if len(others) < 2:
            continue
        lo = next((o for o in reversed(others) if o.strike < p.strike), None)
        hi = next((o for o in others if o.strike > p.strike), None)
        if lo is None or hi is None:
            continue
        # neighbour-implied value: monotone interpolation between the fitted neighbours
        t = (p.strike - lo.strike) / max(hi.strike - lo.strike, 1e-12)
        fair = lo.fitted + (hi.fitted - lo.fitted) * t
        if p.ask is not None and fair - p.ask >= min_gap:
            out.append((p.ticker, "yes", p.ask, fair))
        if p.bid is not None and p.bid - fair >= min_gap:
            out.append((p.ticker, "no", 1.0 - p.bid, 1.0 - fair))
    return out


# ------------------------------------------------------------------ lead/lag
@dataclass(frozen=True)
class LeadScore:
    lag_steps: int
    corr: float
    t_stat: float
    n: int
    beta: float


def lead_lag(spot: list[float], implied: list[float], max_lag: int = 8) -> list[LeadScore]:
    """corr(Δlog spot_t, Δlog implied_{t+k}) for k = 0..max_lag on aligned samples (equal spacing)."""
    if len(spot) != len(implied) or len(spot) < 20:
        return []
    ds = [math.log(b / a) for a, b in zip(spot[:-1], spot[1:], strict=True)]
    di = [math.log(b / a) for a, b in zip(implied[:-1], implied[1:], strict=True)]
    out = []
    for k in range(0, max_lag + 1):
        x, y = ds[: len(ds) - k] if k else ds, di[k:]
        n = len(x)
        if n < 15:
            break
        mx, my = sum(x) / n, sum(y) / n
        sxx = sum((v - mx) ** 2 for v in x)
        syy = sum((v - my) ** 2 for v in y)
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
        if sxx <= 0 or syy <= 0:
            out.append(LeadScore(k, 0.0, 0.0, n, 0.0))
            continue
        r = sxy / math.sqrt(sxx * syy)
        t = r * math.sqrt(max(n - 2, 1) / max(1 - r * r, 1e-12))
        out.append(LeadScore(k, r, t, n, sxy / sxx))
    return out


def best_lead(scores: list[LeadScore], t_min: float = 3.0) -> LeadScore | None:
    """Strongest significant lag ≥ 1 (Coinbase leads Kalshi by k steps); None if no stable lead exists."""
    sig = [s for s in scores if s.lag_steps >= 1 and s.t_stat >= t_min]
    return max(sig, key=lambda s: s.t_stat) if sig else None


# ------------------------------------------------------------------ edge half-life
def half_life(observations: list[tuple[float, float]]) -> float | None:
    """observations = [(seconds since first sighting, remaining edge)], first is (0, edge0>0).
    Returns the first time the edge fell to ≤ 50% of edge0 (linear interpolation), or None if it never did."""
    if not observations or observations[0][1] <= 0:
        return None
    e0 = observations[0][1]
    for (t1, e1), (t2, e2) in zip(observations[:-1], observations[1:], strict=False):
        if e2 <= 0.5 * e0:
            if e1 == e2:
                return t2
            return t1 + (t2 - t1) * (e1 - 0.5 * e0) / (e1 - e2)
    return None
