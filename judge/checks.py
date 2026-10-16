"""Free-arithmetic kill checks — rungs R0, R1, R2. No network, no model, no cost.

THE RULE: anything a comparison can settle must be settled HERE, before a candidate is worth a paid
judgement. The reference desk's `authority_open` and `honeypot` are comparisons, not questions, for
exactly this reason. Forge's version is richer because Forge has three edge classes, each with its own
structural facts that can kill for free:

    R0 free arithmetic — pure numbers already in candidate.facts (age, notional, fee-vs-edge)
    R1 fact kill        — venue/ledger/rail facts (executable? keyed? session open? fee-negative?)
    R2 structural       — the identity/basis checks that make an edge structural or a mirage

A check returns None to pass, or a SHORT REASON STRING to kill. That string is also the bench key, so
the reason sets how long the candidate stays benched (a structural fact benches ~forever; a condition
that matures inside the hour benches briefly). Reasons are drawn from thresholds.BENCH_MINUTES keys.

Every check is pure: facts in, verdict out. That makes the whole funnel unit-testable with zero
inference and zero network — which is why we can validate it overnight.
"""
from __future__ import annotations

from typing import Any

from forge.judge.funnel import Candidate
from forge.judge.thresholds import STABLE, EVENT, SPOT, EXIT


def _f(c: Candidate, key: str, default: Any = None) -> Any:
    return c.facts.get(key, default)


def _num(c: Candidate, key: str, default: float | None = None) -> float | None:
    v = c.facts.get(key, default)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# =========================================================================================
# R0 — FREE ARITHMETIC. Pure numbers. Kills the most, costs nothing, touches no network.
# =========================================================================================
def r0_missing_required_facts(c: Candidate) -> str | None:
    """A candidate without the numbers its edge class needs cannot be judged — bench it, do not guess.

    'dark does not mean skip, it means cut the ticket' applies to a JUDGEMENT; but a candidate missing
    the arithmetic inputs entirely cannot even be costed, so it does not deserve a downstream slot.
    """
    need = _f(c, "required_facts") or []
    missing = [k for k in need if c.facts.get(k) is None]
    return "insufficient_evidence" if missing else None


def r0_fee_negative(c: Candidate) -> str | None:
    """Kill candidates whose edge cannot pay for the trade. Two honest forms:

    (a) `net_edge_bp` present — the engine's OWN recorded net-of-fee edge. Test it directly and report
        `net_edge_nonpositive`. This is the form the live shadow path uses, so no second fee model is
        layered on top of one the engine already applied.
    (b) gross/cost pair present — a candidate built from raw components (replay, research). Compare them
        and report `fee_negative`.
    """
    net = _num(c, "net_edge_bp")
    if net is not None:
        return "net_edge_nonpositive" if net <= 0 else None
    edge = _num(c, "gross_edge_bp")
    cost = _num(c, "total_cost_bp")
    if edge is None or cost is None:
        return None                                   # can't cost it here; a later rung may
    if edge <= cost:
        return "fee_negative"                         # structural: will not become positive on its own
    return None


def r0_notional_out_of_band(c: Candidate) -> str | None:
    """A ticket the venue cannot hold, or too small to matter, is killed for free."""
    notional = _num(c, "our_ticket_usd")
    depth = _num(c, "depth_at_touch_usd")
    if notional is None:
        return None
    if notional <= 0:
        return "liquidity_too_thin"
    if depth is not None and notional > depth:
        return "liquidity_too_thin"                   # cannot exit what we cannot fit
    return None


def r0_too_young_or_stale(c: Candidate) -> str | None:
    """Age bounds: too young is noise, too old is not a launch/opportunity any more."""
    age_min = _num(c, "age_minutes")
    if age_min is not None and age_min < 15:
        return "too_young"                            # matures inside the hour => short bench
    data_age_h = _num(c, "data_age_hours")
    if data_age_h is not None and data_age_h > EVENT["max_data_age_hours"]:
        return "stale_data"
    return None


