"""Every question the desk can ask, in one file. This is the file you reread later.

A question is a prompt and has a prompt's failure modes, so wording matters here more than anywhere
else in the system. Rules this file is written to:

  * ONE SET PER DECISION, ONE CALL PER CANDIDATE. State is tokenised once; splitting a set into one
    call per question re-charges identical state for identical answers.
  * STATE IS A NAMED OBJECT. Every question declares `reads=` — the fields it may see. Pruning is
    enforced from that declaration, so a fat state cannot silently cost accuracy.
  * FACTS ARE NOT QUESTIONS. Anything a comparison can settle lives in judge/checks.py as a free
    arithmetic kill, never here. We ask the model how dangerous the concentration is; we do not ask
    it what the concentration IS.
  * EVERY PICK SHIPS AN ABSOLUTE GATE. A Choice settles *which*; it always returns a winner even when
    every option is bad. The `worth_*` Noul beside it is what says "none — stand down today".
  * MISSING DATA IS AN ANSWER, NOT A PASS. `unknown`/`dark` gets its own option and its own
    consequence downstream (cut the ticket), and no question may treat null as fine.

These sets are Forge-native. The reference desk judged memecoin launches; Forge judges structural
edges, event-contract gaps, and directional spot — three different evidence shapes, three sets.
"""
from __future__ import annotations

from forge.judge.primitives import Choice, Noul, Score

# --------------------------------------------------------------------------- shared questions
DATA_COVERAGE = Choice(
    instructions="Judge how much of this candidate is actually visible from which fields in `state` "
                 "carry values and which are null or unknown. Visibility is an input to SIZE, not to "
                 "skip: less visibility means a smaller ticket, never a free pass.",
    criteria={
        "indexed": "Every field the decision needs carries a real value.",
        "partial": "The primary fields are present but distribution, depth, or the settlement source "
                   "is missing.",
        "dark": "Only price and volume are known. No depth, no distribution, no settlement source.",
    },
    reads=("fields_present", "fields_missing"),
)

SETTLEMENT_MATCHES_BASIS = Noul(
    instructions="The contract settles on the exact source and definition named in `settlement_rule`, "
                 "and `model_basis` describes that same quantity. A contract that settles on source X "
                 "while the model prices proxy Y is a basis mismatch, not an edge.",
    criteria={"true": "Settlement source and modelled quantity are the same observable, same timezone, "
                      "same rounding/strike convention.",
              "false": "Different source, different window, different rounding, or the model prices a "
                       "correlated proxy rather than the settled quantity."},
    reads=("settlement_rule", "model_basis", "strike_convention"),
)

CONCENTRATION_IS_EXIT_RISK = Noul(
    instructions="Holding this size means being exit liquidity, judged from `top_holder_share`, "
                 "`depth_at_touch_usd` and `our_ticket_usd`. This is about whether we can LEAVE, not "
                 "about whether the thesis is right.",
    criteria={"true": "A few wallets, or thin displayed depth, could end the market before we exit.",
              "false": "Depth and float are wide enough to absorb our ticket invisibly."},
    reads=("top_holder_share", "depth_at_touch_usd", "our_ticket_usd"),
)


# --------------------------------------------------------------------------- structural edges
# The crown-jewel class. The question is never "will price go up" — it is "is this a must-agree
# relationship, and is the violation wider than the cost of capturing it".
STABLE_EDGE = {
    "is_structural_identity": Noul(
        instructions="The edge in `state` arises from a relationship that MUST hold by construction "
                     "(a free 1:1 conversion, a settlement identity, a hard peg, a fee-free leg), so "
                     "the gap is a violation of an identity rather than a forecast about price. A "
                     "forecast is not structural no matter how reliable it has looked.",
        criteria={"true": "Name the identity and the mechanism that enforces it (e.g. free 1:1 "
                          "USD<->USDC conversion forces USDT-USD and USDT-USDC to imply one price).",
                  "false": "The gap depends on price continuing to move, on momentum, or on a crowd "
                           "behaviour that could stop."},
        reads=("identity", "mechanism", "legs", "historical_win_rate", "n_observed"),
    ),
    "gap_exceeds_all_costs": Noul(
        instructions="The measured gap clears EVERY cost of capturing it: taker fees on both legs, "
                     "spread, expected slippage at `our_ticket_usd` against `depth_at_touch_usd`, and "
                     "the safety buffer. Judge from the numbers in `state`; do not assume a cost is zero.",
        criteria={"true": "Net after all named costs is positive at the intended ticket size.",
                  "false": "Gross gap is positive but a named cost consumes it."},
        reads=("gap_bp", "fee_bp_total", "spread_bp", "slippage_bp_est", "buffer_bp",
               "our_ticket_usd", "depth_at_touch_usd"),
    ),
    "leg_failure_risk": Noul(
        instructions="One leg of the cycle could fail to fill, fill partially, or fill at a worse "
                     "price, leaving us holding inventory we did not intend. Judge from `leg_asks`, "
                     "`leg_bids`, `queue_ahead` and `venue_status`.",
        criteria={"true": "Thin depth on a leg, a stale book, degraded venue status, or a queue that "
                          "makes a partial fill likely.",
                  "false": "Both legs are deep, live, and our ticket is small relative to the touch."},
        reads=("leg_asks", "leg_bids", "queue_ahead", "venue_status", "our_ticket_usd"),
    ),
    "depth_fits_ticket": Noul(
        instructions="A ticket of `our_ticket_usd` could be entered AND exited against "
                     "`depth_at_touch_usd` without moving the price more than a few basis points.",
        reads=("our_ticket_usd", "depth_at_touch_usd"),
    ),
    "data_coverage": DATA_COVERAGE,
}


