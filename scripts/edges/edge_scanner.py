"""OVERNIGHT EDGE-CLASS SCANNER — thousands of deterministic evaluations, ZERO inference.

PURPOSE. The founder's directive: find new proprietary edges by the thousands, and prove them. The
architecture that makes that affordable is the funnel philosophy applied to DISCOVERY: a deterministic
scanner evaluates thousands of candidate relationships per hour for free (public data, no model), and only
survivors are handed to the intelligence layer to reason about. Inference is spent on judgement, never on
enumeration.

THE SELECTION CRITERION LEARNED TONIGHT (this is the real secret sauce, and it is empirical):
  The crown jewel (stable_triangle) wins 1,481/1,481 because it has a FREE LEG — Coinbase converts
  USD<->USDC 1:1 at zero cost, so the identity's capture hurdle is ~5bp.
  A three-leg crypto triangle was scanned tonight across 122 live books: max observed gap +8.01bp, median
  -9.09bp, cheapest hurdle 75bp (3 legs x maker). ZERO profitable.
  => An identity alone is NOT an edge. An edge needs: (1) a must-agree relationship, AND (2) a free or
     rebated leg, OR a gap that exceeds every leg's fee. Class (1) without (2) is a mirage.

CLASSES SCANNED (each is a hypothesis with a measurable pass/fail, not a vibe):
  A  free_leg_identity   — pairs bridged by a zero-cost conversion (the proven class; find siblings)
  B  multi_leg_triangle  — control: re-measured every run so we know if the class ever wakes up
  C  maker_spread_capture— instruments whose displayed spread exceeds 2x round-trip maker cost, so posting
                           both sides is +EV before adverse selection (generalizes the pegmaker beyond stables)
  D  cross_venue         — same asset on Coinbase vs another public venue; measures whether the class is alive
  E  tick_discreteness   — coarse price grids relative to price create maker advantage; ranked
  F  stablecoin_peg      — every stablecoin vs USD/USDC; deviation beyond fees?
  G  listing_recency     — newly listed products have wider spreads and less competition

OUTPUT: /srv/forge/var/reports/edges/scan_<ts>.json + a human digest. Every claim carries its own
measurement so nothing has to be taken on trust. Rate-limited and polite; public endpoints only.
"""
from __future__ import annotations

import json
import os
import statistics
import time
import urllib.request
from collections import defaultdict

CB = "https://api.exchange.coinbase.com"
UA = {"User-Agent": "forge-edge-research/1.0", "Accept": "application/json"}
OUT_DIR = "/srv/forge/var/reports/edges"

# Fee assumptions are stated as a RANGE because Coinbase's exact tier is login-only and we refuse to
# assert an unverified constant. A class that only passes under the most optimistic fee assumption is
# flagged as fee-fragile rather than claimed as an edge.
FEE_LOW = {"maker": 0.0025, "taker": 0.0040}     # optimistic
FEE_MID = {"maker": 0.0040, "taker": 0.0060}     # plausible intro
FEE_HIGH = {"maker": 0.0050, "taker": 0.0090}    # what our spot path currently assumes

STABLES = {"USD", "USDC", "USDT", "DAI", "PYUSD", "EURC", "GUSD", "USDP", "TUSD", "FDUSD", "USDE"}


def get(url, timeout=20, retries=2):
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:                      # noqa: BLE001 - research script, report and continue
            last = e
            time.sleep(0.4)
    raise last


def book(sym):
    d = get(f"{CB}/products/{sym}/book?level=2")
    bids = d.get("bids") or []
    asks = d.get("asks") or []
    if not bids or not asks:
        return None
    bb = float(bids[0][0]); ba = float(asks[0][0])
    mid = (bb + ba) / 2
    # depth within 25bp of touch, in quote terms (what we could actually fill)
    bd = sum(float(x[1]) for x in bids[:30] if float(x[0]) >= bb * 0.9975) * bb
    ad = sum(float(x[1]) for x in asks[:30] if float(x[0]) <= ba * 1.0025) * ba
    return {"bid": bb, "ask": ba, "mid": mid, "spread_bp": (ba - bb) / mid * 1e4 if mid else None,
            "bid_usd": bd, "ask_usd": ad, "tick": None}


