"""Allocator gates from the 2026-10-07 strategic answers (P0.2, P0.3, P0.7, P1 §10).

Pure functions — deterministic, unit-tested, no I/O:
- Edge Coverage Ratio (ECR): cost-survival gate (expected GROSS edge / expected all-in costs).
- Live Retention haircut (LRR prior H): backtest-derived expectations are shrunk until forward evidence earns trust.
- Conditional exposure scaling: market breadth tiers, volatility percentile gate, treasury high-water-mark drawdown states.
- Risk-at-stop sizing cap: per-position and aggregate open risk bounded as a fraction of equity.

Policy (OP-012/"paper explores, live exploits"): LIVE enforces every gate; the PAPER book logs the would-be verdict and still
trades ECR ≥ 1.5 candidates so forward evidence keeps accruing (otherwise the haircut could never be earned back).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------- ECR
ECR_REJECT = 1.5          # < 1.5 → reject everywhere
ECR_LIVE = 2.0            # 1.5–2.0 → shadow/paper only; ≥ 2.0 small-live eligible
ECR_STRONG = 3.0
ECR_CONCENTRATE = 4.0


def edge_coverage_ratio(p: float, win_net: float, loss_net: float, cost_win: float, cost_loss: float,
                        uncertainty: float = 0.0) -> float:
    """ECR = E[gross return] / E[fees + spread + slippage + execution uncertainty].
    `win_net`/`loss_net` are net-of-cost outcomes (loss_net < 0); costs are round-trip fractions for each branch."""
    g_win, g_loss = win_net + cost_win, loss_net + cost_loss
    e_gross = p * g_win + (1 - p) * g_loss
    e_cost = p * cost_win + (1 - p) * cost_loss + max(uncertainty, 0.0)
    if e_cost <= 0:
        return float("inf") if e_gross > 0 else 0.0
    return e_gross / e_cost


def ecr_tier(ecr: float) -> str:
    if ecr < ECR_REJECT:
        return "REJECT"
    if ecr < ECR_LIVE:
        return "SHADOW_ONLY"
    if ecr < ECR_STRONG:
        return "SMALL_LIVE"
    if ecr < ECR_CONCENTRATE:
        return "STRONG"
    return "CONCENTRATION_CANDIDATE"


# ---------------------------------------------------------------- Live Retention Ratio / backtest haircut
H_PRIOR = 0.25            # heavily searched families: keep 25% of backtest edge until forward evidence earns more
H_PRIOR_N = 30.0          # prior strength (pseudo-trades)


def retention_haircut(backtest_mean: float, forward_mean: float | None, forward_n: int,
                      h_prior: float = H_PRIOR, n0: float = H_PRIOR_N) -> float:
    """Bayesian-shrunk live retention ratio H ∈ [0, 1]: (n0·H0 + n·clip(fwd/bt, 0, 1)) / (n0 + n)."""
    if forward_n <= 0 or forward_mean is None or backtest_mean <= 0:
        return h_prior
    ratio = min(max(forward_mean / backtest_mean, 0.0), 1.0)
    return (n0 * h_prior + forward_n * ratio) / (n0 + forward_n)


def haircut_probability(p: float, win: float, loss: float, h: float) -> float:
    """Shrink p toward break-even so that expected value scales exactly by h (EV is linear in p, EV(p_be) = 0).
    Kelly/velocity/ECR computed from the result inherit the haircut consistently."""
    if win <= 0 or loss >= 0:
        return p
    p_be = -loss / (win - loss)
    return min(max(p_be + h * (p - p_be), 0.0), 1.0)


# ---------------------------------------------------------------- conditional exposure scaling (answers §10)
TREND_FAMILIES = {"momentum", "breakout", "trend_pullback", "rotation", "volatility", "beta", "trend"}
SPECIALIST_FAMILIES = {"liquidity_provision", "panic", "panic_absorb", "mean_reversion"}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * min(max(t, 0.0), 1.0)


def breadth_multiplier(breadth: float | None, family: str) -> float:
    """Trend exposure by market breadth (fraction of universe in uptrend). Panic/reversion specialists exempt."""
    if breadth is None or breadth != breadth or family in SPECIALIST_FAMILIES:
        return 1.0
    if breadth >= 0.60:
        return 1.0
    if breadth >= 0.40:
        return _lerp(0.50, 0.75, (breadth - 0.40) / 0.20)
    if breadth >= 0.30:
        return _lerp(0.25, 0.50, (breadth - 0.30) / 0.10)
    return _lerp(0.0, 0.25, breadth / 0.30)


def volatility_multiplier(vol_pct: float | None, specialist: bool) -> float:
    """Realized-volatility percentile gate: > p90 halve generic notional; > p97 generic strategies stand aside."""
    if vol_pct is None or vol_pct != vol_pct or specialist:
        return 1.0
    if vol_pct > 0.97:
        return 0.0
    if vol_pct > 0.90:
        return 0.5
    return 1.0


@dataclass(frozen=True)
class DrawdownState:
    state: str            # NORMAL | DD5 | DD10 | DD15
    drawdown: float       # ≤ 0, fraction from high-water mark
    multiplier: float     # new-risk multiplier
    generic_live_paused: bool
    postmortem_required: bool


def drawdown_state(equity: float, high_water: float) -> DrawdownState:
    dd = equity / high_water - 1 if high_water > 0 else 0.0
    if dd <= -0.15:
        return DrawdownState("DD15", dd, 0.25, True, True)
    if dd <= -0.10:
        return DrawdownState("DD10", dd, 0.50, False, True)
    if dd <= -0.05:
        return DrawdownState("DD5", dd, 0.75, False, False)
    return DrawdownState("NORMAL", dd, 1.0, False, False)


# ---------------------------------------------------------------- risk-at-stop (answers §9)
@dataclass(frozen=True)
class RiskCap:
    max_notional: float
    risk_fraction: float
    open_risk_usd: float
    budget_usd: float
    explanation: str = field(default="")


def risk_at_stop_cap(equity: float, stop_frac: float, kelly_full: float, open_risk_usd: float,
                     per_pos: float = 0.05, aggregate: float = 0.10, calibration: float = 1.0,
                     robustness: float = 1.0, regime_cap: float = 1.0) -> RiskCap:
    """riskFraction = min(RegimeCap, 0.25·Kelly, per_pos·Calibration·Robustness); notional = equity·risk / stop distance,
    bounded by the remaining aggregate open-risk budget."""
    rf = min(regime_cap, 0.25 * kelly_full if kelly_full > 0 else per_pos * 0.3,
             per_pos * min(max(calibration, 0.0), 1.0) * min(max(robustness, 0.0), 1.0))
    budget = max(0.0, aggregate * equity - open_risk_usd)
    risk_usd = min(equity * rf, budget)
    cap = risk_usd / max(stop_frac, 1e-4)
    why = (f"risk-at-stop {rf:.2%}×${equity:.2f} (open risk ${open_risk_usd:.2f}/{aggregate:.0%} budget) "
           f"÷ stop {stop_frac:.2%} → ≤ ${cap:.2f}")
    return RiskCap(cap, rf, open_risk_usd, budget, why)


def correlation_penalty(n: int, rho: float) -> float:
    """1 / (1 + (n−1)·ρ): effective diversification of n similarly exposed positions."""
    return 1.0 / (1.0 + max(n - 1, 0) * max(rho, 0.0))
