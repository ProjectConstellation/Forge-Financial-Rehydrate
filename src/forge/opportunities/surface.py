"""Opportunity Surface Registry + rail economics + Capital Allocator (operator directive OP-013).

DISCOVERY, not a static list:
- Coinbase product classes are discovered by probing the `product_type` enum: the API answers "is not a valid value" for
  unknown enums, so a value that is ACCEPTED (even if empty / erroring) is a real product class → a new class appears in
  the registry automatically (e.g. PREDICTION_MARKET was accepted but returned HTTP 500 on 2026-10-07).
- Spot / futures / equities / prediction / account capabilities (permissions, fee tier, CFM account, balances) are
  re-queried on a schedule; every probe is stored (rail_probes) so capability changes are visible over time.
- The CDP documentation index (llms.txt) is diffed daily; new pages mentioning earn/yield/reward/stake/prediction/equity/
  lend/agent are recorded as discovery leads.
- Kalshi series are discovered and mapped to Coinbase underlyings by the cross-rail scanner.

ECONOMICS (per rail, per day, per dollar) — the directive's formula with explicit units:
    cycle_net = E[return] × P(edge real, calibrated) × liquidity − fees − slippage − risk_penalty
    score/day = (cycle_net − hurdle/day × lockup_days) / cycle_days − compute_usd/day ÷ capital
Inputs come from MEASURED evidence (arena/forward/real outcomes, cross-rail settled shadow P&L, account-verified yields).
Unverified inputs get probability ≤ 0.5 and the rail stays non-executable — FORGE never assumes an advertised rate.

ALLOCATION — dollars go to the highest score/day among EXECUTABLE rails up to capacity; idle capital goes to the best
executable idle rail. The same computation over ALL rails (as if unblocked) gives the "unlock value": what each missing
credential / eligibility / policy decision is worth per day — surfaced to the operator, never acted on autonomously.
Only rails with legitimate APIs and authorized credentials can ever be EXECUTABLE; browser automation is never used.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import math
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

log = logging.getLogger("forge.surface")

PRODUCT_TYPE_CANDIDATES = ("SPOT", "FUTURE", "EQUITY", "PREDICTION_MARKET", "OPTION", "OPTIONS", "PERPETUAL", "INDEX",
                           "BOND", "COMMODITY", "FUND", "STAKING", "LENDING", "TOKENIZED_ASSET", "CRYPTO_INDEX")
DOC_KEYWORDS = re.compile(r"earn|yield|reward|stak|predict|equit|stock|lend|vault|agent|convert|perp|futures|x402", re.I)
EQUITY_WATCH = ("GLD", "IAU", "SGOV", "BIL", "SPY", "QQQ", "IBIT", "COIN", "SLV", "USFR")


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ------------------------------------------------------------------ economics
@dataclass
class RailEconomics:
    expected_return: float = 0.0     # per cycle, fraction of deployed capital (gross of the costs listed below)
    probability: float = 0.0         # calibrated P(the edge/yield is real for THIS account)
    cycle_days: float = 1.0          # capital turnover period (velocity = 1 / cycle_days)
    liquidity: float = 1.0           # 0..1: fill probability × usable depth at our size
    fees: float = 0.0                # per cycle, fraction
    slippage: float = 0.0            # per cycle, fraction
    lockup_days: float = 0.0         # settlement / unbonding / transfer delay beyond the cycle
    compute_usd_day: float = 0.0     # inference + compute attributable to this rail
    risk_penalty: float = 0.0        # per cycle, fraction (variance / drawdown / model-risk charge)
    capacity_usd: float = 0.0        # maximum useful capital
    evidence: str = ""               # where the numbers come from

    def score_per_day(self, capital: float, hurdle_per_day: float) -> float:
        cycle_net = (self.expected_return * self.probability * self.liquidity - self.fees - self.slippage
                     - self.risk_penalty)
        per_day = (cycle_net - hurdle_per_day * self.lockup_days) / max(self.cycle_days, 1e-6)
        return per_day - self.compute_usd_day / max(capital, 1e-6)


@dataclass
class Rail:
    id: str
    provider: str
    category: str
    status: str = "DISCOVERED"
    executable: bool = False
    blockers: list[str] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    economics: RailEconomics = field(default_factory=RailEconomics)


def allocate(rails: list[Rail], capital: float, hurdle_per_day: float, include_blocked: bool = False) -> dict[str, Any]:
    """Greedy by score/day (capacity-bounded). Rails with score ≤ 0 get nothing; leftover stays in cash."""
    elig = [r for r in rails if (r.executable or include_blocked) and r.economics.probability > 0]
    ranked = sorted(elig, key=lambda r: -r.economics.score_per_day(capital, hurdle_per_day))
    left, plan, daily = capital, [], 0.0
    for r in ranked:
        s = r.economics.score_per_day(capital, hurdle_per_day)
        if s <= 0 or left <= 0:
            continue
        amt = min(left, r.economics.capacity_usd if r.economics.capacity_usd > 0 else left)
        if amt <= 0:
            continue
        plan.append({"rail": r.id, "usd": round(amt, 2), "score_per_day": s, "usd_per_day": s * amt})
        daily += s * amt
        left -= amt
    return {"plan": plan, "cash_usd": round(left, 2), "expected_usd_per_day": daily,
            "ranking": [{"rail": r.id, "score_per_day": r.economics.score_per_day(capital, hurdle_per_day),
                         "executable": r.executable, "status": r.status} for r in ranked]}


# ------------------------------------------------------------------ registry
class SurfaceRegistry:
    PROBE_S = 900                 # light probes
    HEAVY_PROBE_S = 24 * 3600     # equity universe pagination, product-type enum sweep, docs diff

    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.rails: dict[str, Rail] = {}
        self.http = httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "FORGE/1.0 (discovery)"})
        self.last_heavy = float(self.f.db.kv_get("surface.last_heavy", 0) or 0)

    # ---------------- helpers
    async def _cb(self, path: str, params: dict[str, Any] | None = None, private: bool = True) -> tuple[int, Any]:
        try:
            return 200, await self.f.rest._request("GET", "/api/v3/brokerage" + path, params=params, private=private,
                                                   retries=0)
        except Exception as e:
            m = re.search(r"HTTP (\d{3})", str(e))
            return (int(m.group(1)) if m else 0), str(e)[:400]

    def _rail(self, rid: str, provider: str, category: str) -> Rail:
        if rid not in self.rails:
            self.rails[rid] = Rail(rid, provider, category)
        return self.rails[rid]

    # ---------------- probes
    async def probe_account(self) -> dict[str, Any]:
        _, kp = await self._cb("/key_permissions")
        _, ts = await self._cb("/transaction_summary")
        _, cfm = await self._cb("/cfm/balance_summary")
        acc: dict[str, Any] = {}
        pf_uuid = kp.get("portfolio_uuid") if isinstance(kp, dict) else None
        if pf_uuid:
            _, pf = await self._cb(f"/portfolios/{pf_uuid}")
            if isinstance(pf, dict):
                b = pf.get("breakdown", {})
                bal = b.get("portfolio_balances", {})
                acc = {"equities_balance": (bal.get("total_equities_balance") or {}).get("value"),
                       "prediction_markets_summary": bal.get("prediction_markets_summary"),
                       "has_prediction_positions_field": "prediction_markets_positions" in b,
                       "has_equity_positions_field": "equity_positions" in b}
        tier = (ts or {}).get("fee_tier", {}) if isinstance(ts, dict) else {}
        out = {"can_view": (kp or {}).get("can_view") if isinstance(kp, dict) else None,
               "can_trade": (kp or {}).get("can_trade") if isinstance(kp, dict) else None,
               "can_transfer": (kp or {}).get("can_transfer") if isinstance(kp, dict) else None,
               "portfolio_type": (kp or {}).get("portfolio_type") if isinstance(kp, dict) else None,
               "fee_tier": tier.get("pricing_tier"), "maker": tier.get("maker_fee_rate"), "taker": tier.get("taker_fee_rate"),
               "cfm_account": bool(isinstance(cfm, dict) and cfm.get("balance_summary")), **acc}
        self.f.db.kv_set("surface.account", {**out, "ts": time.time()})
        return out

    async def probe_spot(self) -> None:
        r = self._rail("coinbase.spot", "Coinbase Advanced Trade", "crypto spot")
        code, d = await self._cb("/market/products", {"product_type": "SPOT", "limit": 1000}, private=False)
        if code == 200:
            P = d.get("products", [])
            online = [p for p in P if p.get("status") == "online" and not p.get("trading_disabled")]
            r.capabilities.update(products=len(P), online=len(online),
                                  usd_quoted=sum(1 for p in online if p.get("quote_currency_id") == "USD"),
                                  usdc_aliases=sum(1 for p in online if p.get("alias")),
                                  paxg=any(p["product_id"] == "PAXG-USD" for p in online))
        r.status, r.executable, r.blockers = "LIVE" if self.f.s.live_trading else "SHADOW", True, []

    async def probe_futures(self, account: dict[str, Any]) -> None:
        r = self._rail("coinbase.futures", "Coinbase Financial Markets (CFM/CDE)", "US-regulated futures & perps")
        code, d = await self._cb("/market/products", {"product_type": "FUTURE", "limit": 500}, private=False)
        if code == 200:
            P = d.get("products", [])
            groups: dict[str, int] = {}
            non_crypto = set()
            min_notional = None
            for p in P:
                fd = p.get("future_product_details") or {}
                g = fd.get("group_description") or fd.get("contract_root_unit") or "?"
                groups[g] = groups.get(g, 0) + 1
                if fd.get("non_crypto"):
                    non_crypto.add(g)
                with_px = float(p.get("price") or 0) * float(fd.get("contract_size") or 0)
                if with_px > 0:
                    min_notional = with_px if min_notional is None else min(min_notional, with_px)
            r.capabilities.update(contracts=len(P), groups=len(groups), non_crypto_groups=sorted(non_crypto)[:20],
                                  min_contract_notional_usd=min_notional)
        r.blockers = []
        if not account.get("cfm_account"):
            r.blockers.append("no CFM futures account (operator onboarding)")
        r.blockers.append("policy: no leverage/shorting in current phase (OPERATOR_POLICY) — data rail only")
        r.status, r.executable = "DATA_ONLY", False

    async def probe_equity(self, heavy: bool) -> None:
        r = self._rail("coinbase.equity", "Coinbase Capital Markets (via Advanced Trade API)", "US equities & ETFs")
        if heavy:
            n, watch, cursor = 0, {}, None
            for _ in range(40):
                params = {"product_type": "EQUITY", "limit": 1000, **({"cursor": cursor} if cursor else {})}
                code, d = await self._cb("/market/products", params, private=False)
                if code != 200:
                    break
                for p in d.get("products", []):
                    n += 1
                    e = p.get("equity_product_details") or {}
                    if e.get("ticker") in EQUITY_WATCH:
                        fl = e.get("equity_trading_flags") or {}
                        watch[e["ticker"]] = {"product_id": p["product_id"], "fractionable": e.get("fractionable"),
                                              "buy_notional": fl.get("buy_notional"), "tradable": fl.get("tradable"),
                                              "min_notional": e.get("fractional_notional_min_size"),
                                              "quote": p.get("quote_currency_id")}
                pg = d.get("pagination") or {}
                cursor = pg.get("next_cursor")
                if not cursor or not pg.get("has_next"):
                    break
            r.capabilities.update(products=n, watch=watch, sessions="OVERNIGHT/PRE/NORMAL/AFTER (fractional+market only NORMAL)",
                                  settlement="T+1 (equities)", automation="official: Advanced Trade API / Coinbase for Agents CLI")
        r.capabilities.update(commission="0 (Coinbase: 'Commission-free 24/5 stock trading', live 2026-10-07); spread applies")
        r.blockers = ["account equity eligibility unverified (operator confirm or one authorized $1 order)",
                      "no equity strategy validated yet; equity quotes not reliable via public API (data rail first)"]
        r.status, r.executable = "CANDIDATE", False

    async def probe_product_types(self) -> dict[str, str]:
        import asyncio
        prev = self.f.db.kv_get("surface.product_types") or {}
        found = {}
        for t in PRODUCT_TYPE_CANDIDATES:
            code, d = 0, None
            for attempt in range(3):
                await asyncio.sleep(1.0 + 2.0 * attempt)                # pace: never trip the shared rate limit
                code, d = await self._cb("/market/products", {"product_type": t, "limit": 1}, private=True)
                if code not in (0, 429):
                    break
            if code == 200:
                found[t] = f"ok ({(d or {}).get('num_products', '?')} products)"
            elif code == 400 and "not a valid value" in str(d):
                continue                                                 # definitively not a product class
            elif code in (0, 429):
                if t in prev:
                    found[t] = prev[t]                                   # unknown this round → keep last knowledge
            else:
                found[t] = f"accepted, HTTP {code}"
        for t, v in found.items():
            if t not in prev:
                self.f.db.insert("listing_events", {"ts": _now(), "product_id": f"TYPE:{t}", "product_type": t,
                                                    "event": "NEW_PRODUCT_CLASS", "before": None, "after": v})
        self.f.db.kv_set("surface.product_types", found)
        return found

    async def probe_prediction(self, types: dict[str, str], account: dict[str, Any]) -> None:
        r = self._rail("coinbase.prediction", "Coinbase Prediction Markets (Kalshi-operated, FCM-cleared)", "event contracts")
        v = types.get("PREDICTION_MARKET", "not offered")
        r.capabilities.update(api_status=v, portfolio_fields=account.get("has_prediction_positions_field"))
        if v.startswith("ok") and "(0 " not in v:
            r.status, r.blockers = "CANDIDATE", ["new: verify order endpoints + fees, then shadow"]
        else:
            r.status, r.blockers = "UNAVAILABLE", [f"Advanced API product_type=PREDICTION_MARKET: {v}; use Kalshi API rail"]
        r.executable = False

    async def probe_kalshi(self) -> None:
        r = self._rail("kalshi.events", "Kalshi (official API)", "event contracts")
        try:
            st = (await self.http.get("https://api.elections.kalshi.com/trade-api/v2/exchange/status")).json()
            r.capabilities.update(trading_active=st.get("trading_active"))
        except Exception as e:
            r.capabilities.update(error=str(e)[:200])
        m = self.f.db.kv_get("crossrail.mapping") or {}
        r.capabilities.update(series_total=m.get("series_total"), mapped_series=len(m.get("mapped", {})),
                              fee_model="taker 0.07·m·C·P(1−P); maker 0 unless series has maker fees")
        r.blockers = []
        if not os.environ.get("KALSHI_API_KEY_ID"):
            r.blockers.append("no Kalshi API key (operator: create Kalshi account + API key)")
        r.blockers.append("funding rail not authorized (Coinbase key has no transfer permission; OP required)")
        r.status, r.executable = "SHADOW", False

    def membership(self) -> dict[str, Any]:
        """MembershipEconomicsAdapter (answers §Coinbase One): verified live 2026-10-07 from coinbase.com/one + /usdc."""
        m = self.f.db.kv_get("membership.coinbase_one") or {}
        base = {"tier": "basic", "monthly_cost_usd": 4.99, "annual_cost_usd": 49.99, "trial_days": 7,
                "trial_start": "2026-10-07", "first_charge": "2026-10-14", "billed_from": "coinbase_balance",
                "simple_trade_zero_fee_cap_usd_month": 500, "simple_trade_api": False,
                "advanced_trade_rebate_pct": 0.0, "advanced_trade_rebate_cap_usd_month": 0.0,
                "usdc_reward_apy": 0.0375, "usdc_rewards_member_only": True, "staking_boost_pct": 5.0,
                "incremental_cost_to_forge_usd_month": 4.99,      # OP-016 update: deducted from the Coinbase balance → FORGE cost
                "source": "coinbase.com/one + coinbase.com/usdc (live 2026-10-07)",
                "notes": "Zero-fee benefit excludes Coinbase Advanced, DEX and derivatives; spread applies on simple trades."}
        if int(m.get("version", 1)) >= 2:                     # stored config only overrides the current schema version
            base.update(m)
        base["version"] = 2
        self.f.db.kv_set("membership.coinbase_one", base)
        return base

    def bill_membership(self) -> None:
        """Book the Coinbase One fee as true operating cost on each monthly billing date (idempotent per month).
        Wallet truth stays authoritative: if Coinbase bills a card instead, the live reconciler corrects cash."""
        from decimal import Decimal
        mem = self.f.db.kv_get("membership.coinbase_one") or {}
        first = mem.get("first_charge")
        if not first or not mem.get("monthly_cost_usd"):
            return
        today = datetime.now(UTC).date()
        start = datetime.fromisoformat(first).date()
        if today < start:
            return
        months = (today.year - start.year) * 12 + (today.month - start.month) + (1 if today.day >= start.day else 0)
        for k in range(months):
            y, m = start.year + (start.month - 1 + k) // 12, (start.month - 1 + k) % 12 + 1
            ref = f"coinbase_one:{y:04d}-{m:02d}"
            for book in {self.f.book if self.f.book in ("live", "paper") else "paper"}:
                with contextlib.suppress(Exception):
                    if self.f.ledger.record_opex(book, "MEMBERSHIP", Decimal(str(mem["monthly_cost_usd"])), ref,
                                                 memo="Coinbase One Basic monthly fee (OP-016)"):
                        self.f.db.insert("listing_events", {"ts": _now(), "product_id": "COINBASE_ONE", "product_type": "membership",
                                                            "event": "MEMBERSHIP_FEE_BOOKED", "before": None, "after": ref})

    def static_rails(self, account: dict[str, Any]) -> None:
        mem = self.membership()
        y = self._rail("coinbase.usdc_rewards", "Coinbase USDC rewards (Coinbase One member)", "idle-capital yield")
        apy = self.f.db.kv_get("config.usdc_reward_apy_verified") or (mem["usdc_reward_apy"] if mem.get("tier") else None)
        y.capabilities.update(convert_api="Advanced Trade convert quote/commit (USD↔USDC)",
                              advertised_apy="3.50–3.75% (Coinbase One pages, 2026-10) — never assumed",
                              verified_apy=apy)
        ys = self.f.db.kv_get("yield.usdc") or {}
        y.capabilities.update(membership=mem.get("tier"), member_apy=mem.get("usdc_reward_apy"),
                              usdc_balance=ys.get("usdc_balance"), rewards_usdc=ys.get("rewards_usdc"),
                              realized_apy=ys.get("realized_apy"))
        if ys.get("conversions"):
            y.blockers = [] if ys.get("realized_apy") else ["rate not yet verified from posted rewards (needs ≥ 1 day)"]
            y.status, y.executable = "LIVE", True
        else:
            y.blockers = ["no idle USDC yet"]
            y.status, y.executable = ("LIVE_ELIGIBLE", False) if apy else ("CANDIDATE", False)
        o = self._rail("cdp.onchain", "Coinbase CDP (Server Wallet v2, swaps, Aave/Morpho vaults, x402)", "onchain / DeFi")
        o.blockers = ["Coinbase key can_transfer=false (cannot fund a wallet)"] if not account.get("can_transfer") else []
        o.blockers += ["no CDP wallet secret / spend policy authorized by operator"]
        o.status, o.executable = "BLOCKED", False
        s = self._rail("coinbase.staking", "Coinbase staking", "staking yield")
        s.blockers = ["no retail staking endpoint in Advanced Trade API (CDP staking/Prime are separate products)"]
        s.status, s.executable = "BLOCKED", False
        pm = self._rail("coinbase.stable_peg_mm", "Coinbase Advanced Trade (stable pairs)", "peg market-making / idle yield")
        fee = self.f.db.kv_get("fees.USDT-USD.maker") or {}
        pm.capabilities.update(pairs=["USDT-USD", "USDT-USDC"], maker_fee=fee.get("rate"), fee_source=fee.get("source"))
        # Clear blockers when shadow evidence is currently +EV; allocator still ranks vs all rails
        st = self.f.db.kv_get("pegmaker.state") or {}
        n_peg = int(self.f.db.scalar("SELECT COUNT(*) FROM shadow_trades WHERE rail='coinbase.stable_peg_mm' AND pnl_usd IS NOT NULL") or 0)
        mean_peg = float(self.f.db.scalar("SELECT AVG(pnl_usd) FROM shadow_trades WHERE rail='coinbase.stable_peg_mm' AND pnl_usd IS NOT NULL") or 0)
        if n_peg >= 30 and mean_peg > 0:
            pm.status = "SHADOW"; pm.executable = True; pm.blockers = []
            pm.economics.evidence = f"{n_peg} shadow RTs mean ${mean_peg:.4f} — current shadow evidence supports allocation contention"
        else:
            pm.blockers = [f"paper only until shadow proves +EV (n={n_peg}, mean={mean_peg:.4f})"]
        pm.status, pm.executable = "SHADOW", False
        tr = self._rail("coinbase.stable_triangle", "Coinbase Advanced Trade (USDT-USD ⇄ USDT-USDC, free USD⇄USDC convert)",
                        "near-riskless stable arbitrage")
        tr.capabilities.update(fees=(self.f.db.kv_get("fees.stable") or {}).get("fees"))
        n_tr = int(self.f.db.scalar("SELECT COUNT(*) FROM shadow_trades WHERE rail='coinbase.stable_triangle' AND pnl_usd IS NOT NULL") or 0)
        mean_tr = float(self.f.db.scalar("SELECT AVG(pnl_usd) FROM shadow_trades WHERE rail='coinbase.stable_triangle' AND pnl_usd IS NOT NULL") or 0)
        sum_tr = float(self.f.db.scalar("SELECT SUM(pnl_usd) FROM shadow_trades WHERE rail='coinbase.stable_triangle' AND pnl_usd IS NOT NULL") or 0)
        if n_tr >= 100 and mean_tr > 0:
            tr.status = "SHADOW"; tr.executable = True; tr.blockers = []
            tr.economics.evidence = f"{n_tr} shadow cycles mean ${mean_tr:.4f} sum ${sum_tr:.2f} — current shadow evidence supports allocation contention (EXCEPTIONAL)"
        else:
            tr.blockers = [f"paper only until shadow +EV after fees (n={n_tr}, mean={mean_tr:.4f})"]
        tr.status, tr.executable = "SHADOW", False
        ld = self._rail("coinbase.listing_discovery", "Coinbase Advanced Trade (new listings)", "event-driven spot")
        ld.blockers = ["paper only: rare events; needs ≥ 20 settled listings with positive net expectancy"]
        ld.status, ld.executable = "SHADOW", False
        x = self._rail("x402.data", "x402 paid data (Coinbase for Agents)", "intelligence purchase (cost rail)")
        x.blockers = ["spend only when IVOI ≥ 1.5 is demonstrated (answers §5)"]
        x.status, x.executable = "CANDIDATE", False

    async def diff_docs(self) -> int:
        try:
            txt = (await self.http.get("https://docs.cdp.coinbase.com/llms.txt")).text
        except Exception:
            return 0
        pages = {ln.strip() for ln in txt.splitlines() if ln.startswith("- [") and DOC_KEYWORDS.search(ln)}
        old = set(self.f.db.kv_get("surface.docs_pages") or [])
        new = sorted(pages - old) if old else []
        for p in new[:50]:
            self.f.db.insert("listing_events", {"ts": _now(), "product_id": "DOCS", "product_type": "cdp_docs",
                                                "event": "NEW_DOC_PAGE", "before": None, "after": p[:500]})
        self.f.db.kv_set("surface.docs_pages", sorted(pages))
        self.f.db.kv_set("surface.docs_hash", hashlib.sha256(txt.encode()).hexdigest()[:16])
        return len(new)

    # ---------------- economics from evidence
    def estimate_economics(self, capital: float, hurdle: float) -> None:
        from forge.research.stats import edge_posterior
        db = self.f.db
        # inference + compute spend (true cost), last 7 days, attributed to the research-heavy spot rail
        from datetime import timedelta
        cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()      # ISO vs ISO (never SQLite datetime())
        opex = float(db.scalar("SELECT COALESCE(SUM(ABS(CAST(amount_usd AS REAL))),0) FROM ledger_entries "
                               "WHERE account LIKE 'OPEX:%' AND ts >= ?", (cutoff,)) or 0.0)
        spot = self.rails.get("coinbase.spot")
        if spot:
            real = [r for r in db.query("SELECT realized_pnl_usd, fees_usd, cost_usd, opened_at, closed_at FROM positions "
                                        "WHERE status='CLOSED' AND CAST(cost_usd AS REAL) > 0")]
            rets = [(float(r["realized_pnl_usd"]) - float(r["fees_usd"])) / float(r["cost_usd"]) for r in real]
            hold_d = 2.0
            if rets:
                post = edge_posterior(__import__("numpy").array(rets))
                e, p, ev = float(sum(rets) / len(rets)), float(post["p_positive"]), f"{len(rets)} closed positions (paper/live)"
            else:
                e, p, ev = 0.0, 0.0, "no closed positions yet"
            spot.economics = RailEconomics(expected_return=e, probability=p, cycle_days=hold_d, liquidity=1.0,
                                           compute_usd_day=abs(opex) / 7.0, capacity_usd=capital, evidence=ev)
        k = self.rails.get("kalshi.events")
        if k:
            rows = db.query("SELECT price, fee, pnl, close_ts, ts FROM crossrail_signals WHERE status='SETTLED' "
                            "AND kind IN ('TAKE_THRESH')")
            if rows:
                import numpy as np
                r = np.array([x["pnl"] / max(x["price"] + x["fee"], 1e-6) for x in rows])
                post = edge_posterior(r)
                cyc = float(np.mean([max(x["close_ts"] - x["ts"], 60) for x in rows])) / 86400
                k.economics = RailEconomics(expected_return=float(r.mean()), probability=float(post["p_positive"]),
                                            cycle_days=max(cyc, 1 / 96), liquidity=0.5, lockup_days=2.0,
                                            capacity_usd=min(capital, 50.0),
                                            evidence=f"{len(rows)} settled shadow signals (net of Kalshi fees)")
            else:
                k.economics = RailEconomics(evidence="no settled shadow signals yet")
        for rid, r_ in self.rails.items():                       # generic: any rail with shadow round trips
            if rid in ("coinbase.spot", "kalshi.events"):
                continue
            rows = db.query("SELECT pnl_usd, entry, qty, hold_s FROM shadow_trades WHERE rail = ?", (rid,))
            if rows:
                import numpy as np
                rr = np.array([x["pnl_usd"] / max(x["entry"] * x["qty"], 1e-9) for x in rows])
                post = edge_posterior(rr)
                hold = float(np.mean([max(x["hold_s"], 60) for x in rows])) / 86400
                r_.economics = RailEconomics(expected_return=float(rr.mean()), probability=float(post["p_positive"]),
                                             cycle_days=max(hold, 1 / 288), liquidity=0.7, capacity_usd=capital,
                                             evidence=f"{len(rows)} shadow round trips (queue-aware fills, net of fees)")
        y = self.rails.get("coinbase.usdc_rewards")
        if y:
            apy = self.f.db.kv_get("config.usdc_reward_apy_verified")
            mem = self.f.db.kv_get("membership.coinbase_one") or {}
            rate = float(apy or mem.get("usdc_reward_apy") or 0.0)
            y.economics = RailEconomics(expected_return=rate / 365, probability=0.95 if (apy or mem.get("tier")) else 0.5,
                                        cycle_days=1.0, capacity_usd=capital,
                                        evidence=("operator-verified rate" if apy else
                                                  f"Coinbase One {mem.get('tier', '?')} member, advertised {rate:.2%} APY "
                                                  "(confirm from first posted reward)"))

    def _has_table(self, name: str) -> bool:
        return bool(self.f.db.scalar("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)))

    # ---------------- persistence
    def persist(self) -> None:
        now = _now()
        for r in self.rails.values():
            self.f.db.execute(
                "INSERT INTO rail_registry(id, provider, category, status, executable, blockers, capabilities, economics, "
                "first_seen, last_probe) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
                "executable=excluded.executable, blockers=excluded.blockers, capabilities=excluded.capabilities, "
                "economics=excluded.economics, last_probe=excluded.last_probe",
                (r.id, r.provider, r.category, r.status, int(r.executable), json.dumps(r.blockers),
                 json.dumps(r.capabilities, default=str), json.dumps(asdict(r.economics)), now, now))
            self.f.db.insert("rail_probes", {"ts": now, "rail_id": r.id, "ok": 1, "status": r.status,
                                             "summary": json.dumps(r.capabilities, default=str)[:2000]})
            self.f.db.execute("INSERT INTO venue_catalog(id, provider, category, status, data, updated_at) VALUES (?,?,?,?,?,?) "
                              "ON CONFLICT(id) DO UPDATE SET status=excluded.status, data=excluded.data, updated_at=excluded.updated_at",
                              (r.id, r.provider, r.category, r.status,
                               json.dumps({"id": r.id, "provider": r.provider, "category": r.category, "status": r.status,
                                           "needs": "; ".join(r.blockers) or "—", "edge": r.economics.evidence,
                                           "capabilities": r.capabilities}, default=str), now))

    async def cycle(self) -> dict[str, Any]:
        heavy = time.time() - self.last_heavy > self.HEAVY_PROBE_S
        account = await self.probe_account()
        await self.probe_spot()
        await self.probe_futures(account)
        types = await self.probe_product_types() if heavy else (self.f.db.kv_get("surface.product_types") or {})
        await self.probe_equity(heavy)
        await self.probe_prediction(types, account)
        await self.probe_kalshi()
        self.static_rails(account)
        if heavy:
            await self.diff_docs()
            self.last_heavy = time.time()
            self.f.db.kv_set("surface.last_heavy", self.last_heavy)
        eq = float(self.f.treasury.get("equity_usd") or 0) or 1.0
        hurdle = float(self.f.hurdle.hurdle(1.0)) * 24.0 if hasattr(self.f, "hurdle") else 0.0   # per hour → per day
        hurdle = hurdle if math.isfinite(hurdle) else 0.0
        self.estimate_economics(eq, hurdle)
        self.persist()
        rails = list(self.rails.values())
        now_plan = allocate(rails, eq, hurdle)
        unlocked = allocate(rails, eq, hurdle, include_blocked=True)
        unlock = []
        for r in rails:
            if r.executable or r.economics.probability <= 0:
                continue
            s = r.economics.score_per_day(eq, hurdle)
            if s > 0:
                unlock.append({"rail": r.id, "usd_per_day_if_unblocked": s * min(eq, r.economics.capacity_usd or eq),
                               "blockers": r.blockers, "evidence": r.economics.evidence})
        self.bill_membership()
        mem = self.f.db.kv_get("membership.coinbase_one") or {}
        fixed_day = float(mem.get("incremental_cost_to_forge_usd_month") or 0) * 12 / 365
        rep = {"ts": time.time(), "capital": eq, "hurdle_per_day": hurdle, "now": now_plan, "if_unblocked": unlocked,
               "fixed_costs_usd_per_day": {"coinbase_one": fixed_day},
               "net_expected_usd_per_day": now_plan["expected_usd_per_day"] - fixed_day,
               "unlock_value": sorted(unlock, key=lambda x: -x["usd_per_day_if_unblocked"]),
               "rails": {r.id: {"status": r.status, "executable": r.executable, "blockers": r.blockers,
                                "score_per_day": r.economics.score_per_day(eq, hurdle), "evidence": r.economics.evidence}
                         for r in rails}}
        self.f.db.kv_set("surface.allocation", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("surface")
            try:
                await asyncio.wait_for(self.cycle(), timeout=600)
            except Exception as e:
                log.warning("surface cycle failed: %s", e)
            await asyncio.sleep(self.PROBE_S)


# ------------------------------------------------------------------ Listing Sentinel (answers §16)
class ListingSentinel:
    """Diffs the Coinbase product universe every 60 s (SPOT + FUTURE): new products, status / trading-flag changes,
    delistings → listing_events + timeline. It never buys blindly; events feed LISTING_DISCOVERY research."""

    INTERVAL_S = 60

    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.snap: dict[str, tuple[str, bool, bool, bool]] = {}

    @staticmethod
    def diff(old: dict[str, tuple[str, bool, bool, bool]], new: dict[str, tuple[str, bool, bool, bool]]) -> list[tuple[str, str, Any, Any]]:
        ev = []
        if not old:
            return ev
        for pid, st in new.items():
            if pid not in old:
                ev.append((pid, "NEW_PRODUCT", None, st))
            elif old[pid] != st:
                kind = "STATUS_CHANGE"
                if old[pid][1] and not st[1]:
                    kind = "TRADING_ENABLED"
                elif not old[pid][1] and st[1]:
                    kind = "TRADING_DISABLED"
                ev.append((pid, kind, old[pid], st))
        for pid in old.keys() - new.keys():
            ev.append((pid, "DELISTED", old[pid], None))
        return ev

    async def tick(self) -> int:
        new: dict[str, tuple[str, bool, bool, bool]] = {}
        types: dict[str, str] = {}
        for t in ("SPOT", "FUTURE"):
            d = await self.f.rest._request("GET", "/api/v3/brokerage/market/products",
                                           params={"product_type": t, "limit": 1000}, retries=1)
            for p in d.get("products", []):
                new[p["product_id"]] = (p.get("status", ""), bool(p.get("trading_disabled")), bool(p.get("limit_only")),
                                        bool(p.get("cancel_only")))
                types[p["product_id"]] = t
        evs = self.diff(self.snap, new)
        await self._listing_shadow(evs, types)
        for pid, kind, before, after in evs:
            self.f.db.insert("listing_events", {"ts": _now(), "product_id": pid, "product_type": types.get(pid),
                                                "event": kind, "before": json.dumps(before), "after": json.dumps(after)})
            if kind in ("NEW_PRODUCT", "TRADING_ENABLED"):
                await self.f.say("Listing Sentinel", f"{kind.replace('_', ' ').title()}: {pid} ({types.get(pid)}) — "
                                                     "recorded for listing-discovery research (no blind buying)")
        if len(new) > 50:
            self.snap = new
        return len(evs)

    async def _listing_shadow(self, evs: list[tuple[str, str, Any, Any]], types: dict[str, str]) -> None:
        """LISTING_DISCOVERY_V1 shadow: taker entry at the first traded price after a listing/re-enable, exits at
        +1h/+4h/+24h net of taker fees both ways → shadow_trades (rail coinbase.listing_discovery). No blind buying live."""
        pend = self.f.db.kv_get("listing.shadow") or []
        for pid, kind, _, _ in evs:
            if kind in ("NEW_PRODUCT", "TRADING_ENABLED") and types.get(pid) == "SPOT" and pid.endswith("-USD"):
                pend.append({"pid": pid, "t0": time.time(), "px0": None, "done": []})
        now = time.time()
        fee = float(getattr(getattr(self.f, "fees", None), "taker", 0.009) or 0.009)
        keep = []
        for p in pend[-200:]:
            try:
                px = float((await self.f.rest.product(p["pid"])).get("price") or 0)
            except Exception:
                px = 0.0
            if p["px0"] is None:
                if px > 0:
                    p["px0"], p["t_entry"] = px, now
                elif now - p["t0"] > 6 * 3600:
                    continue
                keep.append(p)
                continue
            for h in (1, 4, 24):
                if h not in p["done"] and now - p["t_entry"] >= h * 3600 and px > 0:
                    entry, exit_ = p["px0"] * (1 + fee), px * (1 - fee)
                    self.f.db.insert("shadow_trades", {"ts": now, "rail": "coinbase.listing_discovery", "symbol": p["pid"],
                                                       "side": f"hold_{h}h", "qty": 1.0 / entry, "entry": entry, "exit": exit_,
                                                       "fee_usd": fee * 2 / entry, "pnl_usd": exit_ / entry - 1.0,
                                                       "hold_s": h * 3600.0, "detail": None})
                    p["done"].append(h)
            if len(p["done"]) < 3:
                keep.append(p)
        self.f.db.kv_set("listing.shadow", keep)

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("listing_sentinel")
            try:
                await asyncio.wait_for(self.tick(), timeout=45)
            except Exception as e:
                log.debug("listing sentinel: %s", e)
            await asyncio.sleep(self.INTERVAL_S)