# --------------------------------------------------------------------------- event contracts
# Kalshi / Polymarket / cross-venue. The structural sub-class (same question, two venues) is a
# must-agree relationship and gets judged as such; model-vs-market is a forecast and is held to a
# much higher evidence bar.
EVENT_GAP = {
    "same_question_both_venues": Noul(
        instructions="`venue_a_question` and `venue_b_question` ask the SAME question and settle on "
                     "the SAME observable outcome, so their prices must agree. Ambiguity is a kill: "
                     "never average two prices that might describe different events.",
        criteria={"true": "Identical subject, identical resolution source, identical strike/definition, "
                          "compatible close time.",
                  "false": "Different wording that could resolve differently, different source, "
                           "different timezone or rounding, or an uncertain pairing."},
        reads=("venue_a_question", "venue_b_question", "settlement_rule", "close_time_a", "close_time_b"),
    ),
    "gap_is_real_after_costs": Noul(
        instructions="The cross-venue gap survives Kalshi's taker fee (≈0.07·C·P·(1−P)), both spreads, "
                     "and slippage at `our_ticket_usd`. Judge from the numbers in `state`.",
        criteria={"true": "Net positive at the intended ticket size after every named cost.",
                  "false": "A named cost consumes the gap."},
        reads=("gap_cents", "kalshi_fee_cents", "spread_a_cents", "spread_b_cents",
               "our_ticket_usd", "liquidity_a_usd", "liquidity_b_usd"),
    ),
    "settlement_basis_matches": SETTLEMENT_MATCHES_BASIS,
    "model_beats_market": Noul(
        instructions="Our de-vigged model probability `p_model` differs from the market price "
                     "`p_market` by more than the cost of the trade, AND the model has earned that "
                     "difference on this class of question (see `model_brier`, `model_n`, "
                     "`scorecard_note`). A model that is wrong on this class does not move our number.",
        criteria={"true": "Edge exceeds cost and the model's realized calibration on this question "
                          "class supports trusting it.",
                  "false": "Edge is inside cost, or the model has no track record / a poor Brier on "
                           "this class, or the market has already priced the information."},
        reads=("p_model", "p_market", "edge_cents", "cost_cents", "model_brier", "model_n",
               "scorecard_note", "data_age_hours"),
    ),
    "information_not_already_priced": Noul(
        instructions="The signal we are reasoning from is NOT yet visible in the current price. A "
                     "signal the market has already absorbed is noise, not an edge.",
        criteria={"true": "The move or information is absent from the current price.",
                  "false": "The price already reflects it; there is nothing left to take."},
        reads=("signal_summary", "p_market", "price_move_last_h", "signal_timestamp"),
    ),
    "data_coverage": DATA_COVERAGE,
}


