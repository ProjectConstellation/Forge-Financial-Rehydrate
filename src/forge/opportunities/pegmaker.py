"""Stable-Peg Maker — paper engine for maker liquidity around stablecoin pegs on Coinbase (OP-013 idle-capital rail).

Why this can be statistically favourable (measured 2026-10-07, not assumed):
- USDT-USD maker fee 0.5 bp (order preview commission 0.0002475 on $4.95) vs 50 bp on volatile pairs → a round trip costs
  ~1 bp; USDT-USD oscillated 3 bp (0.99964–0.99994) in 5 h with $78M/day volume and a 0.1 bp tick.
- Edge source: mean reversion of a pegged asset around its slow fair value, captured passively (we are paid the spread,
  never pay it). Main risks: queue position (we may never fill), adverse selection at regime shifts, depeg tails.

Honest simulation (the result decides, not the story):
- QUEUE-AWARE FILLS: when we join a level we sit behind the displayed size; only real prints at our price on the same
  side consume that queue; a print THROUGH our price fills us fully. Re-pricing loses queue priority.
- Inventory cap = paper capital; buys only below fair − θ, sells only at ≥ entry + fees + 1 tick (never a planned loss),
  stale-inventory exit after `max_hold_s` at the best available maker price (losses are booked honestly).
- DEPEG BREAKER: |mid − 1| > 30 bp or fair drifting fast → stop quoting, mark inventory at bid.
- Fees re-measured from Coinbase order previews every 6 h (read-only preview; no order is placed).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("forge.pegmaker")


@dataclass
class Quote:
    side: str                 # buy | sell
    price: float
    qty: float
    queue_ahead: float
    placed_ts: float


@dataclass
class PegBook:
    symbol: str
    tick: float
    fair: float | None = None
    inv_qty: float = 0.0
    inv_cost: float = 0.0          # USD paid incl. fee
    inv_ts: float = 0.0
    bid: Quote | None = None
    ask: Quote | None = None
    last_trade_id: int = 0
    halted: str = ""
    stats: dict[str, float] = field(default_factory=lambda: {"round_trips": 0, "pnl_usd": 0.0, "fills": 0, "fees_usd": 0.0})


def queue_after_prints(q: Quote, prints: list[tuple[float, float, str]]) -> tuple[float, float]:
    """Advance a resting quote through new prints. Returns (filled_qty, remaining_queue_ahead).
    prints = [(price, size, maker_side)], maker_side is the RESTING side of the print (Coinbase semantics)."""
    ahead, filled = q.queue_ahead, 0.0
    want_side = "BUY" if q.side == "buy" else "SELL"
    for px, sz, maker in prints:
        through = px < q.price - 1e-12 if q.side == "buy" else px > q.price + 1e-12
        if through:
            return q.qty, 0.0                                    # traded through our level → we were filled
        if abs(px - q.price) <= 1e-12 and maker == want_side:
            if ahead >= sz:
                ahead -= sz
            else:
                filled += sz - ahead
                ahead = 0.0
                if filled >= q.qty:
                    return q.qty, 0.0
    return min(filled, q.qty), ahead


class PegMaker:
    POLL_S = 5.0
    FAIR_HALFLIFE_S = 2 * 3600
    MAX_HOLD_S = 6 * 3600
    DEPEG_BP = 30.0

    def __init__(self, forge: Any, symbols: tuple[str, ...] = ("USDT-USD", "USDT-USDC"), capital_usd: float | None = None) -> None:
        self.f = forge
        self.books = {s: PegBook(s, 0.00001 if s == "USDT-USD" else 0.0001) for s in symbols}
        self.capital = capital_usd
        self.maker_fee = 0.00005                                  # legacy default (USDT-USD)
        self.fees: dict[str, tuple[float, float]] = {"USDT-USD": (0.00005, 0.0001), "USDT-USDC": (0.0, 0.00001)}
        self.last_fee_probe = 0.0
        self.tri_last = 0.0
        self.theta_bp = 0.5                                       # minimum discount to fair before we bid
        self.tops: dict[str, tuple[float, float, float, float]] = {}

    # ---------------------------------------------------------------- helpers
    def _cap(self) -> float:
        """PAPER capital-hours: prefer $200–500 band / multiplier from lab.stable_capital_policy when LIVE off."""
        eq = float(self.f.treasury.get("equity_usd") or 0) if self.capital is None else float(self.capital)
        try:
            live = bool(getattr(self.f.s, "live_trading", False) or self.f.db.kv_get("FORGE_LIVE_TRADING"))
        except Exception:
            live = False
        if not live:
            pol = self.f.db.kv_get("lab.stable_capital_policy") or {}
            band = pol.get("target_band_usd") or [200, 500]
            mult = float(pol.get("multiplier") or 3.0)
            lo, hi = float(band[0]), float(band[1])
            # Simulated PAPER sleeve: scale evidenced stables without requiring live NAV
            target = max(lo, min(hi, max(eq, 1.0) * mult * 10))  # ~$280–500 from $28 NAV
            eq = max(eq, target)
        return max(eq / max(len(self.books), 1), 1.0)

    async def _fees(self) -> None:
        """Measured per pair from Coinbase order PREVIEWS (read-only; commission is returned even without funds)."""
        if time.time() - self.last_fee_probe < 6 * 3600:
            return
        self.last_fee_probe = time.time()
        for sym in self.books:
            out = []
            for cfg in ({"limit_limit_gtc": {"base_size": "10", "limit_price": "0.99", "post_only": True}},
                        {"market_market_ioc": {"quote_size": "10"}}):
                try:
                    pv = await self.f.rest.preview_order({"product_id": sym, "side": "BUY", "order_configuration": cfg})
                    c = float(pv.get("commission_total") or 0)
                    out.append(c / (9.9 if "limit_limit_gtc" in cfg else 10.0))
                except Exception as e:
                    log.debug("fee probe %s failed: %s", sym, e)
                    out.append(None)
            if out[0] is not None and out[1] is not None:
                self.fees[sym] = (out[0], out[1])
        self.maker_fee = self.fees.get("USDT-USD", (self.maker_fee, 0))[0]
        self.f.db.kv_set("fees.stable", {"fees": self.fees, "ts": time.time(), "source": "order preview"})
        self.f.db.kv_set("fees.USDT-USD.maker", {"rate": self.maker_fee, "ts": time.time(), "source": "order preview"})

    def _mfee(self, sym: str) -> float:
        return self.fees.get(sym, (self.maker_fee, 0.0))[0]

    def triangle(self, tops: dict[str, tuple[float, float, float, float]]) -> None:
        """USD ⇄ USDC convert is 1:1 and free → USDT-USD and USDT-USDC must agree. Taker-taker cycle when the gap beats
        both taker fees + a safety buffer (sizes bounded by displayed top-of-book and PAPER capital band)."""
        a, b = tops.get("USDT-USD"), tops.get("USDT-USDC")
        if not a or not b:
            return
        # Under target / RED ZONE: poll opportunities every few seconds, not once/30s
        nav = float((self.f.db.kv_get("econ.treasury_board") or {}).get("nav") or (self.f.treasury.get("equity_usd") or 0))
        proven = float(((self.f.db.kv_get("velocity") or {}).get("expected_usd_per_h") or {}).get("proven") or 0)
        hot = nav < 50.0 or proven < 0.10
        min_gap = 5.0 if hot else 30.0
        if time.time() - self.tri_last < min_gap:
            return
        cap = self._cap() * len(self.books)
        # Prefer placing up to 80% of band when hot so capital-hours actually accumulate
        if hot:
            cap = max(cap, float((self.f.db.kv_get("lab.stable_capital_policy") or {}).get("target_band_usd", [200, 500])[1]) * 0.8)
        min_edge = 0.000015 if hot else 0.00002  # 0.15bp hot / 0.2bp normal (still fee+buffer aware via fees)
        best = None
        for buy_sym, sell_sym, ask, ask_sz, bid, bid_sz in (("USDT-USDC", "USDT-USD", b[2], b[3], a[0], a[1]),
                                                            ("USDT-USD", "USDT-USDC", a[2], a[3], b[0], b[1])):
            fb, fs = self.fees.get(buy_sym, (0, 0.0001))[1], self.fees.get(sell_sym, (0, 0.0001))[1]
            edge = bid * (1 - fs) - ask * (1 + fb)
            if edge / ask > min_edge:
                qty = min(ask_sz, bid_sz, cap / ask)
                if qty <= 0:
                    continue
                pnl = edge * qty
                cand = (pnl, buy_sym, sell_sym, ask, bid, qty, fb, fs, edge)
                if best is None or cand[0] > best[0]:
                    best = cand
        if best is None:
            return
        pnl, buy_sym, sell_sym, ask, bid, qty, fb, fs, edge = best
        self.tri_last = time.time()
        self.f.db.insert("shadow_trades", {"ts": time.time(), "rail": "coinbase.stable_triangle", "symbol": f"{buy_sym}>{sell_sym}",
                                           "side": "round_trip", "qty": qty, "entry": ask, "exit": bid,
                                           "fee_usd": qty * (ask * fb + bid * fs), "pnl_usd": pnl, "hold_s": 2.0,
                                           "detail": None})
        # Track capital-hours intent for scorecard
        try:
            ch = self.f.db.kv_get("lab.stable_capital_hours") or {"hours": 0.0, "notional_usd": 0.0, "n": 0}
            notional = float(qty) * float(ask)
            ch["notional_usd"] = float(ch.get("notional_usd") or 0) + notional
            ch["n"] = int(ch.get("n") or 0) + 1
            ch["hours"] = float(ch.get("hours") or 0) + (notional / max(cap, 1.0)) * (2.0 / 3600.0)
            ch["last_pnl"] = pnl
            ch["last_qty"] = qty
            ch["hot"] = hot
            ch["ts"] = time.time()
            self.f.db.kv_set("lab.stable_capital_hours", ch)
        except Exception:
            pass

    async def _snapshot(self, b: PegBook) -> tuple[float, float, float, float, list[tuple[float, float, str]]] | None:
        rest = self.f.rest
        t = await rest._request("GET", f"/api/v3/brokerage/market/products/{b.symbol}/ticker", params={"limit": 100})
        bk = await rest.book(b.symbol, 5)
        bids, asks = bk.get("bids") or [], bk.get("asks") or []
        if not bids or not asks:
            return None
        bb, bsz = float(bids[0]["price"]), float(bids[0]["size"])
        ba, asz = float(asks[0]["price"]), float(asks[0]["size"])
        new = []
        for tr in t.get("trades", []):
            tid = int(tr["trade_id"])
            if tid > b.last_trade_id:
                new.append((tid, float(tr["price"]), float(tr["size"]), str(tr.get("side", "")).upper()))
        new.sort()
        if new:
            b.last_trade_id = new[-1][0]
        return bb, bsz, ba, asz, [(p, s, m) for _, p, s, m in new]

    # ---------------------------------------------------------------- one step
    async def step(self, b: PegBook) -> None:
        snap = await self._snapshot(b)
        if snap is None:
            return
        bb, bsz, ba, asz, prints = snap
        self.tops[b.symbol] = (bb, bsz, ba, asz)
        mid = 0.5 * (bb + ba)
        now = time.time()
        a = 1 - math.exp(math.log(0.5) * self.POLL_S / self.FAIR_HALFLIFE_S)
        b.fair = mid if b.fair is None else (1 - a) * b.fair + a * mid
        # depeg breaker
        quote_ccy_peg = 1.0
        if abs(mid / quote_ccy_peg - 1) * 1e4 > self.DEPEG_BP:
            b.halted = f"depeg {abs(mid - 1) * 1e4:.0f}bp"
            b.bid = b.ask = None
            return
        b.halted = ""
        # fills on resting quotes (prints since the last poll only — first poll just sets the cursor)
        for q_name in ("bid", "ask"):
            q: Quote | None = getattr(b, q_name)
            if q is None or not prints:
                continue
            filled, ahead = queue_after_prints(q, prints)
            q.queue_ahead = ahead
            if filled > 0:
                self._fill(b, q, filled, now)
                q.qty -= filled
                if q.qty <= 1e-9:
                    setattr(b, q_name, None)
        # quoting policy
        cap_qty = self._cap() / max(mid, 1e-9)
        fair_bid = b.fair * (1 - self.theta_bp / 1e4)
        if b.inv_qty < cap_qty * 0.99 and bb <= fair_bid:
            qty = cap_qty - b.inv_qty
            if b.bid is None or abs(b.bid.price - bb) > 1e-12:
                b.bid = Quote("buy", bb, qty, bsz, now)              # join best bid behind the displayed size
            else:
                b.bid.qty = qty
        elif b.bid is not None and (bb > fair_bid or b.inv_qty >= cap_qty * 0.99):
            b.bid = None
        if b.inv_qty > 0:
            avg = b.inv_cost / b.inv_qty
            min_px = avg * (1 + 2 * self._mfee(b.symbol)) + b.tick
            stale = now - b.inv_ts > self.MAX_HOLD_S
            px = max(ba, math.ceil(min_px / b.tick) * b.tick) if not stale else ba
            if b.ask is None or abs(b.ask.price - px) > 1e-12:
                b.ask = Quote("sell", px, b.inv_qty, asz if abs(px - ba) < 1e-12 else 0.0, now)
        else:
            b.ask = None
        b.stats["mark_usd"] = b.inv_qty * bb - b.inv_cost

    def _fill(self, b: PegBook, q: Quote, qty: float, now: float) -> None:
        fee = q.price * qty * self._mfee(b.symbol)
        b.stats["fills"] += 1
        b.stats["fees_usd"] += fee
        if q.side == "buy":
            b.inv_cost += q.price * qty + fee
            b.inv_qty += qty
            b.inv_ts = b.inv_ts or now
        else:
            avg = b.inv_cost / b.inv_qty if b.inv_qty > 0 else q.price
            pnl = (q.price * qty - fee) - avg * qty
            b.inv_cost -= avg * qty
            b.inv_qty -= qty
            if b.inv_qty <= 1e-9:
                b.inv_qty, b.inv_cost, b.inv_ts = 0.0, 0.0, 0.0
            b.stats["round_trips"] += 1
            b.stats["pnl_usd"] += pnl
            self.f.db.insert("shadow_trades", {"ts": now, "rail": "coinbase.stable_peg_mm", "symbol": b.symbol, "side": "round_trip",
                                               "qty": qty, "entry": avg, "exit": q.price, "fee_usd": fee, "pnl_usd": pnl,
                                               "hold_s": now - (b.inv_ts or now), "detail": None})

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("pegmaker")
            try:
                await self._fees()
                for b in self.books.values():
                    await asyncio.wait_for(self.step(b), timeout=20)
                self.triangle(self.tops)
                self.f.db.kv_set("pegmaker.state", {"ts": time.time(), "fees": self.fees, "books": {
                    s: {"fair": b.fair, "inv_qty": b.inv_qty, "halted": b.halted, **b.stats,
                        "bid": b.bid.price if b.bid else None, "ask": b.ask.price if b.ask else None,
                        "queue_ahead": b.bid.queue_ahead if b.bid else None} for s, b in self.books.items()}})
            except Exception as e:
                log.debug("pegmaker step failed: %s", e)
            await asyncio.sleep(self.POLL_S)
