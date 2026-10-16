"""All thresholds in ONE file.

Retuning the desk is editing this file and nothing else. If a decision disagrees with you,
you disagree with a number here — not with an agent's prose, and not with a constant buried
in a code path.

Every value carries its provenance: `measured` (derived from Forge's own realized data),
`reference` (a shape borrowed from the reference desk, to be re-earned from our data), or
`provisional` (a starting guess that shadow mode must confirm before it gates money).

FOUNDER RULE this file enforces: inference spend must be recouped. A rung that cannot pay for
itself is not a rung — it is a leak. `MIN_VALUE_PER_JUDGE_USD` is that floor.
"""
from __future__ import annotations

# ------------------------------------------------------------------------------------------
# FUNNEL BUDGETS — the cost-ordered ladder. Each rung must kill harder than the one below it.
# Rung 0 costs nothing and touches no network; only survivors are worth a paid judgement.
# ------------------------------------------------------------------------------------------
FUNNEL = {
    # universe_size: how many candidates a rung may pass down. Zero-inference rungs are generous;
    # paid rungs are scarce, because a judgement that cannot be recouped is a salary nobody earned.
    "r0_free_arithmetic": {"max_pass": 60, "cost_usd": 0.0, "network": False},
    "r1_fact_kill": {"max_pass": 24, "cost_usd": 0.0, "network": True},   # ledger/on-chain facts, cheap reads
    "r2_structural": {"max_pass": 10, "cost_usd": 0.0, "network": True},   # identity/carry/basis checks
    "r3_judge": {"max_pass": 4, "cost_usd": 0.0, "network": False},        # typed judgement seats (officer's own call)
    "r4_pick": {"max_pass": 1, "cost_usd": 0.0, "network": False},         # one choice over survivors
}

# A paid judgement must be expected to earn at least this much, or the funnel refuses to spend it.
# This is the "inference must be recouped" floor, expressed per judgement.
MIN_VALUE_PER_JUDGE_USD = 0.0005          # ~$0.36/day if 720 judgements are spent; provisional

# ------------------------------------------------------------------------------------------
# STABLE / STRUCTURAL EDGES — the crown-jewel class. Measured from Forge's own realized data.
# ------------------------------------------------------------------------------------------
STABLE = {
    # stable_triangle: Coinbase converts USD<->USDC 1:1 FREE, so USDT-USD and USDT-USDC must imply
    # one USDT price. min_edge must clear both taker fees + a buffer. NEVER cut this to raise λ:
    # it is the only reason the edge wins 100% of the time.
    "triangle_min_edge_bp": 0.15,          # measured: engine uses 0.15bp hot / 0.20bp normal
    "triangle_min_edge_bp_normal": 0.20,
    "triangle_usdt_usd_taker": 0.00009999,  # measured from Forge fee KV
    "triangle_usdt_usdc_taker": 0.0000099990,
    "triangle_max_notional_usd": 500.0,     # measured: max observed round-trip notional
    "triangle_p90_notional_usd": 300.0,     # measured p90
    # stable_peg_mm: passive maker around an EMA fair. θ is the discount required before bidding.
    "peg_theta_bp": 0.5,                    # measured: engine value
    "peg_fair_halflife_s": 7200.0,          # measured: engine value (2h) — λ constraint under study
    "peg_max_inventory_usd": None,          # None => derive from regime cap (RATE-THEN-SCALE)
}

# ------------------------------------------------------------------------------------------
# EVENT / CROSS-VENUE (Phase 3 research gate). These are REFERENCE shapes, not earned constants:
# the reference desk used an 8% model-vs-market gap. Cross-venue structural gaps are a different
# quantity (a must-agree relationship), so the threshold starts tighter and shadow must confirm.
# ------------------------------------------------------------------------------------------
EVENT = {
    "xvenue_min_gap_cents": 1.5,            # provisional: Kalshi vs Polymarket, same question
    "xvenue_fee_cents_est": 0.7,            # Kalshi taker ~0.07*C*P(1-P) + Polymarket spread share
    "xvenue_min_liquidity_usd": 250.0,      # provisional: must absorb our ticket without moving it
    "xvenue_max_spread_cents": 3.0,
    "xvenue_min_seconds_to_close": 900,     # never enter a market resolving in <15 min (settlement risk)
    "xvenue_ambiguous_match": "SKIP",       # never guess a pairing, never average two unsure prices
    "model_vs_market_min_edge_cents": 8.0,  # reference desk's working threshold; provisional for us
    "kalshi_fee_coef": 0.07,                # fee ≈ 0.07 * C * P * (1-P)
    "max_open_events": 7,                   # reference desk cap; provisional
    "max_data_age_hours": 48.0,             # reference desk rule written after a drawdown; keep it
}