# --------------------------------------------------------------------------- directional spot
# The class that has NOT earned capital: 145 closes measured mu=-0.0012 per unit, tier UNPROVEN.
# These questions are deliberately harder to satisfy than the structural sets.
SPOT_ENTRY = {
    "edge_survives_costs": Noul(
        instructions="The modelled edge in `state` is positive after taker fee, spread, and expected "
                     "slippage at the intended ticket, using the numbers given. Directional spot has "
                     "been measured net-negative on this desk, so the burden of proof is on the edge.",
        criteria={"true": "Net positive after every named cost, with margin, not marginally.",
                  "false": "Net negative, or positive only by less than the uncertainty in the estimate."},
        reads=("edge_bp", "fee_bp", "spread_bp", "slippage_bp_est", "our_ticket_usd", "n_backtest"),
    ),
    "momentum_already_spent": Noul(
        instructions="The move described in `change_windows` has already happened, so entering now "
                     "means buying after the information is public.",
        criteria={"true": "The largest change sits in the OLDER windows.",
                  "false": "The recent windows carry the move."},
        reads=("change_windows", "volume_windows"),
    ),
    "shape_of_flow": Choice(
        instructions="Classify the shape of this instrument's flow from the windowed fields in `state`.",
        criteria={
            "crowd": "Holders/participants growing faster than price; buys outnumber sells across both "
                     "recent windows; volume spread rather than spiking once.",
            "one_bidder": "Price climbing faster than participation; one wallet walking the price up.",
            "fading": "Recent volume a small fraction of the daily average, or sells outnumber buys in "
                      "both recent windows.",
            "too_early": "Too few data points to tell any of the above apart yet.",
        },
        reads=("change_windows", "volume_windows", "participant_growth", "buy_sell_ratio"),
    ),
    "concentration_is_exit_risk": CONCENTRATION_IS_EXIT_RISK,
    "data_coverage": DATA_COVERAGE,
}


# --------------------------------------------------------------------------- the pick
def PICK(state: dict) -> dict:
    """Options are built from the shortlist AT CALL TIME. Never run this on one survivor: a choice
    over a single option returns that option with high confidence because it is the only thing there.
    One survivor goes straight to the soft gates, or nowhere."""
    cands = state.get("candidates") or []
    return {
        "best": Choice(
            instructions="Choose the single candidate in `candidates` that is the best use of one unit "
                         "of capital for the next hour. Weigh structural certainty above size: a "
                         "must-agree identity with a small gap beats a forecast with a large one. "
                         "Prefer an unspent setup over a bigger move that already happened.",
            criteria={str(c.get("key")): str(c.get("summary") or "")[:400] for c in cands[:255]},
            reads=("candidates",),
        ),
        # THE ABSOLUTE GATE. Without this the desk always trades, because a Choice always picks one.
        "worth_acting_at_all": Noul(
            instructions="At least one candidate in `candidates` is worth a position in the next hour, "
                         "rather than all of them being mediocre. Standing down is a normal, correct "
                         "outcome and must be reachable.",
            criteria={"true": "At least one is a clean setup whose edge survives costs.",
                      "false": "Every candidate has a disqualifying weakness, or the best edge is "
                               "inside transaction cost."},
            reads=("candidates",),
        ),
    }


# --------------------------------------------------------------------------- rail readiness
REGIME = {
    "rail_can_earn_now": Noul(
        instructions="This rail is able to produce income RIGHT NOW, judged from `rail_status`, "
                     "`market_session`, `credentials_present` and `feed_health`. A rail that is "
                     "unkeyed, closed, or fed by a degraded source cannot earn regardless of edge.",
        criteria={"true": "Executable, session open, credentials present, feeds healthy.",
                  "false": "Any of: unkeyed, session closed, credentials missing, feed degraded or stale."},
        reads=("rail_status", "market_session", "credentials_present", "feed_health", "last_feed_age_s"),
    ),
    "attention_better_spent_elsewhere": Noul(
        instructions="Given `open_rails_earning`, `this_rail_rate_usd_per_h` and "
                     "`other_rails_rate_usd_per_h`, inference spent on this rail right now would earn "
                     "less than the same inference spent on a rail already earning. Inference is a "
                     "salary and must be recouped.",
        criteria={"true": "Another open rail is earning more per inference-dollar right now.",
                  "false": "This rail is the best available use of attention, or nothing else is earning."},
        reads=("open_rails_earning", "this_rail_rate_usd_per_h", "other_rails_rate_usd_per_h",
               "this_rail_inference_cost_usd"),
    ),
}


SETS: dict[str, Any] = {
    "stable_edge": STABLE_EDGE,
    "event_gap": EVENT_GAP,
    "spot_entry": SPOT_ENTRY,
    "pick": PICK,
    "regime": REGIME,
}


def resolve(question_set: str, state: dict) -> dict:
    """Return the concrete question dict for a set name, building call-time options where needed."""
    if question_set not in SETS:
        raise KeyError(f"unknown question set {question_set!r}; known: {sorted(SETS)}")
    qs = SETS[question_set]
    return qs(state) if callable(qs) else qs
