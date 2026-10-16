"""Cross-bookmaker arbitrage detection — the crown jewel's edge class, applied to sports.

WHY THIS IS THE SAME EDGE AS stable_triangle, NOT A FORECAST.
  stable_triangle earns because Coinbase converts USD<->USDC 1:1 for FREE, so USDT-USD and USDT-USDC MUST
  imply one USDT price. A gap above fees is a violation of an identity, not a prediction — which is why it
  wins 1,452 of 1,452.
  Cross-bookmaker arbitrage is structurally identical: a single match has exactly one winner, so the true
  probabilities of HOME and AWAY must sum to 1. If book A's best HOME odds and book B's best AWAY odds
  imply probabilities summing to LESS than 1, backing both sides at those prices returns more than the
  staked amount whichever side wins. There is no directional risk and no forecast — it is an identity
  violated, captured by staking both legs in proportion.

  This matters for the firm because it is 24/7 (sports run when equities are closed), spans MANY markets
  ("many different kinds of bets"), and is the class of edge that has actually earned here. It reuses
  consensus_h2h, which already returns best_home/best_away per book, so detection is a pure function:
  no network, no model, no inference, fully unit-testable before any API key exists.

HONEST LIMITS (stated up front, because an arb detector that hides these is a liability):
  * Execution risk is real and is NOT zero: two legs at two books can fail independently (one side fills,
    the other moves). The reported `net_pct` is the theoretical return assuming BOTH legs fill at the
    quoted prices. `margin_bp` is therefore required to exceed a buffer, and stake sizing must respect the
    thinner leg's limit.
  * Limits/stakes: books cap stakes, so `max_stake_usd` bounds what is actually capturable.
  * Odds move fast; a detected arb may be gone by the time an order arrives. LATENCY_BUFFER_BP accounts for
    this and must never be set to zero.
"""
from __future__ import annotations

from typing import Any

# Minimum theoretical return, in basis points of total stake, before an arb is worth attempting.
# Must clear: withdrawal/transfer friction between books, the risk that one leg fails, and odds drift
# during execution. Anything smaller is not an opportunity, it is a way to lose money slowly.
MIN_ARB_MARGIN_BP = 50.0

# Cushion for odds moving between detection and execution. Never zero.
LATENCY_BUFFER_BP = 10.0


def implied_prob(decimal_odds: float) -> float | None:
    """Decimal odds -> implied probability. None if not a valid price."""
    try:
        o = float(decimal_odds)
    except (TypeError, ValueError):
        return None
    if o <= 1.0:
        return None
    return 1.0 / o


