"""De-vig / consensus probability tools for bookmaker odds (blueprint §39)."""
from __future__ import annotations

import math
import statistics
from typing import Any


def implied_prob(decimal_odds: float) -> float | None:
    if not decimal_odds or decimal_odds <= 1.0:
        return None
    return 1.0 / float(decimal_odds)


def multiplicative_devig(probs: list[float]) -> list[float]:
    """Remove overround proportionally; returns fair probs summing to 1."""
    s = sum(probs)
    if s <= 0:
        return probs
    return [p / s for p in probs]


def consensus_h2h(book_quotes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """book_quotes: [{book, home_odds, away_odds}] (2-way). Returns fair home/away + dispersion."""
    rows = []
    for b in book_quotes:
        ho, ao = b.get("home_odds"), b.get("away_odds")
        if not ho or not ao or ho <= 1.0 or ao <= 1.0:
            continue
        ih, ia = implied_prob(ho), implied_prob(ao)
        if ih is None or ia is None:
            continue
        fh, fa = multiplicative_devig([ih, ia])
        rows.append({
            "book": b.get("book"),
            "home_odds": float(ho), "away_odds": float(ao),
            "fair_home": fh, "fair_away": fa,
            "overround": ih + ia - 1.0,
        })
    if len(rows) < 3:
        return None
    # Weight sharper (lower overround) books more
    weights = [1.0 / max(r["overround"], 0.005) for r in rows]
    wsum = sum(weights)
    p_home = sum(r["fair_home"] * w for r, w in zip(rows, weights)) / wsum
    p_away = 1.0 - p_home
    homes = [r["fair_home"] for r in rows]
    disp = statistics.pstdev(homes) if len(homes) > 1 else 0.0
    best_home = max(rows, key=lambda r: r["home_odds"])
    best_away = max(rows, key=lambda r: r["away_odds"])
    return {
        "n_books": len(rows),
        "p_home": p_home,
        "p_away": p_away,
        "dispersion": disp,
        "median_overround": statistics.median(r["overround"] for r in rows),
        "best_home": {"book": best_home["book"], "odds": best_home["home_odds"], "q": implied_prob(best_home["home_odds"])},
        "best_away": {"book": best_away["book"], "odds": best_away["away_odds"], "q": implied_prob(best_away["away_odds"])},
        "books": rows,
    }


def binary_kelly(p: float, decimal_odds: float, fraction: float = 0.125) -> float:
    """Fractional Kelly for decimal odds. b = decimal-1."""
    b = decimal_odds - 1.0
    if b <= 0 or p <= 0 or p >= 1:
        return 0.0
    q = 1.0 - p
    f = (b * p - q) / b
    return max(0.0, f * fraction)


def edge_ok(p_hat: float, q_price: float, dispersion: float) -> tuple[bool, str, float]:
    """Strict intelligence gate: value on likely winners OR strong underdog edge with book agreement."""
    if q_price is None or p_hat is None:
        return False, "missing_p", 0.0
    edge = p_hat - q_price
    if dispersion > 0.14:
        return False, "books_disagree", edge
    # Prefer bets that are both likely AND mispriced
    if p_hat >= 0.55 and edge >= 0.03:
        return True, "favorite_value", edge
    if p_hat >= 0.48 and edge >= 0.045:
        return True, "coin_flip_value", edge
    if p_hat >= 0.38 and edge >= 0.07:
        return True, "underdog_strong_edge", edge
    return False, "no_edge", edge
