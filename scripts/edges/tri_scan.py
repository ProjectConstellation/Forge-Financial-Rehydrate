"""TRIANGULAR-IDENTITY SCANNER — deterministic, zero inference, public data only.

THE HYPOTHESIS (same class as the crown jewel): if ADA-BTC, ADA-ETH and ETH-BTC all trade on one venue,
then by transitivity ETH/BTC implied through ADA must equal the directly quoted ETH-BTC. A deviation above
the cost of executing the cycle is an identity violated, not a forecast.

WHAT THIS MEASURES (rather than assumes): for every closed triangle in Coinbase's cross-pair graph, the
implied-vs-direct price gap in basis points, versus the fee cost of actually capturing it. That answers
"does this edge exist here" with data instead of optimism.

IMPORTANT HONESTY NOTE, stated up front: unlike the USDT triangle (where Coinbase converts USD<->USDC
1:1 for FREE, so one leg costs nothing), a pure crypto triangle pays taker/maker fees on ALL THREE legs.
So the hurdle is much higher. This scanner measures the hurdle and the observed gaps in the same units so
the comparison is real. It also tests the MAKER variant, because posting rather than crossing changes the
hurdle dramatically — and a maker-rebate leg can turn a negative cycle positive.

Public endpoints, no key, no orders, no inference. Rate-limited politely.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import defaultdict
from itertools import combinations

BASE = "https://api.exchange.coinbase.com"
UA = {"User-Agent": "forge-research/1.0", "Accept": "application/json"}

# Coinbase Advanced Trade published structure: maker/taker vary by 30-day-volume tier, and STABLECOIN
# pairs have their own lower schedule. We do NOT assert exact tier numbers (login-only); we test the cycle
# across a RANGE of plausible fee assumptions so the conclusion does not depend on a guessed constant.
FEE_SCENARIOS = {
    "taker_intro_high":  {"maker": 0.0040, "taker": 0.0060},   # plausible low-volume taker
    "taker_typical":     {"maker": 0.0025, "taker": 0.0040},
    "maker_only":        {"maker": 0.0025, "taker": 0.0040},   # all legs posted as maker
    "our_hardcoded":     {"maker": 0.0050, "taker": 0.0090},   # what spot currently assumes
}


def get(path, params=None, timeout=20):
    url = BASE + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    out = {"ts": time.time()}

    prods = [p for p in get("/products")
             if p.get("status") == "online" and not p.get("trading_disabled")]
    out["online_products"] = len(prods)

    # Build the graph: which bases are quoted in which quotes.
    quoted_in = defaultdict(dict)      # base -> {quote: product_id}
    for p in prods:
        quoted_in[p["base_currency"]][p["quote_currency"]] = p["id"]

    # Candidate triangles: A-Q, A-R, R-Q all exist => A/Q via R must equal A/Q direct.
    triangles = []
    for a, qs in quoted_in.items():
        for r, q in combinations(qs.keys(), 2):
            # need A-R and R-Q (or Q-R) to bridge
            if r in quoted_in.get(a, {}) and q in quoted_in.get(r, {}):
                triangles.append({"direct": f"{a}-{q}", "via": r,
                                  "leg1": f"{a}-{r}", "leg2": f"{r}-{q}"})
            if q in quoted_in.get(a, {}) and r in quoted_in.get(q, {}):
                triangles.append({"direct": f"{a}-{r}", "via": q,
                                  "leg1": f"{a}-{q}", "leg2": f"{q}-{r}"})
    # de-duplicate on the frozenset of the three symbols
    seen = set()
    uniq = []
    for t in triangles:
        key = frozenset((t["direct"], t["leg1"], t["leg2"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    out["triangles_found"] = len(uniq)
    out["triangle_list"] = [{"direct": t["direct"], "via": t["via"]} for t in uniq]

    # Fetch books for every symbol involved (polite rate limit: public API allows ~10 rps)
    syms = sorted({s for t in uniq for s in (t["direct"], t["leg1"], t["leg2"])})
    out["symbols_to_fetch"] = len(syms)
    books = {}
    for i, sym in enumerate(syms):
        try:
            d = get(f"/products/{sym}/book", {"level": "2"})
            bids = d.get("bids") or []
            asks = d.get("asks") or []
            if not bids or not asks:
                continue
            bb = float(bids[0][0]); ba = float(asks[0][0])
            bsz = float(bids[0][1]); asz = float(asks[0][1])
            # depth within 25bp of the touch — what we could actually fill
            bb_d = sum(float(x[1]) for x in bids[:20] if float(x[0]) >= bb * 0.9975)
            ba_d = sum(float(x[1]) for x in asks[:20] if float(x[0]) <= ba * 1.0025)
            books[sym] = {"bid": bb, "ask": ba, "mid": (bb + ba) / 2,
                          "bid_depth": bb_d, "ask_depth": ba_d,
                          "bid_usd_depth": bb_d * bb, "ask_usd_depth": ba_d * ba,
                          "spread_bp": (ba - bb) / ((bb + ba) / 2) * 1e4}
        except Exception as e:
            books[sym] = {"error": f"{type(e).__name__}: {str(e)[:60]}"}
        if (i + 1) % 5 == 0:
            time.sleep(0.6)

    out["books_fetched"] = sum(1 for v in books.values() if "bid" in v)
    out["books_failed"] = sum(1 for v in books.values() if "error" in v)

    # ---- evaluate every triangle, both crossing (taker) and posting (maker) ----
    results = []
    for t in uniq:
        d, l1, l2 = books.get(t["direct"]), books.get(t["leg1"]), books.get(t["leg2"])
        if not all(x and "bid" in x for x in (d, l1, l2)):
            continue
        # implied price of A/Q going through R:  (A-R) * (R-Q)
        # two directions matter; use executable prices for the direction that would actually be traded.
        # Direction 1: buy A with R (pay l1 ask), buy R with Q (pay l2 ask) => cost of A in Q
        implied_buy = l1["ask"] * l2["ask"]
        # sell A for R (get l1 bid), sell R for Q (get l2 bid) => proceeds of A in Q
        implied_sell = l1["bid"] * l2["bid"]
        direct_bid, direct_ask = d["bid"], d["ask"]

        # Arb A: buy A cheaply via the cross legs, sell A directly into the bid
        gap_a = (direct_bid - implied_buy) / direct_bid * 1e4
        # Arb B: buy A directly at the ask, sell it via the cross legs
        gap_b = (implied_sell - direct_ask) / direct_ask * 1e4

        # executable size: limited by the thinnest leg (in quote terms)
        size_usd = min(d["bid_usd_depth"], l1["ask_usd_depth"], l2["ask_usd_depth"])
        size_usd_b = min(d["ask_usd_depth"], l1["bid_usd_depth"], l2["bid_usd_depth"])

        for name, gap_bp, depth in (("buy_cross_sell_direct", gap_a, size_usd),
                                    ("buy_direct_sell_cross", gap_b, size_usd_b)):
            for scen, fees in FEE_SCENARIOS.items():
                rate = fees["taker"] if "taker" in scen else fees["maker"]
                cost_bp = 3 * rate * 1e4          # three legs
                results.append({
                    "triangle": f"{t['leg1']}+{t['leg2']}->{t['direct']}", "via": t["via"],
                    "direction": name, "gap_bp": round(gap_bp, 2),
                    "fee_scenario": scen, "cost_bp": round(cost_bp, 1),
                    "net_bp": round(gap_bp - cost_bp, 2),
                    "depth_usd": round(depth, 0),
                    "profitable": gap_bp - cost_bp > 0,
                })

    results.sort(key=lambda x: -x["gap_bp"])
    out["evaluations"] = len(results)
    out["top_gaps"] = results[:24]

    # summarise by scenario: does ANY triangle clear the hurdle?
    summary = {}
    for scen in FEE_SCENARIOS:
        rows = [r for r in results if r["fee_scenario"] == scen]
        prof = [r for r in rows if r["profitable"]]
        summary[scen] = {
            "cost_bp_per_cycle": round(3 * FEE_SCENARIOS[scen]["taker" if "taker" in scen else "maker"] * 1e4, 1),
            "triangles_evaluated": len(rows),
            "gap_bp_max": max((r["gap_bp"] for r in rows), default=None),
            "gap_bp_median": sorted(r["gap_bp"] for r in rows)[len(rows) // 2] if rows else None,
            "profitable_count": len(prof),
            "best": prof[0] if prof else None,
        }
    out["summary_by_fee_scenario"] = summary

    # Write the FULL result to a file (never truncate JSON mid-string) and print only the summary.
    path = "/srv/forge/var/reports/edges/tri_scan_latest.json"
    import os as _os
    _os.makedirs(_os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("wrote", path)
    print(json.dumps({k: v for k, v in out.items()
                      if k in ("ts","online_products","triangles_found","symbols_to_fetch",
                               "books_fetched","books_failed","evaluations",
                               "summary_by_fee_scenario")}, indent=1, default=str))
    print("\nTOP GAPS:")
    for r in out["top_gaps"][:14]:
        print("  %-46s %-22s gap=%+8.2fbp cost=%.0fbp net=%+8.2fbp depth=$%s %s" % (
            r["triangle"], r["direction"], r["gap_bp"], r["cost_bp"], r["net_bp"], r["depth_usd"],
            "PROFITABLE" if r["profitable"] else ""))


if __name__ == "__main__":
    main()