def detect_arb(cons: dict[str, Any] | None, *, min_margin_bp: float = MIN_ARB_MARGIN_BP,
               latency_buffer_bp: float = LATENCY_BUFFER_BP,
               stake_usd: float = 100.0) -> dict[str, Any] | None:
    """Detect a cross-bookmaker arbitrage from a consensus_h2h() result. Pure function.

    Returns None when there is no arb worth taking. Otherwise returns the stake split, the theoretical
    net return, and the explicit risks — so a caller can size, execute and account for it honestly.

    Stake split logic: to guarantee the same payout whichever side wins, stake each leg inversely to its
    odds. If HOME odds are H and AWAY odds are A, staking s_h on home and s_a on away with
    s_h * H == s_a * A returns the same amount on either outcome. With S = s_h + s_a:
        s_h = S * (1/H) / (1/H + 1/A)      s_a = S * (1/A) / (1/H + 1/A)
        payout = s_h * H = s_a * A = S / (1/H + 1/A)
    So the arb exists exactly when 1/H + 1/A < 1, and net return = payout - S.
    """
    if not cons:
        return None
    bh = cons.get("best_home") or {}
    ba = cons.get("best_away") or {}
    ho, ao = bh.get("odds"), ba.get("odds")
    if not ho or not ao:
        return None
    ih = implied_prob(ho)
    ia = implied_prob(ao)
    if ih is None or ia is None:
        return None

    book = ih + ia                      # < 1.0 means an arbitrage exists
    if book >= 1.0:
        return None                     # no arb: the market is internally consistent (the normal case)

    # Apply the latency buffer: require the edge to survive odds moving against us before we act.
    buffered_book = book + (latency_buffer_bp / 10000.0)
    if buffered_book >= 1.0:
        return None

    net_pct = (1.0 / book) - 1.0        # theoretical return on total stake if both legs fill
    margin_bp = net_pct * 10000.0
    if margin_bp < min_margin_bp:
        return None                     # real but too thin to survive friction — not an opportunity

    # Stake split that equalises the payout on either outcome.
    inv_h, inv_a = 1.0 / ho, 1.0 / ao
    denom = inv_h + inv_a
    s_home = stake_usd * inv_h / denom
    s_away = stake_usd * inv_a / denom
    payout = s_home * ho                # == s_away * ao by construction

    # A single book cannot be both legs: that would be one book quoting an arb against itself, which in
    # practice means stale or crossed data, not a capturable opportunity.
    same_book = bh.get("book") is not None and bh.get("book") == ba.get("book")

    return {
        "is_arb": True,
        "cross_book": not same_book,
        "home_book": bh.get("book"), "away_book": ba.get("book"),
        "home_odds": float(ho), "away_odds": float(ao),
        "implied_home": round(ih, 6), "implied_away": round(ia, 6),
        "book_sum": round(book, 6),                 # <1.0 == arb
        "net_pct": round(net_pct, 6),
        "margin_bp": round(margin_bp, 3),
        "stake_total_usd": round(stake_usd, 4),
        "stake_home_usd": round(s_home, 4),
        "stake_away_usd": round(s_away, 4),
        "guaranteed_payout_usd": round(payout, 4),
        "guaranteed_profit_usd": round(payout - stake_usd, 6),
        "n_books": cons.get("n_books"),
        # HONEST RISK DISCLOSURE — every consumer must surface these, not bury them.
        "risks": {
            "execution": "two legs at two books can fail independently; net_pct assumes BOTH fill at quote",
            "odds_drift": "prices move between detection and execution; buffered by "
                          f"{latency_buffer_bp}bp",
            "stake_limits": "books cap stakes, so max_stake_usd bounds what is actually capturable",
            "same_book_warning": ("best home and best away are the SAME book — likely stale/crossed data, "
                                  "not a capturable arb") if same_book else None,
        },
        "min_margin_bp": min_margin_bp,
        "latency_buffer_bp": latency_buffer_bp,
    }


def max_capturable(arb: dict[str, Any], home_limit_usd: float | None = None,
                   away_limit_usd: float | None = None) -> dict[str, Any]:
    """Scale an arb down to what the thinner book will actually accept.

    A detected arb sized above a book's stake limit is not capturable at that size. This returns the
    largest total stake where BOTH legs fit their limits, preserving the equal-payout split.
    """
    ho = float(arb.get("home_odds") or 0)
    ao = float(arb.get("away_odds") or 0)
    if ho <= 0 or ao <= 0:
        return {"total_usd": 0.0, "limited_by": "invalid_odds"}
    inv_h, inv_a = 1.0 / ho, 1.0 / ao
    denom = inv_h + inv_a
    # For total S: s_home = S*inv_h/denom <= home_limit  =>  S <= home_limit*denom/inv_h
    caps = []
    if home_limit_usd is not None:
        caps.append((float(home_limit_usd) * denom / inv_h, "home_book_limit"))
    if away_limit_usd is not None:
        caps.append((float(away_limit_usd) * denom / inv_a, "away_book_limit"))
    base = float(arb.get("stake_total_usd") or 0.0)
    if not caps:
        return {"total_usd": round(base, 4), "limited_by": None,
                "stake_home_usd": arb.get("stake_home_usd"), "stake_away_usd": arb.get("stake_away_usd")}
    cap, why = min(caps, key=lambda x: x[0])
    total = min(base, cap)
    return {"total_usd": round(total, 4), "limited_by": why if total < base else None,
            "stake_home_usd": round(total * inv_h / denom, 4),
            "stake_away_usd": round(total * inv_a / denom, 4),
            "guaranteed_profit_usd": round(total * float(arb.get("net_pct") or 0.0), 6)}


def scan_events(consensus_by_event: dict[str, dict[str, Any]], **kw: Any) -> list[dict[str, Any]]:
    """Scan many events for arbs. Returns them best-margin-first, each tagged with its event key.

    Deterministic and pure: given the same odds snapshot it returns the same arbs in the same order, so
    results are reproducible and unit-testable without a live feed.
    """
    out = []
    for key, cons in (consensus_by_event or {}).items():
        a = detect_arb(cons, **kw)
        if a:
            a = dict(a)
            a["event"] = key
            out.append(a)
    out.sort(key=lambda x: -float(x.get("margin_bp") or 0))
    return out