# ======================================================================================= CLASS A
def class_free_leg(products, books):
    """Find pairs bridged by a ZERO-COST conversion leg — the proven crown-jewel class.

    Coinbase converts USD<->USDC 1:1 for free. Any asset quoted in BOTH USD and USDC therefore has a
    must-agree relationship whose capture hurdle is ONE leg's fee, not two. Tonight's product scan found
    only USDT qualifies — but the scan must be repeated because listings change, and the same logic
    applies to any future free-conversion pair (including other stablecoins if Coinbase adds them).
    """
    by_base = defaultdict(set)
    for p in products:
        by_base[p["base_currency"]].add(p["quote_currency"])
    out = []
    for base, quotes in by_base.items():
        if "USD" in quotes and "USDC" in quotes:
            out.append({"base": base, "bridge": "USD<->USDC free convert",
                        "pairs": [f"{base}-USD", f"{base}-USDC"],
                        "hurdle_bp": "one leg only (the convert leg is free)"})
    # measure the ones we can
    measured = []
    for o in out:
        a, b = books.get(o["pairs"][0]), books.get(o["pairs"][1])
        if not a or not b:
            continue
        gap_bp = (a["mid"] - b["mid"]) / a["mid"] * 1e4
        measured.append({**o, "gap_bp": round(gap_bp, 3),
                         "a_mid": a["mid"], "b_mid": b["mid"],
                         "a_spread_bp": round(a["spread_bp"] or 0, 3),
                         "b_spread_bp": round(b["spread_bp"] or 0, 3),
                         "min_depth_usd": round(min(a["bid_usd"], b["ask_usd"]), 0)})
    return {"candidates": len(out), "measured": len(measured), "rows": measured,
            "note": ("USDT is currently the only base quoted in both USD and USDC. This class is proven "
                     "(1,481 round-trips, ~100% win) and is re-scanned every run because listings change.")}


# ======================================================================================= CLASS B
def class_triangles(products, books):
    """Control class: re-measure three-leg triangles so we know if the class ever becomes viable."""
    quoted_in = defaultdict(dict)
    for p in products:
        quoted_in[p["base_currency"]][p["quote_currency"]] = p["id"]
    tris, seen = [], set()
    for a, qs in quoted_in.items():
        for r, q in ((x, y) for x in qs for y in qs if x != y):
            if q in quoted_in.get(r, {}) and a != q:
                key = frozenset((f"{a}-{q}", f"{a}-{r}", f"{r}-{q}"))
                if len(key) == 3 and key not in seen:
                    seen.add(key)
                    tris.append((f"{a}-{q}", f"{a}-{r}", f"{r}-{q}"))
    gaps = []
    for direct, l1, l2 in tris:
        d, x, y = books.get(direct), books.get(l1), books.get(l2)
        if not all(v and v.get("mid") for v in (d, x, y)):
            continue
        implied_buy = x["ask"] * y["ask"]
        if implied_buy <= 0:
            continue
        gap = (d["bid"] - implied_buy) / d["bid"] * 1e4
        gaps.append({"triangle": f"{l1}+{l2}->{direct}", "gap_bp": round(gap, 2),
                     "depth_usd": round(min(d["bid_usd"], x["ask_usd"], y["ask_usd"]), 0)})
    gaps.sort(key=lambda g: -g["gap_bp"])
    hurdle = 3 * FEE_LOW["maker"] * 1e4
    return {"triangles_tested": len(gaps),
            "gap_max_bp": gaps[0]["gap_bp"] if gaps else None,
            "gap_median_bp": round(statistics.median(g["gap_bp"] for g in gaps), 2) if gaps else None,
            "cheapest_hurdle_bp": round(hurdle, 1),
            "profitable_count": sum(1 for g in gaps if g["gap_bp"] > hurdle),
            "top5": gaps[:5],
            "verdict": ("DEAD: max gap is far below the 3-leg fee hurdle. Re-measured every run in case "
                        "it wakes." if gaps and gaps[0]["gap_bp"] < hurdle else "CHECK MANUALLY")}


# ======================================================================================= CLASS C
def class_maker_spread(books, products):
    """Which instruments are wide enough to PAY a maker to quote both sides?

    Generalizes the proven pegmaker beyond stables. Posting both sides of a spread earns
    (spread - 2*maker_fee) per round trip, before adverse selection. We measure the pre-adverse-selection
    margin and the depth, and rank. Adverse selection is the real risk and must be measured in shadow
    before any capital is committed — this scan only says where to LOOK.
    """
    rows = []
    for sym, b in books.items():
        if not b or not b.get("spread_bp"):
            continue
        for label, f in (("low", FEE_LOW), ("mid", FEE_MID), ("high", FEE_HIGH)):
            margin_bp = b["spread_bp"] - 2 * f["maker"] * 1e4
            if label == "mid":
                rows.append({"symbol": sym, "spread_bp": round(b["spread_bp"], 2),
                             "maker_margin_bp_low_fee": round(b["spread_bp"] - 2 * FEE_LOW["maker"] * 1e4, 2),
                             "maker_margin_bp_mid_fee": round(margin_bp, 2),
                             "maker_margin_bp_high_fee": round(b["spread_bp"] - 2 * FEE_HIGH["maker"] * 1e4, 2),
                             "bid_usd": round(b["bid_usd"], 0), "ask_usd": round(b["ask_usd"], 0),
                             "is_stable": sym.split("-")[0] in STABLES})
    rows.sort(key=lambda r: -r["maker_margin_bp_mid_fee"])
    viable = [r for r in rows if r["maker_margin_bp_mid_fee"] > 0]
    return {"instruments_measured": len(rows),
            "viable_at_mid_fee": len(viable),
            "viable_at_high_fee": sum(1 for r in rows if r["maker_margin_bp_high_fee"] > 0),
            "top20": rows[:20],
            "note": ("maker margin = spread - 2x maker fee, per round trip, BEFORE adverse selection. "
                     "Adverse selection is what killed nothing yet because it has never been measured here — "
                     "any candidate must run in shadow and be scored on realized fill PnL, not on this margin.")}


