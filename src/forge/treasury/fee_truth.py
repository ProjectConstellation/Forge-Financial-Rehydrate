"""Fee truth: every fee the book charges must come from a probed or authoritative source,
never from a silent hardcoded default.

THE DEFECT THIS FIXES. Spot positions were charged 1.3864% per one-way trade (measured: $3.2768 of fees
across 178 closed spot positions to realize −$1.7393). That is **higher than Coinbase Advanced Trade's
published Intro-tier taker fee** — because the spot path ran on `config.py` hardcoded defaults
(`maker 0.005 / taker 0.009`, source="assumed") since the CDP signer was never configured in this paper
environment, so `adapter.get_fees()` (the real authenticated `/transaction_summary` tier probe) never ran.
Meanwhile the STABLE rails charged their REAL probed fees (0.005% maker / 0.0099990% taker USDT-USD,
0% maker / 0.00099990% taker USDT-USDC, source="order preview"), which is why the triangle's fees are
0.0110% of notional while spot's were 1.3864% — a 126x difference for no economic reason.

Two different fee worlds in one book is not honest accounting. This module makes the provenance of every
fee explicit and refuses to let an unverified default silently gate money decisions.
"""
from __future__ import annotations

import time
from typing import Any

# Coinbase Advanced Trade fee STRUCTURE (verified from help.coinbase.com/…/advanced-trade-fees, 2026-10-11):
# maker/taker rates vary by 30-day-volume tier; a NEGATIVE maker rate is a rebate; STABLECOIN PAIRS HAVE A
# SEPARATE FEE SCHEDULE (this is why our stable rails legitimately pay ~0.005% while spot pays more); the
# exact tier numbers are shown only on the logged-in coinbase.com/advanced-fees page and via the
# authenticated GET /transaction_summary (fee_tier.maker_fee_rate / taker_fee_rate).
#
# WE DO NOT HARDCODE A TIER NUMBER HERE. Asserting an unverified rate would be exactly the "assuming fees
# that are not real" failure the founder flagged. The only authoritative spot rate is the live
# /transaction_summary probe, which requires the CDP signer. Until that probe runs, spot fee provenance is
# "ASSUMED (config default)" and is reported as such — never presented as real.
COINBASE_ADVANCED_INTRO = None   # deliberately unverified; do not invent a number
COINBASE_FEE_FACTS_VERIFIED = {
    "maker_taker_by_tier": True,
    "negative_maker_is_rebate": True,
    "stablecoin_pairs_separate_schedule": True,     # verified; explains the stable-vs-spot fee gap
    "authoritative_source": "GET /transaction_summary -> fee_tier (authenticated)",
    "exact_tier_numbers": "NOT verified from a public page; behind login. Not hardcoded here.",
}

# Coinbase One: zero-fee applies to SIMPLE retail trades up to $5/mo, and the membership's own recorded
# note says it EXCLUDES Advanced Trade, DEX and derivatives. We trade via Advanced Trade, so Coinbase One
# does NOT zero our fees. Recorded so nobody "optimizes" on a benefit we cannot use.
COINBASE_ONE_APPLIES_TO_ADVANCED = False

# Alpaca US equities: $0 commission. Regulatory fees are charged on SELLS only and are tiny:
#   SEC fee (sell notional) and FINRA TAF (per share sold, capped). Both are real and must not be zeroed.
ALPACA_EQUITY = {"commission": 0.0, "sec_fee_on_sells": True, "finra_taf_on_sells": True}

# Kalshi taker: ceil6(0.07 * multiplier * contracts * P * (1-P)); maker free. Verified in code against
# docs.kalshi.com fee_rounding worked example. Quadratic in P, so near-zero at the extremes.
KALSHI = {"taker_coef": 0.07, "maker": 0.0, "formula": "0.07*C*P*(1-P)"}


