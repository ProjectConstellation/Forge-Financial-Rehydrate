"""Paper Event Desk — fake-money sports/event bets driven by Odds API intelligence.

PAPER ONLY. No real sportsbook or Kalshi orders.
Intelligence: multi-book de-vigged consensus vs best available price; skip blind favorites and blind longshots.
Vast portfolio: many small uncorrelated stakes across sports; settle from official scores feed.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from forge.core.ids import new_id
from forge.intel.devig import binary_kelly, consensus_h2h, edge_ok

log = logging.getLogger("forge.paper_bets")

# Free-tier: few sports, cache hard
SPORTS = (
    "americanfootball_nfl",
    "americanfootball_ncaaf",
    "basketball_nba",
    "basketball_ncaab",
    "icehockey_nhl",
    "baseball_mlb",
    "soccer_epl",
    "soccer_usa_mls",
)
BANKROLL_START = 400.0  # founder operating band $200–$500
MAX_STAKE_PCT = 0.06  # still small per-bet; book stays diversified
MIN_STAKE = 2.0
MAX_OPEN = 12  # vast ≠ oversized; fit $200–$500 book
MIN_BOOKS = 5
MIN_HOURS_TO_START = 0.5
MAX_HOURS_TO_START = 72.0
ODDS_CACHE_S = 600


class PaperBetDesk:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self._ensure()

    def _ensure(self) -> None:
        self.f.db.execute(
            """CREATE TABLE IF NOT EXISTS paper_bets (
                id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                sport TEXT NOT NULL,
                event_id TEXT NOT NULL,
                commence_ts REAL,
                home TEXT,
                away TEXT,
                selection TEXT NOT NULL,
                side TEXT NOT NULL,
                decimal_odds REAL NOT NULL,
                implied_q REAL NOT NULL,
                p_hat REAL NOT NULL,
                edge REAL NOT NULL,
                stake_usd REAL NOT NULL,
                status TEXT NOT NULL,
                pnl_usd REAL,
                settled_ts REAL,
                detail TEXT
            )"""
        )
        self.f.db.execute("CREATE INDEX IF NOT EXISTS idx_paper_bets_status ON paper_bets(status)")
        self.f.db.execute("CREATE INDEX IF NOT EXISTS idx_paper_bets_event ON paper_bets(event_id)")
        bank = self.f.db.kv_get("paper_bets.bankroll")
        if not bank:
            self.f.db.kv_set("paper_bets.bankroll", {
                "cash": BANKROLL_START, "start": BANKROLL_START, "ts": time.time(),
                "note": "PAPER event desk — simulated money only",
            })

    def _key(self) -> str:
        return os.environ.get("THE_ODDS_API_KEY") or ""

    def _get(self, url: str) -> Any:
        req = urllib.request.Request(url, headers={"User-Agent": "ImagineForge/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            remaining = r.headers.get("x-requests-remaining")
            if remaining is not None:
                self.f.db.kv_set("intel.odds_quota", {
                    "ts": time.time(), "remaining": remaining,
                    "used": r.headers.get("x-requests-used"),
                })
            return json.loads(r.read().decode())

    def _bank(self) -> dict[str, Any]:
        return self.f.db.kv_get("paper_bets.bankroll") or {"cash": BANKROLL_START, "start": BANKROLL_START}

    def _set_bank(self, cash: float, **extra: Any) -> None:
        b = self._bank()
        b.update(extra)
        b["cash"] = round(cash, 4)
        b["ts"] = time.time()
        self.f.db.kv_set("paper_bets.bankroll", b)

    def fetch_odds(self, sport: str) -> list[dict[str, Any]]:
        key = self._key()
        if not key:
            return []
        cache = self.f.db.kv_get(f"paper_bets.odds_cache.{sport}") or {}
        if cache.get("events") is not None and time.time() - float(cache.get("ts") or 0) < ODDS_CACHE_S:
            return cache["events"]
        url = (
            f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?"
            + urllib.parse.urlencode({
                "apiKey": key, "regions": "us,uk,eu", "markets": "h2h",
                "oddsFormat": "decimal",
            })
        )
        try:
            events = self._get(url) or []
        except Exception as e:
            log.warning("odds fetch %s: %s", sport, e)
            return cache.get("events") or []
        self.f.db.kv_set(f"paper_bets.odds_cache.{sport}", {"ts": time.time(), "events": events})
        return events

    def fetch_scores(self, sport: str) -> list[dict[str, Any]]:
        key = self._key()
        if not key:
            return []
        url = (
            f"https://api.the-odds-api.com/v4/sports/{sport}/scores/?"
            + urllib.parse.urlencode({"apiKey": key, "daysFrom": 3})
        )
        try:
            return self._get(url) or []
        except Exception as e:
            log.warning("scores %s: %s", sport, e)
            return []

    def _parse_event(self, sport: str, ev: dict[str, Any]) -> dict[str, Any] | None:
        home, away = ev.get("home_team"), ev.get("away_team")
        if not home or not away:
            return None
        quotes = []
        for b in ev.get("bookmakers") or []:
            for m in b.get("markets") or []:
                if m.get("key") != "h2h":
                    continue
                odds = {o.get("name"): float(o.get("price") or 0) for o in (m.get("outcomes") or [])}
                if home in odds and away in odds:
                    quotes.append({"book": b.get("key"), "home_odds": odds[home], "away_odds": odds[away]})
        cons = consensus_h2h(quotes)
        if not cons or cons["n_books"] < MIN_BOOKS:
            return None
        commence = ev.get("commence_time") or ""
        try:
            import datetime as dt
            cts = dt.datetime.fromisoformat(commence.replace("Z", "+00:00")).timestamp()
        except Exception:
            cts = time.time() + 3600
        hours = (cts - time.time()) / 3600
        if hours < MIN_HOURS_TO_START or hours > MAX_HOURS_TO_START:
            return None
        return {
            "sport": sport, "event_id": ev.get("id"), "home": home, "away": away,
            "commence_ts": cts, "hours": hours, "consensus": cons,
        }

    def scan_edges(self) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        for sport in SPORTS:
            for ev in self.fetch_odds(sport):
                parsed = self._parse_event(sport, ev)
                if not parsed:
                    continue
                c = parsed["consensus"]
                for side, sel, best, p_hat in (
                    ("home", parsed["home"], c["best_home"], c["p_home"]),
                    ("away", parsed["away"], c["best_away"], c["p_away"]),
                ):
                    q = best.get("q")
                    ok, reason, edge = edge_ok(p_hat, q or 0.0, c["dispersion"])
                    if not ok:
                        continue
                    edges.append({
                        **parsed,
                        "side": side, "selection": sel,
                        "decimal_odds": best["odds"], "book": best["book"],
                        "implied_q": q, "p_hat": p_hat, "edge": edge,
                        "gate": reason, "n_books": c["n_books"],
                        "dispersion": c["dispersion"],
                    })
            time.sleep(1.2)  # free-tier politeness between sports
        edges.sort(key=lambda e: (-e["edge"], -e["p_hat"]))
        return edges

    def _already_on_event(self, event_id: str) -> bool:
        return bool(self.f.db.scalar(
            "SELECT 1 FROM paper_bets WHERE event_id=? AND status='OPEN'", (event_id,)
        ))

    def place(self, edge: dict[str, Any]) -> dict[str, Any] | None:
        bank = self._bank()
        cash = float(bank.get("cash") or 0)
        open_n = int(self.f.db.scalar("SELECT COUNT(*) FROM paper_bets WHERE status='OPEN'") or 0)
        if open_n >= MAX_OPEN or cash < MIN_STAKE:
            return None
        if self._already_on_event(edge["event_id"]):
            return None
        kelly = binary_kelly(edge["p_hat"], edge["decimal_odds"], fraction=0.125)
        stake = max(MIN_STAKE, min(cash * MAX_STAKE_PCT, cash * kelly, 20.0, cash * 0.08))
        stake = round(stake, 2)
        if stake < MIN_STAKE:
            return None
        bid = new_id("pbet")
        detail = {
            "book": edge["book"], "gate": edge["gate"], "n_books": edge["n_books"],
            "dispersion": edge["dispersion"], "hours_to_start": edge["hours"],
            "intelligence": "de-vig consensus vs best price; PAPER only",
        }
        self.f.db.insert("paper_bets", {
            "id": bid, "ts": time.time(), "sport": edge["sport"], "event_id": edge["event_id"],
            "commence_ts": edge["commence_ts"], "home": edge["home"], "away": edge["away"],
            "selection": edge["selection"], "side": edge["side"],
            "decimal_odds": edge["decimal_odds"], "implied_q": edge["implied_q"],
            "p_hat": edge["p_hat"], "edge": edge["edge"], "stake_usd": stake,
            "status": "OPEN", "pnl_usd": None, "settled_ts": None,
            "detail": json.dumps(detail),
        })
        self._set_bank(cash - stake)
        # Evidence rail
        try:
            self.f.db.insert("shadow_trades", {
                "ts": time.time(), "rail": "odds.paper_h2h", "symbol": f"{edge['sport']}:{edge['selection']}",
                "side": edge["side"], "qty": stake, "entry": edge["decimal_odds"],
                "exit": None, "fee_usd": 0.0, "pnl_usd": None, "hold_s": None,
                "detail": json.dumps({"bet_id": bid, "p_hat": edge["p_hat"], "edge": edge["edge"]}),
            })
        except Exception:
            pass
        return {"id": bid, "stake": stake, "selection": edge["selection"], "edge": edge["edge"], "p_hat": edge["p_hat"]}

    def settle(self) -> list[dict[str, Any]]:
        open_rows = self.f.db.query("SELECT * FROM paper_bets WHERE status='OPEN'") or []
        if not open_rows:
            return []
        by_sport: dict[str, list] = {}
        for r in open_rows:
            by_sport.setdefault(r["sport"], []).append(dict(r))
        settled: list[dict[str, Any]] = []
        bank = self._bank()
        cash = float(bank.get("cash") or 0)
        for sport, rows in by_sport.items():
            scores = {s.get("id"): s for s in self.fetch_scores(sport)}
            time.sleep(1.0)
            for bet in rows:
                sc = scores.get(bet["event_id"])
                if not sc or not sc.get("completed"):
                    continue
                score_map = {x.get("name"): int(x.get("score") or 0) for x in (sc.get("scores") or [])}
                hs, aws = score_map.get(bet["home"]), score_map.get(bet["away"])
                if hs is None or aws is None:
                    continue
                if hs == aws:
                    status, pnl = "PUSH", 0.0
                    cash += float(bet["stake_usd"])
                else:
                    won = (bet["side"] == "home" and hs > aws) or (bet["side"] == "away" and aws > hs)
                    if won:
                        status = "WON"
                        payout = float(bet["stake_usd"]) * float(bet["decimal_odds"])
                        pnl = payout - float(bet["stake_usd"])
                        cash += payout
                    else:
                        status, pnl = "LOST", -float(bet["stake_usd"])
                self.f.db.execute(
                    "UPDATE paper_bets SET status=?, pnl_usd=?, settled_ts=? WHERE id=?",
                    (status, pnl, time.time(), bet["id"]),
                )
                settled.append({"id": bet["id"], "status": status, "pnl": pnl, "selection": bet["selection"]})
                try:
                    self.f.db.insert("shadow_trades", {
                        "ts": time.time(), "rail": "odds.paper_h2h", "symbol": f"{bet['sport']}:{bet['selection']}",
                        "side": "settle", "qty": bet["stake_usd"], "entry": bet["decimal_odds"],
                        "exit": 1.0 if status == "WON" else (0.0 if status == "LOST" else 0.5),
                        "fee_usd": 0.0, "pnl_usd": pnl, "hold_s": time.time() - float(bet["ts"]),
                        "detail": json.dumps({"bet_id": bet["id"], "status": status}),
                    })
                except Exception:
                    pass
        if settled:
            self._set_bank(cash)
        return settled

    def equity_sleeve(self) -> dict[str, Any]:
        """Twelve Data cross-sectional PAPER sleeve — features only, tiny shadow notionals."""
        tw = self.f.db.kv_get("intel.twelve_data") or {}
        quotes = tw.get("quotes") or {}
        spy = (quotes.get("SPY") or {}).get("change_pct")
        out = {"ts": time.time(), "signals": [], "status": tw.get("status")}
        if spy is None or not quotes:
            self.f.db.kv_set("lab.equity_sleeve", out)
            return out
        rel = []
        for sym, q in quotes.items():
            if sym == "SPY" or q.get("change_pct") is None:
                continue
            rel.append((sym, float(q["change_pct"]) - float(spy), q.get("price")))
        rel.sort(key=lambda x: -x[1])
        # Long relative strength leader if beating SPY by ≥0.4%
        for sym, alpha, px in rel[:2]:
            if alpha < 0.4:
                continue
            sig = {"symbol": sym, "alpha_vs_spy": alpha, "price": px, "action": "PAPER_OBSERVE_LONG",
                   "note": "not a blind buy — relative strength feature for equity PAPER research"}
            out["signals"].append(sig)
            try:
                self.f.db.insert("shadow_trades", {
                    "ts": time.time(), "rail": "twelve.equity_paper", "symbol": f"{sym}-USD",
                    "side": "observe", "qty": 25.0, "entry": float(px or 0), "exit": None,
                    "fee_usd": 0.0, "pnl_usd": 0.0, "hold_s": 0,
                    "detail": json.dumps(sig),
                })
            except Exception:
                pass
        # Also mark laggards
        for sym, alpha, px in rel[-2:]:
            if alpha > -0.4:
                continue
            out["signals"].append({"symbol": sym, "alpha_vs_spy": alpha, "price": px, "action": "PAPER_OBSERVE_AVOID"})
        self.f.db.kv_set("lab.equity_sleeve", out)
        return out

    def tick(self) -> dict[str, Any]:
        if not self._key():
            rep = {"ts": time.time(), "status": "blocked_no_key", "placed": [], "settled": []}
            self.f.db.kv_set("lab.paper_bets", rep)
            return rep
        settled = self.settle()
        edges = self.scan_edges()
        placed = []
        # Vast but selective: take top edges across sports, one per event
        seen_sport = {}
        for e in edges:
            sp = e["sport"]
            seen_sport[sp] = seen_sport.get(sp, 0)
            if seen_sport[sp] >= 3:  # breadth across sports
                continue
            bet = self.place(e)
            if bet:
                placed.append({**bet, "sport": sp, "gate": e["gate"]})
                seen_sport[sp] += 1
            if len(placed) >= 4:  # per tick cap (small book)
                break
        eq = self.equity_sleeve()
        bank = self._bank()
        open_n = int(self.f.db.scalar("SELECT COUNT(*) FROM paper_bets WHERE status='OPEN'") or 0)
        won = int(self.f.db.scalar("SELECT COUNT(*) FROM paper_bets WHERE status='WON'") or 0)
        lost = int(self.f.db.scalar("SELECT COUNT(*) FROM paper_bets WHERE status='LOST'") or 0)
        pnl = float(self.f.db.scalar("SELECT COALESCE(SUM(pnl_usd),0) FROM paper_bets WHERE status IN ('WON','LOST','PUSH')") or 0)
        rep = {
            "ts": time.time(),
            "status": "ok",
            "bankroll": bank,
            "equity_usd": float(bank.get("cash") or 0) + sum(
                float(r["stake_usd"]) for r in (self.f.db.query(
                    "SELECT stake_usd FROM paper_bets WHERE status='OPEN'") or [])
            ),
            "open": open_n, "won": won, "lost": lost, "realized_pnl": pnl,
            "edges_found": len(edges), "placed": placed, "settled": settled,
            "top_edges": [
                {"sport": e["sport"], "selection": e["selection"], "p_hat": round(e["p_hat"], 3),
                 "edge": round(e["edge"], 3), "odds": e["decimal_odds"], "gate": e["gate"]}
                for e in edges[:8]
            ],
            "equity_sleeve": eq,
            "policy": {
                "mode": "PAPER_ONLY",
                "intelligence": "de-vig multi-book consensus vs best price; favorites-with-value preferred",
                "min_books": MIN_BOOKS,
                "kelly_fraction": 0.125,
                "max_stake_pct": MAX_STAKE_PCT,
            },
        }
        self.f.db.kv_set("lab.paper_bets", rep)
        # Wake officers when we placed or found fat edges
        if placed or any(e["edge"] >= 0.06 for e in edges[:3]):
            try:
                self.f.db.kv_set("paper_bets.wake", {"ts": time.time(), "placed": len(placed), "edges": len(edges)})
                now = time.time()
                if placed:
                    top = "; ".join(f"{p['selection']} edge={p['edge']:.1%}" for p in placed[:3])
                    self.f.db.execute(
                        "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                        (now, "scout",
                         f"PAPER bet desk placed {len(placed)} intelligent bets. Review odds consensus + CLV. Top: {top}",
                         "high", "OPEN", "paper_bets"),
                    )
                    self.f.db.execute(
                        "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                        (now, "adversary",
                         f"Vale/Ada risk: red-team {len(placed)} new PAPER event bets — vig trap? correlated books? stale line?",
                         "high", "OPEN", "paper_bets"),
                    )
                    self.f.db.execute(
                        "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                        (now, "governor",
                         f"Cyrus/Ellis: Event PAPER open≈{open_n+len(placed)} realized_pnl=${pnl:.2f}. Shift marginal $ if +EV vs spot drains.",
                         "high", "OPEN", "paper_bets"),
                    )
            except Exception as e:
                log.debug("directives: %s", e)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("paper_bets")
            try:
                rep = await asyncio.to_thread(self.tick)
                placed = rep.get("placed") or []
                settled = rep.get("settled") or []
                if placed:
                    bits = "; ".join(
                        f"{p.get('selection')}@{float(p.get('edge') or 0):.0%}" for p in placed[:3]
                    )
                    await self.f.say(
                        "Paper Bet Desk",
                        f"Placed {len(placed)} PAPER bets (sim money) on de-vigged edges. "
                        f"Bank ${float((rep.get('bankroll') or {}).get('cash') or 0):.0f} | open {rep.get('open')} | {bits}",
                        level="info",
                    )
                if settled:
                    bits = ", ".join(
                        f"{s.get('selection')} {s.get('status')} ({float(s.get('pnl') or 0):+.2f})"
                        for s in settled[:4]
                    )
                    await self.f.say("Paper Bet Desk", f"Settled {len(settled)}: {bits}", level="info")
            except Exception as e:
                log.warning("paper_bets: %s", e, exc_info=True)
            await asyncio.sleep(900)