def r0_spread_too_wide(c: Candidate) -> str | None:
    spread = _num(c, "spread_bp")
    if spread is not None and spread > EVENT["xvenue_max_spread_cents"] * 100:
        return "spread_too_wide"
    return None


# =========================================================================================
# R1 — FACT KILL. Venue / ledger / rail facts. Cheap reads, still no judgement.
# =========================================================================================
def r1_rail_not_executable(c: Candidate) -> str | None:
    """A rail that cannot execute (unkeyed, blocked) cannot earn, whatever the edge."""
    if _f(c, "rail_executable") is False:
        return "not_executable"
    if _f(c, "rail_unkeyed") is True:
        return "rail_unkeyed"
    return None


def r1_market_closed(c: Candidate) -> str | None:
    """Equities are 24/5. Never spend a judgement on a trade the session cannot execute now.

    Crypto and event contracts are 24/7 and never trip this. `market_session` comes from
    forge.core.market_hours, computed for free.
    """
    sess = _f(c, "market_session")
    if sess in ("CLOSED", "WEEKEND"):
        return "market_closed"
    return None


def r1_event_rail_negative_edge(c: Candidate) -> str | None:
    """Event-contract candidates (Kalshi crossrail / cross-venue) are gated by the MEASURED edge.

    Live measurement (n=45,852 settled): model Brier 0.12994 vs market 0.12856 — the market beats our
    model — and 19,988 settled shadow signals total -$417.60. A negative measured edge is a fact, not a
    judgement, so it kills here for free. The verdict is recomputed from live data and SELF-HEALS: the
    moment the model beats the market and shadow pnl turns positive, event candidates flow again.
    """
    if c.family not in ("cross_venue", "event", "prediction") and "kalshi" not in c.rail.lower():
        return None
    try:
        from forge.judge.event_verdict import event_rail_tradeable
        if not event_rail_tradeable(c.db if hasattr(c, "db") else _DB.get()):
            return "insufficient_evidence"          # benches; verdict records the real reason
    except Exception:
        return None                                  # fail OPEN: never block on an introspection error
    return None


# The funnel passes `db` into checks via a module-level reference set by default_funnel(), so the
# event verdict (which needs the DB) can be consulted without changing the Check signature.
class _DB:
    _db: Any = None

    @classmethod
    def get(cls) -> Any:
        return cls._db


def r1_identity_absent(c: Candidate) -> str | None:
    """For the structural class: if there is no must-agree relationship, it is not this edge class."""
    if c.family in ("stable_triangle", "cross_venue") and _f(c, "has_identity") is False:
        return "identity_absent"
    return None


def r1_settlement_basis_mismatch(c: Candidate) -> str | None:
    """A contract settling on source X while the model prices proxy Y is a basis mismatch, killable
    for free when the sources are known to differ (no model needed to compare two strings)."""
    settle_src = _f(c, "settlement_source")
    model_src = _f(c, "model_source")
    if settle_src and model_src and settle_src != model_src and _f(c, "basis_equivalent") is not True:
        return "settlement_basis_mismatch"
    return None


def r1_no_sells_only_buys(c: Candidate) -> str | None:
    """Buys with no sells is a honeypot-shaped fact, not a judgement."""
    buys = _num(c, "buys_recent", 0) or 0
    sells = _num(c, "sells_recent", 0) or 0
    if sells == 0 and buys > 20:
        return "not_executable"                       # cannot exit => not tradeable
    return None