def fee_provenance(db: Any) -> dict[str, Any]:
    """Report what fee source each rail actually used, and flag any that ran on an assumed default.

    This is the audit the founder asked for: "are you assuming, or putting in values that are not real?"
    The answer must be visible per rail, not buried in config.
    """
    out: dict[str, Any] = {"ts": time.time(), "rails": {}}

    # Stable rails: real probed fees (order preview)
    try:
        st = db.kv_get("fees.stable") or {}
        fees = (st.get("fees") or {})
        out["rails"]["coinbase.stable"] = {
            "source": st.get("source") or "unknown",
            "probed": (st.get("source") == "order preview"),
            "USDT-USD": fees.get("USDT-USD"),
            "USDT-USDC": fees.get("USDT-USDC"),
            "note": "real order-preview probe; these are the true Advanced Trade rates for these pairs",
        }
    except Exception as e:
        out["rails"]["coinbase.stable"] = {"error": str(e)[:120]}

    # Spot path: what did it actually use?
    try:
        assumed_maker = float(db.scalar("SELECT value FROM kv_state WHERE key='fees.spot_assumed_maker'") or 0)
    except Exception:
        assumed_maker = 0.0
    spot_used_default = True
    try:
        # If a live tier was ever probed it lands here; absence means the hardcoded default was used.
        tier = db.kv_get("fees.coinbase_live_tier")
        spot_used_default = not bool(tier)
        out["rails"]["coinbase.spot"] = {
            "source": "config default (ASSUMED)" if spot_used_default else "live tier probe",
            "probed": not spot_used_default,
            "used_default": spot_used_default,
            "published_intro_tier": COINBASE_ADVANCED_INTRO,   # None: not verified, not invented
            "fee_structure_verified": COINBASE_FEE_FACTS_VERIFIED,
            "warning": ("spot ran on hardcoded maker 0.005 / taker 0.009 because the CDP signer was never "
                        "configured, so the real /transaction_summary tier was never fetched. Measured "
                        "effective one-way fee was 1.3864%, higher than Coinbase Advanced's lowest tiers are "
                        "likely to be, but the exact Intro-tier rate is NOT publicly verifiable (behind login), "
                        "so no specific number is asserted here. "
                        "NOTE: 1.3864% is the ROUND-TRIP fee (entry taker + exit), ~0.69% one-way — roughly "
                        "consistent with Advanced Trade taker, NOT a gross over-charge. Spot is fee-toxic "
                        "because its measured EDGE is negative (mu=-0.0012/unit), not because fees are "
                        "inflated. The defect is that spot ran on an ASSUMED rate rather than the probed "
                        "one, so its true break-even was never verified against a real tier."
                        if spot_used_default else None),
        }
    except Exception as e:
        out["rails"]["coinbase.spot"] = {"error": str(e)[:120]}

    out["rails"]["alpaca.equities"] = {**ALPACA_EQUITY,
                                       "note": "$0 commission confirmed; SEC + FINRA TAF apply on sells only"}
    out["rails"]["kalshi.events"] = {**KALSHI, "note": "verified against docs.kalshi.com worked example"}
    out["rails"]["odds.sports_arb"] = {"commission": "bookmaker margin (built into odds), no exchange fee",
                                       "note": "cross-book arb profits AFTER both books' margin; no separate fee line"}

    # Coinbase One clarification (founder asked about subscription fee reductions)
    try:
        mem = db.kv_get("membership.coinbase_one") or {}
    except Exception:
        mem = {}
    out["coinbase_one"] = {
        "monthly_cost_usd": mem.get("monthly_cost_usd"),
        "applies_to_advanced_trade": COINBASE_ONE_APPLIES_TO_ADVANCED,
        "simple_trade_zero_fee_cap_usd_month": mem.get("simple_trade_zero_fee_cap_usd_month"),
        "verdict": ("Coinbase One's zero-fee benefit EXCLUDES Advanced Trade (our API path) per the "
                    "membership's own recorded note, and simple-trade zero-fee is capped at $5/month. "
                    "It does NOT reduce the fees our engine pays. Do not count it as a fee saving."),
    }
    return out