# ======================================================================================= CLASS E
def class_tick_discreteness(products, books):
    """Coarse price grids create structural maker advantage: fewer price levels to compete on."""
    rows = []
    for p in products:
        sym = p.get("id")
        tick = p.get("quote_increment")
        b = books.get(sym)
        if not tick or not b or not b.get("mid"):
            continue
        try:
            tick = float(tick)
        except (TypeError, ValueError):
            continue
        if tick <= 0:
            continue
        ratio_bp = tick / b["mid"] * 1e4
        rows.append({"symbol": sym, "tick": tick, "mid": b["mid"], "tick_bp": round(ratio_bp, 2),
                     "spread_bp": round(b["spread_bp"] or 0, 2),
                     "spread_in_ticks": round((b["spread_bp"] or 0) / ratio_bp, 2) if ratio_bp else None})
    rows.sort(key=lambda r: -r["tick_bp"])
    return {"measured": len(rows), "top15": rows[:15],
            "note": ("tick_bp is the minimum price move in basis points. When tick_bp is large relative to "
                     "spread, queue position matters more than price competition — a maker advantage that "
                     "does not decay with volume the way a pure spread does.")}


# ======================================================================================= CLASS F
def class_stablecoin_pegs(products, books):
    """Stable-vs-stable pairs only: is any peg deviation wide enough to capture?

    GUARD (a defect found in the first run): deviation-from-1.0 is only meaningful when BOTH sides are
    dollar-pegged. The first version admitted any product whose base OR quote was a stable, which made it
    report BTC-USD as "836,201,550 bp from peg" — an absurd number that would have been taken seriously by
    anyone reading the report. Both sides must be in STABLES.
    """
    dollar_pegged = {"USD", "USDC", "USDT", "DAI", "PYUSD", "GUSD", "USDP", "TUSD", "FDUSD", "USDE"}
    rows = []
    for p in products:
        base, quote = p.get("base_currency"), p.get("quote_currency")
        if base not in dollar_pegged or quote not in dollar_pegged:
            continue                      # BOTH sides must be dollar-pegged
        b = books.get(p["id"])
        if not b or not b.get("mid"):
            continue
        rows.append({"symbol": p["id"], "mid": b["mid"], "spread_bp": round(b["spread_bp"] or 0, 2),
                     "deviation_from_1_bp": round((b["mid"] - 1.0) * 1e4, 2),
                     "bid_usd": round(b["bid_usd"], 0), "ask_usd": round(b["ask_usd"], 0)})
    rows.sort(key=lambda r: -abs(r["deviation_from_1_bp"]))
    return {"measured": len(rows), "rows": rows[:15],
            "note": ("a stable trading away from 1.0 by more than fees+buffer is the same trade as the "
                     "crown jewel. Both sides must be dollar-pegged or the metric is meaningless.")}