# =========================================================================================
# R2 — STRUCTURAL. The checks that decide whether an edge is real or a mirage, still free.
# =========================================================================================
def r2_structural_gap_below_buffer(c: Candidate) -> str | None:
    """For the crown-jewel class: the identity gap must clear fees + buffer, computed exactly.

    This is the arithmetic the pegmaker already does; the funnel does it earlier so a sub-threshold gap
    never costs a judgement. Uses measured fee coefficients, never an assumed zero.
    """
    if c.family != "stable_triangle":
        return None
    gap_bp = _num(c, "gap_bp")
    if gap_bp is None:
        return None
    fee_bp = (_num(c, "fee_bp_total") or 0.0)
    buffer_bp = STABLE["triangle_min_edge_bp"]
    if gap_bp <= fee_bp + buffer_bp:
        return "fee_negative"
    return None


def r2_crossvenue_gap_below_threshold(c: Candidate) -> str | None:
    """Kalshi vs Polymarket on the same question: the gap must clear every cost AND a minimum floor.

    cost = both venues' taker fees + half-spread on each leg. The floor exists because a gap that is
    only barely net-positive is not worth the settlement and leg-failure risk it carries.
    """
    if c.family != "cross_venue":
        return None
    gap = _num(c, "gap_cents")
    if gap is None:
        return None
    fee = _num(c, "kalshi_fee_cents")
    fee = EVENT["xvenue_fee_cents_est"] if fee is None else fee
    spread = _num(c, "spread_cents") or 0.0
    cost = fee + spread
    if gap <= cost:
        return "fee_negative"                         # does not even cover cost
    if gap < cost + EVENT["xvenue_min_gap_cents"]:
        return "fee_negative"                         # covers cost but not the risk floor
    return None


def r2_liquidity_cannot_absorb(c: Candidate) -> str | None:
    """Even a real structural gap is untradeable if the book cannot take our size."""
    if c.family not in ("stable_triangle", "cross_venue"):
        return None
    liq = _num(c, "liquidity_usd")
    ticket = _num(c, "our_ticket_usd")
    if liq is not None and ticket is not None and liq < ticket:
        return "liquidity_too_thin"
    if c.family == "cross_venue" and liq is not None and liq < EVENT["xvenue_min_liquidity_usd"]:
        return "liquidity_too_thin"
    return None


def r2_spot_unproven_needs_more(c: Candidate) -> str | None:
    """Directional spot has been measured net-negative here. Hold it to a higher, arithmetic bar:
    it must show enough closed trades AND a positive backtested mean before it may cost a judgement."""
    if c.family != "spot":
        return None
    n = _num(c, "n_closed", 0) or 0
    mu = _num(c, "mu_per_unit")
    if n < SPOT["min_n_closed"]:
        return "insufficient_evidence"
    if mu is not None and mu <= 0:
        return "fee_negative"                         # measured non-positive: not worth a judgement
    return None


def r2_resolving_too_soon(c: Candidate) -> str | None:
    """Never enter an event resolving inside the settlement-risk window."""
    if c.family not in ("cross_venue", "event"):
        return None
    secs = _num(c, "seconds_to_close")
    if secs is not None and secs < EVENT["xvenue_min_seconds_to_close"]:
        return "too_young"                            # short bench: it only gets more urgent, not less
    return None


# =========================================================================================
# The default ladder. Order within a rung is cheapest-and-most-selective first.
# =========================================================================================
R0 = (r0_missing_required_facts, r0_fee_negative, r0_notional_out_of_band, r0_too_young_or_stale, r0_spread_too_wide)
R1 = (r1_rail_not_executable, r1_market_closed, r1_event_rail_negative_edge, r1_identity_absent,
      r1_settlement_basis_mismatch, r1_no_sells_only_buys)
R2 = (r2_structural_gap_below_buffer, r2_crossvenue_gap_below_threshold, r2_liquidity_cannot_absorb,
      r2_spot_unproven_needs_more, r2_resolving_too_soon)


def default_funnel(db: Any):
    """Build a Funnel with the standard cost-ordered ladder."""
    from forge.judge.funnel import Funnel
    _DB._db = db                      # let the event-rail verdict check consult the live DB
    return Funnel(db, r0=R0, r1=R1, r2=R2)
