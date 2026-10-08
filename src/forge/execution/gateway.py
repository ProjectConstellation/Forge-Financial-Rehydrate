"""Execution Gateway + Position Manager (DOSSIER §23, §35; DIRECTIVE §32; OP-009 §3 execution alpha). PROTECTED CORE.

Pipeline: approved intent → OrderRequest (deterministic client_order_id) → persisted PENDING *before* sending
(crash safety) → venue → ack/ambiguous → monitored until terminal → fills posted to ledger idempotently
(unique trade ids) → position state machine → exits.

Entries are maker-first (post-only, priced from the live book); unfilled makers expire at their TTL (the edge
decays) and may be converted to taker only if the remaining expected edge still exceeds taker cost.
Take-profits rest as post-only limits (paid as maker); stops/trailing/time-stops are monitored by the engine on
live prices and executed as market orders. An order that times out after submit is UNKNOWN — never assumed
failed — and is reconciled against the venue by client_order_id.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any

from forge.audit.journal import AuditJournal
from forge.core.ids import idempotency_key, new_id
from forge.domain.market import BestBidAsk, MarketRules, d
from forge.domain.trading import (
    TERMINAL,
    ExitPlan,
    IntentPurpose,
    OrderRequest,
    OrderStatus,
    RiskDecision,
    TradeIntent,
)
from forge.ledger.ledger import Ledger
from forge.persistence.db import Database, dumps
from forge.risk.breakers import BreakerBoard
from forge.venues.base import VenueError

log = logging.getLogger("forge.execution")


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class MarketView:
    bbo: Callable[[str], BestBidAsk | None]
    rules: Callable[[str], MarketRules | None]


class ExecutionGateway:
    def __init__(self, db: Database, ledger: Ledger, venue: Any, book: str, market: MarketView,
                 audit: AuditJournal, breakers: BreakerBoard,
                 on_event: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
                 on_position_closed: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
                 taker_fee: float = 0.009, maker_fee: float = 0.005) -> None:
        self.db, self.ledger, self.venue, self.book = db, ledger, venue, book
        self.market, self.audit, self.breakers = market, audit, breakers
        self.on_event = on_event
        self.on_position_closed = on_position_closed
        self.taker_fee, self.maker_fee = taker_fee, maker_fee
        self._unknown_attempts: dict[str, int] = {}

    async def _emit(self, kind: str, data: dict[str, Any]) -> None:
        if self.on_event:
            try:
                await self.on_event(kind, data)
            except Exception:
                log.exception("event emit failed")

    # ------------------------------------------------------------------ intents → orders
    async def execute_entry(self, intent: TradeIntent, decision: RiskDecision, ttl_s: float,
                            maker_offset_bps: float, entry_style: str, meta: dict[str, Any]) -> str | None:
        """Place an approved entry. Returns position id (OPENING) or None."""
        bbo, rules = self.market.bbo(intent.symbol), self.market.rules(intent.symbol)
        if bbo is None or rules is None:
            return None
        notional = decision.approved_notional_usd
        pid = new_id("pos")
        if entry_style == "maker":
            px = min(d(bbo.bid), d(bbo.mid * (1 - maker_offset_bps / 1e4)))
            px = rules.round_price(px, "buy")
            if float(px) >= bbo.ask:                     # never cross as maker
                px = rules.round_price(d(bbo.bid), "buy")
            base = rules.round_base(notional / (px * (1 + Decimal(str(self.maker_fee)))))
            req = OrderRequest(client_order_id=idempotency_key(intent.idem_key, "entry"), venue=intent.venue,
                               symbol=intent.symbol, side="buy", order_type="post_only", base_size=base, limit_price=px)
        else:
            req = OrderRequest(client_order_id=idempotency_key(intent.idem_key, "entry"), venue=intent.venue,
                               symbol=intent.symbol, side="buy", order_type="market", quote_size=rules.round_quote(notional))
        self.db.insert("positions", {
            "id": pid, "book": self.book, "venue": intent.venue, "symbol": intent.symbol,
            "strategy_id": intent.strategy_id, "opportunity_id": intent.opportunity_id, "status": "OPENING",
            "opened_at": _now(), "exit_plan": dumps(intent.exit_plan.model_dump() if intent.exit_plan else {}),
            "meta": dumps({**meta, "entry_cid": req.client_order_id, "ttl_deadline": time.time() + ttl_s, "ttl_s": ttl_s,
                           "quoted_at": time.time(), "notional": str(notional), "reprices": 0,
                           "decision_mid": bbo.mid, "intent_id": intent.id, "entry_style": entry_style})})
        ok = await self._submit(req, intent.id)
        if not ok:
            self.db.execute("UPDATE positions SET status = 'CLOSED', closed_at = ?, exit_reason = ? WHERE id = ?",
                            (_now(), "ENTRY_REJECTED", pid))
            return None
        self.audit.append("LIVE_ORDER_INTENT" if self.book == "live" else "PAPER_ORDER",
                          {"intent": intent.id, "cid": req.client_order_id, "symbol": req.symbol, "side": req.side,
                           "type": req.order_type, "notional": str(notional), "position": pid})
        return pid

    async def _submit(self, req: OrderRequest, intent_id: str | None) -> bool:
        if self.db.scalar("SELECT 1 FROM orders WHERE client_order_id = ?", (req.client_order_id,)):
            self.breakers.record("duplicate_order", req.client_order_id)
            log.error("duplicate client_order_id blocked: %s", req.client_order_id)
            return False
        now = _now()
        self.db.insert("orders", {          # persisted BEFORE sending (crash consistency)
            "id": new_id("ord"), "intent_id": intent_id, "book": self.book, "venue": req.venue,
            "client_order_id": req.client_order_id, "symbol": req.symbol, "side": req.side,
            "order_type": req.order_type, "limit_price": str(req.limit_price) if req.limit_price else None,
            "base_size": str(req.base_size) if req.base_size else None,
            "quote_size": str(req.quote_size) if req.quote_size else None,
            "post_only": int(req.order_type == "post_only"), "status": OrderStatus.PENDING.value,
            "submitted_at": now, "updated_at": now})
        try:
            ack = await self.venue.submit_order(req)
        except VenueError as e:
            if e.ambiguous:
                self._set_order(req.client_order_id, OrderStatus.UNKNOWN, reason=str(e))
                log.warning("order %s outcome UNKNOWN — will reconcile", req.client_order_id)
                return True
            self._set_order(req.client_order_id, OrderStatus.REJECTED, reason=str(e))
            self.breakers.record("auth_error" if e.status in (401, 403) else "exchange_reject", str(e)[:200])
            return False
        if ack.status == OrderStatus.REJECTED:
            self._set_order(req.client_order_id, OrderStatus.REJECTED, reason=ack.reject_reason)
            if ack.reject_reason not in ("POST_ONLY_WOULD_CROSS", "INSUFFICIENT_FUND"):
                self.breakers.record("exchange_reject", str(ack.reject_reason))
            return False
        self.db.execute("UPDATE orders SET venue_order_id = ?, status = ?, updated_at = ? WHERE client_order_id = ?",
                        (ack.venue_order_id, OrderStatus.OPEN.value, _now(), req.client_order_id))
        return True

    def _set_order(self, cid: str, st: OrderStatus, reason: str | None = None, **extra: Any) -> None:
        sets = ["status = ?", "updated_at = ?"]
        vals: list[Any] = [st.value, _now()]
        if reason is not None:
            sets.append("reject_reason = ?")
            vals.append(reason[:500])
        for k, v in extra.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        self.db.execute(f"UPDATE orders SET {', '.join(sets)} WHERE client_order_id = ?", (*vals, cid))

    # ------------------------------------------------------------------ monitoring
    async def tick(self, trading_state: str = "RUNNING") -> None:
        """Advance every non-terminal order and every position. Call every ~1–3 s."""
        for o in self.db.query("SELECT * FROM orders WHERE book = ? AND status IN ('PENDING','OPEN','PARTIAL','UNKNOWN')",
                               (self.book,)):
            await self._refresh_order(o)
        for p in self.db.query("SELECT * FROM positions WHERE book = ? AND status IN ('OPENING','OPEN','CLOSING')",
                               (self.book,)):
            try:
                await self._manage_position(p, trading_state)
            except VenueError as e:
                log.warning("position %s management error: %s", p["id"], e)

    async def _refresh_order(self, o: dict[str, Any]) -> None:
        cid = o["client_order_id"]
        try:
            st = await self.venue.get_order(cid, o["venue_order_id"])
        except VenueError as e:
            log.warning("get_order %s failed: %s", cid, e)
            return
        if st is None:
            if self.book == "paper" and o["status"] in (OrderStatus.OPEN.value, OrderStatus.PENDING.value,
                                                         OrderStatus.PARTIAL.value):
                # the paper venue keeps resting orders in memory → after a restart they no longer exist anywhere
                self._set_order(cid, OrderStatus.CANCELLED, reason="paper venue restarted (resting order not carried over)")
                return
            if o["status"] == OrderStatus.UNKNOWN.value:
                n = self._unknown_attempts[cid] = self._unknown_attempts.get(cid, 0) + 1
                if n >= 10:                              # venue has no record after repeated checks → never placed
                    self._set_order(cid, OrderStatus.REJECTED, reason="not found at venue after reconciliation")
            return
        await self._post_fills(o, cid, st.venue_order_id)
        self._set_order(cid, st.status if st.status != OrderStatus.UNKNOWN else OrderStatus(o["status"]),
                        venue_order_id=st.venue_order_id, filled_size=str(st.filled_size),
                        avg_fill_price=str(st.avg_fill_price) if st.avg_fill_price else None, fees=str(st.fees))

    async def _post_fills(self, o: dict[str, Any], cid: str, vid: str | None) -> None:
        fills = await self.venue.list_fills(cid, vid)
        pos = self._position_for_order(cid)
        for f in fills:
            inserted = self.db.insert("fills", {
                "order_id": cid, "book": self.book, "venue": f.venue, "trade_id": f.trade_id, "symbol": f.symbol,
                "side": f.side, "price": str(f.price), "size": str(f.size), "fee": str(f.fee),
                "liquidity": f.liquidity, "ts": _now()}, or_ignore=True)
            if not inserted:
                continue
            quote = f.symbol.split("-")[1]
            realized = self.ledger.record_fill(self.book, f.venue, f.symbol, f.side, f.price, f.size, f.fee,
                                               f.trade_id, pos["strategy_id"] if pos else None, cid, quote_asset=quote)
            if pos is not None:
                self._apply_fill_to_position(pos["id"], f.side, f.price, f.size, f.fee, realized)
            await self._emit("ORDER_FILLED", {"cid": cid, "symbol": f.symbol, "side": f.side, "price": str(f.price),
                                              "size": str(f.size), "fee": str(f.fee), "liquidity": f.liquidity,
                                              "position": pos["id"] if pos else None})
            self.audit.append("FILL", {"cid": cid, "trade_id": f.trade_id, "symbol": f.symbol, "side": f.side,
                                       "price": str(f.price), "size": str(f.size), "fee": str(f.fee), "book": self.book})

    def repair_unrecorded_fills(self) -> int:
        """Idempotent accounting repair: orders the venue reported FILLED (size, avg price, fees on the order row) whose
        fills were never recorded — paper fill ids used to restart at pt-1 after every FORGE restart, so later fills
        collided with old ids and were silently dropped. Rebuild one fill per such order from the order's own truth,
        post it to the ledger and the owning position (CLOSED positions included)."""
        n = 0
        rows = self.db.query("SELECT * FROM orders WHERE book = ? AND status = ? AND CAST(filled_size AS REAL) > 0 AND "
                             "avg_fill_price IS NOT NULL AND NOT EXISTS (SELECT 1 FROM fills f WHERE f.order_id = "
                             "orders.client_order_id)", (self.book, OrderStatus.FILLED.value))
        for o in rows:
            cid = o["client_order_id"]
            size, px, fee = Decimal(o["filled_size"]), Decimal(o["avg_fill_price"]), Decimal(o["fees"] or "0")
            tid = f"repair:{cid}"
            pos = None
            for p in self.db.query("SELECT id, strategy_id, meta FROM positions WHERE book = ?", (self.book,)):
                m = json.loads(p["meta"] or "{}")
                if cid in (m.get("entry_cid"), m.get("tp_cid"), m.get("exit_cid")):
                    pos = p
                    break
            if not self.db.insert("fills", {"order_id": cid, "book": self.book, "venue": o["venue"], "trade_id": tid,
                                            "symbol": o["symbol"], "side": o["side"], "price": str(px), "size": str(size),
                                            "fee": str(fee), "liquidity": "taker" if o["order_type"] == "market" else "maker",
                                            "ts": o["updated_at"] or _now()}, or_ignore=True):
                continue
            realized = self.ledger.record_fill(self.book, o["venue"], o["symbol"], o["side"], px, size, fee, tid,
                                               pos["strategy_id"] if pos else None, cid, quote_asset=o["symbol"].split("-")[1])
            if pos is not None:
                self._apply_fill_to_position(pos["id"], o["side"], px, size, fee, realized)
            self.audit.append("FILL_REPAIRED", {"cid": cid, "symbol": o["symbol"], "side": o["side"], "price": str(px),
                                                "size": str(size), "fee": str(fee), "realized": str(realized),
                                                "position": pos["id"] if pos else None, "book": self.book})
            n += 1
        # positions wrongly closed while still holding coins (e.g. entry fill dropped → "ENTRY_NOT_FILLED") → reopen so the
        # normal exit plan (SL / TP / time stop) manages them again instead of leaving an unmanaged orphan holding
        for p in self.db.query("SELECT id, symbol, meta, qty, cost_usd FROM positions WHERE book = ? AND status = 'CLOSED' "
                               "AND CAST(qty AS REAL) > 0", (self.book,)):
            m = json.loads(p["meta"] or "{}")
            qty = Decimal(p["qty"])
            m.update(opened_ts=time.time(), high_water=float(Decimal(p["cost_usd"]) / qty), reopened_by_repair=True)
            self.db.execute("UPDATE positions SET status = 'OPEN', closed_at = NULL, exit_reason = NULL, meta = ? WHERE id = ?",
                            (dumps(m), p["id"]))
            self.audit.append("POSITION_REOPENED", {"position": p["id"], "symbol": p["symbol"], "qty": p["qty"],
                                                    "reason": "closed while still holding (dropped fill)", "book": self.book})
            n += 1
        return n

    def _position_for_order(self, cid: str) -> dict[str, Any] | None:
        for p in self.db.query("SELECT id, strategy_id, meta FROM positions WHERE book = ? AND status != 'CLOSED'", (self.book,)):
            m = json.loads(p["meta"] or "{}")
            if cid in (m.get("entry_cid"), m.get("tp_cid"), m.get("exit_cid")):
                return p
        return None

    def _apply_fill_to_position(self, pid: str, side: str, price: Decimal, size: Decimal, fee: Decimal,
                                realized: Decimal) -> None:
        p = self.db.query_one("SELECT * FROM positions WHERE id = ?", (pid,))
        if p is None:
            return
        qty, cost = Decimal(p["qty"]), Decimal(p["cost_usd"])
        fees = Decimal(p["fees_usd"]) + fee
        rp = Decimal(p["realized_pnl_usd"])
        if side == "buy":
            qty += size
            cost += price * size
            self.db.execute("UPDATE positions SET qty = ?, cost_usd = ?, fees_usd = ?, entry_price = ? WHERE id = ?",
                            (str(qty), str(cost), str(fees), str(cost / qty), pid))
        else:
            qty -= size
            rp += realized
            self.db.execute("UPDATE positions SET qty = ?, fees_usd = ?, realized_pnl_usd = ?, exit_price = ? WHERE id = ?",
                            (str(max(qty, Decimal(0))), str(fees), str(rp), str(price), pid))

    # ------------------------------------------------------------------ positions
    async def _manage_position(self, p: dict[str, Any], trading_state: str) -> None:
        meta = json.loads(p["meta"] or "{}")
        plan = ExitPlan.model_validate(json.loads(p["exit_plan"])) if p["exit_plan"] and p["exit_plan"] != "{}" else None
        sym = p["symbol"]
        bbo, rules = self.market.bbo(sym), self.market.rules(sym)
        qty = Decimal(p["qty"])
        entry_o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("entry_cid"),))
        if p["status"] == "OPENING":
            terminal = entry_o is not None and OrderStatus(entry_o["status"]) in TERMINAL
            expired = time.time() > float(meta.get("ttl_deadline", 0))
            # smarter order placement: re-quote an unfilled maker entry toward the touch (bounded chase, idempotent ids)
            if (not expired and trading_state == "RUNNING" and meta.get("entry_style") == "maker" and entry_o is not None
                    and entry_o["status"] == "OPEN" and qty <= 0 and bbo is not None and rules is not None
                    and int(meta.get("reprices", 0)) < 3
                    and time.time() - float(meta.get("quoted_at", 0)) > max(20.0, float(meta.get("ttl_s", 300)) / 3)):
                cur = Decimal(entry_o["limit_price"])
                new_px = rules.round_price(d(bbo.bid), "buy")
                if new_px > cur and (new_px - cur) / cur <= Decimal("0.004") and float(new_px) < bbo.ask:
                    await self.venue.cancel_order(entry_o["client_order_id"], entry_o["venue_order_id"])
                    await self._refresh_order(entry_o)
                    fresh = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (entry_o["client_order_id"],))
                    if fresh and fresh["status"] == OrderStatus.CANCELLED.value and Decimal(fresh["filled_size"] or "0") == 0:
                        n = int(meta.get("reprices", 0)) + 1
                        notional = Decimal(meta.get("notional", "0"))
                        base = rules.round_base(notional / (new_px * (1 + Decimal(str(self.maker_fee)))))
                        req = OrderRequest(client_order_id=idempotency_key(meta.get("intent_id", p["id"]), "entry", n),
                                           venue=self.venue.name, symbol=sym, side="buy", order_type="post_only",
                                           base_size=base, limit_price=new_px)
                        if base > 0 and await self._submit(req, meta.get("intent_id")):
                            meta.update(entry_cid=req.client_order_id, reprices=n, quoted_at=time.time())
                            self.db.execute("UPDATE positions SET meta = ? WHERE id = ?", (dumps(meta), p["id"]))
                    return
            if (expired or trading_state != "RUNNING") and entry_o and not terminal:
                await self.venue.cancel_order(entry_o["client_order_id"], entry_o["venue_order_id"])
                await self._refresh_order(entry_o)
                return
            if terminal or (qty > 0 and expired):
                if qty <= 0:
                    self.db.execute("UPDATE positions SET status = 'CLOSED', closed_at = ?, exit_reason = ? WHERE id = ?",
                                    (_now(), "ENTRY_NOT_FILLED", p["id"]))
                    await self._emit("ENTRY_EXPIRED", {"position": p["id"], "symbol": sym, "strategy": p["strategy_id"]})
                    return
                meta["opened_ts"] = time.time()
                meta["high_water"] = float(Decimal(p["cost_usd"]) / qty)
                self.db.execute("UPDATE positions SET status = 'OPEN', meta = ? WHERE id = ?", (dumps(meta), p["id"]))
                await self._emit("POSITION_OPENED", {"position": p["id"], "symbol": sym, "strategy": p["strategy_id"],
                                                     "qty": str(qty), "cost": p["cost_usd"]})
                if plan and rules and plan.take_profit_pct < 1.0:      # convex exits carry no resting target
                    await self._place_tp(p["id"], sym, qty, Decimal(p["cost_usd"]) / qty, plan, rules, meta)
            return
        if p["status"] == "OPEN":
            force = None
            try:
                force = self.db.kv_get(f"position.force_exit.{p['id']}")
            except Exception:
                force = None
            if force and not (isinstance(force, dict) and force.get("done")):
                qty = Decimal(p["qty"] or 0)
                meta = json.loads(p["meta"] or "{}")
                reason = str((force or {}).get("reason") or "FORCE_EXIT")
                tp_o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("tp_cid"),)) if meta.get("tp_cid") else None
                # PAPER must recirculate even if BBO briefly missing (stale/delisted marks)
                if self.book == "paper" or (bbo and rules):
                    if qty > 0:
                        await self._market_exit(p, qty, reason, meta, tp_o)
                    else:
                        await self._close(p, reason, meta)
                    try:
                        self.db.kv_set(f"position.force_exit.{p['id']}", {"done": True, "ts": time.time(), "reason": reason})
                    except Exception:
                        pass
                    return  # force_exit early
        if p["status"] == "OPEN" and plan and bbo and rules:
            entry_px = float(Decimal(p["cost_usd"]) / qty) if qty > 0 else float(p["entry_price"] or 0)
            tp_o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("tp_cid"),)) if meta.get("tp_cid") else None
            if tp_o and tp_o["status"] == OrderStatus.FILLED.value or qty <= Decimal("0"):
                await self._close(p, "TP", meta)
                return
            hw = max(float(meta.get("high_water", entry_px)), bbo.bid)
            meta["high_water"] = hw
            stop = entry_px * (1 - plan.stop_loss_pct)
            if plan.trailing_pct:
                stop = max(stop, hw * (1 - plan.trailing_pct))
            fav = hw / entry_px - 1 if entry_px > 0 else 0.0
            if plan.chandelier_pct and plan.chandelier_arm_pct is not None and fav >= plan.chandelier_arm_pct:
                stop = max(stop, hw * (1 - plan.chandelier_pct))          # convex trend exit: trail only once armed
                if not meta.get("chandelier_armed"):
                    meta["chandelier_armed"] = True
                    await self._emit("TRAIL_ARMED", {"position": p["id"], "symbol": sym, "stop": stop, "peak_gain": fav})
            if plan.be_trigger_pct is not None and plan.be_trigger_pct < 0.5 and fav >= plan.be_trigger_pct:   # evolved profit lock
                stop = max(stop, entry_px * (1 + plan.be_buffer_pct))
                if plan.lock_frac is not None:
                    stop = max(stop, entry_px * (1 + plan.lock_frac * fav))
                if not meta.get("lock_armed"):
                    meta["lock_armed"] = True
                    await self._emit("PROFIT_LOCK", {"position": p["id"], "symbol": sym, "locked_stop": stop,
                                                     "peak_gain": fav})
            age = time.time() - float(meta.get("opened_ts", time.time()))
            reason = None
            force = None
            try:
                force = self.db.kv_get(f"position.force_exit.{p['id']}")
            except Exception:
                force = None
            if force:
                reason = str((force or {}).get("reason") or "FORCE_EXIT")
            elif bbo.bid <= stop:
                reason = ("LOCK" if stop > entry_px else "TRAIL") if stop > entry_px * (1 - plan.stop_loss_pct) + 1e-12 else "SL"
            elif age >= plan.time_stop_s:
                reason = "TIME"
            elif (plan.progress_s and age >= plan.progress_s and not meta.get("progress_ok")):
                if bbo.bid / entry_px - 1 < plan.progress_min_pct:
                    reason = "NO_PROGRESS"
                else:
                    meta["progress_ok"] = True
            elif trading_state == "STOPPED" and json.loads(json.dumps(meta)).get("flatten_on_stop"):
                reason = "EMERGENCY"
            if reason:
                await self._market_exit(p, qty, reason, meta, tp_o)
            else:
                self.db.execute("UPDATE positions SET meta = ? WHERE id = ?", (dumps(meta), p["id"]))
            return
        if p["status"] == "CLOSING":
            ex = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("exit_cid"),))
            if ex and ex["status"] in (OrderStatus.FILLED.value,) or qty <= 0:
                await self._close(p, meta.get("exit_reason", "EXIT"), meta)
            elif ex and ex["status"] in (OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value, OrderStatus.EXPIRED.value):
                reason = str(meta.get("exit_reason") or "")
                # PAPER force/reap on untradeable symbols (delisted): write off inventory so capital recirculates
                if self.book == "paper" and ("reap" in reason.lower() or "force" in reason.lower() or reason == "FORCE_EXIT"):
                    await self._close(p, reason or "FORCE_EXIT_UNTRADEABLE", meta)
                else:
                    self.db.execute("UPDATE positions SET status = 'OPEN' WHERE id = ?", (p["id"],))   # retry next tick

    async def _place_tp(self, pid: str, sym: str, qty: Decimal, entry: Decimal, plan: ExitPlan, rules: MarketRules,
                        meta: dict[str, Any]) -> None:
        tp_px = rules.round_price(entry * Decimal(str(1 + plan.take_profit_pct)), "sell")
        size = rules.round_base(qty)
        if size <= 0:
            return
        cid = idempotency_key(pid, "tp")
        req = OrderRequest(client_order_id=cid, venue=self.venue.name, symbol=sym, side="sell", order_type="post_only",
                           base_size=size, limit_price=tp_px)
        if await self._submit(req, None):
            meta["tp_cid"] = cid
            self.db.execute("UPDATE positions SET meta = ? WHERE id = ?", (dumps(meta), pid))

    async def _market_exit(self, p: dict[str, Any], qty: Decimal, reason: str, meta: dict[str, Any],
                           tp_o: dict[str, Any] | None) -> None:
        if tp_o and tp_o["status"] in ("OPEN", "PENDING", "PARTIAL"):
            await self.venue.cancel_order(tp_o["client_order_id"], tp_o["venue_order_id"])
            await self._refresh_order(tp_o)
            p = self.db.query_one("SELECT * FROM positions WHERE id = ?", (p["id"],)) or p
            qty = Decimal(p["qty"])
        rules = self.market.rules(p["symbol"])
        size = rules.round_base(qty) if rules else qty
        if size <= 0:
            await self._close(p, reason, meta)
            return
        n = int(meta.get("exit_attempts", 0)) + 1
        cid = idempotency_key(p["id"], "exit", n)
        req = OrderRequest(client_order_id=cid, venue=self.venue.name, symbol=p["symbol"], side="sell",
                           order_type="market", base_size=size)
        meta.update(exit_cid=cid, exit_reason=reason, exit_attempts=n)
        self.db.execute("UPDATE positions SET status = 'CLOSING', meta = ? WHERE id = ?", (dumps(meta), p["id"]))
        await self._submit(req, None)
        o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (cid,))
        if o:
            await self._refresh_order(o)

    async def _close(self, p: dict[str, Any], reason: str, meta: dict[str, Any]) -> None:
        p = self.db.query_one("SELECT * FROM positions WHERE id = ?", (p["id"],)) or p
        if p["status"] == "CLOSED":
            return
        self.db.execute("UPDATE positions SET status = 'CLOSED', closed_at = ?, exit_reason = ? WHERE id = ?",
                        (_now(), reason, p["id"]))
        cost = Decimal(p["cost_usd"])
        net = Decimal(p["realized_pnl_usd"]) - Decimal(p["fees_usd"])
        info = {"position": p["id"], "strategy_id": p["strategy_id"], "symbol": p["symbol"], "reason": reason,
                "cost_usd": str(cost), "realized_usd": p["realized_pnl_usd"], "fees_usd": p["fees_usd"],
                "net_usd": str(net), "net_return": float(net / cost) if cost > 0 else 0.0,
                "hold_hours": (time.time() - float(meta.get("opened_ts", time.time()))) / 3600,
                "opportunity_id": p["opportunity_id"], "meta": meta, "book": self.book}
        self.audit.append("POSITION_CLOSED", {k: v for k, v in info.items() if k != "meta"})
        await self._emit("POSITION_CLOSED", {k: v for k, v in info.items() if k != "meta"})
        if self.on_position_closed:
            await self.on_position_closed(info)

    # ------------------------------------------------------------------ emergency / cash-out
    async def cancel_all_entries(self) -> int:
        n = 0
        for p in self.db.query("SELECT * FROM positions WHERE book = ? AND status = 'OPENING'", (self.book,)):
            meta = json.loads(p["meta"] or "{}")
            o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("entry_cid"),))
            if o and o["status"] in ("OPEN", "PENDING", "PARTIAL", "UNKNOWN"):
                await self.venue.cancel_order(o["client_order_id"], o["venue_order_id"])
                n += 1
        return n

    async def liquidate(self, reason: str, symbols: set[str] | None = None) -> int:
        """Market-exit open positions (cash-out / flatten-when-safe)."""
        n = 0
        for p in self.db.query("SELECT * FROM positions WHERE book = ? AND status = 'OPEN'", (self.book,)):
            if symbols and p["symbol"] not in symbols:
                continue
            meta = json.loads(p["meta"] or "{}")
            tp_o = self.db.query_one("SELECT * FROM orders WHERE client_order_id = ?", (meta.get("tp_cid"),)) if meta.get("tp_cid") else None
            await self._market_exit(p, Decimal(p["qty"]), reason, meta, tp_o)
            n += 1
        return n

    def open_summary(self) -> dict[str, Any]:
        rows = self.db.query("SELECT symbol, strategy_id, status, qty, cost_usd FROM positions WHERE book = ? AND status != 'CLOSED'",
                             (self.book,))
        return {"count": len(rows), "positions": rows}


def quantize_usd(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


__all__ = ["ExecutionGateway", "MarketView", "IntentPurpose", "quantize_usd"]
