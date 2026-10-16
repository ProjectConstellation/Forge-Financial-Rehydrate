"""ZERO-INFERENCE proof that cross-bookmaker arbitrage detection is mathematically correct.

The whole value of this edge is that it is an IDENTITY, not a forecast — so the test must verify the
identity holds exactly: when 1/H + 1/A < 1, staking both legs in proportion returns MORE than staked
regardless of which side wins. If that property does not hold to the cent, the "arb" is a lie and must
not be traded.

Also proves: a normal (non-arb) market is correctly rejected, thin arbs below the buffer are rejected,
same-book "arbs" are flagged as suspect, and stake-limit scaling preserves the equal-payout property.
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/srv/forge/src")
from forge.intel.arb import detect_arb, max_capturable, scan_events, implied_prob, MIN_ARB_MARGIN_BP

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  <- " + detail) if detail and not cond else ""))

print("=" * 84)
print("CROSS-BOOKMAKER ARBITRAGE — MATHEMATICAL CORRECTNESS PROOF (zero inference)")
print("=" * 84)

def cons(home_book, home_odds, away_book, away_odds, n=5):
    return {"n_books": n, "best_home": {"book": home_book, "odds": home_odds, "q": implied_prob(home_odds)},
            "best_away": {"book": away_book, "odds": away_odds, "q": implied_prob(away_odds)}}

# ---------------------------------------------------------------- 1. THE IDENTITY: payout > stake both ways
print("\n[1] THE ARBITRAGE IDENTITY — guaranteed profit whichever side wins")
# Home 2.10 at bookA, Away 2.10 at bookB => 1/2.10 + 1/2.10 = 0.952 < 1 => arb.
a = detect_arb(cons("bookA", 2.10, "bookB", 2.10), stake_usd=100.0)
check("clear arb detected", a is not None and a["is_arb"], str(a)[:80])
if a:
    S = a["stake_total_usd"]; sh = a["stake_home_usd"]; sa = a["stake_away_usd"]
    payout_home = sh * a["home_odds"]      # if home wins
    payout_away = sa * a["away_odds"]      # if away wins
    check("stake split sums to total", abs((sh + sa) - S) < 1e-6, f"{sh}+{sa} vs {S}")
    check("payout EQUAL on both outcomes (the identity)", abs(payout_home - payout_away) < 1e-6,
          f"home={payout_home:.6f} away={payout_away:.6f}")
    check("payout EXCEEDS stake if HOME wins", payout_home > S, f"{payout_home:.4f} vs {S:.4f}")
    check("payout EXCEEDS stake if AWAY wins", payout_away > S, f"{payout_away:.4f} vs {S:.4f}")
    check("guaranteed profit is positive and matches", abs((payout_home - S) - a["guaranteed_profit_usd"]) < 1e-6,
          f"{payout_home - S:.6f} vs {a['guaranteed_profit_usd']}")
    check("book_sum < 1.0 (arb condition)", a["book_sum"] < 1.0, str(a["book_sum"]))
    print("     book_sum=%.6f net_pct=%.4f%% margin=%.1fbp profit=$%.4f on $%.0f" % (
        a["book_sum"], a["net_pct"]*100, a["margin_bp"], a["guaranteed_profit_usd"], S))
    check("cross-book flagged (two different books)", a["cross_book"] is True)
    check("risks disclosed, not hidden", isinstance(a.get("risks"), dict) and "execution" in a["risks"])

# ---------------------------------------------------------------- 2. NO ARB in a normal market
print("\n[2] A NORMAL MARKET IS CORRECTLY REJECTED (no free money where none exists)")
# Home 1.90, Away 1.90 => 1/1.9+1/1.9 = 1.053 > 1 => no arb (books hold their margin)
check("fair-ish market has NO arb", detect_arb(cons("a", 1.90, "b", 1.90)) is None)
# Home 1.50 Away 2.50 => 1/1.5+1/2.5 = 1.0667 > 1 => no arb
check("asymmetric market has NO arb", detect_arb(cons("a", 1.50, "b", 2.50)) is None)
# Home 2.00 Away 2.00 => exactly 1.0 => breakeven, NOT an arb (must be strictly < 1)
check("breakeven (sum==1.0) is NOT an arb", detect_arb(cons("a", 2.00, "b", 2.00)) is None)

# ---------------------------------------------------------------- 3. THIN arbs rejected by buffer/margin
print("\n[3] THIN ARBS ARE REJECTED — must clear friction + latency buffer")
# A tiny arb: 1/2.01+1/2.01 = 0.995 => 0.5% net = 50bp, right at the margin
thin = detect_arb(cons("a", 2.01, "b", 2.01), stake_usd=100.0)
print("     2.01/2.01 -> margin_bp:", (thin or {}).get("margin_bp"), "detected:", thin is not None)
# Just inside the buffer: 1/2.005+1/2.005 = 0.99751 => ~24.9bp < 50bp min => rejected
check("sub-margin arb rejected (<%sbp)" % MIN_ARB_MARGIN_BP,
      detect_arb(cons("a", 2.005, "b", 2.005), stake_usd=100.0) is None)
# A strong arb well above margin: 1/2.2+1/2.2=0.909 => ~10% => detected
check("strong arb detected", detect_arb(cons("a", 2.2, "b", 2.2), stake_usd=100.0) is not None)
# Latency buffer: an arb whose raw margin is real but vanishes after the buffer
b = detect_arb(cons("a", 2.02, "b", 2.02), stake_usd=100.0, latency_buffer_bp=200.0)
check("arb killed by a large latency buffer", b is None)

# ---------------------------------------------------------------- 4. SAME-BOOK suspect data
print("\n[4] SAME-BOOK 'ARB' IS FLAGGED AS SUSPECT (stale/crossed data, not capturable)")
same = detect_arb(cons("bookX", 2.10, "bookX", 2.10), stake_usd=100.0)
check("same-book detected but flagged cross_book=False", same is not None and same["cross_book"] is False)
check("same-book warning present", same is not None and same["risks"].get("same_book_warning") is not None)

# ---------------------------------------------------------------- 5. stake-limit scaling preserves the identity
print("\n[5] STAKE-LIMIT SCALING PRESERVES THE EQUAL-PAYOUT IDENTITY")
a = detect_arb(cons("bookA", 2.10, "bookB", 2.10), stake_usd=1000.0)
if a:
    capped = max_capturable(a, home_limit_usd=200.0, away_limit_usd=200.0)
    print("     requested $%.0f -> capturable $%.2f limited_by=%s" % (
        a["stake_total_usd"], capped["total_usd"], capped["limited_by"]))
    sh, sa = capped["stake_home_usd"], capped["stake_away_usd"]
    ph = sh * a["home_odds"]; pa = sa * a["away_odds"]
    check("scaled stake fits home limit", sh <= 200.0 + 1e-6, f"{sh}")
    check("scaled stake fits away limit", sa <= 200.0 + 1e-6, f"{sa}")
    check("equal payout preserved after scaling", abs(ph - pa) < 1e-4, f"{ph:.4f} vs {pa:.4f}")
    check("still profitable after scaling", ph > capped["total_usd"], f"{ph:.4f} vs {capped['total_usd']}")

# ---------------------------------------------------------------- 6. multi-event scan ordering
print("\n[6] MULTI-EVENT SCAN — best margin first, deterministic")
events = {
    "evt_small": cons("a", 2.05, "b", 2.05),      # small arb
    "evt_big": cons("a", 2.30, "b", 2.30),        # big arb
    "evt_none": cons("a", 1.90, "b", 1.90),       # no arb
}
found = scan_events(events, stake_usd=100.0)
check("scan finds exactly the 2 real arbs", len(found) == 2, f"found {len(found)}")
check("best margin first", found and found[0]["event"] == "evt_big",
      found[0]["event"] if found else "none")
check("non-arb event excluded", all(f["event"] != "evt_none" for f in found))
check("deterministic order", [f["event"] for f in found] == [f["event"] for f in scan_events(events, stake_usd=100.0)])

# ---------------------------------------------------------------- 7. malformed input never crashes
print("\n[7] MALFORMED INPUT NEVER CRASHES (fails closed, returns None)")
check("None consensus -> None", detect_arb(None) is None)
check("missing odds -> None", detect_arb({"best_home": {}, "best_away": {}}) is None)
check("odds <= 1.0 -> None", detect_arb(cons("a", 1.0, "b", 0.5)) is None)
check("garbage odds -> None (no exception)", detect_arb(cons("a", "x", "b", None)) is None)
check("zero stake -> still computes (0 profit)", (detect_arb(cons("a", 2.1, "b", 2.1), stake_usd=0.0) or {}).get("guaranteed_profit_usd") == 0.0)

print("\n" + "=" * 84)
print("RESULT: %d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
print("=" * 84)
sys.exit(1 if FAIL else 0)
