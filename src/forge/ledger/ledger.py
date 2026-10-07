"""Immutable treasury ledger and true net P&L (DOSSIER §2.6, DIRECTIVE §5).

Accounts (per book: live | paper):
  CASH:<asset>          quote cash (USD/USDC)
  ASSET:<venue>:<asset> base holdings; qty = units, amount_usd = cost basis
  FEES                  trading fees paid (positive = cost)
  PNL                   realized trading P&L (proceeds − cost basis), fees excluded
  OPEX:INFERENCE        DeepSeek spend (paid outside the trading account)
  OPEX:COMPUTE          Modal spend (paid outside the trading account)
  OPEX:DATA             paid data / x402 spend
  INCOME:OTHER          rebates/rewards/other realized income
  EXTERNAL              deposits/withdrawals/opening balances (equity contributions)

Slippage/spread are NOT separate cash flows — they are already inside fill prices. They are
tracked as attribution (vs. decision-time mid) so they are reported but never double-counted
(DECISIONS D-009).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from forge.core.ids import idempotency_key
from forge.persistence.db import Database

ZERO = Decimal("0")


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Holding:
    asset: str
    venue: str
    qty: Decimal = ZERO
    cost_usd: Decimal = ZERO

    @property
    def avg_cost(self) -> Decimal:
        return self.cost_usd / self.qty if self.qty > 0 else ZERO


@dataclass
class BookState:
    book: str
    cash: dict[str, Decimal] = field(default_factory=dict)
    holdings: dict[tuple[str, str], Holding] = field(default_factory=dict)
    contributed_usd: Decimal = ZERO
    realized_pnl_usd: Decimal = ZERO
    fees_usd: Decimal = ZERO
    opex_inference_usd: Decimal = ZERO
    opex_compute_usd: Decimal = ZERO
    opex_data_usd: Decimal = ZERO
    other_income_usd: Decimal = ZERO

    @property
    def cash_usd(self) -> Decimal:
        return sum((v for k, v in self.cash.items() if k in ("USD", "USDC")), ZERO)

    def holdings_cost_usd(self) -> Decimal:
        return sum((h.cost_usd for h in self.holdings.values()), ZERO)

    def market_value(self, marks: dict[str, float]) -> Decimal:
        """Mark holdings by symbol `<ASSET>-USD` (fallback: cost basis when no mark)."""
        total = ZERO
        for (_venue, asset), h in self.holdings.items():
            if h.qty <= 0:
                continue
            m = marks.get(f"{asset}-USD") or marks.get(f"{asset}-USDC")
            total += h.qty * Decimal(repr(m)) if m else h.cost_usd
        return total

    def equity(self, marks: dict[str, float]) -> Decimal:
        return self.cash_usd + self.market_value(marks)

    def unrealized(self, marks: dict[str, float]) -> Decimal:
        return self.market_value(marks) - self.holdings_cost_usd()

    def summary(self, marks: dict[str, float]) -> dict[str, Any]:
        unreal = self.unrealized(marks)
        trading_net = self.realized_pnl_usd - self.fees_usd + self.other_income_usd
        opex = self.opex_inference_usd + self.opex_compute_usd + self.opex_data_usd
        return {
            "book": self.book,
            "equity_usd": self.equity(marks),
            "cash_usd": self.cash_usd,
            "deployed_usd": self.market_value(marks),
            "contributed_usd": self.contributed_usd,
            "realized_pnl_usd": self.realized_pnl_usd,
            "unrealized_pnl_usd": unreal,
            "fees_usd": self.fees_usd,
            "other_income_usd": self.other_income_usd,
            "opex_inference_usd": self.opex_inference_usd,
            "opex_compute_usd": self.opex_compute_usd,
            "opex_data_usd": self.opex_data_usd,
            "trading_net_usd": trading_net,
            # TRUE NET = realized + income − fees − every operating cost (unrealized shown separately)
            "true_net_usd": trading_net - opex,
            "true_net_incl_unrealized_usd": trading_net - opex + unreal,
            "holdings": [
                {"venue": v, "asset": a, "qty": h.qty, "cost_usd": h.cost_usd, "avg_cost": h.avg_cost}
                for (v, a), h in self.holdings.items() if h.qty > 0
            ],
        }


class Ledger:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---- primitive ---------------------------------------------------------------------------
    def _post(self, rows: list[dict[str, Any]]) -> bool:
        """Post a balanced group atomically. Returns False if already posted (idempotent)."""
        with self.db.transaction():
            first = rows[0].get("idem_key")
            if first and self.db.scalar("SELECT 1 FROM ledger_entries WHERE idem_key = ?", (first,)):
                return False
            for r in rows:
                self.db.insert("ledger_entries", {
                    "ts": r.get("ts") or _now(), "book": r["book"], "account": r["account"],
                    "kind": r["kind"], "asset": r.get("asset", "USD"), "qty": r.get("qty", ZERO),
                    "amount_usd": r["amount_usd"], "strategy_id": r.get("strategy_id"),
                    "ref_type": r.get("ref_type"), "ref_id": r.get("ref_id"),
                    "idem_key": r.get("idem_key"), "memo": r.get("memo"),
                })
        return True

    # ---- capital -----------------------------------------------------------------------------
    def deposit(self, book: str, amount_usd: Decimal, asset: str = "USD", memo: str = "deposit",
                ref_id: str | None = None) -> bool:
        k = idempotency_key("deposit", book, asset, amount_usd, ref_id or memo)
        return self._post([
            {"book": book, "account": f"CASH:{asset}", "kind": "DEPOSIT", "asset": asset,
             "qty": amount_usd, "amount_usd": amount_usd, "idem_key": k, "ref_id": ref_id, "memo": memo},
            {"book": book, "account": "EXTERNAL", "kind": "DEPOSIT", "asset": asset,
             "amount_usd": -amount_usd, "idem_key": k + ":x", "ref_id": ref_id, "memo": memo},
        ])

    def opening_asset(self, book: str, venue: str, asset: str, qty: Decimal, value_usd: Decimal,
                      ref_id: str) -> bool:
        """Adopt an existing holding (OP-001: whole account is the treasury) at its mark value."""
        k = idempotency_key("opening_asset", book, venue, asset, ref_id)
        return self._post([
            {"book": book, "account": f"ASSET:{venue}:{asset}", "kind": "OPENING", "asset": asset,
             "qty": qty, "amount_usd": value_usd, "idem_key": k, "ref_id": ref_id},
            {"book": book, "account": "EXTERNAL", "kind": "OPENING", "asset": asset,
             "amount_usd": -value_usd, "idem_key": k + ":x", "ref_id": ref_id},
        ])

    def withdraw(self, book: str, amount_usd: Decimal, asset: str = "USD", ref_id: str = "",
                 memo: str = "withdrawal") -> bool:
        k = idempotency_key("withdraw", book, asset, amount_usd, ref_id)
        return self._post([
            {"book": book, "account": f"CASH:{asset}", "kind": "WITHDRAWAL", "asset": asset,
             "qty": -amount_usd, "amount_usd": -amount_usd, "idem_key": k, "ref_id": ref_id, "memo": memo},
            {"book": book, "account": "EXTERNAL", "kind": "WITHDRAWAL", "asset": asset,
             "amount_usd": amount_usd, "idem_key": k + ":x", "ref_id": ref_id, "memo": memo},
        ])

    # ---- trading -----------------------------------------------------------------------------
    def record_fill(self, book: str, venue: str, symbol: str, side: str, price: Decimal, size: Decimal,
                    fee: Decimal, trade_id: str, strategy_id: str | None, order_id: str,
                    quote_asset: str = "USD") -> Decimal:
        """Post a fill. Returns realized P&L for sells (fees excluded), 0 for buys. Idempotent."""
        base = symbol.split("-")[0]
        notional = price * size
        k = idempotency_key("fill", book, venue, trade_id)
        if self.db.scalar("SELECT 1 FROM ledger_entries WHERE idem_key = ?", (k,)):
            return ZERO
        acct = f"ASSET:{venue}:{base}"
        common = {"book": book, "strategy_id": strategy_id, "ref_type": "order", "ref_id": order_id}
        rows: list[dict[str, Any]] = []
        realized = ZERO
        if side == "buy":
            rows += [
                {**common, "account": f"CASH:{quote_asset}", "kind": "TRADE_BUY", "asset": quote_asset,
                 "qty": -notional, "amount_usd": -notional, "idem_key": k},
                {**common, "account": acct, "kind": "TRADE_BUY", "asset": base, "qty": size,
                 "amount_usd": notional, "idem_key": k + ":a"},
            ]
        else:
            h = self._holding(book, venue, base)
            if h.qty <= 0:
                basis = notional  # unknown basis (shouldn't happen) → zero realized, flagged in memo
                memo = "sell without tracked basis"
            else:
                sell_qty = min(size, h.qty)
                basis = h.avg_cost * sell_qty + (notional / size * (size - sell_qty) if size > sell_qty else ZERO)
                memo = None
            realized = notional - basis
            rows += [
                {**common, "account": f"CASH:{quote_asset}", "kind": "TRADE_SELL", "asset": quote_asset,
                 "qty": notional, "amount_usd": notional, "idem_key": k},
                {**common, "account": acct, "kind": "TRADE_SELL", "asset": base, "qty": -size,
                 "amount_usd": -basis, "idem_key": k + ":a", "memo": memo},
                {**common, "account": "PNL", "kind": "REALIZED_PNL", "amount_usd": realized,
                 "idem_key": k + ":p"},
            ]
        if fee:
            rows += [
                {**common, "account": f"CASH:{quote_asset}", "kind": "FEE", "asset": quote_asset,
                 "qty": -fee, "amount_usd": -fee, "idem_key": k + ":f"},
                {**common, "account": "FEES", "kind": "FEE", "amount_usd": fee, "idem_key": k + ":fx"},
            ]
        self._post(rows)
        return realized

    # ---- operating costs / income -----------------------------------------------------------------
    def record_opex(self, book: str, category: str, amount_usd: Decimal, ref_id: str,
                    strategy_id: str | None = None, memo: str | None = None) -> bool:
        assert category in ("INFERENCE", "COMPUTE", "DATA", "MEMBERSHIP")
        k = idempotency_key("opex", book, category, ref_id)
        return self._post([{"book": book, "account": f"OPEX:{category}", "kind": f"{category}_COST",
                            "amount_usd": amount_usd, "strategy_id": strategy_id, "ref_id": ref_id,
                            "idem_key": k, "memo": memo}])

    def record_income(self, book: str, amount_usd: Decimal, ref_id: str, memo: str = "income") -> bool:
        k = idempotency_key("income", book, ref_id)
        return self._post([
            {"book": book, "account": "CASH:USD", "kind": "INCOME", "qty": amount_usd,
             "amount_usd": amount_usd, "idem_key": k, "ref_id": ref_id, "memo": memo},
            {"book": book, "account": "INCOME:OTHER", "kind": "INCOME", "amount_usd": amount_usd,
             "idem_key": k + ":i", "ref_id": ref_id, "memo": memo},
        ])

    def adjust(self, book: str, account: str, asset: str, qty: Decimal, amount_usd: Decimal, reason: str,
               ref_id: str) -> bool:
        """Reconciliation adjustment toward venue truth (always audited by caller)."""
        k = idempotency_key("adjust", book, account, ref_id)
        return self._post([
            {"book": book, "account": account, "kind": "RECON_ADJUST", "asset": asset, "qty": qty,
             "amount_usd": amount_usd, "idem_key": k, "ref_id": ref_id, "memo": reason},
            {"book": book, "account": "EXTERNAL", "kind": "RECON_ADJUST", "asset": asset,
             "amount_usd": -amount_usd, "idem_key": k + ":x", "ref_id": ref_id, "memo": reason},
        ])

    # ---- views -------------------------------------------------------------------------------
    def _holding(self, book: str, venue: str, asset: str) -> Holding:
        r = self.db.query(
            "SELECT qty, amount_usd FROM ledger_entries WHERE book = ? AND account = ?",
            (book, f"ASSET:{venue}:{asset}"))
        h = Holding(asset=asset, venue=venue)
        for row in r:
            h.qty += Decimal(row["qty"])
            h.cost_usd += Decimal(row["amount_usd"])
        return h

    def state(self, book: str) -> BookState:
        st = BookState(book=book)
        acc: dict[str, list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
        for row in self.db.query(
                "SELECT account, qty, amount_usd FROM ledger_entries WHERE book = ?", (book,)):
            a = acc[row["account"]]
            a[0] += Decimal(row["qty"])
            a[1] += Decimal(row["amount_usd"])
        for account, (qty, amt) in acc.items():
            if account.startswith("CASH:"):
                st.cash[account[5:]] = amt
            elif account.startswith("ASSET:"):
                _, venue, asset = account.split(":", 2)
                st.holdings[(venue, asset)] = Holding(asset=asset, venue=venue, qty=qty, cost_usd=amt)
            elif account == "EXTERNAL":
                st.contributed_usd = -amt
            elif account == "PNL":
                st.realized_pnl_usd = amt
            elif account == "FEES":
                st.fees_usd = amt
            elif account == "OPEX:INFERENCE":
                st.opex_inference_usd = amt
            elif account == "OPEX:COMPUTE":
                st.opex_compute_usd = amt
            elif account == "OPEX:DATA":
                st.opex_data_usd = amt
            elif account == "INCOME:OTHER":
                st.other_income_usd = amt
        return st

    def strategy_pnl(self, book: str) -> dict[str, dict[str, Decimal]]:
        out: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"realized": ZERO, "fees": ZERO, "opex": ZERO})
        for r in self.db.query(
                "SELECT strategy_id, account, amount_usd FROM ledger_entries "
                "WHERE book = ? AND strategy_id IS NOT NULL AND account IN "
                "('PNL','FEES','OPEX:INFERENCE','OPEX:COMPUTE','OPEX:DATA')", (book,)):
            k = {"PNL": "realized", "FEES": "fees"}.get(r["account"], "opex")
            out[r["strategy_id"]][k] += Decimal(r["amount_usd"])
        for v in out.values():
            v["true_net"] = v["realized"] - v["fees"] - v["opex"]
        return dict(out)

    def check_balanced(self, book: str) -> Decimal:
        """Double-entry invariant: Σ amount over value accounts must net to zero against EXTERNAL,
        except P&L-type accounts which mirror value created/destroyed. Returns the residual."""
        s = self.state(book)
        # cash + holdings_cost = contributed + realized − fees + income  (opex is paid externally)
        lhs = s.cash_usd + s.holdings_cost_usd()
        rhs = s.contributed_usd + s.realized_pnl_usd - s.fees_usd + s.other_income_usd
        return lhs - rhs