# ------------------------------------------------------------------------------------------
# SPOT / DIRECTIONAL — the class that has NOT earned capital. Measured: 145 closes, mu=-0.0012.
# ------------------------------------------------------------------------------------------
SPOT = {
    "min_p_positive": 0.80,                 # required before any capital
    "min_n_closed": 30,                     # measured: n<30 is promising, never proven
    "max_fee_to_edge_ratio": 0.35,          # fees must stay under 35% of gross edge
    "diagnostic_allowance_frac": 0.25,      # of concurrency, while proven < first rung
    "diagnostic_allowance_floor": 2,
    "min_edge_bp": 12.0,                    # provisional: below this, fees and slippage eat it
    "max_age_hours": 6.0,                   # a directional thesis older than this is stale
}

# ------------------------------------------------------------------------------------------
# EXITS — one dumb, unarguable rule beneath the risk governor. "A position you cannot measure
# is a position you do not hold."
# ------------------------------------------------------------------------------------------
EXIT = {
    "volume_death_ratio": 0.20,             # vol_recent / (vol_window/n_windows) below this => CLOSE
    "volume_death_window_s": 21600,         # 6h
    "volume_death_recent_s": 3600,          # last 1h
    "volume_death_close_within_s": 60,
    "unmeasurable_action": "CLOSE",         # no mark available => exit, never hold blind
    "mark_to_market_loss_cut": -0.02,       # real unrealized loss threshold (already deployed)
}

# ------------------------------------------------------------------------------------------
# JUDGEMENT QUALITY — when a typed answer may be trusted to move money.
# ------------------------------------------------------------------------------------------
JUDGE = {
    "noul_min_calibrated_n": 30,            # below this the calibration is provisional
    "noul_provisional_size_factor": 0.40,   # provisional judgement => cut the ticket, do not skip
    "choice_min_confidence": 0.55,          # flat over N options means no favourite
    "pick_min_worth": 0.60,                 # absolute gate: is today a day at all
    "insufficient_data_size_factor": 0.40,  # "dark" cuts the ticket; it never means "fine"
    "no_social_size_factor": 0.60,          # missing evidence => smaller, flagged, not skipped
    "max_options_per_choice": 255,
    "never_run_pick_on_one_survivor": True,  # a choice over one option returns it with false confidence
}

# ------------------------------------------------------------------------------------------
# BENCH — a rejected candidate stays rejected, for a length set by WHY it failed.
# Benching on the token instead of the check re-pays for the same dead thing every cycle.
# ------------------------------------------------------------------------------------------
BENCH_MINUTES = {
    # structural facts that will not change while this instrument exists
    "identity_absent": 100_000,
    "not_executable": 100_000,
    "rail_unkeyed": 100_000,
    "fee_negative": 100_000,
    "settlement_basis_mismatch": 1_440,
    # slow to change
    "insufficient_evidence": 360,
    "net_edge_nonpositive": 25,      # the engine's own net edge was <= 0: re-check as prices move
    "provisional_calibration": 180,
    "concentration": 90,
    "liquidity_too_thin": 90,
    # can change inside the hour — keep short or we miss the setup maturing
    "momentum_spent": 25,
    "volume_too_low": 25,
    "spread_too_wide": 25,
    "too_young": 20,
    "stale_data": 30,
    "market_closed": 120,                   # equities: re-check when the session can act on it
}
DEFAULT_BENCH_MINUTES = 45

# ------------------------------------------------------------------------------------------
# MILESTONE LADDER (Constitution C3 §9). Never redefined downward.
# ------------------------------------------------------------------------------------------
MILESTONES = (0.25, 0.50, 0.75, 1.00)
MILESTONE_STEP_BEYOND = 0.25               # after $1.00/h: every further $0.25/h

# ------------------------------------------------------------------------------------------
# INFERENCE ECONOMY — "their salary is their inference; if it cannot pay for itself, they lose
# the job." Measured against realized income, per role, per window.
# ------------------------------------------------------------------------------------------
SALARY = {
    "window_h": 24.0,
    "min_income_share": 0.0,                # 0 during PAPER proof: no role is fired before the
                                            # book can pay anyone. Rises to a real floor at LIVE.
    "min_income_share_live": 1.0,           # at LIVE: attributed income must cover attributed cost
    "warning_value_per_usd": 0.5,           # below $0.50 of income per $1 of inference => WARN
    "critical_value_per_usd": 0.15,         # below $0.15 => CRITICAL: role loses its wake budget
    "crew_247": ("prediction", "execution", "scout", "doctor", "governor", "treasury", "ops"),
    "off_peak_only": ("alpha_inventor", "adversary", "critic", "intelligence", "rail_hunter", "architect"),
}