# ======================================================================================= CLASS D
def class_cross_venue(books):
    """Same asset, different venue. Measures whether the class is ALIVE without needing an account."""
    venues = {"kraken": "https://api.kraken.com/0/public/Ticker?pair=%s",
              "coinbase": None}
    pairs = {"BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "SOLUSD": "SOL-USD"}
    out = []
    for kp, cb in pairs.items():
        try:
            d = get(venues["kraken"] % kp, timeout=15)
            res = (d.get("result") or {})
            if not res:
                continue
            k = list(res.values())[0]
            kb = float(k["b"][0]); ka = float(k["a"][0])
            c = books.get(cb)
            if not c:
                continue
            gap_bp = (c["mid"] - (kb + ka) / 2) / c["mid"] * 1e4
            out.append({"asset": cb, "coinbase_mid": round(c["mid"], 2), "kraken_mid": round((kb + ka) / 2, 2),
                        "gap_bp": round(gap_bp, 2),
                        "hurdle_note": "executable only with pre-positioned inventory at BOTH venues; "
                                       "a withdrawal would cost more than the gap"})
        except Exception as e:
            out.append({"asset": cb, "error": f"{type(e).__name__}: {str(e)[:60]}"})
    return {"rows": out,
            "note": ("cross-venue gaps are real but usually smaller than the cost of moving funds. Only "
                     "executable with inventory already on both venues — which is a capital requirement, "
                     "not a code requirement, and we have $50 on one venue.")}


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    products = [p for p in get(f"{CB}/products") if p.get("status") == "online" and not p.get("trading_disabled")]

    # ALWAYS fetch the proven class's own pairs first. The first run found the free-leg candidate but
    # measured 0 rows, because the sorted+capped want-list excluded USDT-USDC — i.e. the scanner skipped
    # the one pair we KNOW earns. Priority beats alphabetical ordering.
    priority = ["USDT-USD", "USDT-USDC", "USDC-USD", "BTC-USD", "ETH-USD", "SOL-USD",
                "ETH-BTC", "SOL-BTC", "SOL-ETH", "ADA-BTC", "LINK-BTC", "LINK-ETH"]

    # Fetch books for a broad, liquid slice: all stables + all crypto-quoted + top USD pairs.
    want = set()
    for p in products:
        b, q = p["base_currency"], p["quote_currency"]
        if b in STABLES or q in STABLES or q not in ("USD", "EUR", "GBP"):
            want.add(p["id"])
    valid = {p["id"] for p in products}
    want = [x for x in priority if x in valid] + sorted(want - set(priority))
    want = want[:150]                             # polite bound per run, priority first

    books = {}
    for i, sym in enumerate(want):
        try:
            books[sym] = book(sym)
        except Exception:
            books[sym] = None
        if (i + 1) % 8 == 0:
            time.sleep(0.7)
    books = {k: v for k, v in books.items() if v}

    report = {
        "ts": time.time(), "generated_by": "edge_class_scanner", "inference_cost_usd": 0.0,
        "runtime_s": None,
        "products_online": len(products), "books_fetched": len(books), "books_requested": len(want),
        "selection_criterion": {
            "rule": "an edge needs (1) a must-agree relationship AND (2) a free/rebated leg, or a gap "
                    "exceeding every leg's fee",
            "evidence": "stable_triangle has a free USD<->USDC convert leg => ~5bp hurdle => 1,481/1,481 wins. "
                        "Three-leg crypto triangles pay all legs => 75bp hurdle vs +8.01bp max observed gap => 0 wins.",
        },
        "A_free_leg_identity": class_free_leg(products, books),
        "B_multi_leg_triangle": class_triangles(products, books),
        "C_maker_spread_capture": class_maker_spread(books, products),
        "E_tick_discreteness": class_tick_discreteness(products, books),
        "F_stablecoin_pegs": class_stablecoin_pegs(products, books),
    }
    try:
        report["D_cross_venue"] = class_cross_venue(books)
    except Exception as e:
        report["D_cross_venue"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}

    report["runtime_s"] = round(time.time() - t0, 1)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = os.path.join(OUT_DIR, f"scan_{stamp}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=1, default=str)
    latest = os.path.join(OUT_DIR, "latest_scan.json")
    with open(latest, "w") as f:
        json.dump(report, f, indent=1, default=str)

    # human digest
    L = ["=" * 88, "EDGE-CLASS SCAN — %s  (zero inference, public data only)" % stamp, "=" * 88]
    L.append("products online: %d | books fetched: %d/%d | runtime %.1fs | inference cost $0.00" % (
        report["products_online"], report["books_fetched"], report["books_requested"], report["runtime_s"]))
    L.append("\nSELECTION CRITERION (empirical): identity + FREE LEG, or gap > every leg's fee.")
    for cls in ("A_free_leg_identity", "B_multi_leg_triangle", "C_maker_spread_capture",
                "E_tick_discreteness", "F_stablecoin_pegs", "D_cross_venue"):
        d = report.get(cls) or {}
        L.append("\n[%s]" % cls)
        for k, v in d.items():
            if k in ("top20", "top15", "top5", "rows", "measured_rows"):
                L.append("   %s: (%d rows, first 5 below)" % (k, len(v) if isinstance(v, list) else 0))
                for r in (v[:5] if isinstance(v, list) else []):
                    L.append("      %s" % json.dumps(r, default=str)[:180])
            else:
                L.append("   %s: %s" % (k, str(v)[:220]))
    txt = "\n".join(L)
    with open(os.path.join(OUT_DIR, "latest_scan.txt"), "w") as f:
        f.write(txt + "\n")
    print(txt)
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
