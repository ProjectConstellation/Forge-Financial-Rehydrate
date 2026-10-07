"""Growth-optimal, uncertainty-aware position sizing (DOSSIER §21.3, EDGE PLAN E4).

final_fraction = min( kelly(p_cal, W, L) × kelly_mult × evidence_shrink × state_mult × breaker_mult,
                      genome.max_fraction, regime.max_position_fraction )
- p_cal is the *calibrated* win probability; W/L are net-of-cost win/loss returns.
- evidence_shrink grows with sample size (few trades → small bets): n / (n + 30).
- CHALLENGER strategies trade at reduced size until they displace incumbents.
"""

from __future__ import annotations

from dataclasses import dataclass


def kelly_fraction(p: float, win: float, loss: float) -> float:
    """Binary-outcome Kelly for returns win>0, loss<0 (fractions of stake). Clipped to [0, 1]."""
    if win <= 0 or loss >= 0:
        return 0.0
    f = (p * win - (1 - p) * (-loss)) / (win * -loss)
    return max(0.0, min(1.0, f))


@dataclass(frozen=True)
class SizeDecision:
    fraction: float
    notional_usd: float
    kelly_raw: float
    shrink: float
    explanation: str


STATE_MULT = {"PRODUCTION": 1.0, "CHALLENGER": 0.35}


def size_position(p_cal: float, win: float, loss: float, n_evidence: int, kelly_mult: float, genome_max: float,
                  policy_max: float, deployable_usd: float, state: str, breaker_mult: float = 1.0,
                  velocity_score: float = 0.5) -> SizeDecision:
    k = kelly_fraction(p_cal, win, loss)
    shrink = n_evidence / (n_evidence + 30.0)
    vel = 0.75 + 0.5 * min(max(velocity_score, 0.0), 1.0)         # OP-008: faster recycling earns more capital
    f = k * kelly_mult * shrink * STATE_MULT.get(state, 0.0) * breaker_mult * vel
    f = min(f, genome_max, policy_max)
    notional = max(0.0, f * deployable_usd)
    why = (f"Kelly={k:.3f} (p={p_cal:.2f}, W={win:+.2%}, L={loss:+.2%}) × {kelly_mult:.2f} × evidence {shrink:.2f} "
           f"× {state} {STATE_MULT.get(state, 0):.2f} × velocity {vel:.2f} → {f:.3f} of ${deployable_usd:.2f}")
    return SizeDecision(f, notional, k, shrink, why)
